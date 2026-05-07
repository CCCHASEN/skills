#!/usr/bin/env python3
"""
SQLite SessionDB for My-AI
设计特点：
- Session lineage (parent_session_id chains)
- FTS5 + Trigram 双索引（porter 英文 + trigram 中文/CJK）
- State meta key/value 存储
- Tool call counting
- Source tagging

用法:
  python3 session_db.py init                           # 初始化数据库
  python3 session_db.py insert_session <title> [source] # 插入会话
  python3 session_db.py insert_message <role> <content> # 插入消息
  python3 session_db.py search <query> [limit]          # FTS5 搜索（双索引）
  python3 session_db.py search_trigram <query> [limit]  # Trigram 子串搜索
  python3 session_db.py recent [limit]                  # 最近会话
  python3 session_db.py memories [limit]                # 最近记忆
  python3 session_db.py set_meta <key> <value>          # 设置状态
  python3 session_db.py get_meta <key>                  # 获取状态
  python3 session_db.py increment_tools <session_id>    # 增加工具调用计数
  python3 session_db.py end_session <id> [reason]       # 结束会话
  python3 session_db.py cleanup_old [days]              # 清理旧消息（默认90天）
"""

import sqlite3
import sys
import json
from pathlib import Path
from datetime import datetime, timedelta

# 可移植路径：基于本文件位置自动推导
SCRIPT_DIR = Path(__file__).parent.resolve()
DB_PATH = SCRIPT_DIR.parent / "memory" / ".sessions.db"


def get_conn():
    conn = sqlite3.connect(str(DB_PATH))
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=5000")  # 并发安全
    return conn


def init_db():
    """创建数据库表和 FTS5 虚拟表"""
    conn = get_conn()

    # 会话表
    conn.execute("""
        CREATE TABLE IF NOT EXISTS sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source TEXT DEFAULT 'cli',
            title TEXT,
            summary TEXT,
            parent_session_id INTEGER,
            end_reason TEXT,
            message_count INTEGER DEFAULT 0,
            tool_call_count INTEGER DEFAULT 0,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            ended_at TEXT,
            FOREIGN KEY (parent_session_id) REFERENCES sessions(id)
        )
    """)

    # 消息表
    conn.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id INTEGER,
            role TEXT,
            content TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (session_id) REFERENCES sessions(id)
        )
    """)

    # 记忆条目表（含 Hebbian 衰减字段）
    conn.execute("""
        CREATE TABLE IF NOT EXISTS memories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source TEXT,
            content TEXT,
            tags TEXT,
            score INTEGER,
            activation REAL DEFAULT 1.0,        -- Hebbian 激活值，召回时提升
            decay_score REAL DEFAULT 1.0,       -- 衰减系数，0-1
            access_count INTEGER DEFAULT 0,     -- 被访问次数
            last_accessed TEXT,                 -- 最后访问时间
            archived BOOLEAN DEFAULT 0,         -- 是否已归档
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # 向后兼容：为已有表添加 Hebbian 列（如果不存在）
    try:
        conn.execute("ALTER TABLE memories ADD COLUMN activation REAL DEFAULT 1.0")
    except:
        pass
    try:
        conn.execute("ALTER TABLE memories ADD COLUMN decay_score REAL DEFAULT 1.0")
    except:
        pass
    try:
        conn.execute("ALTER TABLE memories ADD COLUMN access_count INTEGER DEFAULT 0")
    except:
        pass
    try:
        conn.execute("ALTER TABLE memories ADD COLUMN last_accessed TEXT")
    except:
        pass
    try:
        conn.execute("ALTER TABLE memories ADD COLUMN archived BOOLEAN DEFAULT 0")
    except:
        pass

    # 状态元数据表
    conn.execute("""
        CREATE TABLE IF NOT EXISTS state_meta (
            key TEXT PRIMARY KEY,
            value TEXT,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # 召回日志表 — 用于 Recall-Driven Importance
    conn.execute("""
        CREATE TABLE IF NOT EXISTS recall_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            memory_id TEXT,
            query TEXT,
            was_used BOOLEAN DEFAULT 0,
            recalled_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # 恢复快照表 — 用于 Session Recovery
    conn.execute("""
        CREATE TABLE IF NOT EXISTS recovery_snapshots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id INTEGER,
            content TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (session_id) REFERENCES sessions(id)
        )
    """)

    # FTS5 全文搜索（porter tokenizer — 英文/词干）
    conn.execute("""
        CREATE VIRTUAL TABLE IF NOT EXISTS messages_fts USING fts5(
            content,
            content_rowid=id,
            tokenize='porter'
        )
    """)

    conn.execute("""
        CREATE VIRTUAL TABLE IF NOT EXISTS memories_fts USING fts5(
            content,
            content_rowid=id,
            tokenize='porter'
        )
    """)

    # FTS5 Trigram 索引 — 中文/CJK/子串搜索
    conn.execute("""
        CREATE VIRTUAL TABLE IF NOT EXISTS messages_fts_trigram USING fts5(
            content,
            content_rowid=id,
            tokenize='trigram'
        )
    """)

    # 触发器：porter 索引
    conn.execute("""
        CREATE TRIGGER IF NOT EXISTS messages_fts_insert AFTER INSERT ON messages
        BEGIN
            INSERT INTO messages_fts(rowid, content) VALUES (NEW.id, NEW.content);
        END
    """)

    conn.execute("""
        CREATE TRIGGER IF NOT EXISTS memories_fts_insert AFTER INSERT ON memories
        BEGIN
            INSERT INTO memories_fts(rowid, content) VALUES (NEW.id, NEW.content);
        END
    """)

    # 触发器：trigram 索引
    conn.execute("""
        CREATE TRIGGER IF NOT EXISTS messages_trigram_insert AFTER INSERT ON messages
        BEGIN
            INSERT INTO messages_fts_trigram(rowid, content) VALUES (NEW.id, NEW.content);
        END
    """)

    # 触发器：自动更新 message_count
    conn.execute("""
        CREATE TRIGGER IF NOT EXISTS trg_msg_count AFTER INSERT ON messages
        BEGIN
            UPDATE sessions SET message_count = message_count + 1
            WHERE id = NEW.session_id;
        END
    """)

    conn.commit()
    conn.close()
    print(f"SessionDB initialized at {DB_PATH}")


def insert_session(title, source="cli", summary=""):
    """插入会话，返回 session_id"""
    conn = get_conn()
    cursor = conn.execute(
        "INSERT INTO sessions (title, source, summary) VALUES (?, ?, ?)",
        (title, source, summary)
    )
    session_id = cursor.lastrowid
    conn.commit()
    conn.close()
    print(json.dumps({"session_id": session_id}))
    return session_id


def end_session(session_id, reason="user_exit"):
    """结束会话，记录原因"""
    conn = get_conn()
    conn.execute(
        "UPDATE sessions SET end_reason = ?, ended_at = ? WHERE id = ?",
        (reason, datetime.now().isoformat(), session_id)
    )
    conn.commit()
    conn.close()
    print(json.dumps({"session_id": session_id, "end_reason": reason}))


def increment_tool_count(session_id=None):
    """增加工具调用计数"""
    conn = get_conn()
    if session_id is None:
        row = conn.execute("SELECT id FROM sessions ORDER BY id DESC LIMIT 1").fetchone()
        session_id = row[0] if row else None
    if session_id:
        conn.execute(
            "UPDATE sessions SET tool_call_count = tool_call_count + 1 WHERE id = ?",
            (session_id,)
        )
        conn.commit()
    conn.close()


def insert_message(role, content):
    """插入消息到当前最新会话"""
    conn = get_conn()
    row = conn.execute("SELECT id FROM sessions ORDER BY id DESC LIMIT 1").fetchone()
    if not row:
        cursor = conn.execute("INSERT INTO sessions (title) VALUES (?)", ("Default",))
        session_id = cursor.lastrowid
    else:
        session_id = row[0]

    conn.execute(
        "INSERT INTO messages (session_id, role, content) VALUES (?, ?, ?)",
        (session_id, role, content)
    )
    conn.commit()
    conn.close()


def search(query, limit=5):
    """FTS5 搜索（porter tokenizer — 适合英文/词干）"""
    conn = get_conn()
    results = []

    # Porter 搜索消息
    rows = conn.execute("""
        SELECT m.id, m.role, m.content, m.created_at, s.title
        FROM messages_fts fts
        JOIN messages m ON fts.rowid = m.id
        JOIN sessions s ON m.session_id = s.id
        WHERE messages_fts MATCH ?
        ORDER BY rank
        LIMIT ?
    """, (query, limit)).fetchall()

    for row in rows:
        results.append({
            "type": "message",
            "id": row[0],
            "role": row[1],
            "content": row[2][:300],
            "created_at": row[3],
            "session_title": row[4]
        })

    # Porter 搜索记忆
    rows = conn.execute("""
        SELECT m.id, m.source, m.content, m.tags, m.score, m.created_at
        FROM memories_fts fts
        JOIN memories m ON fts.rowid = m.id
        WHERE memories_fts MATCH ?
        ORDER BY rank
        LIMIT ?
    """, (query, limit)).fetchall()

    for row in rows:
        results.append({
            "type": "memory",
            "id": row[0],
            "source": row[1],
            "content": row[2][:300],
            "tags": row[3],
            "score": row[4],
            "created_at": row[5]
        })

    conn.close()
    print(json.dumps(results, ensure_ascii=False))
    return results


def search_trigram(query, limit=5):
    """Trigram 子串搜索（适合中文/CJK/短词）"""
    conn = get_conn()
    results = []

    # Trigram 搜索消息
    rows = conn.execute("""
        SELECT m.id, m.role, m.content, m.created_at, s.title
        FROM messages_fts_trigram fts
        JOIN messages m ON fts.rowid = m.id
        JOIN sessions s ON m.session_id = s.id
        WHERE messages_fts_trigram MATCH ?
        ORDER BY rank
        LIMIT ?
    """, (query, limit)).fetchall()

    for row in rows:
        results.append({
            "type": "message",
            "id": row[0],
            "role": row[1],
            "content": row[2][:300],
            "created_at": row[3],
            "session_title": row[4],
            "match_type": "trigram"
        })

    conn.close()
    print(json.dumps(results, ensure_ascii=False))
    return results


def recent_sessions(limit=5):
    conn = get_conn()
    rows = conn.execute(
        """SELECT id, title, source, parent_session_id, end_reason,
                  message_count, tool_call_count, created_at, summary
           FROM sessions ORDER BY id DESC LIMIT ?""",
        (limit,)
    ).fetchall()
    results = [{
        "id": r[0], "title": r[1], "source": r[2],
        "parent_session_id": r[3], "end_reason": r[4],
        "message_count": r[5], "tool_call_count": r[6],
        "created_at": r[7], "summary": r[8]
    } for r in rows]
    conn.close()
    print(json.dumps(results, ensure_ascii=False))
    return results


def recent_memories(limit=10):
    conn = get_conn()
    rows = conn.execute(
        "SELECT id, source, content, tags, score, created_at FROM memories ORDER BY id DESC LIMIT ?",
        (limit,)
    ).fetchall()
    results = [{"id": r[0], "source": r[1], "content": r[2][:300], "tags": r[3], "score": r[4], "created_at": r[5]} for r in rows]
    conn.close()
    print(json.dumps(results, ensure_ascii=False))
    return results


def set_meta(key, value):
    conn = get_conn()
    conn.execute(
        """INSERT INTO state_meta (key, value, updated_at) VALUES (?, ?, ?)
            ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated_at=excluded.updated_at""",
        (key, value, datetime.now().isoformat())
    )
    conn.commit()
    conn.close()


def get_meta(key):
    conn = get_conn()
    row = conn.execute("SELECT value FROM state_meta WHERE key = ?", (key,)).fetchone()
    conn.close()
    if row:
        print(json.dumps({"key": key, "value": row[0]}))
    else:
        print(json.dumps({"key": key, "value": None}))


def cleanup_old_messages(days=90):
    """清理超过 N 天的旧消息"""
    conn = get_conn()
    cutoff = (datetime.now() - timedelta(days=days)).isoformat()
    
    # 先统计要删除的数量
    count = conn.execute(
        "SELECT COUNT(*) FROM messages WHERE created_at < ?",
        (cutoff,)
    ).fetchone()[0]
    
    # 删除旧消息（FTS5 触发器会自动清理索引）
    conn.execute("DELETE FROM messages WHERE created_at < ?", (cutoff,))
    conn.commit()
    conn.close()
    
    print(json.dumps({"deleted_messages": count, "cutoff_days": days}))
    return count


# ====== Recall-Driven Importance ======

def insert_recall_log(memory_id, query, was_used=0):
    """记录一次召回事件"""
    conn = get_conn()
    conn.execute(
        "INSERT INTO recall_log (memory_id, query, was_used) VALUES (?, ?, ?)",
        (memory_id, query, was_used)
    )
    conn.commit()
    conn.close()


def get_recall_stats(memory_id):
    """获取某条记忆的召回统计"""
    conn = get_conn()
    row = conn.execute("""
        SELECT 
            COUNT(*) as total_recalls,
            SUM(CASE WHEN was_used = 1 THEN 1 ELSE 0 END) as used_count,
            COUNT(DISTINCT query) as unique_queries
        FROM recall_log
        WHERE memory_id = ?
    """, (memory_id,)).fetchone()
    conn.close()
    return {
        "memory_id": memory_id,
        "total_recalls": row[0] or 0,
        "used_count": row[1] or 0,
        "unique_queries": row[2] or 0
    }


def get_top_recalled(limit=10):
    """获取被召回次数最多的记忆"""
    conn = get_conn()
    rows = conn.execute("""
        SELECT memory_id, COUNT(*) as recall_count,
               SUM(CASE WHEN was_used = 1 THEN 1 ELSE 0 END) as used_count
        FROM recall_log
        GROUP BY memory_id
        ORDER BY recall_count DESC
        LIMIT ?
    """, (limit,)).fetchall()
    conn.close()
    return [{"memory_id": r[0], "recall_count": r[1], "used_count": r[2]} for r in rows]


# ====== Session Recovery ======

def get_last_unended_session():
    """获取最近未正常结束的 session"""
    conn = get_conn()
    row = conn.execute("""
        SELECT id, title, message_count, tool_call_count, created_at
        FROM sessions
        WHERE end_reason IS NULL
        ORDER BY id DESC
        LIMIT 1
    """).fetchone()
    conn.close()
    if row:
        return {"id": row[0], "title": row[1], "message_count": row[2],
                "tool_call_count": row[3], "created_at": row[4]}
    return None


def save_recovery_snapshot(session_id, content):
    """保存恢复快照"""
    conn = get_conn()
    conn.execute(
        "INSERT INTO recovery_snapshots (session_id, content) VALUES (?, ?)",
        (session_id, content)
    )
    conn.commit()
    conn.close()


def get_recovery_snapshot(session_id):
    """获取最新的恢复快照"""
    conn = get_conn()
    row = conn.execute("""
        SELECT content, created_at FROM recovery_snapshots
        WHERE session_id = ?
        ORDER BY id DESC LIMIT 1
    """, (session_id,)).fetchone()
    conn.close()
    if row:
        return {"content": row[0], "created_at": row[1]}
    return None


# ====== Hebbian Decay & Self-Purification ======

def update_memory_access(memory_id):
    """记录记忆被访问，提升 activation"""
    conn = get_conn()
    conn.execute("""
        UPDATE memories 
        SET activation = MIN(5.0, activation + 0.3),
            access_count = access_count + 1,
            last_accessed = CURRENT_TIMESTAMP
        WHERE id = ?
    """, (memory_id,))
    conn.commit()
    conn.close()


def apply_hebbian_decay(decay_rate=0.02, archive_threshold=0.3):
    """
    Hebbian 衰减：未使用的记忆自然衰减
    - 激活值衰减: activation *= (1 - decay_rate)
    - 冷记忆归档: activation < archive_threshold 且 7天未访问 → archived=1
    """
    conn = get_conn()
    conn.execute("""
        UPDATE memories 
        SET activation = MAX(0.0, activation * (1 - ?)),
            decay_score = MAX(0.0, decay_score * (1 - ?))
        WHERE archived = 0
    """, (decay_rate, decay_rate))
    conn.execute("""
        UPDATE memories 
        SET archived = 1
        WHERE archived = 0 
          AND activation < ?
          AND (last_accessed IS NULL OR last_accessed < datetime('now', '-7 days'))
          AND created_at < datetime('now', '-7 days')
    """, (archive_threshold,))
    stats = conn.execute("""
        SELECT COUNT(*), SUM(CASE WHEN archived=1 THEN 1 ELSE 0 END),
               AVG(activation), MIN(activation), MAX(activation)
        FROM memories
    """).fetchone()
    conn.commit()
    conn.close()
    return {
        "total": stats[0] or 0, "archived": stats[1] or 0,
        "avg_activation": round(stats[2] or 0, 3),
        "min_activation": round(stats[3] or 0, 3),
        "max_activation": round(stats[4] or 0, 3)
    }


def get_cold_memories(limit=50):
    """获取即将被归档的冷记忆"""
    conn = get_conn()
    rows = conn.execute("""
        SELECT id, content, activation, access_count, created_at
        FROM memories WHERE archived = 0 AND activation < 0.5
        ORDER BY activation ASC, created_at ASC LIMIT ?
    """, (limit,)).fetchall()
    conn.close()
    return [{"id": r[0], "content": r[1][:200], "activation": r[2], "access_count": r[3], "created_at": r[4]} for r in rows]


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "help"

    if cmd == "init":
        init_db()
    elif cmd == "insert_session":
        title = sys.argv[2] if len(sys.argv) > 2 else "Untitled"
        source = sys.argv[3] if len(sys.argv) > 3 else "cli"
        insert_session(title, source)
    elif cmd == "end_session":
        sid = int(sys.argv[2]) if len(sys.argv) > 2 else 0
        reason = sys.argv[3] if len(sys.argv) > 3 else "user_exit"
        end_session(sid, reason)
    elif cmd == "increment_tools":
        sid = int(sys.argv[2]) if len(sys.argv) > 2 else None
        increment_tool_count(sid)
    elif cmd == "insert_message":
        role = sys.argv[2] if len(sys.argv) > 2 else "user"
        content = sys.argv[3] if len(sys.argv) > 3 else ""
        insert_message(role, content)
    elif cmd == "search":
        query = sys.argv[2] if len(sys.argv) > 2 else ""
        limit = int(sys.argv[3]) if len(sys.argv) > 3 else 5
        search(query, limit)
    elif cmd == "search_trigram":
        query = sys.argv[2] if len(sys.argv) > 2 else ""
        limit = int(sys.argv[3]) if len(sys.argv) > 3 else 5
        search_trigram(query, limit)
    elif cmd == "recent":
        limit = int(sys.argv[2]) if len(sys.argv) > 2 else 5
        recent_sessions(limit)
    elif cmd == "memories":
        limit = int(sys.argv[2]) if len(sys.argv) > 2 else 10
        recent_memories(limit)
    elif cmd == "set_meta":
        key = sys.argv[2] if len(sys.argv) > 2 else ""
        value = sys.argv[3] if len(sys.argv) > 3 else ""
        set_meta(key, value)
    elif cmd == "get_meta":
        key = sys.argv[2] if len(sys.argv) > 2 else ""
        get_meta(key)
    elif cmd == "cleanup_old":
        days = int(sys.argv[2]) if len(sys.argv) > 2 else 90
        cleanup_old_messages(days)
    elif cmd == "apply_decay":
        decay_rate = float(sys.argv[2]) if len(sys.argv) > 2 else 0.02
        archive_threshold = float(sys.argv[3]) if len(sys.argv) > 3 else 0.3
        result = apply_hebbian_decay(decay_rate, archive_threshold)
        print(json.dumps(result, ensure_ascii=False))
    elif cmd == "update_access":
        memory_id = int(sys.argv[2]) if len(sys.argv) > 2 else 0
        update_memory_access(memory_id)
        print(json.dumps({"updated": memory_id}, ensure_ascii=False))
    elif cmd == "cold_memories":
        limit = int(sys.argv[2]) if len(sys.argv) > 2 else 50
        result = get_cold_memories(limit)
        print(json.dumps(result, ensure_ascii=False))
    elif cmd == "recall_log":
        memory_id = sys.argv[2] if len(sys.argv) > 2 else ""
        query = sys.argv[3] if len(sys.argv) > 3 else ""
        was_used = int(sys.argv[4]) if len(sys.argv) > 4 else 0
        insert_recall_log(memory_id, query, was_used)
    elif cmd == "recall_stats":
        memory_id = sys.argv[2] if len(sys.argv) > 2 else ""
        result = get_recall_stats(memory_id)
        print(json.dumps(result, ensure_ascii=False))
    elif cmd == "top_recalled":
        limit = int(sys.argv[2]) if len(sys.argv) > 2 else 10
        result = get_top_recalled(limit)
        print(json.dumps(result, ensure_ascii=False))
    elif cmd == "last_unended":
        result = get_last_unended_session()
        print(json.dumps(result, ensure_ascii=False))
    elif cmd == "save_recovery":
        sid = int(sys.argv[2]) if len(sys.argv) > 2 else 0
        content = sys.argv[3] if len(sys.argv) > 3 else ""
        save_recovery_snapshot(sid, content)
    elif cmd == "get_recovery":
        sid = int(sys.argv[2]) if len(sys.argv) > 2 else 0
        result = get_recovery_snapshot(sid)
        print(json.dumps(result, ensure_ascii=False))
    else:
        print(__doc__)
