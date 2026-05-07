#!/usr/bin/env python3
"""记忆操作：外部脚本封装、搜索、排序、图操作、数据库写入"""

import json
import math
import re
from datetime import datetime

import jieba

from config import SEMANTIC_DEDUP_THRESHOLD
from utils import run_script


# ======= 外部能力封装 =======

def extract_intent(query):
    output = run_script("extract.py", "intent", query)
    try:
        return json.loads(output)
    except:
        return {"primary": "WHAT", "strategy": "通用语义搜索"}


def extract_entities(text):
    output = run_script("extract.py", "entities", text)
    try:
        return json.loads(output)
    except:
        return []


def analyze_content(text):
    output = run_script("extract.py", "analyze", text)
    try:
        return json.loads(output)
    except:
        return {"entities": [], "keywords": [], "relations": [], "quality_score": 0}


def score_importance(text, files_modified=None):
    files_str = ",".join(files_modified) if files_modified else ""
    output = run_script("extract.py", "importance", text, files_str)
    try:
        return json.loads(output).get("importance", 5)
    except:
        return 5


def should_capture(text):
    """
    判断内容是否值得存入长期记忆。
    
    过滤策略（本地 heuristics + 外部模型）：
    1. 纯知识性问答（无用户个人信息/态度/要求）→ 过滤
    2. 用户明确要求记忆（"记住"、"以后"）→ 保留
    3. 用户观点/态度/偏好 → 保留
    4. 文件修改/技术决策 → 保留
    5. 闲聊/问候/简单确认 → 过滤
    """
    # 先跑外部模型判断
    output = run_script("extract.py", "should_capture", text)
    try:
        model_result = json.loads(output)
    except:
        model_result = {"should_capture": True, "reason": "fallback", "quality_score": 50}
    
    t = text.lower()
    
    # 强制保留信号（用户明确要求）
    if any(s in t for s in ["记住", "remember", "以后", "always", "prefer", "别忘了", "记一下"]):
        return {"should_capture": True, "reason": "user_explicit_request", "quality_score": 90}
    
    # 强制保留信号（用户观点/态度）
    opinion_signals = [
        "我觉得", "我认为", "我喜欢", "我讨厌", "我不想", "我希望",
        "我的看法", "我的观点", "我觉得", "i think", "i feel", "i like", "i hate",
        "i prefer", "i believe", "in my opinion", "我的态度", "我的立场"
    ]
    if any(s in t for s in opinion_signals):
        return {"should_capture": True, "reason": "user_opinion", "quality_score": 85}
    
    # 强制保留信号（人格/身份/偏好变更）
    identity_signals = [
        "改名叫", "你以后叫", "你叫", "你的名字", "你的人格", "你的性格",
        "说话风格", "说话方式", "角色", "扮演", "人设", "persona", "role",
        "以后都", "always", "prefer"
    ]
    if any(s in t for s in identity_signals):
        return {"should_capture": True, "reason": "identity_preference", "quality_score": 95}
    
    # 强制过滤信号（纯知识问答特征）
    knowledge_signals = [
        "什么是", "怎么", "如何", "为什么", "介绍", "解释", "说明",
        "什么是", "的定义", "的原理", "的历史", "的方法",
        "what is", "how to", "why does", "explain", "define", "describe"
    ]
    # 如果内容较长（>200字）且以疑问词开头，大概率是知识性问答
    if len(text) > 200:
        first_50 = t[:50]
        if any(s in first_50 for s in knowledge_signals):
            # 进一步检查：是否包含用户个人信息
            has_personal = any(s in t for s in ["我", "我的", "我家", "我爸", "我妈", "我哥", "我姐", "我朋友", "i ", "my "])
            if not has_personal:
                return {"should_capture": False, "reason": "knowledge_qa_no_personal", "quality_score": 10}
    
    # 强制过滤信号（闲聊/问候）
    casual_signals = [
        "你好", "hello", "hi", "在吗", "在不在", "忙吗",
        "谢谢", "thanks", "thank you", "不客气", "没事",
        "再见", "bye", "goodbye", "晚安", "早安", "早上好"
    ]
    if len(text) < 100 and any(s in t for s in casual_signals):
        return {"should_capture": False, "reason": "casual_greeting", "quality_score": 5}
    
    # 强制过滤信号（短知识问答：以疑问词开头且无个人标记）
    if len(text) < 200:
        knowledge_prefixes = [
            "什么是", "怎么", "如何", "为什么", "介绍", "解释", "说明",
            "什么是", "的定义", "的原理", "的历史", "的方法",
            "what is", "how to", "why does", "explain", "define", "describe"
        ]
        first_60 = t[:60]
        has_knowledge_prefix = any(s in first_60 for s in knowledge_prefixes)
        has_personal = any(s in t for s in ["我", "我的", "我家", "我爸", "我妈", "我哥", "我姐", "我朋友", "i ", "my "])
        if has_knowledge_prefix and not has_personal:
            return {"should_capture": False, "reason": "knowledge_qa_short", "quality_score": 10}
    
    # 委托外部模型判断（兜底）
    return model_result


def security_scan(text):
    output = run_script("extract.py", "security_scan", text)
    try:
        return json.loads(output)
    except:
        return {"threats": [], "safe": True}


def memory_used_in_reply(reply, memory_content):
    output = run_script("extract.py", "memory_used", reply, memory_content)
    try:
        return json.loads(output)
    except:
        return {"used": False, "confidence": 0.0}


def estimate_tokens(text):
    output = run_script("extract.py", "estimate_tokens", text)
    try:
        return json.loads(output)
    except:
        return {"tokens": len(text), "method": "fallback"}


def detect_contradiction(new_text, old_text):
    output = run_script("extract.py", "contradict", new_text, old_text)
    try:
        return json.loads(output)
    except:
        return {"has_contradiction": False, "contradictions": []}


def extract_keywords(text, n=8):
    """提取关键词"""
    output = run_script("extract.py", "keywords", text, str(n))
    try:
        return json.loads(output)
    except:
        return []


# ======= 图操作 =======

def graph_query(text, n=3):
    output = run_script("memory_graph.py", "query", text, str(n))
    try:
        return json.loads(output)
    except:
        return {"matches": {}}


def graph_add(memory_id, content, tags=""):
    return run_script("memory_graph.py", "add", memory_id, content, tags)


def graph_stats():
    output = run_script("memory_graph.py", "stats")
    try:
        return json.loads(output)
    except:
        return {}


# ======= 搜索与排序 =======

def extract_relevant_entries(content, query, max_entries=3):
    if not content or not content.strip():
        return []
    entries = []
    current = []
    for line in content.splitlines():
        if line.startswith("## ") and current:
            entries.append("\n".join(current).strip())
            current = [line]
        else:
            current.append(line)
    if current:
        entries.append("\n".join(current).strip())
    if len(entries) <= 1:
        entries = [e.strip() for e in content.split("\n\n") if e.strip() and len(e.strip()) > 20]
    query_words = set(query.lower().split())
    scored = []
    for entry in entries:
        entry_lower = entry.lower()
        score = sum(1 for w in query_words if w in entry_lower)
        scored.append((score, entry))
    scored.sort(reverse=True)
    return [e for s, e in scored[:max_entries] if s > 0]


def vector_search(query, limit=5):
    """向量搜索，返回带距离的结果用于三维排序"""
    output = run_script("vector_memory.py", "search", query, str(limit))
    try:
        results = json.loads(output)
        for r in results:
            dist = r.get("distance", 1.0)
            r["relevance"] = max(0, 1.0 - dist)
        return results
    except:
        return []


def semantic_dedup_check(content, threshold=SEMANTIC_DEDUP_THRESHOLD):
    """语义去重检查，返回最相似的已有记忆或 None"""
    output = run_script("vector_memory.py", "dedup", content, str(threshold))
    try:
        return json.loads(output)
    except:
        return None


def hybrid_search(query, limit=5):
    """FTS5 双索引搜索"""
    porter_output = run_script("session_db.py", "search", query, str(limit))
    trigram_output = run_script("session_db.py", "search_trigram", query, str(limit))
    all_results = []
    seen = set()
    for output in [porter_output, trigram_output]:
        try:
            results = json.loads(output)
            for r in results:
                content = r.get("content", "")[:300]
                if content and content not in seen:
                    seen.add(content)
                    all_results.append({
                        "content": content,
                        "source": r.get("source", "session_db"),
                        "created_at": r.get("created_at", ""),
                        "relevance": 0.7,
                        "type": r.get("type", "unknown")
                    })
        except:
            pass
    return all_results[:limit]


def get_dynamic_importance(memory_id, base_importance):
    """
    Recall-Driven Importance: 基于召回历史动态调整重要性
    """
    output = run_script("session_db.py", "recall_stats", memory_id)
    try:
        stats = json.loads(output)
        total_recalls = stats.get("total_recalls", 0)
        used_count = stats.get("used_count", 0)
        
        recall_boost = 1 + math.log(total_recalls + 1) * 0.15
        
        usage_boost = 1.0
        if total_recalls > 0:
            usage_rate = used_count / total_recalls
            usage_boost = 0.8 + usage_rate * 0.4
        
        dynamic = base_importance * recall_boost * usage_boost
        return min(10, round(dynamic, 1))
    except:
        return base_importance


def record_recall(memory_id, query, was_used=0):
    """记录一次召回事件"""
    if not memory_id:
        return
    run_script("session_db.py", "recall_log", memory_id, query, str(was_used))


def rank_memories_3d(memories, query_entities=None):
    """
    三维排序：Relevance × Importance × Recency
    
    创新：使用 get_dynamic_importance 替代静态 importance
    """
    now = datetime.now()
    scored = []
    
    for m in memories:
        relevance = m.get("relevance", 0.5)
        
        base_importance = 0.5
        tags = m.get("metadata", {}).get("tags", "") if "metadata" in m else m.get("tags", "")
        if "importance:" in tags:
            try:
                imp_part = tags.split("importance:")[1].split()[0]
                base_importance = int(imp_part) / 10.0
            except:
                pass
        elif "score:" in tags:
            try:
                score_part = tags.split("score:")[1].split()[0]
                base_importance = int(score_part) / 50.0
            except:
                pass
        
        memory_id = m.get("id", "")
        importance = get_dynamic_importance(memory_id, base_importance) if memory_id else base_importance
        
        created_at = m.get("created_at", "")
        recency = 0.5
        if created_at:
            try:
                dt = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
                days_old = (now - dt).days
                gamma = 0.05
                recency = max(0.1, min(1.0, 2.718 ** (-gamma * days_old)))
            except:
                pass
        
        entity_boost = 0
        if query_entities:
            content_lower = m.get("content", "").lower()
            for ent in query_entities:
                if ent.lower() in content_lower:
                    entity_boost += 0.05
        entity_boost = min(0.2, entity_boost)
        
        total_score = 0.4 * relevance + 0.35 * importance + 0.25 * recency + entity_boost
        scored.append((total_score, m))
    
    scored.sort(reverse=True, key=lambda x: x[0])
    return [m for s, m in scored]


# ======= 数据库写入 =======

def insert_to_session_db(role, content):
    return run_script("session_db.py", "insert_message", role, content)


def insert_to_vector_db(content, tags="", importance=5):
    """P0: Semantic Merge — 写入前检查语义重复"""
    dup = semantic_dedup_check(content[:500])
    if dup and dup.get("id"):
        old_content = dup.get("content", "")
        old_id = dup.get("id", "")
        
        merged = old_content + "\n" + content
        if len(merged) > 1000:
            merged = merged[:1000]
        
        new_importance = min(10, importance + 1)
        
        run_script("vector_memory.py", "update", old_id, merged, f"{tags} merged:1")
        run_script("vector_memory.py", "update_importance", old_id, str(new_importance))
        
        return json.dumps({"status": "merged", "id": old_id, "importance": new_importance})
    
    tags_with_score = f"{tags} importance:{importance}"
    return run_script("vector_memory.py", "add", content, tags_with_score)


def jaccard_similarity(text1, text2):
    """计算两段文本的 Jaccard 相似度"""
    words1 = set(jieba.lcut(text1.lower()))
    words2 = set(jieba.lcut(text2.lower()))
    intersection = words1 & words2
    union = words1 | words2
    if not union:
        return 0.0
    return len(intersection) / len(union)
