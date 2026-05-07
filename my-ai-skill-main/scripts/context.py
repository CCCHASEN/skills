#!/usr/bin/env python3
"""
Context Log 管理与话题切换检测

话题检测采用三重信号融合：
1. TF-IDF 加权关键词重叠（区分通用词与话题核心词）
2. 滑动窗口衰减（早期轮次贡献逐渐降低）
3. ChromaDB 向量余弦相似度（捕捉语义层面的话题漂移）
"""

import json
import math
import re
from collections import Counter
from datetime import datetime
from pathlib import Path

import jieba
from chromadb.utils import embedding_functions

from config import (
    JOURNAL_DIR, CONTEXT_LOG_MD,
    CONTEXT_LOG_MAX_TOKENS, CONTEXT_LOG_FLUSH_THRESHOLD,
    _TOPIC_STOPWORDS, _TOPIC_STATE_FILE
)
from utils import _sanitize_text, estimate_tokens_fast, run_script

# ======= Embedding 缓存（用于向量距离话题检测） =======
_EMB_CACHE_FILE = Path(__file__).parent.parent / "memory" / ".query_embeds.json"
_embedding_fn = embedding_functions.DefaultEmbeddingFunction()


def _load_embed_cache():
    if _EMB_CACHE_FILE.exists():
        try:
            return json.loads(_EMB_CACHE_FILE.read_text(encoding="utf-8"))
        except:
            pass
    return {"queries": []}  # [{"text": ..., "emb": [...], "turn": ...}]


def _save_embed_cache(cache):
    _EMB_CACHE_FILE.write_text(json.dumps(cache, ensure_ascii=False), encoding="utf-8")


def _cosine_similarity(a, b):
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def _get_query_embedding(text):
    """获取 query 的 embedding 向量"""
    try:
        emb = _embedding_fn([text])
        return emb[0].tolist() if hasattr(emb[0], 'tolist') else list(emb[0])
    except Exception:
        return None


# ======= Context Log 系统 =======

def append_context_log(user_msg, assistant_reply, thinking="", tools_used=None, files_modified=None):
    """
    将一轮对话实时追加到 Context Log（纯粹上下文缓冲区）
    """
    JOURNAL_DIR.mkdir(parents=True, exist_ok=True)
    
    turn_num = 1
    if CONTEXT_LOG_MD.exists():
        content = CONTEXT_LOG_MD.read_text(encoding="utf-8")
        turn_matches = re.findall(r'Turn (\d+)', content)
        if turn_matches:
            turn_num = max(int(m) for m in turn_matches) + 1
    
    user_msg = _sanitize_text(user_msg)
    assistant_reply = _sanitize_text(assistant_reply)
    thinking = _sanitize_text(thinking)
    
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    entry = f"\n## [{timestamp}] Turn {turn_num}\n"
    entry += f"**User**: {user_msg.strip()}\n"
    if thinking:
        entry += f"**Thinking**: {thinking.strip()}\n"
    entry += f"**Assistant**: {assistant_reply.strip()}\n"
    if tools_used:
        entry += f"**Tools**: {', '.join(tools_used)}\n"
    if files_modified:
        entry += f"**Files**: {', '.join(files_modified)}\n"
    entry += "\n"
    
    if turn_num == 1:
        header = f"# Context Log — {datetime.now().strftime('%Y-%m-%d')}\n\n"
        entry = header + entry
    
    with open(CONTEXT_LOG_MD, "a", encoding="utf-8") as f:
        f.write(entry)
    
    return turn_num


def read_context_log(limit=20):
    """读取 Context Log 的最近 N 轮"""
    if not CONTEXT_LOG_MD.exists():
        return []
    
    content = CONTEXT_LOG_MD.read_text(encoding="utf-8")
    if not content.strip():
        return []
    
    turns = []
    pattern = r'## \[(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\] Turn (\d+)\n(.*?)\n(?=## \[|$)'
    matches = list(re.finditer(pattern, content, re.DOTALL))
    
    for m in matches:
        timestamp = m.group(1)
        turn_num = int(m.group(2))
        body = m.group(3)
        
        turn = {"turn": turn_num, "timestamp": timestamp}
        for field in ["User", "Thinking", "Assistant", "Tools", "Files"]:
            field_pattern = rf'\*\*{field}\*\*: (.*?)(?=\n\*\*|\n$|$)'
            field_match = re.search(field_pattern, body, re.DOTALL)
            if field_match:
                turn[field.lower()] = field_match.group(1).strip()
        
        turns.append(turn)
    
    turns.sort(key=lambda x: x["turn"])
    return turns[-limit:] if limit else turns


def get_context_log_stats():
    """获取 Context Log 统计"""
    if not CONTEXT_LOG_MD.exists():
        return {"turns": 0, "tokens": 0, "exists": False}
    
    content = CONTEXT_LOG_MD.read_text(encoding="utf-8")
    turns = content.count("## [")
    tokens = estimate_tokens_fast(content)
    
    return {"turns": turns, "tokens": tokens, "exists": True, "path": str(CONTEXT_LOG_MD)}


def flush_context_log(reason=""):
    """将 Context Log 内容提取到 Memory，然后归档"""
    if not CONTEXT_LOG_MD.exists():
        return {"flushed": False, "reason": "no_context_log"}
    
    content = CONTEXT_LOG_MD.read_text(encoding="utf-8")
    turns = read_context_log(limit=None)
    
    if len(turns) < 5:
        return {"flushed": False, "reason": "not_enough_turns", "turns": len(turns)}
    
    report = {
        "flushed_at": datetime.now().isoformat(),
        "flush_reason": reason,
        "total_turns": len(turns),
        "promoted_to_knowledge": 0,
        "promoted_to_active": 0,
        "archived": False,
        "kept_for_continuity": 0
    }
    
    # 分析每轮并提取重要内容（保留最后5轮不处理）
    for turn in turns[:-5]:
        combined = f"{turn.get('user', '')} {turn.get('assistant', '')}"
        if not combined.strip():
            continue
        
        importance = _quick_importance_score(combined)
        
        has_action_items = any(s in combined.lower() for s in [
            "待办", "todo", "任务", "task", "下一步", "next step",
            "阻塞", "blocked", "问题", "issue", "bug"
        ])
        
        has_decisions = any(s in combined.lower() for s in [
            "决定", "选择", "方案", "决策", "decision", "choose",
            "教训", "lesson", "错了", "纠正", "wrong", "correct"
        ])
        
        tags = f"flushed_from:context_log turn:{turn['turn']}"
        
        if importance >= 7 or has_decisions:
            report["promoted_to_knowledge"] += 1
        elif importance >= 5 or has_action_items:
            report["promoted_to_active"] += 1
        
        # 通过 memory_ops 写入向量库（避免循环导入，用 run_script）
        run_script("vector_memory.py", "add", combined[:500], tags)
    
    # 归档
    archive_date = datetime.now().strftime("%Y-%m-%d")
    archive_file = JOURNAL_DIR / f"{archive_date}.md"
    
    if archive_file.exists():
        with open(archive_file, "a", encoding="utf-8") as f:
            f.write(f"\n\n---\n\n{content}")
    else:
        with open(archive_file, "w", encoding="utf-8") as f:
            f.write(content)
    
    report["archived"] = True
    report["archive_path"] = str(archive_file)
    
    # 保留最近 5 轮作为上下文衔接
    recent_turns = turns[-5:]
    if recent_turns:
        new_header = f"# Context Log — {datetime.now().strftime('%Y-%m-%d')} (continued)\n\n"
        new_content = new_header
        for turn in recent_turns:
            new_content += f"## [{turn['timestamp']}] Turn {turn['turn']}\n"
            for field in ["User", "Thinking", "Assistant", "Tools", "Files"]:
                val = turn.get(field.lower(), "")
                if val:
                    new_content += f"**{field}**: {val}\n"
            new_content += "\n"
        
        with open(CONTEXT_LOG_MD, "w", encoding="utf-8") as f:
            f.write(new_content)
        report["kept_for_continuity"] = len(recent_turns)
    else:
        CONTEXT_LOG_MD.unlink(missing_ok=True)
    
    # 清空 embedding 缓存（flush 后话题已重置）
    if _EMB_CACHE_FILE.exists():
        _EMB_CACHE_FILE.unlink(missing_ok=True)
    
    return report


def _quick_importance_score(text):
    """快速本地重要性评分（无需 subprocess），1-10"""
    score = 3
    t = text.lower()
    
    # 用户显式指令
    if any(s in t for s in ["记住", "remember", "以后", "always", "prefer"]):
        score += 3
    
    # 纠正信号
    if any(s in t for s in ["错了", "纠正", "不对", "wrong", "correct", "shouldn't"]):
        score += 2
    
    # 决策信号
    if any(s in t for s in ["决定", "选择", "方案", "decision", "choose", "lesson", "教训"]):
        score += 2
    
    # 文件修改信号
    if any(s in t for s in [".py", ".js", ".ts", ".md", ".json", ".yaml", ".toml"]):
        score += 1
    
    # 长度信号
    if len(text) < 50:
        score -= 1
    elif len(text) > 300:
        score += 1
    
    return min(10, max(1, int(score)))


# ======= 话题切换检测（TF-IDF + 滑动窗口 + 向量距离） =======

def _load_topic_state():
    if _TOPIC_STATE_FILE.exists():
        try:
            return json.loads(_TOPIC_STATE_FILE.read_text(encoding="utf-8"))
        except:
            pass
    return {"streak": 0, "last_topic_keywords": [], "last_updated": ""}


def _save_topic_state(state):
    _TOPIC_STATE_FILE.write_text(json.dumps(state, ensure_ascii=False), encoding="utf-8")


def _extract_keywords(text):
    """提取关键词：lcut_for_search 返回子词 + 停用词过滤"""
    words = set(jieba.lcut_for_search(text.lower()))
    result = {w for w in words if len(w) > 1 and w not in _TOPIC_STOPWORDS}
    # 额外提取：如果文本中有自定义词表中的术语，确保被包含
    # 这帮助子话题（如"k线图"）与父话题（"股票"）建立弱关联
    return result


def _compute_tfidf_weights(recent_history, decay_rate=0.8):
    """
    计算会话主题中每个词的 TF-IDF 权重。
    
    - TF：词在当前轮用户消息中的出现频率
    - IDF：log(总轮数 / 包含该词的轮数 + 1) + 1
    - 滑动窗口衰减：越早的轮次权重越低
    
    返回: {word: weight}
    """
    n = len(recent_history)
    if n == 0:
        return {}
    
    # 每轮的关键词集合
    round_keywords = []
    for turn in recent_history:
        words = _extract_keywords(turn.get("user", ""))
        round_keywords.append(Counter(words))
    
    # 统计每个词出现在多少轮中
    doc_freq = Counter()
    all_words = set()
    for counter in round_keywords:
        for w in counter:
            doc_freq[w] += 1
            all_words.add(w)
    
    # 计算每个词的加权 TF-IDF
    weights = {}
    for word in all_words:
        tfidf_sum = 0.0
        for i, counter in enumerate(round_keywords):
            # 滑动窗口衰减：最近轮次权重最高
            window_weight = decay_rate ** (n - 1 - i)
            tf = counter.get(word, 0)
            if tf > 0:
                idf = math.log(n / (doc_freq[word] + 1)) + 1
                tfidf_sum += tf * idf * window_weight
        weights[word] = tfidf_sum
    
    return weights


def _detect_topic_shift(current_query, recent_history):
    """
    三重信号话题切换检测：TF-IDF 加权关键词 + 滑动窗口衰减 + 向量余弦相似度
    
    策略：
    - 综合偏离度 = 0.55 * (1 - keyword_sim) + 0.45 * (1 - vector_sim)
    - 综合偏离度 > 0.70 且 streak >= 1 → 话题切换
    - 综合偏离度 > 0.85 → 直接切换（无需 streak）
    - 有关键词重叠且 vector_sim >= 0.45 → 重置 streak
    
    返回: (is_shift, streak, details)
    """
    if not recent_history:
        return False, 0, {"keyword_sim": 1.0, "vector_sim": 1.0, "composite": 0.0}
    
    curr_words = _extract_keywords(current_query)
    if not curr_words:
        return False, 0, {"keyword_sim": 1.0, "vector_sim": 1.0, "composite": 0.0}
    
    # ===== 信号1: TF-IDF 加权关键词相似度 =====
    session_weights = _compute_tfidf_weights(recent_history, decay_rate=0.8)
    if not session_weights:
        keyword_sim = 0.0
    else:
        # 重叠词的加权权重
        overlap = curr_words & set(session_weights.keys())
        overlap_weight = sum(session_weights.get(w, 0) for w in overlap)
        # 当前查询中不在 session 中的词（惩罚项）
        curr_only = curr_words - set(session_weights.keys())
        curr_only_weight = sum(1.0 for w in curr_only)
        # 归一化：以当前查询为基准
        keyword_sim = overlap_weight / (overlap_weight + curr_only_weight + 1e-6)
        keyword_sim = min(1.0, keyword_sim)
    
    # ===== 信号2: 向量余弦相似度 =====
    has_vector_history = False
    vector_sim = 0.0
    emb_cache = _load_embed_cache()
    current_emb = _get_query_embedding(current_query)
    
    if current_emb and emb_cache["queries"]:
        # 与最近 3 个 query 比较
        sims = []
        for q in emb_cache["queries"][-3:]:
            if q.get("emb"):
                sims.append(_cosine_similarity(current_emb, q["emb"]))
        if sims:
            vector_sim = sum(sims) / len(sims)
            has_vector_history = True
    
    # 保存当前 query embedding
    if current_emb:
        emb_cache["queries"].append({
            "text": current_query[:200],
            "emb": current_emb,
            "turn": recent_history[-1].get("turn", 0) + 1 if recent_history else 1
        })
        # 只保留最近 10 个
        emb_cache["queries"] = emb_cache["queries"][-10:]
        _save_embed_cache(emb_cache)
    
    # ===== 综合偏离度 =====
    # 无向量历史时，降低向量权重，避免默认值干扰
    vector_weight = 0.45 if has_vector_history else 0.25
    keyword_weight = 1.0 - vector_weight
    composite_drift = keyword_weight * (1 - keyword_sim) + vector_weight * (1 - vector_sim)
    
    # ===== 状态机决策 =====
    state = _load_topic_state()
    
    # 强信号：直接切换（需 keyword_sim 极低、当前查询有足够多关键词、且向量也低）
    # 防止短查询（如2个词的子话题）被误判为强切换
    # 条件：composite > 0.85 AND 关键词数 >= 3 AND (无向量历史 OR 向量相似度 < 0.35)
    is_strong_drift = (
        composite_drift > 0.85 
        and len(curr_words) >= 3 
        and (not has_vector_history or vector_sim < 0.35)
    )
    if is_strong_drift:
        state["streak"] = 0
        state["last_topic_keywords"] = list(curr_words)[:50]
        state["last_updated"] = datetime.now().isoformat()
        _save_topic_state(state)
        return True, 0, {
            "keyword_sim": round(keyword_sim, 3),
            "vector_sim": round(vector_sim, 3),
            "composite": round(composite_drift, 3),
            "reason": "strong_drift"
        }
    
    # 同话题信号：重置 streak
    # - keyword_sim >= 0.15：有足够的关键词重叠
    # - 或有向量历史且 vector_sim >= 0.55：语义高度相似
    has_overlap = keyword_sim >= 0.15 or (has_vector_history and vector_sim >= 0.55)
    if has_overlap:
        state["streak"] = 0
        state["last_topic_keywords"] = list(curr_words)[:50]
        state["last_updated"] = datetime.now().isoformat()
        _save_topic_state(state)
        return False, 0, {
            "keyword_sim": round(keyword_sim, 3),
            "vector_sim": round(vector_sim, 3),
            "composite": round(composite_drift, 3),
            "reason": "overlap"
        }
    
    # 偏离信号：streak +1
    state["streak"] = state.get("streak", 0) + 1
    state["last_updated"] = datetime.now().isoformat()
    _save_topic_state(state)
    
    # 切换确认：连续2轮偏离，或综合偏离度极高
    is_shift = state["streak"] >= 2 or composite_drift > 0.82
    return is_shift, state["streak"], {
        "keyword_sim": round(keyword_sim, 3),
        "vector_sim": round(vector_sim, 3),
        "composite": round(composite_drift, 3),
        "reason": "deviation"
    }


def _should_flush_context_log(current_query=""):
    """
    动态 flush 决策：多信号融合
    
    触发条件（任一满足）：
    1. 话题切换（综合偏离度 > 0.70 且 streak >= 2，或 > 0.85 直接触发）
    2. 上下文 token 数超过阈值（4000）
    3. 轮数超过硬上限（40轮，保底）
    """
    stats = get_context_log_stats()
    if not stats["exists"]:
        return False, "no_log"
    
    # 信号1: 多轮话题切换检测
    if current_query:
        recent = read_context_log(limit=5)
        is_shift, streak, details = _detect_topic_shift(current_query, recent)
        if is_shift and len(recent) >= 5:
            _save_topic_state({"streak": 0, "last_topic_keywords": [], "last_updated": ""})
            # 清空 embedding 缓存
            if _EMB_CACHE_FILE.exists():
                _EMB_CACHE_FILE.unlink(missing_ok=True)
            return True, f"topic_shift (streak={streak}, composite={details['composite']})"
    
    # 信号2: Token 压力
    if stats["tokens"] >= CONTEXT_LOG_MAX_TOKENS:
        return True, "token_pressure"
    
    # 信号3: 轮数上限（保底）
    if stats["turns"] >= 40:
        return True, "turn_limit"
    
    return False, "none"
