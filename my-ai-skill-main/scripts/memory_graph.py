#!/usr/bin/env python3
"""
My-AI 记忆关系图 — 多层语义关联网络

依赖: networkx, jieba

构建语义+时间+因果的多层记忆图，支持:
  - 记忆节点关联
  - 实体节点提取
  - 相似度边（语义）
  - 时间边（先后顺序）
  - 因果边（因为...所以...）
  - 矛盾边（冲突检测）
  - 图遍历查询相关记忆

用法:
  python3 memory_graph.py add <memory_id> '<content>' [tags]   # 添加记忆节点
  python3 memory_graph.py link <id1> <id2> <relation> [weight]  # 建立关系边
  python3 memory_graph.py related <memory_id> [depth]           # 查询相关记忆
  python3 memory_graph.py entity <entity_name> <entity_type>    # 添加实体节点
  python3 memory_graph.py query '<text>' [n]                    # 基于文本查询相关
  python3 memory_graph.py stats                                 # 图统计
  python3 memory_graph.py export                                # 导出为JSON
"""

import sys
import json
import os
import pickle
from pathlib import Path
from datetime import datetime
from collections import Counter

import networkx as nx
import jieba

# 抑制 jieba 首次加载的 stdout 输出
import logging
jieba.setLogLevel(logging.CRITICAL)
jieba.initialize()

# 可移植路径：基于本文件位置自动推导
SCRIPT_DIR = Path(__file__).parent.resolve()
GRAPH_PATH = SCRIPT_DIR.parent / "memory" / ".memory_graph.pkl"

# 自定义词典（与 extract.py 同步）
CUSTOM_WORDS = [
    "Python", "JavaScript", "TypeScript", "Go", "Rust", "Java", "C++", "C#",
    "React", "Vue", "Next.js", "Node.js", "Django", "Flask", "FastAPI",
    "PostgreSQL", "MySQL", "MongoDB", "Redis", "Elasticsearch",
    "Docker", "Kubernetes", "AWS", "GCP", "Azure",
    "Claude", "Kimi",
    "ChromaDB", "SQLite", "FTS5", "MCP", "API",
    "AI", "LLM", "RAG", "向量", "嵌入", "语义",
]
for word in CUSTOM_WORDS:
    jieba.add_word(word, freq=1000)


def load_graph():
    """加载记忆图"""
    if GRAPH_PATH.exists():
        with open(GRAPH_PATH, "rb") as f:
            return pickle.load(f)
    return nx.MultiDiGraph()


def save_graph(G):
    """保存记忆图"""
    GRAPH_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(GRAPH_PATH, "wb") as f:
        pickle.dump(G, f)


def add_memory_node(memory_id, content, tags=""):
    """添加记忆节点"""
    G = load_graph()
    
    # 提取关键词作为节点属性
    words = [w for w in jieba.lcut(content) if len(w.strip()) >= 2]
    keywords = Counter(words).most_common(10)
    
    G.add_node(memory_id,
               type="memory",
               content=content[:500],
               keywords=dict(keywords),
               tags=tags,
               created_at=datetime.now().isoformat())
    
    # 自动提取实体并建立关联
    from extract import extract_entities
    entities = extract_entities(content)
    for ent in entities:
        ent_id = f"entity:{ent['type']}:{ent['text']}"
        if ent_id not in G:
            G.add_node(ent_id,
                      type="entity",
                      entity_type=ent['type'],
                      name=ent['text'],
                      first_seen=datetime.now().isoformat())
        G.add_edge(memory_id, ent_id, relation="mentions", weight=1.0)
    
    save_graph(G)
    print(json.dumps({"added": memory_id, "entities_linked": len(entities)}, ensure_ascii=False))


def add_entity_node(name, entity_type):
    """添加实体节点"""
    G = load_graph()
    ent_id = f"entity:{entity_type}:{name}"
    G.add_node(ent_id,
               type="entity",
               entity_type=entity_type,
               name=name,
               first_seen=datetime.now().isoformat())
    save_graph(G)
    print(json.dumps({"added": ent_id}, ensure_ascii=False))


def link_nodes(id1, id2, relation, weight=1.0):
    """建立关系边"""
    G = load_graph()
    if id1 not in G or id2 not in G:
        print(json.dumps({"error": "Node not found"}, ensure_ascii=False))
        return
    G.add_edge(id1, id2, relation=relation, weight=float(weight),
               created_at=datetime.now().isoformat())
    save_graph(G)
    print(json.dumps({"linked": f"{id1} -> {id2}", "relation": relation}, ensure_ascii=False))


def find_related(memory_id, depth=2):
    """查询相关记忆（图遍历）"""
    G = load_graph()
    if memory_id not in G:
        print(json.dumps({"error": "Node not found"}, ensure_ascii=False))
        return
    
    # BFS 遍历
    related = {}
    visited = {memory_id}
    queue = [(memory_id, 0)]
    
    while queue:
        node_id, dist = queue.pop(0)
        if dist >= depth:
            continue
        
        for neighbor in G.neighbors(node_id):
            if neighbor not in visited:
                visited.add(neighbor)
                # 获取边的关系类型
                edges = G.get_edge_data(node_id, neighbor)
                if edges:
                    edge_info = list(edges.values())[0]
                    related[neighbor] = {
                        "distance": dist + 1,
                        "relation": edge_info.get("relation", "unknown"),
                        "weight": edge_info.get("weight", 1.0),
                        "node_type": G.nodes[neighbor].get("type", "unknown"),
                        "content": G.nodes[neighbor].get("content", "")[:200]
                    }
                queue.append((neighbor, dist + 1))
    
    # 按权重排序
    sorted_related = sorted(related.items(), key=lambda x: -x[1]["weight"])
    result = {
        "query": memory_id,
        "related_count": len(sorted_related),
        "related": dict(sorted_related[:10])
    }
    print(json.dumps(result, ensure_ascii=False))


def query_by_text(text, n=5):
    """基于文本查询相关记忆"""
    G = load_graph()
    
    # 提取查询文本的关键词
    query_words = set(jieba.lcut(text))
    query_words = {w for w in query_words if len(w.strip()) >= 2}
    
    scores = {}
    for node_id, attrs in G.nodes(data=True):
        if attrs.get("type") != "memory":
            continue
        
        score = 0
        node_keywords = attrs.get("keywords", {})
        node_content = attrs.get("content", "")
        
        # 关键词匹配
        for kw in query_words:
            if kw in node_keywords:
                score += node_keywords[kw]
            if kw in node_content:
                score += 1
        
        # 实体匹配
        for neighbor in G.neighbors(node_id):
            neighbor_attrs = G.nodes[neighbor]
            if neighbor_attrs.get("type") == "entity":
                ent_name = neighbor_attrs.get("name", "")
                if ent_name in text:
                    score += 5
        
        if score > 0:
            scores[node_id] = {
                "score": score,
                "content": node_content[:200],
                "tags": attrs.get("tags", ""),
                "created_at": attrs.get("created_at", "")
            }
    
    sorted_scores = sorted(scores.items(), key=lambda x: -x[1]["score"])
    result = {
        "query": text,
        "matches": dict(sorted_scores[:n])
    }
    print(json.dumps(result, ensure_ascii=False))


def graph_stats():
    """图统计"""
    G = load_graph()
    
    memory_nodes = [n for n, a in G.nodes(data=True) if a.get("type") == "memory"]
    entity_nodes = [n for n, a in G.nodes(data=True) if a.get("type") == "entity"]
    
    relation_types = Counter()
    for u, v, attrs in G.edges(data=True):
        relation_types[attrs.get("relation", "unknown")] += 1
    
    result = {
        "total_nodes": G.number_of_nodes(),
        "total_edges": G.number_of_edges(),
        "memory_nodes": len(memory_nodes),
        "entity_nodes": len(entity_nodes),
        "relation_types": dict(relation_types),
        "density": round(nx.density(G), 4) if G.number_of_nodes() > 1 else 0
    }
    print(json.dumps(result, ensure_ascii=False))


def export_graph():
    """导出为 JSON"""
    G = load_graph()
    data = {
        "nodes": [{"id": n, **a} for n, a in G.nodes(data=True)],
        "edges": [{"source": u, "target": v, **a} for u, v, a in G.edges(data=True)]
    }
    print(json.dumps(data, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "help"
    
    if cmd == "add" and len(sys.argv) > 3:
        mid = sys.argv[2]
        content = sys.argv[3]
        tags = sys.argv[4] if len(sys.argv) > 4 else ""
        add_memory_node(mid, content, tags)
    elif cmd == "entity" and len(sys.argv) > 3:
        add_entity_node(sys.argv[2], sys.argv[3])
    elif cmd == "link" and len(sys.argv) > 4:
        weight = float(sys.argv[5]) if len(sys.argv) > 5 else 1.0
        link_nodes(sys.argv[2], sys.argv[3], sys.argv[4], weight)
    elif cmd == "related" and len(sys.argv) > 2:
        depth = int(sys.argv[3]) if len(sys.argv) > 3 else 2
        find_related(sys.argv[2], depth)
    elif cmd == "query" and len(sys.argv) > 2:
        n = int(sys.argv[3]) if len(sys.argv) > 3 else 5
        query_by_text(sys.argv[2], n)
    elif cmd == "stats":
        graph_stats()
    elif cmd == "export":
        export_graph()
    else:
        print(__doc__)
