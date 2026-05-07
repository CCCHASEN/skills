#!/usr/bin/env python3
"""My-AI 全局配置与常量"""

import sys
import logging
from pathlib import Path

# ======= 可移植路径配置 =======
SCRIPT_DIR = Path(__file__).parent.resolve()
BASE_DIR = SCRIPT_DIR.parent.resolve()
MEMORY_DIR = BASE_DIR / "memory"

# 四层架构路径
IDENTITY_DIR = MEMORY_DIR / "identity"
KNOWLEDGE_DIR = MEMORY_DIR / "knowledge"
CONTEXT_DIR = MEMORY_DIR / "context"
ARCHIVE_DIR = MEMORY_DIR / "archive"
UNSORTED_DIR = ARCHIVE_DIR / "unsorted"
DAILY_DIR = MEMORY_DIR / "daily"
HANDOFF_DIR = MEMORY_DIR / "handoffs"
RECOVERY_DIR = MEMORY_DIR / "recovery"

ACTIVE_MD = CONTEXT_DIR / "ACTIVE.md"
KNOWLEDGE_MD = KNOWLEDGE_DIR / "KNOWLEDGE.md"
USER_MD = IDENTITY_DIR / "USER.md"
SOUL_MD = IDENTITY_DIR / "SOUL.md"

PYTHON = sys.executable

# ======= 常量配置 =======
CACHE_BUDGET = 2000  # token budget for bootstrap files
SEMANTIC_DEDUP_THRESHOLD = 0.15  # distance < 0.15 = similarity > 0.85

# ======= Context Log 配置 =======
JOURNAL_DIR = MEMORY_DIR / "journal"
CONTEXT_LOG_MD = JOURNAL_DIR / "current.md"
CONTEXT_LOG_MAX_TURNS = 30      # 最大保留轮数
CONTEXT_LOG_MAX_TOKENS = 4000   # 最大 token 估算
CONTEXT_LOG_FLUSH_THRESHOLD = 25  # 触发 flush 的轮数阈值

# ======= jieba 初始化 =======
import jieba
import jieba.posseg as pseg

jieba.setLogLevel(logging.CRITICAL)
jieba.initialize()

# 添加常见领域术语，避免切词错误导致话题检测误判
_JIEBA_CUSTOM_WORDS = [
    "k线图", "macd", "rsi", "布林带", "成交量", "买卖点",
    "超买", "超卖", "均线", "涨停", "跌停", "龙头股",
    "人工智能", "机器学习", "深度学习", "神经网络",
    "区块链", "比特币", "以太坊", "nft",
    "react", "vue", "angular", "typescript", "javascript",
    "docker", "kubernetes", "aws", "azure", "gcp",
]
for w in _JIEBA_CUSTOM_WORDS:
    jieba.add_word(w)

# ======= 轻量停用词（用于话题切换检测）— 扩展版 =======
_TOPIC_STOPWORDS = set([
    # 中文虚词/代词
    "的", "了", "是", "在", "我", "有", "和", "就", "不", "人", "都", "一", "上", "也", "很", "到", "说", "要", "去", "你", "会", "着", "没有", "看", "好", "自己", "这", "那", "什么", "怎么", "怎么样", "如何", "吗", "吧", "呢", "啊", "嗯", "哦",
    "我们", "你们", "他们", "它们", "咱们", "大家", "别人", "有人", "没人",
    "聊聊", "谈谈", "说说", "问问", "讨论", "聊", "谈", "说", "问", "想", "觉得", "感觉",
    "还有", "也是", "就是", "不是", "但是", "因为", "所以", "然后", "接着", "最后", "首先",
    "一下", "一些", "一点", "一种", "一个", "一起", "一直", "一样",
    "可以", "可能", "应该", "需要", "想要", "喜欢", "觉得", "认为", "知道", "了解", "明白",
    "现在", "今天", "明天", "昨天", "刚才", "后来", "之前", "之后",
    # 英文停用词
    "the", "a", "an", "is", "are", "was", "were", "be", "been", "being",
    "have", "has", "had", "do", "does", "did", "will", "would", "could",
    "should", "may", "might", "must", "can", "need", "shall",
    "this", "that", "these", "those", "it", "its", "they", "them", "their",
    "and", "or", "but", "if", "then", "else", "when", "where", "why", "how",
    "to", "of", "in", "for", "on", "with", "at", "by", "from", "as", "into",
    "i", "you", "he", "she", "we", "us", "me", "my", "your", "his", "her",
    "let", "lets", "talk", "discuss", "chat", "about", "tell", "ask",
])

# Topic state 文件路径（持久化偏离 streak）
_TOPIC_STATE_FILE = MEMORY_DIR / ".topic_state.json"
