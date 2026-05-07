#!/usr/bin/env python3
"""
ChromaDB 向量记忆搜索 for My-AI — 增加更新/删除/语义去重

用法:
  python3 vector_memory.py init                          # 初始化向量库
  python3 vector_memory.py add <content> [tags]          # 添加记忆条目
  python3 vector_memory.py update <id> <content> [tags]  # 更新记忆条目
  python3 vector_memory.py update_importance <id> <score> # 更新重要性评分
  python3 vector_memory.py delete <id>                   # 删除记忆条目
  python3 vector_memory.py search <query> [limit]        # 语义搜索
  python3 vector_memory.py dedup <content> [threshold]   # 语义去重检查
  python3 vector_memory.py sync                          # 从 Markdown 文件同步
  python3 vector_memory.py stats                         # 统计信息
"""

import chromadb
import sys
import json
import re
from pathlib import Path

# 可移植路径
SCRIPT_DIR = Path(__file__).parent.resolve()
MEMORY_DIR = SCRIPT_DIR.parent / "memory"
CHROMA_PATH = MEMORY_DIR / ".chroma"


def get_client():
    return chromadb.PersistentClient(path=str(CHROMA_PATH))


def get_collection():
    client = get_client()
    return client.get_or_create_collection("my_ai_memory")


def init_db():
    collection = get_collection()
    count = collection.count()
    print(f"Vector memory initialized at {CHROMA_PATH}")
    print(f"Current entries: {count}")


def add_memory(content, tags="", source="manual"):
    """添加记忆条目到向量库"""
    collection = get_collection()
    import uuid
    from datetime import datetime
    doc_id = str(uuid.uuid4())

    collection.add(
        documents=[content],
        metadatas=[{"tags": tags, "source": source, "timestamp": str(datetime.now())}],
        ids=[doc_id]
    )
    print(json.dumps({"id": doc_id, "status": "added"}))
    return doc_id


def update_memory(doc_id, new_content, new_tags=""):
    """更新已有记忆条目（用于语义合并）"""
    collection = get_collection()
    from datetime import datetime
    
    # 先获取现有 metadata
    try:
        existing = collection.get(ids=[doc_id])
        old_meta = existing["metadatas"][0] if existing["metadatas"] else {}
        # 合并 tags
        merged_tags = f"{old_meta.get('tags', '')} {new_tags}".strip()
        # 增加 consolidation_count
        consolidation = int(old_meta.get("consolidation_count", 0)) + 1
    except:
        merged_tags = new_tags
        consolidation = 1
    
    collection.update(
        ids=[doc_id],
        documents=[new_content],
        metadatas=[{
            "tags": merged_tags,
            "source": old_meta.get("source", "manual"),
            "timestamp": str(datetime.now()),
            "consolidation_count": str(consolidation)
        }]
    )
    print(json.dumps({"id": doc_id, "status": "updated", "consolidation_count": consolidation}))
    return doc_id


def update_importance(doc_id, new_importance):
    """更新记忆的重要性评分"""
    collection = get_collection()
    from datetime import datetime
    
    try:
        existing = collection.get(ids=[doc_id])
        old_meta = existing["metadatas"][0] if existing["metadatas"] else {}
        old_doc = existing["documents"][0] if existing["documents"] else ""
        
        # 更新 tags 中的 importance
        tags = old_meta.get("tags", "")
        # 移除旧的 importance 标记
        tags = re.sub(r'importance:\d+', f'importance:{new_importance}', tags)
        if 'importance:' not in tags:
            tags += f" importance:{new_importance}"
        
        collection.update(
            ids=[doc_id],
            documents=[old_doc],
            metadatas=[{
                "tags": tags.strip(),
                "source": old_meta.get("source", "manual"),
                "timestamp": str(datetime.now())
            }]
        )
        print(json.dumps({"id": doc_id, "status": "importance_updated", "importance": new_importance}))
    except Exception as e:
        print(json.dumps({"error": str(e)}))


def delete_memory(doc_id):
    """删除记忆条目"""
    collection = get_collection()
    try:
        collection.delete(ids=[doc_id])
        print(json.dumps({"id": doc_id, "status": "deleted"}))
    except Exception as e:
        print(json.dumps({"error": str(e)}))


def search(query, limit=5):
    """语义搜索记忆，返回带距离的结果"""
    collection = get_collection()
    if collection.count() == 0:
        print(json.dumps([]))
        return []

    results = collection.query(
        query_texts=[query],
        n_results=min(limit, collection.count())
    )

    output = []
    for i in range(len(results["documents"][0])):
        output.append({
            "id": results["ids"][0][i],
            "content": results["documents"][0][i],
            "metadata": results["metadatas"][0][i],
            "distance": results["distances"][0][i]
        })

    print(json.dumps(output, ensure_ascii=False, indent=2))
    return output


def semantic_dedup_search(content, threshold=0.15):
    """
    语义去重检查：查找与 content 语义相似度高的已有记忆
    
    threshold: 最大距离（越小越严格，默认 0.15 ≈ 相似度 > 0.85）
    
    返回: 最相似的条目或 None
    """
    collection = get_collection()
    if collection.count() == 0:
        print(json.dumps(None))
        return None
    
    results = collection.query(
        query_texts=[content],
        n_results=1
    )
    
    if results["distances"][0]:
        distance = results["distances"][0][0]
        if distance <= threshold:
            output = {
                "id": results["ids"][0][0],
                "content": results["documents"][0][0],
                "metadata": results["metadatas"][0][0],
                "distance": distance,
                "similarity": round(1.0 - distance, 3)
            }
            print(json.dumps(output, ensure_ascii=False))
            return output
    
    print(json.dumps(None))
    return None


def sync_from_files():
    """从四层架构的 Markdown 文件同步到向量库"""
    collection = get_collection()
    import uuid
    import re
    from datetime import datetime

    files_to_sync = [
        MEMORY_DIR / "identity" / "SOUL.md",
        MEMORY_DIR / "identity" / "USER.md",
        MEMORY_DIR / "knowledge" / "KNOWLEDGE.md",
        MEMORY_DIR / "context" / "ACTIVE.md",
    ]

    added = 0
    for file_path in files_to_sync:
        if not file_path.exists():
            continue

        content = file_path.read_text(encoding="utf-8")
        # 按 ## 分割成条目
        entries = []
        if "##" in content:
            raw_entries = content.split("##")
            entries = [e.strip() for e in raw_entries if e.strip() and len(e.strip()) > 30]
        else:
            entries = [content]

        for entry in entries:
            if len(entry) < 20:
                continue
            doc_id = f"{file_path.stem}_{uuid.uuid4().hex[:8]}"
            rel_source = str(file_path.relative_to(MEMORY_DIR.parent))
            collection.add(
                documents=[entry[:2000]],
                metadatas=[{
                    "source": rel_source,
                    "tags": file_path.stem,
                    "timestamp": str(datetime.now())
                }],
                ids=[doc_id]
            )
            added += 1

    print(json.dumps({"synced_entries": added}))
    return added


def stats():
    """统计向量库信息"""
    collection = get_collection()
    print(json.dumps({
        "total_entries": collection.count(),
        "chroma_path": str(CHROMA_PATH)
    }))


if __name__ == "__main__":
    import re
    from datetime import datetime

    cmd = sys.argv[1] if len(sys.argv) > 1 else "help"

    if cmd == "init":
        init_db()
    elif cmd == "add":
        content = sys.argv[2] if len(sys.argv) > 2 else ""
        tags = sys.argv[3] if len(sys.argv) > 3 else ""
        add_memory(content, tags)
    elif cmd == "update":
        doc_id = sys.argv[2] if len(sys.argv) > 2 else ""
        content = sys.argv[3] if len(sys.argv) > 3 else ""
        tags = sys.argv[4] if len(sys.argv) > 4 else ""
        update_memory(doc_id, content, tags)
    elif cmd == "update_importance":
        doc_id = sys.argv[2] if len(sys.argv) > 2 else ""
        score = int(sys.argv[3]) if len(sys.argv) > 3 else 5
        update_importance(doc_id, score)
    elif cmd == "delete":
        doc_id = sys.argv[2] if len(sys.argv) > 2 else ""
        delete_memory(doc_id)
    elif cmd == "search":
        query = sys.argv[2] if len(sys.argv) > 2 else ""
        limit = int(sys.argv[3]) if len(sys.argv) > 3 else 5
        search(query, limit)
    elif cmd == "dedup":
        content = sys.argv[2] if len(sys.argv) > 2 else ""
        threshold = float(sys.argv[3]) if len(sys.argv) > 3 else 0.15
        semantic_dedup_search(content, threshold)
    elif cmd == "sync":
        sync_from_files()
    elif cmd == "stats":
        stats()
    else:
        print(__doc__)
