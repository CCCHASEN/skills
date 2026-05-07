# My-AI v1.2 开发者完全指南

> 版本: 1.2 | 总代码量: ~4,727 行 (10 个 Python 模块 + 6 个系统文档)  
> 目标: 读完本文档，你可以理解、修改、扩展 My-AI 的每一行代码。

---

## 目录

1. [项目概述](#1-项目概述)
2. [五层存储架构](#2-五层存储架构)
3. [十大模块详解](#3-十大模块详解)
4. [完整数据流](#4-完整数据流-pre--post--boot)
5. [核心算法](#5-核心算法)
6. [存储引擎深入](#6-存储引擎深入)
7. [配置与扩展](#7-配置与扩展)
8. [已知问题与路线图](#8-已知问题与路线图)

---

## 1. 项目概述

My-AI 是一个为 **Kimi CLI** 设计的持久记忆 Skill。它不依赖后台进程，完全通过 CLI 的 `pre/post/boot` 钩子驱动，每轮对话自动执行记忆搜索与保存。

### 1.1 设计约束

| 约束 | 原因 | 影响 |
|------|------|------|
| 纯 CLI，无后台进程 | Kimi CLI Skill 架构限制 | 所有操作必须能在 30 秒内完成 |
| 单用户本地运行 | 无需多租户 | 无需认证、并发控制极简 |
| 可移植 | 用户可能换电脑 | 所有路径基于 `__file__` 自动推导 |
| 自包含 venv | 避免污染系统 Python | `setup.sh` 一键初始化 |

### 1.2 项目结构

```
my-ai/
├── SKILL.md                          # Skill 定义：触发词、权限、流程
├── setup.sh                          # 一键初始化脚本
├── .gitignore                        # 忽略 venv/DB/运行时文件
├── scripts/                          # 核心 Python 模块（10 个）
│   ├── config.py      (82 行)       # 全局配置、路径、jieba 初始化
│   ├── utils.py       (53 行)       # 工具函数：subprocess、token 估算、Unicode 清理
│   ├── extract.py     (829 行)      # NLP 引擎：意图/实体/关键词/关系/矛盾/安全扫描
│   ├── context.py     (488 行)      # 上下文日志 + 三重信号话题切换检测
│   ├── memory_ops.py  (392 行)      # 外部脚本封装、搜索排序、图操作、DB 写入
│   ├── maintenance.py (567 行)      # 维护任务、Dreaming、Recovery、Handoff
│   ├── my_ai_turn.py  (443 行)      # CLI 入口与编排（Pre/Post/Boot/Status）
│   ├── session_db.py  (663 行)      # SQLite + FTS5 Porter/Trigram + Hebbian 衰减
│   ├── vector_memory.py (287 行)    # ChromaDB 向量记忆（增删改查/去重/同步）
│   └── memory_graph.py (279 行)     # NetworkX 记忆关系图（实体关联/PageRank）
├── memory/                           # 五层存储目录
│   ├── identity/
│   │   ├── SOUL.md                   # 人格/身份/规则（永不丢弃）
│   │   └── USER.md                   # 用户画像/偏好
│   ├── knowledge/
│   │   └── KNOWLEDGE.md              # 知识/决策/教训
│   ├── context/
│   │   └── ACTIVE.md                 # 当前任务/待办/阻塞
│   ├── journal/
│   │   └── current.md                # 实时上下文日志（每轮追加）
│   ├── daily/                        # 每日归档
│   ├── archive/
│   │   ├── unsorted/                 # 未分类记忆
│   │   ├── patterns/                 # 模式归档
│   │   ├── sessions/                 # 会话归档
│   │   └── deprecated/               # 过期记忆
│   ├── handoffs/                     # 会话接续文件
│   ├── recovery/                     # 恢复快照
│   ├── sessions/                     # 压缩后的会话摘要
│   ├── system/                       # 系统文档（本文档所在目录）
│   ├── .sessions.db                  # SQLite 主数据库（gitignore）
│   ├── .chroma/                      # ChromaDB 向量库（gitignore）
│   └── .memory_graph.pkl             # 图持久化文件（gitignore）
└── agents/                           # 多 Agent Prompt 模板（概念层）
    ├── coder.md
    ├── compressor.md
    ├── purifier.md
    ├── researcher.md
    └── scribe.md
```

---

## 2. 五层存储架构

My-AI 采用分层存储，每层有不同的生命周期、访问速度和保留策略。

```
┌─────────────────────────────────────────────────────────────┐
│ Layer 5: Identity (15%)                                     │
│   identity/SOUL.md + identity/USER.md                       │
│   → 永不丢弃，Boot 时优先加载                                 │
├─────────────────────────────────────────────────────────────┤
│ Layer 4: Knowledge + Active (20%)                           │
│   knowledge/KNOWLEDGE.md + context/ACTIVE.md                │
│   → 可压缩，按需加载，重要性 >=5 才写入                       │
├─────────────────────────────────────────────────────────────┤
│ Layer 3: Journal (25%)                                      │
│   journal/current.md + journal/YYYY-MM-DD.md                │
│   → 每轮实时追加，定期 flush 归档                             │
├─────────────────────────────────────────────────────────────┤
│ Layer 2: Session History (25%)                              │
│   CLI 原生上下文（LLM 内部）                                   │
│   → 中间轮次可被摘要替换                                       │
├─────────────────────────────────────────────────────────────┤
│ Layer 1: Recent Turns (15%)                                 │
│   最近 3-5 轮 + 工具输出                                       │
│   → 永不丢弃，保证上下文连贯                                   │
└─────────────────────────────────────────────────────────────┘
```

### 2.1 各层详细说明

#### Layer 5: Identity
- **SOUL.md**: AI 人格、核心规则、记忆协议、禁止事项。由 LLM 根据用户指令主动维护。
- **USER.md**: 用户画像（称呼、风格、红线、期望）。同样由 LLM 主动维护。
- **特点**: 纯文本 Markdown，无格式约束，Boot 时必加载。

#### Layer 4: Knowledge + Active
- **KNOWLEDGE.md**: 长期知识。技术决策、教训、项目信息、模式。目标 < 500 行。
- **ACTIVE.md**: 短期工作记忆。当前项目、待办、阻塞。目标 < 80 行。
- **特点**: 重要性 >= 5 且通过内容过滤才写入。LLM 主动维护，非脚本自动写入。

#### Layer 3: Journal
- **current.md**: 当前会话的完整对话记录。每轮自动追加（User + Thinking + Assistant + Tools + Files）。
- **YYYY-MM-DD.md**: 归档后的历史日志。Flush 时 current.md 的内容迁移至此。
- **特点**: Append-only，脚本自动维护，LLM 不直接读写。

#### Layer 2+1: CLI 原生上下文
- LLM 内部的对话历史。Pre 命令返回 `context_history` 注入到 LLM 提示中。
- 分层策略: 最近 3 轮完整保留，3-10 轮仅保留 User+Assistant（截断到 200 字）。

---

## 3. 十大模块详解

### 3.1 config.py — 全局配置中心

**职责**: 所有模块共享的路径定义、常量、jieba 初始化。

**关键设计**:
```python
# 可移植路径：基于本文件位置自动推导
SCRIPT_DIR = Path(__file__).parent.resolve()
BASE_DIR = SCRIPT_DIR.parent.resolve()
MEMORY_DIR = BASE_DIR / "memory"
```

这意味着整个项目目录可以复制到任何位置，代码自动适应新路径。

**核心常量**:
| 常量 | 值 | 说明 |
|------|-----|------|
| `CACHE_BUDGET` | 2000 | Bootstrap 文件 token 预算 |
| `SEMANTIC_DEDUP_THRESHOLD` | 0.15 | 向量距离 < 0.15 触发语义合并 |
| `CONTEXT_LOG_MAX_TURNS` | 30 | 上下文日志最大轮数 |
| `CONTEXT_LOG_MAX_TOKENS` | 4000 | 上下文日志最大 token 数 |
| `CONTEXT_LOG_FLUSH_THRESHOLD` | 25 | 触发 flush 的轮数阈值 |

**jieba 自定义词典**:
```python
_JIEBA_CUSTOM_WORDS = [
    "k线图", "macd", "rsi", "布林带", "成交量",  # 金融术语
    "人工智能", "机器学习", "深度学习", "神经网络",  # AI 术语
    "区块链", "比特币", "以太坊", "nft",            # 区块链
    "react", "vue", "angular", "typescript",        # 前端
    "docker", "kubernetes", "aws", "azure", "gcp",   # 云原生
]
```

金融/技术术语被加入 jieba 词典是为了**避免话题检测误判**。例如"K线图"如果被切成"K"+"线图"，会与"股票"话题的关键词集合完全没有交集，导致子话题被误判为话题切换。

**停用词扩展** (103 个):
```python
_TOPIC_STOPWORDS = set([
    # 中文虚词 + 动词短语（聊聊/谈谈/怎么样/如何）
    # 英文停用词
    # 新增: "let", "talk", "discuss", "chat", "about", "tell", "ask"
])
```

### 3.2 utils.py — 通用工具

**三个函数**:

1. `run_cmd(cmd_list, cwd=None)`: subprocess wrapper，30 秒超时。所有脚本间通信的基础。
2. `run_script(script_name, *args)`: 基于 `run_cmd` 的快捷调用，自动拼接 `.venv/bin/python scripts/xxx.py`。
3. `estimate_tokens_fast(text)`: 本地 token 估算，无需 subprocess。
   - 中文: ~1 token/字
   - 英文: ~1.3 tokens/词
   - 其他: ~0.25 tokens/字符
4. `_sanitize_text(text)`: Unicode 清理。移除 surrogate pairs (U+D800-U+DFFF) 和非法控制字符。这个函数在 v1.2 中修复了多次编码错误导致的崩溃。

### 3.3 extract.py — NLP 提取引擎

**829 行，10 个 CLI 命令**，是系统中最复杂的独立模块。

#### 3.3.1 意图分类 (classify_intent)

```python
scores = {"WHY": 0, "WHEN": 0, "ENTITY": 0, "WHAT": 0}
```

- **WHY**: "为什么", "原因", "why", "reason", "explain" → 搜索时增强 "决定 原因 因为"
- **WHEN**: "什么时候", "之前", "上次", "when", "before", "recently" → 搜索时附加当前日期
- **ENTITY**: "什么是", "谁是", "what is", "who is" → 搜索时只用实体名
- **WHAT**: 默认

意图只影响**查询增强**，不影响搜索范围。所有来源始终搜索。

#### 3.3.2 实体提取 (extract_entities)

四层提取策略:
1. **jieba 词性标注**: `nr`(人名), `nt`(机构), `ns`(地名)
2. **自定义词典匹配**: config.py 中定义的技术术语
3. **正则补充**: Python/JavaScript/React/PostgreSQL/Docker 等
4. **文件名/URL/日期**: 正则模式匹配

返回格式:
```json
{"text": "Python", "type": "TECH", "start": 10, "end": 16}
```

#### 3.3.3 关键词提取 (extract_keywords)

基于 jieba 词性过滤 + 词频 + 位置加权:
- 只保留名词、动词、形容词、英文词
- 停用词过滤
- **句首词 ×1.5，句尾词 ×1.3**

#### 3.3.4 关系推理 (infer_relations)

四种关系类型:
| 类型 | 模式示例 | 置信度 |
|------|---------|--------|
| causal | "因为...所以...", "由于...因此..." | 0.8 |
| preference | "偏好...", "喜欢...", "prefer..." | 0.75 |
| decision | "决定...", "选择...", "decided to..." | 0.85 |
| lesson | "教训...", "注意...", "避免..." | 0.7 |

#### 3.3.5 重要性评分 (score_importance)

基础分 3 分，多维信号叠加:
```
+4: 用户显式指令 ("记住这个")
+2: 记忆指令关键词 ("待办", "改名叫", "人格", "角色")
+3: 被纠正
+2 per file: 文件修改 (max +4)
+0-3: 实体密度 (每 2 个实体 +1)
+0-4: 关系类型 (decision/preference/lesson 每个 +2)
+1: 否定/纠正语言 ("不", "错了", "wrong")
+1: 长度适中 (50-500 字符)
-1: 过长 (>2000 字符)
-2: 过短 (<30 字符)
+1: 包含代码块
```

最终 clamp 到 [1, 10]。

#### 3.3.6 内容过滤 (should_capture)

**双层过滤**: extract.py 提供基础判断 + memory_ops.py 叠加本地 heuristics。

extract.py 的过滤逻辑:
1. 系统消息过滤（正则匹配系统提示风格）
2. 低价值过滤（纯礼貌用语、过短文本）— 记忆指令可豁免
3. 原始数据过滤（代码行比例 > 70% 且长度 > 500）
4. 质量评分 < 15 → 不保存

memory_ops.py 的增强过滤（见 3.5 节）:
- 强制保留: 用户显式请求、用户观点、身份变更
- 强制过滤: 纯知识问答、闲聊问候

#### 3.3.7 安全扫描 (security_scan)

正则模式检测:
| 类别 | 示例 | 严重度 |
|------|------|--------|
| INJECTION | "ignore all previous instructions" | high |
| EXFILTRATION | "curl ... $ENV_VAR" | high |
| INVISIBLE_UNICODE | U+200B-U+200F 等 | high |
| EVAL | "eval(" | high |
| CREDENTIAL_LEAK | "password: xxx" | high |
| HTML_COMMENT | "<!-- ... -->" | low (仅标记含可疑词的) |

#### 3.3.8 矛盾检测 (detect_contradiction)

两种检测:
1. **偏好冲突**: 新文本"喜欢X" + 旧文本"讨厌X"
2. **决策冲突**: 同一主题下关键词重叠率 < 30% 的不同决策

#### 3.3.9 记忆使用检测 (memory_used_in_reply)

检测 assistant_reply 中是否使用了某条记忆:
- 提取记忆关键词，计算在回复中的覆盖率
- 长片段匹配（>=10 字的句子直接出现在回复中）
- coverage >= 0.3 判定为"已使用"

#### 3.3.10 Token 估算 (estimate_tokens)

比 `utils.py` 更精确:
- 检测代码比例（代码模式: 1.2 token/字符）
- 混合文本: 中文 1.0 + 英文 0.75 + 其他 0.5

---

### 3.4 context.py — 上下文日志与话题切换检测

**488 行，两大职责**:

#### 3.4.1 上下文日志管理

三个核心函数:
- `append_context_log()`: 每轮追加到 `journal/current.md`。包含 Turn 编号、时间戳、User/Thinking/Assistant/Tools/Files。
- `read_context_log(limit=20)`: 用正则解析 markdown，返回结构化 turn 列表。
- `flush_context_log()`: 归档到 `journal/YYYY-MM-DD.md`，保留最近 5 轮作为衔接。

**分层读取策略** (在 `cmd_pre` 中实现):
```python
for i, turn in enumerate(context_history):
    if i < len(context_history) - 3:
        # 旧轮次：删除 thinking/tools/files，截断到 200 字
        turn.pop("thinking", None)
        turn.pop("tools", None)
        turn.pop("files", None)
    else:
        # 最近 3 轮：保留所有字段，截断到 250 字
        pass
```

#### 3.4.2 三重信号话题切换检测

这是 v1.2 的核心创新。不再固定 25 轮 flush，而是**动态检测话题切换**。

**信号 1: TF-IDF 加权关键词重叠**
```python
session_weights = _compute_tfidf_weights(recent_history, decay_rate=0.8)
overlap = curr_words & set(session_weights.keys())
overlap_weight = sum(session_weights.get(w, 0) for w in overlap)
curr_only_weight = sum(1.0 for w in curr_words - set(session_weights.keys()))
keyword_sim = overlap_weight / (overlap_weight + curr_only_weight + 1e-6)
```

TF-IDF 权重计算:
- TF: 词在当前轮的出现频率
- IDF: log(总轮数 / 包含该词的轮数 + 1) + 1
- **滑动窗口衰减**: 越早的轮次权重越低 (`decay_rate ** (n - 1 - i)`)

**信号 2: ChromaDB 向量余弦相似度**
```python
# 与最近 3 个 query 的 embedding 比较平均相似度
vector_sim = avg(cosine_similarity(current_emb, q.emb) for q in last_3_queries)
```

使用 `chromadb.utils.embedding_functions.DefaultEmbeddingFunction()`，384 维向量。Embedding 缓存到 `.query_embeds.json`，最多保留 10 个。

**信号 3: 综合偏离度**
```python
composite_drift = keyword_weight * (1 - keyword_sim) + vector_weight * (1 - vector_sim)
# keyword_weight = 0.55~0.75, vector_weight = 0.25~0.45
```

**状态机决策**:
```
强偏离 (composite > 0.85 + len >= 3 + vector < 0.35) → 立即切换
有关键词重叠 (keyword >= 0.15 or vector >= 0.55) → 重置 streak
偏离 (streak +1) → streak >= 2 或 composite > 0.82 确认切换
```

Streak 持久化到 `.topic_state.json`，避免跨轮次丢失状态。

**Flush 触发条件** (三者任一):
1. 话题切换确认
2. Token 压力 >= 4000
3. 轮数 >= 40 (保底)

---

### 3.5 memory_ops.py — 记忆操作中心

**392 行，四大职责**:

#### 3.5.1 外部脚本封装

所有 NLP 能力通过 `run_script("extract.py", ...)` 调用。所有模块间通信都通过 CLI 参数 + JSON stdout，保持松耦合。

#### 3.5.2 内容过滤 (should_capture)

**本地 heuristics + 外部模型双层过滤**:

```
强制保留（最高优先级）:
  - 用户显式请求: "记住", "remember", "以后", "always", "prefer", "别忘了"
  - 用户观点: "我觉得", "我认为", "我喜欢", "I think", "I feel"
  - 身份变更: "改名叫", "你的人格", "说话风格", "角色", "人设"

强制过滤:
  - 闲聊问候 (<100 字, 无个人标记): "你好", "谢谢", "再见"
  - 纯知识问答 (疑问词开头 + 无个人标记 + 长度>200 或 <200)
    "什么是", "怎么", "如何", "what is", "how to"

兜底: 外部模型判断
```

**设计哲学**: 只保存用户**明确要求记住的**、**用户观点/态度**、**身份/偏好信息**。纯知识（可搜索获取的）不保存。

#### 3.5.3 搜索与排序

**四源搜索**:
1. **ACTIVE.md 关键词匹配**: 简单分块 + query 词频打分
2. **KNOWLEDGE.md 关键词匹配**: 同上
3. **ChromaDB 语义搜索**: `vector_memory.py search`，返回带距离的结果
4. **SQLite FTS5 双索引搜索**: Porter (英文词干) + Trigram (中文子串)

**三维排序** (rank_memories_3d):
```python
Score = 0.4 * relevance + 0.35 * importance + 0.25 * recency + entity_boost

# importance 使用动态重要性（Recall-Driven）
dynamic_importance = base_importance * (1 + ln(total_recalls + 1) * 0.15) * usage_boost

# recency 使用指数衰减
recency = e^(-0.05 * days_old)

# entity_boost: 结果包含查询实体时 +0.05 per entity, max 0.2
```

**Recall-Driven Importance**:
- 每次 pre 搜索到的记忆记录到 `recall_log` (memory_id, query, was_used)
- 被召回次数越多 → 重要性提升（log 增长减缓饱和）
- 被召回且实际被使用 → 额外加成 (usage_boost = 0.8 + used_rate * 0.4)
- 效果: 高频知识自动上浮，冷门知识自然下沉

#### 3.5.4 数据库写入

**SessionDB 写入**:
```python
insert_to_session_db(role, content)  # 所有消息都写入 SQLite
```

**向量库写入** (带语义去重):
```python
insert_to_vector_db(content, tags, importance)
  1. semantic_dedup_check(content[:500])  # 搜索最相似的已有记忆
  2. 如果 distance < 0.15 (相似度 > 0.85):
     - 合并文本 (拼接 + 截断到 1000 字)
     - importance + 1
     - 标记 "merged:1"
     - 更新 vector_memory.py
  3. 否则: 创建新条目
```

**记忆图更新**:
```python
graph_add(memory_id, content, tags)
  # 创建记忆节点 + 提取实体节点 + "mentions" 边
```

---

### 3.6 maintenance.py — 维护系统

**567 行，六大职责**:

#### 3.6.1 上下文压力检测

多指标综合评分:
```python
score = 0
if active_lines > 100: score += 3      # ACTIVE.md 过长
elif active_lines > 60: score += 2
elif active_lines > 30: score += 1

if knowledge_lines > 500: score += 2   # KNOWLEDGE.md 过长
elif knowledge_lines > 300: score += 1

if daily_size > 100: score += 1        # 今日日志过长

# score >= 5: high, >= 3: medium, else: low
```

#### 3.6.2 安全扫描

Boot 时扫描所有 bootstrap 文件，检测威胁。

#### 3.6.3 自适应压缩 (precompact_flush)

根据意图类型选择结构化模板:
- coding: Goal/Progress(Done/In Progress/Blocked)/Decisions/Files/Next/Critical
- debugging: 同上，Blocked 改为"错误信息+根因假设"
- discussion: 同上，Progress 改为"已达成共识/正在讨论/分歧点"
- default: 通用模板

#### 3.6.4 上下文生命周期 (classify_context_lifetime)

```
EPHEMERAL:  "先不管", "暂时", "just for now" → 不入任何存储
SESSION:    "刚才", "之前说的", "基于刚才" → 仅入 SessionDB
PERSISTENT: 默认 → 正常写入 Markdown + DB
```

#### 3.6.5 Handoff 生成

退出时生成接续文件:
- 保存到 `handoffs/YYYYMMDD_HHMMSS.md`
- 包含会话信息、当前状态、恢复命令
- 同时保存 recovery snapshot 到 SQLite

#### 3.6.6 智能保存路由 (determine_target_file)

根据内容和重要性决定保存位置:
```
用户显式要求记忆 → 根据内容类型 (任务→ACTIVE, 知识→KNOWLEDGE)
人格/身份变更 → SOUL.md
用户偏好 → USER.md
纠正/教训 → KNOWLEDGE.md
importance >= 8 → KNOWLEDGE.md 或 SOUL.md (根据内容信号)
importance >= 5 → ACTIVE.md (任务类) 或 KNOWLEDGE.md (知识类)
importance >= 3 → 仅 SessionDB + 向量库
importance < 3 → 丢弃
```

#### 3.6.7 三阶段 Dreaming (记忆巩固)

```
Phase 1: Light Sleep
  - 读取最近 7 天日志
  - 分块 → Jaccard 去重 (阈值 0.9)

Phase 2: REM Sleep
  - 关键词共现网络 (networkx Graph)
  - 提取中心度最高的主题

Phase 3: Deep Sleep
  - 六维评分: relevance(0.30) + frequency(0.24) + query_diversity(0.15) + recency(0.15) + consolidation(0.10) + conceptual_richness(0.06)
  - score >= 0.6 → 晋升到 KNOWLEDGE.md
```

#### 3.6.8 维护任务 (run_maintenance)

Boot 时自动执行:
1. ACTIVE.md / KNOWLEDGE.md 长度检查
2. 清理 30 天前的 unsorted 文件到 archive/old/
3. 清理 90 天前的 SessionDB 消息
4. 向量库同步（从 Markdown 文件）
5. 图统计
6. **Hebbian 衰减**: 未使用记忆每天衰减 2%，冷记忆自动归档

---

### 3.7 session_db.py — SQLite 数据库引擎

**663 行，独立 CLI 工具**。

#### 3.7.1 数据库 Schema

```sql
-- 会话表
CREATE TABLE sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source TEXT DEFAULT 'cli',
    title TEXT,
    summary TEXT,
    parent_session_id INTEGER,      -- Session Lineage
    end_reason TEXT,
    message_count INTEGER DEFAULT 0,
    tool_call_count INTEGER DEFAULT 0,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    ended_at TEXT
);

-- 消息表
CREATE TABLE messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id INTEGER,
    role TEXT,
    content TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

-- 记忆条目表（含 Hebbian 衰减字段）
CREATE TABLE memories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source TEXT,
    content TEXT,
    tags TEXT,
    score INTEGER,
    activation REAL DEFAULT 1.0,        -- Hebbian 激活值
    decay_score REAL DEFAULT 1.0,       -- 衰减系数
    access_count INTEGER DEFAULT 0,     -- 被访问次数
    last_accessed TEXT,                 -- 最后访问时间
    archived BOOLEAN DEFAULT 0,         -- 是否已归档
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

-- 状态元数据表
CREATE TABLE state_meta (key TEXT PRIMARY KEY, value TEXT, updated_at TEXT);

-- 召回日志表
CREATE TABLE recall_log (id INTEGER PRIMARY KEY, memory_id TEXT, query TEXT, was_used BOOLEAN DEFAULT 0, recalled_at TEXT);

-- 恢复快照表
CREATE TABLE recovery_snapshots (id INTEGER PRIMARY KEY, session_id INTEGER, content TEXT, created_at TEXT);

-- FTS5 虚拟表（Porter tokenizer）
CREATE VIRTUAL TABLE messages_fts USING fts5(content, content_rowid=id, tokenize='porter');
CREATE VIRTUAL TABLE memories_fts USING fts5(content, content_rowid=id, tokenize='porter');

-- FTS5 虚拟表（Trigram tokenizer）
CREATE VIRTUAL TABLE messages_fts_trigram USING fts5(content, content_rowid=id, tokenize='trigram');
```

#### 3.7.2 FTS5 双索引策略

| 索引 | Tokenizer | 适用场景 |
|------|-----------|---------|
| Porter | 英文词干化 | "running" 匹配 "run" |
| Trigram | 三字符子串 | "股票" 匹配 "股票价格"（"股票"是 4 字符，Trigram 匹配"股价"子串） |

**实际行为**:
- Porter 对中文**几乎无效**（中文没有词干变化），但对英文效果很好
- Trigram 对中文有效，但要求查询词至少 3 个字符（"记住"只有 2 字符，Trigram 无法匹配）
- 这也是为什么 "Python" 能匹配但 "记住" 有时不能匹配的原因

#### 3.7.3 Hebbian 衰减

```sql
-- 每次维护时执行
UPDATE memories 
SET activation = MAX(0.0, activation * (1 - decay_rate)),
    decay_score = MAX(0.0, decay_score * (1 - decay_rate))
WHERE archived = 0;

-- 冷记忆归档
UPDATE memories 
SET archived = 1
WHERE archived = 0 
  AND activation < archive_threshold
  AND (last_accessed IS NULL OR last_accessed < datetime('now', '-7 days'))
  AND created_at < datetime('now', '-7 days');
```

- 衰减率: 2% (可配置)
- 归档阈值: activation < 0.3
- 访问强化: 被召回时 activation +0.3 (上限 5.0)

#### 3.7.4 向后兼容

```python
# 为旧数据库添加新列
try:
    conn.execute("ALTER TABLE memories ADD COLUMN activation REAL DEFAULT 1.0")
except:
    pass
```

每个新字段都用 try/except 包裹，确保旧数据库平滑升级。

---

### 3.8 vector_memory.py — ChromaDB 向量库

**287 行，独立 CLI 工具**。

#### 3.8.1 核心操作

```python
add_memory(content, tags, source)       # UUID 作为主键
update_memory(doc_id, content, tags)    # 语义合并时调用
delete_memory(doc_id)                   # 删除
search(query, limit)                    # 语义搜索，返回带距离
dedup(content, threshold=0.15)          # 语义去重检查
sync()                                  # 从 Markdown 文件同步
stats()                                 # 统计
```

#### 3.8.2 语义去重

```python
def semantic_dedup_search(content, threshold=0.15):
    results = collection.query(query_texts=[content], n_results=1)
    if results["distances"][0][0] <= threshold:
        return {"id": ..., "similarity": 1.0 - distance}
    return None
```

- threshold=0.15 意味着相似度 > 0.85 触发合并
- 合并时: 文本拼接 + 截断到 1000 字 + importance +1 + 标记 "merged:1"

#### 3.8.3 同步机制

```python
def sync_from_files():
    # 扫描 identity/SOUL.md, identity/USER.md, knowledge/KNOWLEDGE.md, context/ACTIVE.md
    # 按 ## 分割成条目，逐个加入向量库
    # doc_id 格式: "{filename}_{uuid.hex[:8]}"
```

Boot 时自动调用，确保向量库与 Markdown 文件一致。

---

### 3.9 memory_graph.py — NetworkX 记忆关系图

**279 行，独立 CLI 工具**。

#### 3.9.1 图结构

```python
G = nx.MultiDiGraph()

# 记忆节点
G.add_node(memory_id, type="memory", content=..., keywords=..., tags=..., created_at=...)

# 实体节点
G.add_node(f"entity:{type}:{name}", type="entity", entity_type=..., name=...)

# 边
G.add_edge(memory_id, entity_id, relation="mentions", weight=1.0)
```

#### 3.9.2 查询方式

1. **图遍历** (`find_related`): BFS 遍历，按权重排序，支持深度限制
2. **文本查询** (`query_by_text`): 提取查询关键词，与节点关键词匹配 + 实体匹配，综合打分

#### 3.9.3 持久化

Pickle 到 `.memory_graph.pkl`。启动时自动加载。

---

### 3.10 my_ai_turn.py — 编排入口

**443 行，CLI 主控**。

#### 3.10.1 命令列表

```bash
.venv/bin/python scripts/my_ai_turn.py pre '<user_query>'
.venv/bin/python scripts/my_ai_turn.py post '<turn_json>'
.venv/bin/python scripts/my_ai_turn.py boot
.venv/bin/python scripts/my_ai_turn.py status
.venv/bin/python scripts/my_ai_turn.py handoff [session_id]
.venv/bin/python scripts/my_ai_turn.py precompact
.venv/bin/python scripts/my_ai_turn.py maintenance
.venv/bin/python scripts/my_ai_turn.py dreaming
.venv/bin/python scripts/my_ai_turn.py recovery_check
.venv/bin/python scripts/my_ai_turn.py context_log
.venv/bin/python scripts/my_ai_turn.py flush_log
```

#### 3.10.2 Pre 阶段完整流程

```python
def cmd_pre(user_query):
    # 1. 动态刷新：检测话题切换，提前 flush
    should_flush, flush_reason = _should_flush_context_log(user_query)
    if should_flush:
        flush_context_log(reason=flush_reason)
    
    # 2. 意图分类 + 实体提取
    intent = extract_intent(user_query)
    entities = extract_entities(user_query)
    
    # 3. 读取上下文日志（分层策略）
    context_history = read_context_log(limit=10)
    #   - 旧轮次: 删除 thinking/tools/files，截断到 200 字
    #   - 新轮次: 保留所有字段，截断到 250 字
    
    # 4. 上下文生命周期判断
    lifetime = classify_context_lifetime(user_query)
    
    # 5. 查询增强（基于意图）
    if intent == "WHY": search_query += " 决定 原因 因为"
    if intent == "WHEN": search_query += " 当前日期"
    if intent == "ENTITY": search_query = 实体名拼接
    
    # 6. 多源搜索
    relevant_active = extract_relevant_entries(ACTIVE.md, search_query, 2)
    relevant_knowledge = extract_relevant_entries(KNOWLEDGE.md, search_query, 2)
    vec_results = vector_search(search_query, 5)
    fts_results = hybrid_search(search_query, 5)
    
    # 7. 上下文压力检测
    pressure = get_context_pressure()
    if pressure == "high": precompact_flush(intent)
    
    # 8. 合并所有来源 + 三维排序
    all_memories = [...active..., ...knowledge..., ...vector..., ...fts...]
    ranked = rank_memories_3d(all_memories, query_entities=entity_names)
    
    # 9. 召回追踪 + 访问强化
    for m in ranked[:3]:
        record_recall(mem_id, user_query, was_used=0)
        update_access(mem_id)
    
    # 10. 安全扫描 + 去重
    safe_memories = [m for m in ranked if security_scan(m["content"]).safe]
    final_memories = deduplicate(safe_memories)[:5]
    
    # 11. Skill Discovery 提示
    skill_hints = detect_skills(user_query)
    
    # 12. 输出 JSON
    print(json.dumps({
        "intent": intent["primary"],
        "entities": entity_names,
        "memories": final_memories,
        "lifetime": lifetime,
        "context_history": context_history,
        "skill_hints": skill_hints,
        "pressure": pressure  # 仅 high/medium 时返回
    }))
```

#### 3.10.3 Post 阶段完整流程

```python
def cmd_post(turn_json):
    turn_data = json.loads(turn_json)
    
    # 1. 纯粹上下文日志（ALWAYS 记录，不受过滤影响）
    append_context_log(user_msg, assistant_reply, thinking, tools, files)
    
    # 2. Flush 检查
    should_flush, flush_reason = _should_flush_context_log(user_msg)
    if should_flush: flush_context_log(reason=flush_reason)
    
    # 3. 工具调用计数
    for tool in tools: increment_tools()
    
    # 4. 内容过滤（仅影响长期记忆）
    capture_check = should_capture(combined)
    if not capture_check.should_capture:
        return {"synced": False, "reason": capture_check.reason}
    
    # 5. 重要性评分
    importance = score_importance(combined, files_modified)
    
    # 6. 内容分析
    analysis = analyze_content(combined)
    
    # 7. 矛盾检测（只检查最近 5 个段落）
    for source in [KNOWLEDGE.md, ACTIVE.md]:
        for segment in source.split("\n\n")[-5:]:
            if detect_contradiction(combined, segment).has_contradiction:
                mark_conflict()
    
    # 8. 保存位置判断
    target_file, tags = determine_target_file(importance, combined, user_msg)
    
    # 9. 自动保存层
    insert_to_session_db("assistant", summary[:500])
    if importance >= 3:
        vector_result = insert_to_vector_db(summary[:1000], tags, importance)
        graph_add(memory_id, summary[:500], tags)
    
    # 10. 输出 JSON
    print(json.dumps({
        "synced": importance >= 3,
        "score": importance * 5,
        "importance": importance,
        "target": target_file,
        "analysis": analysis.summary,
        "contradiction": has_contradiction,
        "compress": pressure == "high"
    }))
```

#### 3.10.4 Boot 阶段

```python
def cmd_boot():
    # 1. 安全扫描
    threats = check_bootstrap_security()
    
    # 2. 会话恢复检测
    recovery = check_session_recovery()
    
    # 3. 维护任务
    maintenance = run_maintenance()
    
    # 4. 上下文日志恢复
    context_history = read_context_log(limit=10)
    stats = get_context_log_stats()
    
    # 5. 状态输出
    return {
        "ready": SOUL.md exists,
        "vector": vector_stats,
        "graph": graph_stats,
        "pressure": pressure,
        "session": recent_session,
        "maintenance": maintenance,
        "security": threats,
        "recovery": recovery,
        "context_history": context_history,
        "context_log": stats
    }
```

---

## 4. 完整数据流 (Pre → Post → Boot)

### 4.1 单轮对话数据流

```
用户输入 ──→ SKILL.md 触发 "pre" 命令
                │
                ▼
        ┌───────────────┐
        │  my_ai_turn.py│
        │   cmd_pre()   │
        └───────────────┘
                │
    ┌───────────┼───────────┐
    ▼           ▼           ▼
context.py  extract.py  memory_ops.py
(话题检测)  (意图/实体)  (搜索/排序)
    │           │           │
    ▼           ▼           ▼
journal/    JSON 输出    vector_memory.py
(current)   (memories)   session_db.py
            │           memory_graph.py
            ▼
        LLM 回复用户
            │
            ▼
    ┌───────────────┐
    │   cmd_post()  │
    └───────────────┘
            │
    ┌───────┼───────┐
    ▼       ▼       ▼
context.py extract.py memory_ops.py
(追加日志) (分析)   (过滤/评分/保存)
    │               │
    ▼               ▼
journal/      SQLite + ChromaDB + Graph + Markdown
(current)     (根据重要性决定写入哪些存储)
```

### 4.2 Boot 数据流

```
用户说 "My AI" 触发 Skill
        │
        ▼
SKILL.md 执行 Boot 命令
        │
        ▼
ReadFile SOUL.md
ReadFile USER.md
        │
        ▼
Shell "my_ai_turn.py boot"
        │
        ▼
安全扫描 → 恢复检测 → 维护 → 上下文恢复
        │
        ▼
LLM 获得: SOUL + USER + 系统状态 + 上下文历史
```

### 4.3 跨 Session 数据流

```
Session A (结束)
        │
        ▼
用户说 "退出记忆模式"
        │
        ▼
SKILL.md 触发退出
        │
        ▼
Shell "my_ai_turn.py handoff"
        │
        ▼
生成 handoff 文件 + recovery snapshot
        │
        ▼
LLM 正常退出

─────────────────────────────

Session B (开始，几天后)
        │
        ▼
用户说 "My AI"
        │
        ▼
Boot 命令执行
        │
        ▼
check_session_recovery() 检测到未结束 session
        │
        ▼
返回恢复提示: "上次会话未正常结束，是否恢复？"
        │
        ▼
LLM 向用户确认，同时加载上下文历史
```

---

## 5. 核心算法

### 5.1 话题切换检测算法

**输入**: 当前查询字符串 + 最近 N 轮历史  
**输出**: (is_shift, streak, details)

```
Step 1: 提取当前查询关键词
  curr_words = jieba.lcut_for_search(query) - stopwords
  
Step 2: 计算历史会话的 TF-IDF 权重
  for each turn in recent_history:
    round_keywords[turn] = Counter(jieba.lcut_for_search(turn.user_msg) - stopwords)
    
  for each word in all_words:
    for i, counter in enumerate(round_keywords):
      window_weight = 0.8 ** (n - 1 - i)  # 滑动窗口衰减
      tf = counter.get(word, 0)
      idf = log(n / (doc_freq[word] + 1)) + 1
      weights[word] += tf * idf * window_weight

Step 3: 计算关键词相似度
  overlap = curr_words ∩ history_words
  overlap_weight = sum(weights[w] for w in overlap)
  curr_only_weight = len(curr_words - history_words)
  keyword_sim = overlap_weight / (overlap_weight + curr_only_weight + 1e-6)

Step 4: 计算向量相似度
  current_emb = embedding_function(query)  # 384-dim
  vector_sim = avg(cosine_similarity(current_emb, q.emb) for q in last_3_queries)
  
Step 5: 综合偏离度
  has_vector_history = len(query_embeds) > 0
  vector_weight = 0.45 if has_vector_history else 0.25
  keyword_weight = 1.0 - vector_weight
  composite_drift = keyword_weight * (1 - keyword_sim) + vector_weight * (1 - vector_sim)

Step 6: 状态机决策
  if composite_drift > 0.85 and len(curr_words) >= 3 and (not has_vector_history or vector_sim < 0.35):
    return (True, 0, "strong_drift")
  
  if keyword_sim >= 0.15 or (has_vector_history and vector_sim >= 0.55):
    return (False, 0, "overlap")
  
  streak += 1
  if streak >= 2 or composite_drift > 0.82:
    return (True, streak, "deviation")
  
  return (False, streak, "deviation")
```

### 5.2 三维排序算法

```python
def rank_memories_3d(memories, query_entities):
    for m in memories:
        # 1. 相关性 (来自向量搜索或 FTS)
        relevance = m.get("relevance", 0.5)
        
        # 2. 重要性（动态调整）
        base_importance = extract_from_tags(m.get("tags", ""))
        importance = get_dynamic_importance(m.get("id"), base_importance)
        
        # 3. 时效性
        recency = e^(-0.05 * days_old)
        
        # 4. 实体加成
        entity_boost = min(0.2, sum(0.05 for ent in query_entities if ent in m["content"]))
        
        # 5. 综合得分
        score = 0.4 * relevance + 0.35 * importance + 0.25 * recency + entity_boost
    
    return sorted(memories, key=lambda x: x["score"], reverse=True)
```

### 5.3 记忆过滤决策树

```
输入: combined_text = user_message + " " + assistant_reply

Layer 1: 强制保留信号（任意匹配即返回 True）
  ├── "记住"/"remember"/"以后"/"always"/"prefer"/"别忘了"
  ├── "我觉得"/"我认为"/"我喜欢"/"I think"/"I feel"
  └── "改名叫"/"你的人格"/"说话风格"/"角色"/"人设"

Layer 2: 强制过滤信号
  ├── 闲聊问候 (<100字 + "你好"/"谢谢"/"再见")
  ├── 纯知识问答 (>200字 + 疑问词开头 + 无个人标记)
  └── 短知识问答 (<200字 + 疑问词开头 + 无个人标记)

Layer 3: 外部模型判断（兜底）
  └── extract.py should_capture → quality_score >= 15

输出: {"should_capture": bool, "reason": str, "quality_score": int}
```

### 5.4 Dreaming 三阶段算法

```
Phase 1: Light Sleep (去重)
  candidates = []
  for day in last_7_days:
    chunks = daily_file.split("##")
    candidates.extend(chunks)
  
  unique = []
  for c in candidates:
    if not any(jaccard_similarity(c, u) > 0.9 for u in unique):
      unique.append(c)

Phase 2: REM Sleep (主题提取)
  G = nx.Graph()
  for chunk in unique:
    keywords = extract_keywords(chunk, n=5)
    for kw in keywords:
      G.add_node(kw, frequency+=1)
    for kw1, kw2 in combinations(keywords, 2):
      G.add_edge(kw1, kw2, weight+=1)
  
  themes = sorted(nx.degree_centrality(G).items(), reverse=True)[:10]

Phase 3: Deep Sleep (晋升)
  for chunk in unique:
    score = 0.30*relevance + 0.24*frequency + 0.15*diversity + 0.15*recency + 0.10*consolidation + 0.06*richness
    if score >= 0.6 and len(chunk) > 50:
      promote_to_knowledge(chunk)
```

---

## 6. 存储引擎深入

### 6.1 SQLite (SessionDB)

**位置**: `memory/.sessions.db`  
**特点**: WAL 模式 (`PRAGMA journal_mode=WAL`)，5 秒 busy timeout，单进程安全。

**表关系**:
```
sessions (1) ──► messages (N)       [session_id FK]
sessions (1) ──► recovery_snapshots (N) [session_id FK]
memories (1) ──► recall_log (N)     [memory_id]
```

**FTS5 触发器**:
```sql
-- 插入 messages 时自动更新 Porter 索引 + Trigram 索引 + message_count
CREATE TRIGGER messages_fts_insert AFTER INSERT ON messages
BEGIN
    INSERT INTO messages_fts(rowid, content) VALUES (NEW.id, NEW.content);
    INSERT INTO messages_fts_trigram(rowid, content) VALUES (NEW.id, NEW.content);
    UPDATE sessions SET message_count = message_count + 1 WHERE id = NEW.session_id;
END;
```

### 6.2 ChromaDB (向量库)

**位置**: `memory/.chroma/`  
**Embedding**: DefaultEmbeddingFunction (ONNX MiniLM-L6-V2, 384 维)  
**Collection**: `my_ai_memory`

**元数据**:
```json
{
  "tags": "source:active importance:5 keywords:Python,偏好",
  "source": "manual",
  "timestamp": "2026-05-05 17:24:51",
  "consolidation_count": "2"
}
```

**注意**: ChromaDB 使用**余弦距离**（不是欧氏距离），distance 范围 [0, 2]。`relevance = 1.0 - distance` 的映射在 distance > 1.0 时会产生负值，因此实际代码用了 `max(0, 1.0 - dist)`。

### 6.3 NetworkX (记忆图)

**位置**: `memory/.memory_graph.pkl`  
**类型**: `MultiDiGraph`（允许同一对节点间有多条边）

**节点类型**:
| 类型 | ID 格式 | 属性 |
|------|---------|------|
| memory | 任意字符串 | content, keywords, tags, created_at |
| entity | `entity:{type}:{name}` | entity_type, name, first_seen |

**边类型**:
- `mentions`: 记忆节点 → 实体节点（默认权重 1.0）
- 可扩展: `similar_to`, `before`, `causes`, `contradicts`

### 6.4 Markdown (Bootstrap 文件)

**四层架构中的角色**:
- **Identity**: SOUL.md + USER.md → Boot 时必加载，LLM 直接维护
- **Knowledge**: KNOWLEDGE.md → 按需加载（涉及知识/决策时）
- **Active**: ACTIVE.md → 按需加载（涉及任务时）
- **Journal**: current.md → 脚本自动维护，LLM 不直接读写

**Frozen Snapshot**: 同一会话中，LLM 写入磁盘后不会重新加载到当前上下文。当前上下文继续使用 session start 时的版本。这避免了 mid-session 变化导致的重复写入或矛盾。

---

## 7. 配置与扩展

### 7.1 修改话题检测阈值

编辑 `scripts/config.py`:
```python
# 当前阈值 (context.py 中硬编码)
# 强偏离: composite > 0.85
# 重叠重置: keyword >= 0.15 or vector >= 0.55
# 偏离确认: streak >= 2 or composite > 0.82
```

如需调整，修改 `context.py` 中 `_detect_topic_shift()` 的阈值常量。

### 7.2 添加新的 Skill Discovery 映射

编辑 `my_ai_turn.py` 中 `cmd_pre()`:
```python
skill_map = [
    (["股票", "股价", "a股", "基金"], "tushare-finance"),
    # 添加新映射:
    (["新关键词1", "新关键词2"], "新skill名"),
]
```

### 7.3 扩展 jieba 词典

编辑 `scripts/config.py`:
```python
_JIEBA_CUSTOM_WORDS = [
    # 在列表末尾添加新术语
    "新术语", "新词组",
]
```

### 7.4 调整三维排序权重

编辑 `scripts/memory_ops.py`:
```python
total_score = 0.4 * relevance + 0.35 * importance + 0.25 * recency + entity_boost
# 修改为:
total_score = 0.5 * relevance + 0.3 * importance + 0.2 * recency + entity_boost
```

### 7.5 添加新的安全扫描模式

编辑 `scripts/extract.py`:
```python
SECURITY_PATTERNS = [
    # 在列表末尾添加:
    (r'新的正则模式', 'NEW_CATEGORY', 'high'),
]
```

### 7.6 添加新的关系类型

编辑 `scripts/extract.py` 中 `infer_relations()`:
```python
# 在现有模式后添加新的正则模式组
new_patterns = [
    ("新模式\s*[:：]?\s*(.+?)" + SENT_END_CN, "new_type"),
]
```

---

## 8. 已知问题与路线图

### 8.1 当前已知问题

#### P1: 话题检测子话题误判

**症状**: "股票投资" → "K线图/MACD/成交量" 时，jieba 切词后关键词集合完全没有交集，keyword_sim = 0，连续 2 轮后触发话题切换。

**根因**: 子话题与父话题的关键词集合不重叠，向量相似度 0.45-0.68 不足以重置 streak。

**当前缓解**: 
- 自定义 jieba 词典添加了金融术语
- 降低 vector_weight 从 0.45 到 0.25（无向量历史时）
- 放宽阈值

**长期修复**: 需要领域本体库或层次话题模型。

#### P2: 向量 Embedding 缓存冷启动

**症状**: Flush 后 embedding 缓存被清空，新 session 的前几个查询没有向量历史，话题检测仅依赖关键词信号。

**根因**: `_EMB_CACHE_FILE` 在 flush 时被删除，没有渐进式重建机制。

**缓解**: 无。

#### P3: 短显式请求被过滤

**症状**: "记住这个"（< 20 字）可能被长度启发式过滤。

**根因**: 过滤逻辑中长度检查在显式请求检测之前。

**缓解**: memory_ops.py 中显式请求检测在最前面，理论上已覆盖。但极端短文本仍需观察。

#### P4: FTS5 Porter 对中文无效

**症状**: `session_db.py search 'python'` 返回空，但 `search_trigram 'python'` 正常。

**根因**: Porter tokenizer 是英文词干化器，对中文无效果。Trigram 对 2 字符中文词无效（Trigram 要求 >= 3 字符）。

**缓解**: hybrid_search 同时调用 Porter 和 Trigram，合并结果。中文短词依赖 Trigram 的 3 字符子串匹配。

#### P5: 无多用户/并发测试

**症状**: 所有测试都是单用户、单会话、顺序执行。

**根因**: 设计目标就是单用户本地使用。

### 8.2 v1.3 路线图

| 优先级 | 功能 | 说明 |
|--------|------|------|
| P0 | 话题检测优化 | 引入层次关键词或领域本体 |
| P1 | Embedding 缓存渐进重建 | Flush 后保留最近 3 个 embedding |
| P1 | 中文 FTS 增强 | 探索 jieba + SQLite 中文分词 |
| P2 | 记忆使用反馈闭环 | post 阶段检测记忆是否被实际使用 |
| P2 | 批量导入/导出 | 支持从 Obsidian/Markdown 批量导入 |
| P3 | 可视化 | 记忆图可视化（导出为 HTML/SVG） |
| P3 | 语音/图片记忆 | 扩展多模态记忆存储 |

---

## 附录 A: 核心数据格式

### Pre 输出 JSON

```json
{
  "intent": "WHAT",
  "entities": ["Python", "JavaScript"],
  "memories": [
    "User: 记住这个：我偏好使用Python...",
    "# SOUL — My-AI 人格\n\n我是 My-AI..."
  ],
  "lifetime": "PERSISTENT",
  "context_history": [
    {"turn": 1, "timestamp": "...", "user": "...", "assistant": "..."}
  ],
  "skill_hints": ["tushare-finance"],
  "pressure": "low"
}
```

### Post 输出 JSON

```json
{
  "synced": true,
  "score": 50,
  "importance": 10,
  "target": "memory/knowledge/KNOWLEDGE.md",
  "analysis": "提取 2 个实体, 5 个关键词, 1 个关系",
  "contradiction": false,
  "compress": false,
  "context_log_flushed": false
}
```

### Boot 输出 JSON

```json
{
  "ready": true,
  "vector": {"total_entries": 15, "chroma_path": "..."},
  "graph": {"total_nodes": 6, "total_edges": 1, "density": 0.0333},
  "pressure": "low",
  "session": [{"id": 1, "title": "Default", "message_count": 28}],
  "maintenance": {"actions": [...], "warnings": [], "hebbian_decay": {...}},
  "security": {"safe": true, "threats": []},
  "recovery": {"needs_recovery": true, "message": "上次会话未正常结束..."},
  "context_history": [],
  "context_log": {"turns": 0, "tokens": 0, "exists": false}
}
```

---

## 附录 B: 快速参考

### 常用命令

```bash
# 状态检查
cd ~/.config/agents/skills/my-ai && .venv/bin/python scripts/my_ai_turn.py status

# 手动维护
cd ~/.config/agents/skills/my-ai && .venv/bin/python scripts/my_ai_turn.py maintenance

# 手动 dreaming
cd ~/.config/agents/skills/my-ai && .venv/bin/python scripts/my_ai_turn.py dreaming

# 查看上下文日志
cd ~/.config/agents/skills/my-ai && .venv/bin/python scripts/my_ai_turn.py context_log

# 手动 flush
cd ~/.config/agents/skills/my-ai && .venv/bin/python scripts/my_ai_turn.py flush_log

# 向量库统计
cd ~/.config/agents/skills/my-ai && .venv/bin/python scripts/vector_memory.py stats

# 图统计
cd ~/.config/agents/skills/my-ai && .venv/bin/python scripts/memory_graph.py stats

# Hebbian 衰减
cd ~/.config/agents/skills/my-ai && .venv/bin/python scripts/session_db.py apply_decay 0.02 0.3
```

### 模块依赖图

```
my_ai_turn.py (编排层)
    ├── config.py (被所有模块导入)
    ├── utils.py (被所有模块导入)
    ├── context.py
    │   └── config.py, utils.py
    ├── memory_ops.py
    │   ├── config.py, utils.py
    │   └── extract.py (通过 subprocess)
    │   └── vector_memory.py (通过 subprocess)
    │   └── session_db.py (通过 subprocess)
    │   └── memory_graph.py (通过 subprocess)
    ├── maintenance.py
    │   ├── config.py, utils.py
    │   └── memory_ops.py
    │   └── extract.py (通过 memory_ops)
    ├── extract.py (独立，被 memory_ops 调用)
    ├── session_db.py (独立 CLI)
    ├── vector_memory.py (独立 CLI)
    └── memory_graph.py (独立 CLI)
```

### Token 预算估算

| 组件 | Token 数 | 说明 |
|------|---------|------|
| SOUL.md | ~400 | Boot 必加载 |
| USER.md | ~200 | Boot 必加载 |
| 搜索结果 | ~750 | 5 条 × 150 字 |
| 上下文历史 | ~600 | 10 轮 × 60 字 |
| 系统提示 | ~200 | SKILL.md 内容 |
| **Boot 总计** | **~1587** | 远低于 128K 限制 |
| 每轮 Pre/Post | ~400-760 | 增量开销 |
| 50 轮 Session | ~20K | 含 flush 重置 |

---

*文档结束。如有疑问，直接阅读对应源码文件，每个文件顶部都有详细注释。*
