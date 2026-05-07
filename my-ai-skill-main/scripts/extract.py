#!/usr/bin/env python3
"""
My-AI 信息提取引擎 — 安全扫描 + 记忆使用检测 + Token 估算

功能:
  1. 查询意图分类 (WHY / WHEN / ENTITY / WHAT)
  2. 命名实体提取 (人名/项目/技术栈/文件名)
  3. 关键词提取 (TF-IDF 风格)
  4. 关系推理 (因果/偏好/决策/教训)
  5. 矛盾检测
  6. 重要性评分 (1-10，基于多维信号)
  7. 内容过滤 (判断是否值得保存)
  8. 安全扫描 (prompt injection / exfiltration / invisible unicode)
  9. 记忆使用检测 (检测回复中是否使用了某条记忆)
  10. Token 估算 (用于 Cache Budget)

用法:
  python3 extract.py intent '<query>'              # 意图分类
  python3 extract.py entities '<text>'             # 实体提取
  python3 extract.py keywords '<text>' [n]         # 关键词提取
  python3 extract.py relations '<text>'            # 关系推理
  python3 extract.py contradict '<new>' '<old>'    # 矛盾检测
  python3 extract.py analyze '<text>'              # 综合分析
  python3 extract.py importance '<text>' [files_modified]  # 重要性评分
  python3 extract.py should_capture '<text>'       # 是否值得保存
  python3 extract.py security_scan '<text>'        # 安全扫描
  python3 extract.py memory_used '<reply>' '<memory>'  # 检测记忆是否被使用
  python3 extract.py estimate_tokens '<text>'      # 估算 token 数
"""

import sys
import json
import re
import math
from collections import Counter
from pathlib import Path

import jieba
import jieba.posseg as pseg

# 抑制 jieba 首次加载的 stdout 输出
import logging
jieba.setLogLevel(logging.CRITICAL)
jieba.initialize()

# 自定义词典：技术术语、项目名称
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

# 停用词
STOPWORDS = set([
    "的", "了", "是", "在", "我", "有", "和", "就", "不", "人", "都", "一", "一个", "上", "也", "很", "到", "说", "要", "去", "你", "会", "着", "没有", "看", "好", "自己", "这", "那", "什么", "怎么", "吗", "吧", "呢", "啊", "嗯", "哦",
    "the", "a", "an", "is", "are", "was", "were", "be", "been", "being",
    "have", "has", "had", "do", "does", "did", "will", "would", "could",
    "should", "may", "might", "must", "can", "need", "shall",
    "this", "that", "these", "those", "it", "its", "they", "them", "their",
    "and", "or", "but", "if", "then", "else", "when", "where", "why", "how",
    "to", "of", "in", "for", "on", "with", "at", "by", "from", "as", "into",
    "through", "during", "before", "after", "above", "below", "between",
    "i", "you", "he", "she", "we", "us", "me", "my", "your", "his", "her",
])

# 句子结束符模式（用于正则）
SENT_END = "[，,。！？;]|$"
SENT_END_CN = "[，,。！？；]|$"

# 系统消息过滤模式
SYSTEM_MSG_PATTERNS = [
    r"^You are\s+",
    r"^you are\s+",
    r"^As an?\s+AI\s+assistant",
    r"^System:\s*",
    r"^system\s+prompt",
    r"^You are a helpful",
    r"^I am an AI",
    r"^我是\s*AI",
    r"^你是一个\s*",
]

# 低质量/礼貌用语过滤
LOW_VALUE_PATTERNS = [
    r"^(ok|okay|thanks|thank you|好的|谢谢|嗯嗯|哦|知道了|明白|收到了)\s*[.!。！]?$",
    r"^(hi|hello|hey|你好|在吗)\s*[.!。！]?$",
    r"^(bye|goodbye|再见|拜拜)\s*[.!。！]?$",
]

# ====== 安全扫描模式 ======
SECURITY_PATTERNS = [
    # Prompt Injection
    (r'ignore\s+(?:all\s+)?(?:previous|prior|above)\s+instructions?', 'INJECTION', 'high'),
    (r'忽略.*(?:之前|以上|前面).*指令', 'INJECTION', 'high'),
    (r'forget\s+(?:everything|all)\s+(?:before|above)', 'INJECTION', 'high'),
    (r'(?:new|override)\s+instruction', 'INJECTION', 'medium'),
    (r'系统提示.*覆盖', 'INJECTION', 'medium'),
    
    # Exfiltration
    (r'curl\s+.*\$[A-Z_]+', 'EXFILTRATION', 'high'),
    (r'wget\s+.*\$[A-Z_]+', 'EXFILTRATION', 'high'),
    (r'fetch\s*\(\s*.*\$[A-Z_]+', 'EXFILTRATION', 'high'),
    (r'http\.request\s*\(.*\$[A-Z_]+', 'EXFILTRATION', 'high'),
    (r'将.*发送到.*http', 'EXFILTRATION', 'medium'),
    (r'send\s+.*to\s+.*url', 'EXFILTRATION', 'medium'),
    
    # Invisible Unicode
    (r'[\u200B-\u200F\uFEFF\u2060-\u206F]', 'INVISIBLE_UNICODE', 'high'),
    
    # Backdoor / Persistence
    (r'<!--\s*.*?-->', 'HTML_COMMENT', 'low'),
    (r'\\x[0-9a-f]{2}', 'ENCODED_PAYLOAD', 'medium'),
    (r'eval\s*\(', 'EVAL', 'high'),
    (r'new\s+Function\s*\(', 'DYNAMIC_CODE', 'high'),
    
    # Credential leak
    (r'(password|passwd|pwd|secret|token|key)\s*[:=]\s*["\'][^"\']{4,}["\']', 'CREDENTIAL_LEAK', 'high'),
    (r'(密码|密钥|令牌)\s*[:：]\s*\S{4,}', 'CREDENTIAL_LEAK', 'high'),
]


def is_system_like(text):
    """判断是否为系统消息或系统提示风格的内容"""
    t = text.strip()
    for pattern in SYSTEM_MSG_PATTERNS:
        if re.search(pattern, t, re.IGNORECASE):
            return True
    if t.startswith("<") and ">" in t[:50]:
        return True
    if "role" in t.lower() and "system" in t.lower():
        return True
    return False


def is_low_value(text):
    """判断是否为低价值内容（纯礼貌用语、过短等）"""
    t = text.strip()
    if len(t) < 15:
        return True
    for pattern in LOW_VALUE_PATTERNS:
        if re.match(pattern, t, re.IGNORECASE):
            return True
    if re.match(r"^[\s\p{Emoji}\p{Punctuation}]+$", t):
        return True
    return False


# 记忆指令关键词（包含这些词的内容不应被低价值过滤）
MEMORY_COMMANDS = [
    "记住", "remember", "以后都", "always", "prefer", "待办", "todo",
    "任务", "task", "你改名叫", "你以后叫", "你的人格", "你的性格",
    "说话风格", "说话方式", "你以后说话", "角色", "扮演", "人设",
]


def should_capture(text):
    """
    内容过滤：判断这段内容是否值得保存
    
    返回: {"should_capture": bool, "reason": str, "quality_score": 0-100}
    """
    t = text.strip()
    
    # 1. 系统消息过滤
    if is_system_like(t):
        return {"should_capture": False, "reason": "system_message", "quality_score": 0}
    
    # 1.5 记忆指令豁免：包含明确记忆指令的短文本不应被过滤
    has_memory_command = any(cmd in t for cmd in MEMORY_COMMANDS)
    
    # 2. 低价值过滤（记忆指令豁免）
    if not has_memory_command and is_low_value(t):
        return {"should_capture": False, "reason": "low_value", "quality_score": 10}
    
    # 3. 临时工具输出过滤
    lines = t.split("\n")
    if len(lines) > 5:
        code_line_ratio = sum(1 for l in lines if l.strip().startswith(("    ", "\t", "|", "- ", "+ "))) / len(lines)
        if code_line_ratio > 0.7 and len(t) > 500:
            return {"should_capture": False, "reason": "raw_data_dump", "quality_score": 20}
    
    # 4. 质量评估
    analysis = analyze(t)
    quality = analysis["quality_score"]
    
    # 记忆指令保底：即使质量评分低，只要有明确指令也保存
    if has_memory_command:
        quality = max(quality, 20)
    
    # 5. 重复检测简化版
    content_fingerprint = re.sub(r"\s+", "", t[:100].lower())
    
    return {
        "should_capture": quality >= 15,
        "reason": "quality_pass" if quality >= 15 else "low_quality",
        "quality_score": quality,
        "fingerprint": content_fingerprint
    }


def security_scan(text):
    """
    内容安全扫描
    
    返回: [{"category": str, "severity": str, "matched": str}]
    """
    threats = []
    SUSPICIOUS_HTML_WORDS = [
        "ignore", "forget", "instruction", "system", "prompt", "override",
        "new", "hidden", "secret", "backdoor", "payload", "eval"
    ]
    
    for pattern, category, severity in SECURITY_PATTERNS:
        for m in re.finditer(pattern, text, re.IGNORECASE):
            matched = m.group(0)
            # HTML 注释额外过滤：只标记包含可疑指令的注释
            if category == "HTML_COMMENT":
                comment_content = matched.strip("<>!")
                if not any(sw in comment_content.lower() for sw in SUSPICIOUS_HTML_WORDS):
                    continue  # 无害的 Markdown 注释，跳过
            # 截断过长的匹配
            if len(matched) > 50:
                matched = matched[:50] + "..."
            threats.append({
                "category": category,
                "severity": severity,
                "matched": matched
            })
    return threats


def memory_used_in_reply(reply, memory_content):
    """
    检测 assistant_reply 中是否使用了某条记忆的内容
    
    返回: {"used": bool, "confidence": float}
    """
    if not reply or not memory_content:
        return {"used": False, "confidence": 0.0}
    
    # 提取记忆的关键词（去掉停用词）
    mem_keywords = set()
    for word, flag in pseg.cut(memory_content):
        w = word.strip().lower()
        if len(w) >= 2 and w not in STOPWORDS and flag[0] in {"n", "v", "a", "eng", "x"}:
            mem_keywords.add(w)
    
    if not mem_keywords:
        return {"used": False, "confidence": 0.0}
    
    reply_lower = reply.lower()
    matched = 0
    for kw in mem_keywords:
        if kw in reply_lower:
            matched += 1
    
    # 计算 Jaccard 风格的覆盖率
    coverage = matched / len(mem_keywords)
    
    # 额外检查：长片段匹配
    long_match = False
    mem_sentences = re.split(r'[。！？\n;]', memory_content)
    for sent in mem_sentences:
        sent = sent.strip()
        if len(sent) >= 10 and sent.lower() in reply_lower:
            long_match = True
            break
    
    confidence = coverage
    if long_match:
        confidence = max(confidence, 0.6)
    
    return {
        "used": confidence >= 0.3,
        "confidence": round(confidence, 2)
    }


def estimate_tokens(text):
    """
    估算文本的 token 数量
    
    中文 ≈ 1 token/字，英文 ≈ 0.75 token/词，代码 ≈ 1.2 token/字符
    
    返回: {"tokens": int, "method": str}
    """
    if not text:
        return {"tokens": 0, "method": "empty"}
    
    # 检测代码比例
    code_lines = sum(1 for line in text.split("\n") if line.strip().startswith(("    ", "\t", "```", "|")))
    code_ratio = code_lines / max(len(text.split("\n")), 1)
    
    # 中文字符数
    chinese_chars = sum(1 for c in text if '\u4e00' <= c <= '\u9fff')
    # 英文单词数（近似）
    english_words = len(re.findall(r'[a-zA-Z]+', text))
    # 其他字符
    other_chars = len(text) - chinese_chars - sum(1 for c in text if c.isalpha())
    
    if code_ratio > 0.5:
        # 代码模式
        tokens = int(len(text) * 1.2)
        method = "code"
    else:
        # 混合文本
        tokens = int(chinese_chars * 1.0 + english_words * 0.75 + other_chars * 0.5)
        method = "mixed"
    
    return {"tokens": max(1, tokens), "method": method}


def score_importance(text, files_modified=None, user_explicit_remember=False, is_correction=False):
    """
    重要性评分 (1-10) — 基于多维信号
    
    信号：
    - 用户显式指令（"记住这个" = +4）
    - 被纠正（+3）
    - 文件修改（+2 per file, max +4）
    - 实体密度（+1 per 2 entities, max +3）
    - 关系数量（决策/偏好/教训 = +2 each, max +4）
    - 否定/纠正语言（+2）
    - 长度适中（50-500字符 = +1, 过长 = -1）
    - 代码块（+1）
    """
    score = 3  # 基础分
    
    # 用户显式指令
    if user_explicit_remember:
        score += 4
    
    # 记忆指令关键词加分（待办、记住、以后都、角色等）
    memory_cmds = ["记住", "remember", "以后都", "always", "待办", "todo",
                   "任务", "task", "改名叫", "人格", "性格", "说话风格", "角色", "扮演"]
    for cmd in memory_cmds:
        if cmd in text:
            score += 2
            break  # 只加一次
    
    # 被纠正
    if is_correction:
        score += 3
    
    # 文件修改
    if files_modified:
        score += min(4, len(files_modified) * 2)
    
    # 内容分析
    analysis = analyze(text)
    entities = analysis["entities"]
    relations = analysis["relations"]
    
    # 实体密度
    score += min(3, len(entities) // 2)
    
    # 关系加分
    for rel in relations:
        if rel["type"] in ("decision", "preference", "lesson"):
            score += 2
        elif rel["type"] == "causal":
            score += 1
    score = min(score, 9)
    
    # 否定/纠正语言
    correction_markers = ["不", "不是", "错了", "纠正", "更正", "应该", "不应该",
                          "no", "not", "wrong", "correct", "should", "shouldn't"]
    t_lower = text.lower()
    for m in correction_markers:
        if m in t_lower:
            score += 1
            break
    
    # 长度因子
    length = len(text)
    if 50 <= length <= 500:
        score += 1
    elif length > 2000:
        score -= 1
    elif length < 30:
        score -= 2
    
    # 代码块
    if "```" in text:
        score += 1
    
    return max(1, min(10, score))


def classify_intent(query):
    """
    查询意图分类
    
    WHY:   寻求原因、解释
    WHEN:  寻求时间、历史、之前的事件
    ENTITY: 寻求特定实体信息
    WHAT:  通用信息查询（默认）
    """
    q = query.lower()
    scores = {"WHY": 0, "WHEN": 0, "ENTITY": 0, "WHAT": 0}
    
    # WHY 指标
    why_markers = ["为什么", "为何", "原因", "怎么会", "凭什么", "why", "reason", "cause", "because", "explain"]
    for m in why_markers:
        if m in q:
            scores["WHY"] += 3
    if any(w in q for w in ["怎么", "怎样", "如何"]):
        scores["WHY"] += 1
    
    # WHEN 指标
    when_markers = ["什么时候", "何时", "之前", "上次", "以前", "最近", "when", "before", "last time", "recently", "ago", "previously", "多久", "几天前"]
    for m in when_markers:
        if m in q:
            scores["WHEN"] += 3
    
    # ENTITY 指标
    entity_markers = ["什么是", "谁是", "哪个", "叫", "名称", "what is", "who is", "which", "named", "called"]
    for m in entity_markers:
        if m in q:
            scores["ENTITY"] += 3
    if re.search(r'[A-Z][a-zA-Z0-9_]+', query):
        scores["ENTITY"] += 1
    
    # 默认 WHAT
    scores["WHAT"] = 1
    
    # 确定主意图
    max_intent = max(scores, key=scores.get)
    max_score = scores[max_intent]
    
    if max_score == 0:
        max_intent = "WHAT"
    
    return {
        "primary": max_intent,
        "scores": scores,
        "strategy": {
            "WHY": "优先搜索决策、原因、因果关系记忆",
            "WHEN": "优先时间线、daily log、历史消息",
            "ENTITY": "优先实体关联记忆、命名识别",
            "WHAT": "通用语义搜索"
        }[max_intent]
    }


def extract_entities(text):
    """
    命名实体提取
    
    返回: [{"text": "...", "type": "...", "start": N, "end": N}]
    类型: PERSON, PROJECT, TECH, FILE, URL, ORG, DATE, MISC
    """
    entities = []
    seen = set()
    
    # 1. jieba 词性标注
    words = pseg.cut(text)
    for word, flag in words:
        if word in seen:
            continue
        
        entity_type = None
        if flag.startswith("nr"):  # 人名
            entity_type = "PERSON"
        elif flag.startswith("nt"):  # 机构名
            entity_type = "ORG"
        elif flag.startswith("ns"):  # 地名
            entity_type = "LOCATION"
        
        if entity_type and len(word) >= 2:
            seen.add(word)
            for m in re.finditer(re.escape(word), text):
                entities.append({
                    "text": word,
                    "type": entity_type,
                    "start": m.start(),
                    "end": m.end()
                })
                break
    
    # 2. 技术栈/项目名识别
    tech_names = {w.lower() for w in CUSTOM_WORDS}
    words = jieba.lcut(text)
    for word in words:
        w = word.strip()
        if not w:
            continue
        if w.lower() in tech_names and w not in seen:
            seen.add(w)
            for m in re.finditer(re.escape(w), text):
                entities.append({
                    "text": w,
                    "type": "TECH",
                    "start": m.start(),
                    "end": m.end()
                })
                break
    
    # 3. 正则补充技术名
    tech_pattern = re.compile(
        r'\b(Python|JavaScript|TypeScript|Go|Rust|Java|C\+\+|C#|'
        r'React|Vue|Next\.js|Node\.js|Django|Flask|FastAPI|'
        r'PostgreSQL|MySQL|MongoDB|Redis|Elasticsearch|'
        r'Docker|Kubernetes|AWS|GCP|Azure|'
        r'Claude|Kimi|ChromaDB|SQLite|FTS5|MCP|'
        r'AI|LLM|RAG|API|HTTP|REST|GraphQL)\b',
        re.IGNORECASE
    )
    for m in tech_pattern.finditer(text):
        word = m.group()
        if word not in seen:
            seen.add(word)
            entities.append({
                "text": word,
                "type": "TECH",
                "start": m.start(),
                "end": m.end()
            })
    
    # 4. 文件名识别
    file_pattern = re.compile(
        r'[~/]?[\w\-./]+\.(py|js|ts|go|rs|java|cpp|c|h|md|json|yaml|yml|sql|sh|txt|css|html)'
    )
    for m in file_pattern.finditer(text):
        word = m.group()
        if word not in seen:
            seen.add(word)
            entities.append({
                "text": word,
                "type": "FILE",
                "start": m.start(),
                "end": m.end()
            })
    
    # 5. URL 识别
    url_pattern = re.compile(r'https?://[^\s<>"{}|\\^`\[\]]+')
    for m in url_pattern.finditer(text):
        word = m.group()
        if word not in seen:
            seen.add(word)
            entities.append({
                "text": word,
                "type": "URL",
                "start": m.start(),
                "end": m.end()
            })
    
    # 6. 日期识别
    date_pattern = re.compile(
        r'\d{4}[-/]\d{1,2}[-/]\d{1,2}|'
        r'\d{1,2}[-/]\d{1,2}[-/]\d{4}|'
        r'(?:今天|昨天|前天|明天|后天|'
        r'周一|周二|周三|周四|周五|周六|周日|'
        r'星期一|星期二|星期三|星期四|星期五|星期六|星期日)'
    )
    for m in date_pattern.finditer(text):
        word = m.group()
        if word not in seen:
            seen.add(word)
            entities.append({
                "text": word,
                "type": "DATE",
                "start": m.start(),
                "end": m.end()
            })
    
    entities = sorted(entities, key=lambda x: x["start"])
    return entities


def extract_keywords(text, n=8):
    """
    关键词提取 — 基于 jieba + 词频 + 词性过滤
    
    返回: [("keyword", weight), ...]
    """
    tagged = pseg.cut(text)
    
    valid_pos = {"n", "nr", "nr1", "nr2", "nrj", "nrf", "ns", "nt", "nz", "nl", "ng",
                 "v", "vd", "vn", "vf", "vx", "vi", "vl", "vg",
                 "a", "ad", "an", "ag", "al",
                 "eng", "x"}
    
    valid_words = []
    for word, flag in tagged:
        w = word.strip().lower()
        if len(w) < 2 or w in STOPWORDS:
            continue
        is_chinese = any('\u4e00' <= c <= '\u9fff' for c in w)
        is_english = w.isalpha() and len(w) >= 3
        if (is_chinese or is_english) and flag[0] in valid_pos:
            valid_words.append(w)
    
    freq = Counter(valid_words)
    
    # 加权：出现在句首/句尾的词权重更高
    sentences = re.split(r'[。！？\n;]', text)
    for sent in sentences:
        sent_words = jieba.lcut(sent.strip())
        if sent_words:
            first = sent_words[0].strip().lower()
            last = sent_words[-1].strip().lower()
            if first in freq:
                freq[first] = int(freq[first] * 1.5)
            if last in freq and last != first:
                freq[last] = int(freq[last] * 1.3)
    
    top = freq.most_common(n)
    return [(word, round(weight, 2)) for word, weight in top]


def infer_relations(text):
    """
    关系推理
    
    返回关系列表
    """
    relations = []
    
    # 1. 因果关系
    causal_patterns = [
        ("因为(.+?)[，,]所以(.+?)" + SENT_END_CN, 1, 2),
        ("由于(.+?)[，,]因此(.+?)" + SENT_END_CN, 1, 2),
        ("(.+?)导致(.+?)" + SENT_END_CN, 1, 2),
        ("because (.+?),? (.+?)[.!?;]|$", 1, 2),
    ]
    for pattern, g1, g2 in causal_patterns:
        for m in re.finditer(pattern, text):
            cause = m.group(g1)
            effect = m.group(g2)
            if cause and effect and cause.strip() and effect.strip():
                relations.append({
                    "type": "causal",
                    "cause": cause.strip(),
                    "effect": effect.strip(),
                    "confidence": 0.8
                })
    
    # 2. 偏好关系
    pref_patterns = [
        ("偏好\\s*[:：]?\\s*(.+?)" + SENT_END_CN, "prefer"),
        ("喜欢\\s*[:：]?\\s*(.+?)" + SENT_END_CN, "like"),
        ("讨厌\\s*[:：]?\\s*(.+?)" + SENT_END_CN, "dislike"),
        ("不喜欢\\s*[:：]?\\s*(.+?)" + SENT_END_CN, "dislike"),
        ("总是\\s*[:：]?\\s*(.+?)" + SENT_END_CN, "always"),
        ("从不\\s*[:：]?\\s*(.+?)" + SENT_END_CN, "never"),
        ("prefer\\s+(.+?)[,;.!?]|$", "prefer"),
        ("like\\s+(.+?)[,;.!?]|$", "like"),
        ("hate\\s+(.+?)[,;.!?]|$", "dislike"),
    ]
    for pattern, rel_type in pref_patterns:
        for m in re.finditer(pattern, text, re.IGNORECASE):
            target = m.group(1)
            if target and target.strip():
                relations.append({
                    "type": "preference",
                    "subtype": rel_type,
                    "target": target.strip(),
                    "confidence": 0.75
                })
    
    # 3. 决策关系
    dec_patterns = [
        ("决定\\s*[:：]?\\s*(.+?)" + SENT_END_CN, "decide"),
        ("选择\\s*[:：]?\\s*(.+?)" + SENT_END_CN, "choose"),
        ("方案\\s*[:：]?\\s*(.+?)" + SENT_END_CN, "plan"),
        ("确定\\s*[:：]?\\s*(.+?)" + SENT_END_CN, "confirm"),
        ("decided?\\s+(?:to\\s+)?(.+?)[,;.!?]|$", "decide"),
        ("choose\\s+(?:to\\s+)?(.+?)[,;.!?]|$", "choose"),
    ]
    for pattern, rel_type in dec_patterns:
        for m in re.finditer(pattern, text, re.IGNORECASE):
            target = m.group(1)
            if target and target.strip():
                relations.append({
                    "type": "decision",
                    "subtype": rel_type,
                    "target": target.strip(),
                    "confidence": 0.85
                })
    
    # 4. 教训关系
    lesson_patterns = [
        ("教训\\s*[:：]?\\s*(.+?)" + SENT_END_CN, "lesson"),
        ("注意\\s*[:：]?\\s*(.+?)" + SENT_END_CN, "caution"),
        ("避免\\s*[:：]?\\s*(.+?)" + SENT_END_CN, "avoid"),
        ("应该\\s*[:：]?\\s*(.+?)" + SENT_END_CN, "should"),
        ("不应该\\s*[:：]?\\s*(.+?)" + SENT_END_CN, "should_not"),
    ]
    for pattern, rel_type in lesson_patterns:
        for m in re.finditer(pattern, text):
            target = m.group(1)
            if target and target.strip():
                relations.append({
                    "type": "lesson",
                    "subtype": rel_type,
                    "target": target.strip(),
                    "confidence": 0.7
                })
    
    return relations


def detect_contradiction(new_text, old_text):
    """
    矛盾检测
    
    简单实现：检查偏好/决策的关键词是否相反
    """
    contradictions = []
    
    # 偏好矛盾检测
    pref_pairs = [
        ("喜欢\\s*[:：]?\\s*(.+?)" + SENT_END_CN, "讨厌\\s*[:：]?\\s*(.+?)" + SENT_END_CN, 1),
        ("喜欢\\s*[:：]?\\s*(.+?)" + SENT_END_CN, "不喜欢\\s*[:：]?\\s*(.+?)" + SENT_END_CN, 1),
        ("prefer\\s+(.+?)[,;.!?]|$", "hate\\s+(.+?)[,;.!?]|$", 1),
    ]
    
    for p1, p2, group_idx in pref_pairs:
        m1 = re.search(p1, new_text)
        m2 = re.search(p2, old_text)
        if m1 and m2:
            g1 = m1.group(group_idx) if m1.groups() else m1.group(0)
            g2 = m2.group(group_idx) if m2.groups() else m2.group(0)
            if g1 and g2 and g1.strip() and g2.strip():
                contradictions.append({
                    "type": "preference_conflict",
                    "new": g1.strip(),
                    "old": g2.strip(),
                    "severity": "medium"
                })
    
    # 决策矛盾检测
    dec_pattern = "(?:决定|选择|方案)\\s*[:：]?\\s*(.+?)" + SENT_END_CN
    new_decisions = re.findall(dec_pattern, new_text)
    old_decisions = re.findall(dec_pattern, old_text)
    
    for nd in new_decisions:
        for od in old_decisions:
            nd_words = set(jieba.lcut(nd.lower()))
            od_words = set(jieba.lcut(od.lower()))
            overlap = len(nd_words & od_words) / max(len(nd_words | od_words), 1)
            if overlap < 0.3 and len(nd) > 5 and len(od) > 5:
                contradictions.append({
                    "type": "decision_conflict",
                    "new": nd.strip(),
                    "old": od.strip(),
                    "severity": "high"
                })
    
    return {
        "has_contradiction": len(contradictions) > 0,
        "contradictions": contradictions
    }


def analyze(text):
    """综合分析：实体 + 关键词 + 关系"""
    entities = extract_entities(text)
    keywords = extract_keywords(text)
    relations = infer_relations(text)
    
    quality = 0
    if entities:
        quality += min(30, len(entities) * 5)
    if relations:
        quality += min(40, len(relations) * 10)
    if keywords:
        quality += min(30, len(keywords) * 3)
    
    return {
        "entities": entities,
        "keywords": keywords,
        "relations": relations,
        "quality_score": min(100, quality),
        "summary": f"提取 {len(entities)} 个实体, {len(keywords)} 个关键词, {len(relations)} 个关系"
    }


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "help"
    
    if cmd == "intent" and len(sys.argv) > 2:
        result = classify_intent(sys.argv[2])
        print(json.dumps(result, ensure_ascii=False))
    elif cmd == "entities" and len(sys.argv) > 2:
        result = extract_entities(sys.argv[2])
        print(json.dumps(result, ensure_ascii=False))
    elif cmd == "keywords" and len(sys.argv) > 2:
        n = int(sys.argv[3]) if len(sys.argv) > 3 else 8
        result = extract_keywords(sys.argv[2], n)
        print(json.dumps(result, ensure_ascii=False))
    elif cmd == "relations" and len(sys.argv) > 2:
        result = infer_relations(sys.argv[2])
        print(json.dumps(result, ensure_ascii=False))
    elif cmd == "contradict" and len(sys.argv) > 3:
        result = detect_contradiction(sys.argv[2], sys.argv[3])
        print(json.dumps(result, ensure_ascii=False))
    elif cmd == "analyze" and len(sys.argv) > 2:
        result = analyze(sys.argv[2])
        print(json.dumps(result, ensure_ascii=False))
    elif cmd == "importance" and len(sys.argv) > 2:
        text = sys.argv[2]
        files = sys.argv[3].split(",") if len(sys.argv) > 3 and sys.argv[3] else []
        explicit = "记住" in text or "remember" in text.lower()
        correction = any(w in text.lower() for w in ["不", "错了", "纠正", "no", "wrong", "correct"])
        result = score_importance(text, files_modified=files, user_explicit_remember=explicit, is_correction=correction)
        print(json.dumps({"importance": result}, ensure_ascii=False))
    elif cmd == "should_capture" and len(sys.argv) > 2:
        result = should_capture(sys.argv[2])
        print(json.dumps(result, ensure_ascii=False))
    elif cmd == "security_scan" and len(sys.argv) > 2:
        result = security_scan(sys.argv[2])
        print(json.dumps({"threats": result, "safe": len(result) == 0}, ensure_ascii=False))
    elif cmd == "memory_used" and len(sys.argv) > 3:
        result = memory_used_in_reply(sys.argv[2], sys.argv[3])
        print(json.dumps(result, ensure_ascii=False))
    elif cmd == "estimate_tokens" and len(sys.argv) > 2:
        result = estimate_tokens(sys.argv[2])
        print(json.dumps(result, ensure_ascii=False))
    else:
        print(__doc__)
