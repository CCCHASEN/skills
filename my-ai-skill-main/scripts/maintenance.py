#!/usr/bin/env python3
"""维护系统： dreaming、recovery、handoff、压缩、目标文件判定"""

import json
import math
from datetime import datetime, timedelta
from pathlib import Path

import jieba
import networkx as nx

from config import (
    MEMORY_DIR, IDENTITY_DIR, KNOWLEDGE_MD, ACTIVE_MD,
    SOUL_MD, USER_MD,
    ARCHIVE_DIR, UNSORTED_DIR, DAILY_DIR, HANDOFF_DIR, RECOVERY_DIR,
    CACHE_BUDGET
)
from utils import run_script, estimate_tokens_fast
from memory_ops import (
    extract_keywords, extract_entities, extract_relevant_entries,
    graph_stats, jaccard_similarity
)


# ======= 上下文压力检测 =======

def get_context_pressure():
    """上下文压力检测"""
    active_lines = 0
    if ACTIVE_MD.exists():
        active_lines = len(ACTIVE_MD.read_text(encoding="utf-8").splitlines())
    
    knowledge_lines = 0
    if KNOWLEDGE_MD.exists():
        knowledge_lines = len(KNOWLEDGE_MD.read_text(encoding="utf-8").splitlines())
    
    daily_size = 0
    today = datetime.now().strftime("%Y-%m-%d")
    daily_file = DAILY_DIR / f"{today}.md"
    if daily_file.exists():
        daily_size = len(daily_file.read_text(encoding="utf-8").splitlines())
    
    score = 0
    if active_lines > 100: score += 3
    elif active_lines > 60: score += 2
    elif active_lines > 30: score += 1
    
    if knowledge_lines > 500: score += 2
    elif knowledge_lines > 300: score += 1
    
    if daily_size > 100: score += 1
    
    if score >= 5: return "high"
    elif score >= 3: return "medium"
    return "low"


# ======= Prompt Cache Budget =======

def load_file_with_budget(file_path, remaining_budget):
    """加载文件并按预算截断或摘要（使用快速 token 估算）"""
    if not file_path.exists():
        return "", remaining_budget
    
    content = file_path.read_text(encoding="utf-8")
    token_count = estimate_tokens_fast(content)
    
    if token_count <= remaining_budget:
        return content, remaining_budget - token_count
    else:
        summary = content[:500] + f"\n\n... [截断：原 ~{token_count} tokens，超出 {CACHE_BUDGET} tokens 预算]"
        summary_tokens = estimate_tokens_fast(summary)
        return summary, remaining_budget - summary_tokens


def check_bootstrap_security():
    """P1: Security Scanner — 扫描所有 bootstrap 文件"""
    from memory_ops import security_scan
    files_to_scan = [
        IDENTITY_DIR / "SOUL.md",
        IDENTITY_DIR / "USER.md",
        KNOWLEDGE_MD,
        ACTIVE_MD,
    ]
    threats_found = []
    for f in files_to_scan:
        if not f.exists():
            continue
        content = f.read_text(encoding="utf-8")
        scan = security_scan(content)
        if scan.get("threats"):
            for t in scan["threats"]:
                threats_found.append({
                    "file": str(f.relative_to(MEMORY_DIR.parent)),
                    "category": t["category"],
                    "severity": t["severity"],
                    "matched": t["matched"]
                })
    return threats_found


# ======= Adaptive Compression =======

def get_compression_template(intent_primary="WHAT"):
    """根据意图类型选择自适应压缩模板"""
    templates = {
        "coding": {
            "goal": "[当前编码目标]",
            "progress": {
                "done": "[已完成：文件路径 + 关键变更]",
                "in_progress": "[进行中]",
                "blocked": "[阻塞：错误信息 + 尝试过的方案]"
            },
            "decisions": "[技术决策：为什么选这个方案]",
            "files": "[相关文件及状态]",
            "next": "[下一步：具体文件/函数/命令]",
            "critical": "[关键配置/环境变量/版本信息]"
        },
        "debugging": {
            "goal": "[调试目标]",
            "progress": {
                "done": "[已验证：什么工作正常]",
                "in_progress": "[正在排查]",
                "blocked": "[错误信息 + 根因假设]"
            },
            "decisions": "[排查路径选择]",
            "files": "[涉及的文件]",
            "next": "[下一步验证方案]",
            "critical": "[错误日志/堆栈/环境信息]"
        },
        "discussion": {
            "goal": "[讨论主题]",
            "progress": {
                "done": "[已达成共识]",
                "in_progress": "[正在讨论]",
                "blocked": "[分歧点]"
            },
            "decisions": "[已做出的决策及原因]",
            "files": "[参考资料]",
            "next": "[待确认事项]",
            "critical": "[用户偏好/约束条件]"
        },
        "default": {
            "goal": "[用户正在尝试完成的目标]",
            "progress": {
                "done": "[已完成的工作]",
                "in_progress": "[正在进行的工作]",
                "blocked": "[遇到的阻塞或问题]"
            },
            "decisions": "[重要的技术决策及原因]",
            "files": "[读取、修改或创建的文件]",
            "next": "[接下来需要做什么]",
            "critical": "[具体值、错误信息、配置细节]"
        }
    }
    
    if intent_primary in templates:
        return templates[intent_primary]
    return templates["default"]


def precompact_flush(intent_primary="WHAT"):
    """压缩前 Flush，使用自适应模板"""
    today = datetime.now().strftime("%Y-%m-%d")
    daily_file = DAILY_DIR / f"{today}.md"
    DAILY_DIR.mkdir(parents=True, exist_ok=True)
    
    template = get_compression_template(intent_primary)
    flush_content = f"\n\n## Pre-compact Flush {datetime.now().strftime('%H:%M')} | Intent: {intent_primary}\n"
    
    if ACTIVE_MD.exists():
        active = ACTIVE_MD.read_text(encoding="utf-8")
        key_entries = extract_relevant_entries(active, "关键决策 待办 阻塞", max_entries=5)
        if key_entries:
            flush_content += f"### {template['progress']['done']}\n"
            for entry in key_entries:
                flush_content += f"- {entry[:200]}\n"
    
    recent = run_script("session_db.py", "recent", "1")
    try:
        sessions = json.loads(recent)
        if sessions:
            s = sessions[0]
            flush_content += f"\n### 当前会话\n"
            flush_content += f"- ID: {s.get('id')}, 消息: {s.get('message_count', 0)}, 工具: {s.get('tool_call_count', 0)}\n"
    except:
        pass
    
    flush_content += "\n"
    with open(daily_file, "a", encoding="utf-8") as f:
        f.write(flush_content)
    return str(daily_file)


# ======= Ephemeral Context Protocol =======

def classify_context_lifetime(user_query):
    """根据用户查询判断上下文生命周期"""
    q = user_query.lower()
    
    ephemeral_signals = [
        "先不管", "暂时", "just for now", "暂时不考虑",
        "抛开", "忽略", "skip", "先跳过"
    ]
    for s in ephemeral_signals:
        if s in q:
            return "EPHEMERAL"
    
    session_signals = [
        "刚才", "之前说的", "上一步", "基于刚才",
        "刚才的结果", "之前的结果", "continue with"
    ]
    for s in session_signals:
        if s in q:
            return "SESSION"
    
    return "PERSISTENT"


def generate_handoff(session_id=None):
    """生成 handoff 文件，同时保存 recovery snapshot"""
    HANDOFF_DIR.mkdir(parents=True, exist_ok=True)
    RECOVERY_DIR.mkdir(parents=True, exist_ok=True)
    
    recent = run_script("session_db.py", "recent", "3")
    try:
        sessions = json.loads(recent)
        target = None
        for s in sessions:
            if session_id is None or s.get("id") == session_id:
                target = s
                break
        if not target:
            target = sessions[0] if sessions else None
    except:
        target = None
    
    if not target:
        return None
    
    sid = target.get('id')
    handoff_file = HANDOFF_DIR / f"{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
    content = f"""# Handoff — {datetime.now().strftime('%Y-%m-%d %H:%M')}

## 会话信息
- Session ID: {sid}
- Title: {target.get('title', 'Untitled')}
- Messages: {target.get('message_count', 0)}
- Tool Calls: {target.get('tool_call_count', 0)}
- End Reason: {target.get('end_reason', 'unknown')}

## 当前状态
"""
    if ACTIVE_MD.exists():
        active = ACTIVE_MD.read_text(encoding="utf-8")
        entries = extract_relevant_entries(active, "项目 决策 待办 阻塞", max_entries=5)
        for entry in entries:
            content += f"- {entry[:200]}\n"
    
    content += "\n## 恢复命令\n"
    content += f"```\nShell \"python3 scripts/session_db.py recent 1\"\n```\n"
    
    with open(handoff_file, "w", encoding="utf-8") as f:
        f.write(content)
    
    try:
        run_script("session_db.py", "save_recovery", str(sid), content[:2000])
    except:
        pass
    
    return str(handoff_file)


# ======= 智能保存系统 =======

def determine_target_file(importance, content, user_message=""):
    """
    决定记忆应该保存到哪个定义文件。
    
    过滤知识性内容：纯知识问答不写入定义文件，仅入向量库。
    """
    um = user_message.lower()
    combined = (user_message + " " + content).lower()
    
    # 用户显式要求记忆
    if "记住这个" in um or "remember this" in um:
        if any(w in combined for w in ["任务", "待办", "todo", "task", "阻塞", "blocked"]):
            return ACTIVE_MD, "forced:active"
        return KNOWLEDGE_MD, "forced:knowledge"
    
    # 人格/身份变更 -> SOUL.md
    if any(s in combined for s in [
        "改名叫", "你以后叫", "你叫", "你的名字",
        "你的人格", "你的性格", "说话风格", "说话方式",
        "你以后说话", "你说话", "你的语气", "你的口吻",
        "角色", "扮演", "人设", "persona", "role",
    ]):
        return SOUL_MD, "personality"
    
    # 用户偏好 -> USER.md
    if "以后都" in um or "always" in um or "prefer" in um:
        return USER_MD, "preference"
    
    # 纠正/教训 -> KNOWLEDGE.md
    if any(w in combined for w in ["错了", "纠正", "更正", "不对", "wrong", "correct", "shouldn't"]):
        return KNOWLEDGE_MD, "lesson"
    
    # 高重要性分层
    if importance >= 8:
        if any(w in combined for w in ["人格", "性格", "说话", "风格", "角色", "persona", "role"]):
            return SOUL_MD, "high:personality"
        if any(w in combined for w in ["决定", "选择", "方案", "偏好", "教训", "decision", "choose", "lesson", "pattern"]):
            return KNOWLEDGE_MD, "high:decision"
        if any(w in combined for w in ["项目", "技术栈", "架构", "project", "stack", "architecture"]):
            return KNOWLEDGE_MD, "high:project"
        return KNOWLEDGE_MD, "high:general"
    
    elif importance >= 5:
        if any(w in combined for w in ["待办", "todo", "任务", "task", "阻塞", "blocked", "下一步", "next step"]):
            return ACTIVE_MD, "medium:active"
        return KNOWLEDGE_MD, "medium:general"
    
    elif importance >= 3:
        if any(w in combined for w in ["待办", "todo", "任务", "task", "阻塞", "blocked", "下一步", "next step"]):
            return ACTIVE_MD, "low:active"
        return None, "low:db_only"
    
    else:
        return None, "discard"


def write_knowledge_entry(content, target_file, tags=""):
    """将精炼后的知识写入定义文件"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    entry = f"\n- {content}  *(更新于 {timestamp})*\n"
    
    target_file.parent.mkdir(parents=True, exist_ok=True)
    with open(target_file, "a", encoding="utf-8") as f:
        f.write(entry)
    return str(target_file)


# ======= On-Demand Dreaming =======

def dreaming_sweep():
    """
    三阶段按需记忆巩固
    
    Phase 1: Light Sleep — 读取最近7天日志 → 分块 → Jaccard 去重
    Phase 2: REM Sleep — 关键词共现网络提取 recurring themes
    Phase 3: Deep Sleep — 六维评分 → 晋升到 KNOWLEDGE.md
    """
    report = {
        "dreaming_run": datetime.now().isoformat(),
        "phases": {}
    }
    
    # Phase 1: Light Sleep
    candidates = []
    for i in range(7):
        day = (datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d")
        daily_file = DAILY_DIR / f"{day}.md"
        if daily_file.exists():
            content = daily_file.read_text(encoding="utf-8")
            chunks = [c.strip() for c in content.split("##") if len(c.strip()) > 30]
            candidates.extend(chunks)
    
    unique_candidates = []
    for c in candidates:
        is_dup = False
        for uc in unique_candidates:
            if jaccard_similarity(c, uc) > 0.9:
                is_dup = True
                break
        if not is_dup:
            unique_candidates.append(c)
    
    report["phases"]["light_sleep"] = {
        "raw_chunks": len(candidates),
        "after_dedup": len(unique_candidates)
    }
    
    if len(unique_candidates) < 3:
        report["status"] = "skipped"
        report["reason"] = "Not enough candidates for dreaming"
        return report
    
    # Phase 2: REM Sleep
    G = nx.Graph()
    chunk_keywords = []
    
    for chunk in unique_candidates:
        keywords = [k[0] for k in extract_keywords(chunk, n=5)]
        chunk_keywords.append(keywords)
        for kw in keywords:
            if not G.has_node(kw):
                G.add_node(kw, frequency=0)
            G.nodes[kw]["frequency"] = G.nodes[kw].get("frequency", 0) + 1
        for i_kw, kw1 in enumerate(keywords):
            for kw2 in keywords[i_kw+1:]:
                if G.has_edge(kw1, kw2):
                    G[kw1][kw2]["weight"] += 1
                else:
                    G.add_edge(kw1, kw2, weight=1)
    
    if len(G.nodes) > 0:
        centrality = nx.degree_centrality(G)
        themes = sorted(centrality.items(), key=lambda x: x[1], reverse=True)[:10]
    else:
        themes = []
    
    report["phases"]["rem_sleep"] = {
        "themes": [t[0] for t in themes],
        "graph_nodes": len(G.nodes),
        "graph_edges": len(G.edges)
    }
    
    # Phase 3: Deep Sleep
    promoted = []
    top_recalled_output = run_script("session_db.py", "top_recalled", "20")
    try:
        top_recalled = json.loads(top_recalled_output)
    except:
        top_recalled = []
    
    recall_map = {r["memory_id"]: r for r in top_recalled}
    
    for chunk in unique_candidates:
        relevance = 0.5
        frequency = 1
        query_diversity = 1
        recency = 0.5
        consolidation = 0
        conceptual_richness = min(1.0, len(extract_entities(chunk)) / 5.0)
        
        score = (
            0.30 * relevance +
            0.24 * frequency +
            0.15 * query_diversity +
            0.15 * recency +
            0.10 * consolidation +
            0.06 * conceptual_richness
        )
        
        if score >= 0.6 and len(chunk) > 50:
            promoted.append({"content": chunk[:500], "score": round(score, 3)})
    
    if promoted:
        promotion_content = "\n\n## [DREAMING] " + datetime.now().strftime("%Y-%m-%d %H:%M") + "\n"
        for p in promoted[:5]:
            promotion_content += f"\n- {p['content']} (score: {p['score']})\n"
        
        with open(KNOWLEDGE_MD, "a", encoding="utf-8") as f:
            f.write(promotion_content)
    
    report["phases"]["deep_sleep"] = {
        "candidates_scored": len(unique_candidates),
        "promoted": len(promoted),
        "promotion_file": str(KNOWLEDGE_MD.relative_to(MEMORY_DIR.parent)) if promoted else None
    }
    report["status"] = "completed"
    
    return report


# ======= Session Recovery =======

def check_session_recovery():
    """检查是否需要会话恢复"""
    output = run_script("session_db.py", "last_unended")
    try:
        last_unended = json.loads(output)
    except:
        last_unended = None
    
    if not last_unended:
        return None
    
    sid = last_unended.get("id")
    
    recovery_output = run_script("session_db.py", "get_recovery", str(sid))
    try:
        recovery = json.loads(recovery_output)
    except:
        recovery = None
    
    handoff_files = sorted(HANDOFF_DIR.glob("*.md"), reverse=True)
    latest_handoff = str(handoff_files[0].relative_to(MEMORY_DIR.parent)) if handoff_files else None
    
    return {
        "needs_recovery": True,
        "last_session": last_unended,
        "recovery_snapshot": recovery,
        "latest_handoff": latest_handoff,
        "message": f"上次会话 (ID: {sid}) 未正常结束。是否恢复？"
    }


# ======= 维护系统 =======

def run_maintenance():
    report = {
        "maintenance_run": datetime.now().isoformat(),
        "actions": [],
        "warnings": []
    }
    
    # 1. ACTIVE.md 长度检查
    if ACTIVE_MD.exists():
        lines = len(ACTIVE_MD.read_text(encoding="utf-8").splitlines())
        if lines > 100:
            report["warnings"].append(f"ACTIVE.md 过长 ({lines} 行)，建议压缩")
        report["actions"].append(f"ACTIVE.md checked: {lines} lines")
    
    # 2. KNOWLEDGE.md 长度检查
    if KNOWLEDGE_MD.exists():
        lines = len(KNOWLEDGE_MD.read_text(encoding="utf-8").splitlines())
        if lines > 500:
            report["warnings"].append(f"KNOWLEDGE.md 过长 ({lines} 行)，建议整理")
        report["actions"].append(f"KNOWLEDGE.md checked: {lines} lines")
    
    # 3. 清理旧 unsorted
    cleaned_unsorted = 0
    if UNSORTED_DIR.exists():
        cutoff = datetime.now() - timedelta(days=30)
        for f in UNSORTED_DIR.glob("*.md"):
            try:
                mtime = datetime.fromtimestamp(f.stat().st_mtime)
                if mtime < cutoff:
                    old_dir = ARCHIVE_DIR / "old"
                    old_dir.mkdir(exist_ok=True)
                    f.rename(old_dir / f.name)
                    cleaned_unsorted += 1
            except:
                pass
    report["actions"].append(f"Cleaned {cleaned_unsorted} old unsorted files")
    
    # 4. 清理旧 SessionDB 消息
    try:
        run_script("session_db.py", "cleanup_old", "90")
        report["actions"].append("SessionDB cleanup completed")
    except:
        pass
    
    # 5. 同步向量库
    try:
        run_script("vector_memory.py", "sync")
        report["actions"].append("Vector DB sync completed")
    except:
        pass
    
    # 6. 图统计
    try:
        gstats = graph_stats()
        report["graph"] = gstats
    except:
        pass
    
    # 7. Hebbian Decay
    try:
        decay_result = json.loads(run_script("session_db.py", "apply_decay", "0.02", "0.3"))
        report["hebbian_decay"] = decay_result
        report["actions"].append(f"Hebbian decay: avg_act={decay_result.get('avg_activation', 0)}")
    except Exception as e:
        report["warnings"].append(f"Hebbian decay failed: {e}")
    
    return report
