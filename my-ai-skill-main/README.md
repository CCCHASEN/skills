# My-AI v1.2

为 **Kimi CLI** 设计的持久记忆 Skill。每轮对话自动搜索历史记忆、保存有价值的信息。

## 快速开始

```bash
# 1. 克隆仓库
git clone https://github.com/CCCHASEN/my-ai-skill.git
cd my-ai-skill

# 2. 一键初始化（创建 venv + 安装依赖 + 初始化数据库）
bash setup.sh

# 3. 在 Kimi CLI 中说出触发词激活
#    "进入记忆模式" / "memory mode" / "my ai" / "My AI"
```

## 核心能力

- **持久记忆** — 五层存储（Identity / Knowledge / Context / Journal / Archive）
- **自动搜索** — 每轮 Pre 阶段自动检索相关记忆
- **智能保存** — Post 阶段自动过滤、评分、去重、保存
- **话题感知** — TF-IDF + 向量相似度动态检测话题切换
- **Hebbian 衰减** — 冷记忆自动归档，热记忆自动上浮
- **安全扫描** — 全链路威胁检测

## 项目结构

```
my-ai-skill/
├── README.md              # 本文件
├── DEVELOPER_GUIDE.md     # 完整开发者文档（1462行）
├── SKILL.md               # Kimi CLI Skill 定义
├── setup.sh               # 初始化脚本
├── scripts/               # 核心 Python 模块（10个）
│   ├── my_ai_turn.py      # CLI 入口与编排
│   ├── context.py         # 上下文日志 + 话题切换检测
│   ├── memory_ops.py      # 搜索排序 + 数据库写入
│   ├── extract.py         # NLP 引擎
│   ├── maintenance.py     # 维护 + Dreaming + Recovery
│   ├── session_db.py      # SQLite + FTS5
│   ├── vector_memory.py   # ChromaDB 向量库
│   ├── memory_graph.py    # NetworkX 关系图
│   ├── config.py          # 全局配置
│   └── utils.py           # 工具函数
└── memory/                # 五层存储目录
    ├── identity/          # SOUL.md + USER.md
    ├── knowledge/         # KNOWLEDGE.md
    ├── context/           # ACTIVE.md
    ├── journal/           # 实时对话日志
    ├── daily/             # 每日归档
    ├── archive/           # 长期归档
    ├── system/            # AI 参考文档
    └── .sessions.db       # SQLite 数据库（运行时生成）
```

## 五层存储

| 层级 | 文件 | 内容 | 写入方式 |
|------|------|------|---------|
| Identity | `identity/SOUL.md` | 人格/规则 | LLM 主动写入 |
| Identity | `identity/USER.md` | 用户偏好 | LLM 主动写入 |
| Knowledge | `knowledge/KNOWLEDGE.md` | 知识/决策/教训 | LLM 主动写入 |
| Context | `context/ACTIVE.md` | 任务/待办 | LLM 主动写入 |
| Journal | `journal/current.md` | 完整对话记录 | 脚本自动追加 |

> Markdown 文件由 LLM 根据记忆协议主动维护，脚本只负责 Journal 和数据库层。

## 依赖

- Python 3.13+
- [uv](https://github.com/astral-sh/uv)（用于虚拟环境管理）
- chromadb, jieba, networkx（`setup.sh` 自动安装）

## 版本历史

- **v1.2** — 模块化重构 + 动态话题切换 + 记忆内容过滤 + Hebbian 衰减
- **v1.1** — 持久记忆基础架构（五层存储 + 向量搜索 + 关系图）
- **v1.0** — Pre/Post/Boot 循环原型

## 开发文档

详见 [`DEVELOPER_GUIDE.md`](DEVELOPER_GUIDE.md)，涵盖：
- 十大模块详细说明
- 完整数据流（Pre/Post/Boot）
- 核心算法（话题检测、三维排序、记忆过滤、Dreaming）
- 存储引擎深入（SQLite FTS5、ChromaDB、NetworkX）
- 配置扩展指南
- 已知问题与路线图

## License

MIT
