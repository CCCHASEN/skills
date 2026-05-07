#!/usr/bin/env python3
"""
My-AI Turn Wrapper — 持久记忆助手的核心控制层（Orchestration 入口）

用法:
  .venv/bin/python scripts/my_ai_turn.py pre <user_query>
  .venv/bin/python scripts/my_ai_turn.py post <turn_json>
  .venv/bin/python scripts/my_ai_turn.py boot
  .venv/bin/python scripts/my_ai_turn.py status
  .venv/bin/python scripts/my_ai_turn.py handoff <session_id>
  .venv/bin/python scripts/my_ai_turn.py precompact
  .venv/bin/python scripts/my_ai_turn.py maintenance
  .venv/bin/python scripts/my_ai_turn.py dreaming
  .venv/bin/python scripts/my_ai_turn.py recovery_check
  .venv/bin/python scripts/my_ai_turn.py context_log
  .venv/bin/python scripts/my_ai_turn.py flush_log
"""

import sys
import json
from datetime import datetime

from config import (
    IDENTITY_DIR, KNOWLEDGE_MD, ACTIVE_MD,
    MEMORY_DIR
)
from context import (
    append_context_log, read_context_log, get_context_log_stats,
    flush_context_log, _should_flush_context_log
)
from memory_ops import (
    extract_intent, extract_entities, analyze_content,
    score_importance, should_capture, security_scan,
    detect_contradiction, vector_search, hybrid_search,
    record_recall, rank_memories_3d, extract_relevant_entries,
    insert_to_session_db, insert_to_vector_db, graph_add
)
from maintenance import (
    get_context_pressure, check_bootstrap_security,
    check_session_recovery, run_maintenance,
    precompact_flush, classify_context_lifetime,
    generate_handoff, determine_target_file, dreaming_sweep
)
from utils import run_script


# ======= 命令处理 =======

def cmd_pre(user_query):
    """回复前：意图分类 + 实体提取 + 分层搜索 + 三维排序 + 安全扫描 + 上下文恢复"""
    
    # 动态刷新：在 pre 阶段检测话题切换，提前 flush
    pre_flushed = False
    should_flush, flush_reason = _should_flush_context_log(user_query)
    if should_flush:
        flush_report = flush_context_log(reason=flush_reason)
        pre_flushed = flush_report.get("flushed", False)
    
    intent = extract_intent(user_query)
    entities = extract_entities(user_query)
    entity_names = [e["text"] for e in entities if e["type"] in ("TECH", "PERSON", "ORG", "PROJECT", "FILE")]
    
    # 读取 Context Log 历史（分层策略以节省 token）
    context_history = read_context_log(limit=10)
    for i, turn in enumerate(context_history):
        if i < len(context_history) - 3:
            turn.pop("thinking", None)
            turn.pop("tools", None)
            turn.pop("files", None)
            for key in ["user", "assistant"]:
                if key in turn and turn[key]:
                    turn[key] = turn[key][:200]
        else:
            for key in ["user", "thinking", "assistant"]:
                if key in turn and turn[key]:
                    turn[key] = turn[key][:250]
    
    lifetime = classify_context_lifetime(user_query)
    
    search_query = user_query
    search_limit = 5
    if intent["primary"] == "WHY":
        search_query = user_query + " 决定 原因 因为"
    elif intent["primary"] == "WHEN":
        search_query = user_query + " " + datetime.now().strftime("%Y-%m-%d")
    elif intent["primary"] == "ENTITY" and entity_names:
        search_query = " ".join(entity_names[:3])
    
    active_content = ACTIVE_MD.read_text(encoding="utf-8") if ACTIVE_MD.exists() else ""
    knowledge_content = KNOWLEDGE_MD.read_text(encoding="utf-8") if KNOWLEDGE_MD.exists() else ""
    
    relevant_active = extract_relevant_entries(active_content, search_query, max_entries=2)
    relevant_knowledge = extract_relevant_entries(knowledge_content, search_query, max_entries=2)
    
    vec_results = vector_search(search_query, search_limit)
    fts_results = hybrid_search(search_query, search_limit)
    
    pressure = get_context_pressure()
    if pressure == "high":
        precompact_flush(intent["primary"])
    
    all_memories = []
    for content in relevant_active:
        all_memories.append({
            "content": content[:250],
            "source": "ACTIVE",
            "relevance": 0.8,
            "created_at": datetime.now().isoformat(),
            "metadata": {"tags": "source:active"}
        })
    
    for content in relevant_knowledge:
        all_memories.append({
            "content": content[:250],
            "source": "KNOWLEDGE",
            "relevance": 0.75,
            "created_at": datetime.now().isoformat(),
            "metadata": {"tags": "source:knowledge"}
        })
    
    for r in vec_results:
        all_memories.append({
            "id": r.get("id", ""),
            "content": r.get("content", "")[:250],
            "source": "DB",
            "relevance": r.get("relevance", 0.5),
            "created_at": r.get("metadata", {}).get("timestamp", ""),
            "metadata": r.get("metadata", {})
        })
    
    for r in fts_results:
        all_memories.append({
            "content": r.get("content", "")[:250],
            "source": "FTS",
            "relevance": r.get("relevance", 0.7),
            "created_at": r.get("created_at", ""),
            "metadata": {"tags": r.get("tags", "")}
        })
    
    ranked = rank_memories_3d(all_memories, query_entities=entity_names)
    
    for m in ranked[:3]:
        mem_id = m.get("id", "")
        if mem_id:
            record_recall(mem_id, user_query, was_used=0)
            try:
                run_script("session_db.py", "update_access", mem_id)
            except:
                pass
    
    safe_memories = []
    for m in ranked:
        scan = security_scan(m.get("content", ""))
        if scan.get("safe", True):
            safe_memories.append(m)
    
    seen = set()
    final_memories = []
    for m in safe_memories:
        key = m["content"][:50]
        if key not in seen and len(m["content"]) > 10:
            seen.add(key)
            final_memories.append(m["content"][:250])
    
    final_memories = final_memories[:5]
    
    skill_hints = []
    uq = user_query.lower()
    skill_map = [
        (["网页", "article", "blog", "url"], "defuddle"),
        (["邮件", "email", "mailbox"], "email"),
        (["浏览器", "browser", "点击", "截图"], "kimi-webbridge"),
        (["日历", "calendar", "schedule"], "macos-calendar"),
        (["obsidian", "vault"], "obsidian-knowledge"),
        (["股票", "股价", "a股", "基金"], "tushare-finance"),
        (["天气", "weather"], "weather"),
        (["github", "pr", "issue"], "github"),
        (["文档", "word", "ppt", "excel", "pdf"], "office-documents"),
        (["前端", "react", "vue", "ui"], "frontend-dev"),
        (["屏幕", "截图", "gui"], "screen-control"),
        (["搜索", "research", "调研"], "tavily"),
    ]
    for keywords, skill in skill_map:
        if any(k in uq for k in keywords):
            skill_hints.append(skill)
    
    result = {
        "intent": intent["primary"],
        "entities": entity_names,
        "memories": final_memories,
        "lifetime": lifetime,
        "context_history": context_history,
        "skill_hints": skill_hints,
    }
    
    if pressure != "low":
        result["pressure"] = pressure
    
    print(json.dumps(result, ensure_ascii=False))


def cmd_post(turn_json_str):
    """回复后：内容过滤 + 重要性评分 + 语义合并 + 智能保存 + 矛盾检测 + 图更新"""
    try:
        turn_data = json.loads(turn_json_str)
    except:
        turn_data = {"user_message": "", "assistant_reply": "", "tools_used": [], "files_modified": []}
    
    user_msg = turn_data.get("user_message", "")
    assistant_reply = turn_data.get("assistant_reply", "")
    combined = user_msg + " " + assistant_reply
    files_modified = turn_data.get("files_modified", [])
    tools = turn_data.get("tools_used", [])
    thinking = turn_data.get("thinking", "")
    
    # 纯粹上下文日志（ALWAYS 记录，不受过滤影响）
    append_context_log(
        user_msg=user_msg,
        assistant_reply=assistant_reply,
        thinking=thinking,
        tools_used=tools,
        files_modified=files_modified
    )
    
    # 检查是否需要 flush
    flushed_log = False
    should_flush, flush_reason = _should_flush_context_log(user_msg)
    if should_flush:
        flush_report = flush_context_log(reason=flush_reason)
        flushed_log = flush_report.get("flushed", False)
    
    for _ in tools:
        run_script("session_db.py", "increment_tools")
    
    # 1. 内容过滤（仅影响长期记忆保存，不影响上下文日志）
    capture_check = should_capture(combined)
    if not capture_check.get("should_capture", True):
        output = {
            "synced": False,
            "reason": capture_check.get("reason", "filtered"),
            "score": 0,
            "importance": 0,
            "analysis": f"Filtered: {capture_check.get('reason')}",
            "contradiction": False,
            "compress": False,
            "context_log_flushed": flushed_log
        }
        print(json.dumps(output, ensure_ascii=False))
        return
    
    # 2. 重要性评分
    importance = score_importance(combined, files_modified=files_modified)
    
    # 3. 分析
    analysis = analyze_content(combined)
    
    # 4. 矛盾检测
    contradictions = {"has_contradiction": False, "contradictions": []}
    check_sources = []
    if KNOWLEDGE_MD.exists():
        check_sources.append(KNOWLEDGE_MD.read_text(encoding="utf-8"))
    if ACTIVE_MD.exists():
        check_sources.append(ACTIVE_MD.read_text(encoding="utf-8"))
    
    for source_text in check_sources:
        segments = [s.strip() for s in source_text.split("\n\n") if s.strip() and len(s.strip()) > 20]
        for seg in segments[-5:]:
            c = detect_contradiction(combined, seg)
            if c.get("has_contradiction"):
                contradictions = c
                break
        if contradictions.get("has_contradiction"):
            break
    
    # 5. 决定保存位置和建议
    target_file, tags = determine_target_file(importance, combined, user_msg)
    
    summary = f"User: {user_msg[:200]}\nReply: {assistant_reply[:300]}"
    tags += f" importance:{importance}"
    if analysis.get("keywords"):
        tags += " keywords:" + ",".join([k[0] for k in analysis["keywords"][:3]])
    
    # 6. 自动保存层
    insert_to_session_db("assistant", summary[:500])
    
    vector_result = None
    if importance >= 3:
        vector_result = insert_to_vector_db(summary[:1000], tags, importance)
        mem_id = f"mem_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        graph_add(mem_id, summary[:500], tags)
    
    suggested_target = None
    if target_file is not None and importance >= 5:
        suggested_target = str(target_file.relative_to(MEMORY_DIR.parent))
    
    compress = get_context_pressure() == "high"
    
    output = {
        "synced": importance >= 3,
        "score": importance * 5,
        "importance": importance,
        "target": suggested_target,
        "analysis": analysis.get("summary", ""),
        "contradiction": contradictions.get("has_contradiction", False),
        "compress": compress,
        "context_log_flushed": flushed_log
    }
    
    if vector_result:
        try:
            vr = json.loads(vector_result)
            if vr.get("status") == "merged":
                output["vector_action"] = "merged"
                output["merged_id"] = vr.get("id")
        except:
            pass
    
    if contradictions.get("has_contradiction"):
        output["warning"] = f"Detected {len(contradictions.get('contradictions', []))} contradiction(s). Review needed."
    
    print(json.dumps(output, ensure_ascii=False))


def cmd_boot():
    threats = check_bootstrap_security()
    recovery = check_session_recovery()
    maintenance_report = run_maintenance()
    
    context_history = read_context_log(limit=10)
    context_log_stats = get_context_log_stats()
    
    log_flushed = False
    should_flush, flush_reason = _should_flush_context_log()
    if should_flush:
        flush_report = flush_context_log(reason=flush_reason)
        log_flushed = flush_report.get("flushed", False)
        context_history = read_context_log(limit=10)
        context_log_stats = get_context_log_stats()
    
    result = {
        "ready": (IDENTITY_DIR / "SOUL.md").exists(),
        "vector": json.loads(run_script("vector_memory.py", "stats")),
        "graph": json.loads(run_script("memory_graph.py", "stats")),
        "pressure": get_context_pressure(),
        "session": json.loads(run_script("session_db.py", "recent", "1")),
        "maintenance": maintenance_report,
        "security": {"safe": len(threats) == 0, "threats": threats},
        "recovery": recovery,
        "context_history": context_history,
        "context_log": context_log_stats,
        "context_log_flushed": log_flushed
    }
    print(json.dumps(result, ensure_ascii=False))


def cmd_status():
    result = {
        "files": {
            "SOUL": (IDENTITY_DIR / "SOUL.md").exists(),
            "USER": (IDENTITY_DIR / "USER.md").exists(),
            "KNOWLEDGE": KNOWLEDGE_MD.exists(),
            "ACTIVE": ACTIVE_MD.exists()
        },
        "vector": json.loads(run_script("vector_memory.py", "stats")),
        "graph": json.loads(run_script("memory_graph.py", "stats")),
        "pressure": get_context_pressure(),
        "session": json.loads(run_script("session_db.py", "recent", "1"))
    }
    print(json.dumps(result, ensure_ascii=False))


def cmd_handoff(session_id=None):
    handoff_file = generate_handoff(session_id)
    if handoff_file:
        print(json.dumps({"handoff": handoff_file}, ensure_ascii=False))
    else:
        print(json.dumps({"error": "No session found"}, ensure_ascii=False))


def cmd_precompact():
    flush_file = precompact_flush()
    print(json.dumps({"flushed_to": flush_file}, ensure_ascii=False))


def cmd_maintenance():
    report = run_maintenance()
    should_flush, flush_reason = _should_flush_context_log()
    if should_flush:
        flush_report = flush_context_log(reason=flush_reason)
        report["context_log_flush"] = flush_report
    print(json.dumps(report, ensure_ascii=False))


def cmd_dreaming():
    report = dreaming_sweep()
    print(json.dumps(report, ensure_ascii=False))


def cmd_recovery_check():
    result = check_session_recovery()
    print(json.dumps(result, ensure_ascii=False))


def cmd_context_log():
    stats = get_context_log_stats()
    turns = read_context_log(limit=5)
    result = {"stats": stats, "recent_turns": turns}
    print(json.dumps(result, ensure_ascii=False))


def cmd_flush_log():
    report = flush_context_log()
    print(json.dumps(report, ensure_ascii=False))


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "help"
    
    if cmd == "pre" and len(sys.argv) > 2:
        cmd_pre(sys.argv[2])
    elif cmd == "post" and len(sys.argv) > 2:
        cmd_post(sys.argv[2])
    elif cmd == "boot":
        cmd_boot()
    elif cmd == "status":
        cmd_status()
    elif cmd == "handoff":
        sid = int(sys.argv[2]) if len(sys.argv) > 2 else None
        cmd_handoff(sid)
    elif cmd == "precompact":
        cmd_precompact()
    elif cmd == "maintenance":
        cmd_maintenance()
    elif cmd == "dreaming":
        cmd_dreaming()
    elif cmd == "recovery_check":
        cmd_recovery_check()
    elif cmd == "context_log":
        cmd_context_log()
    elif cmd == "flush_log":
        cmd_flush_log()
    else:
        print(__doc__)
