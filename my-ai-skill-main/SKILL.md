---
name: my-ai
description: |
  持久记忆助手。每轮自动执行 pre->reply->post。
  五层存储 + 动态刷新 + Hebbian 衰减 + 上下文分层。
metadata:
  version: "1.2"
  trigger: ["进入记忆模式", "memory mode", "my ai", "My AI"]
  exit: ["退出记忆模式", "exit memory", "退出 my-ai"]
---

# My-AI 持久记忆助手 v1.2

每轮自动执行 `pre -> reply -> post`。

## 文件权限

**配置级（只读）**：SKILL.md、scripts/*.py、system/*.md、.venv/

**记忆级（可写）**：

| 文件 | 内容 | 写入方式 |
|------|------|---------|
| `identity/SOUL.md` | 人格/身份/规则 | LLM 主动写入 |
| `identity/USER.md` | 用户画像/偏好 | LLM 主动写入 |
| `knowledge/KNOWLEDGE.md` | 知识/决策/教训 | LLM 主动写入 |
| `context/ACTIVE.md` | 任务/待办/阻塞 | LLM 主动写入 |
| `journal/current.md` | **每轮自动记录**完整对话 | 脚本自动 |

> 定义文件（SOUL/USER/KNOWLEDGE/ACTIVE）**不自动写入**。LLM 根据记忆协议主动维护。

## 流程

### pre
```
Shell ".venv/bin/python scripts/my_ai_turn.py pre '<输入>'"
```
返回：intent, entities, memories, context_history, lifetime, skill_hints。

**搜索策略**：默认搜索所有来源（journal + 向量库 + KNOWLEDGE + ACTIVE + FTS），intent 只影响查询增强。

**Context History 分层**：最近 3 轮完整保留（含 thinking），3-10 轮仅保留 user+assistant。

### post
```
Shell ".venv/bin/python scripts/my_ai_turn.py post '<JSON>'"
```
JSON：`{"user_message":"...","assistant_reply":"...","thinking":"...","tools_used":[],"files_modified":[]}`

自动：追加 journal → 过滤 → 安全扫描 → 评分 → 语义合并 → SessionDB + 向量库。

## Boot（渐进加载）
```
ReadFile memory/identity/SOUL.md
ReadFile memory/identity/USER.md
Shell ".venv/bin/python scripts/my_ai_turn.py boot"
```

**按需加载**：涉及知识/任务时 `ReadFile memory/knowledge/KNOWLEDGE.md` / `memory/context/ACTIVE.md`。

## 动态刷新（Context Log）

不再固定 25 轮刷新。触发条件：
- **话题切换**：当前查询与最近 3 轮关键词重叠率 < 0.35
- **Token 压力**：context log > 4000 tokens
- **轮数上限**：35 轮（保底）

刷新后保留最近 **5 轮**作为上下文衔接。

## Hebbian 记忆衰减（自净化）

`maintenance` 命令自动执行：
- **激活值衰减**：未访问记忆每天衰减 2%
- **访问强化**：被召回的记忆 activation +0.3
- **冷归档**：activation < 0.3 且 7 天未访问 → 自动归档

## Skill Discovery

处理任务前检查可用 skill：

| Skill | 场景 |
|-------|------|
| `defuddle` | 提取网页 clean markdown |
| `email` | 发送/读取邮件 |
| `kimi-webbridge` | 控制真实浏览器 |
| `macos-calendar` | 管理 macOS 日历 |
| `obsidian-knowledge` | Obsidian vault 操作 |
| `tushare-finance` | 中国金融数据 |
| `weather` | 天气查询 |
| `github` | GitHub CLI 操作 |
| `office-documents` | Office 文档处理 |
| `frontend-dev` | 前端开发 |
| `screen-control` | 屏幕控制 |
| `tavily` | AI 优化搜索 |

## 其他命令

| 命令 | 用途 |
|------|------|
| `status` | 查看状态 |
| `maintenance` | 深度维护 + Hebbian 衰减 + flush |
| `dreaming` | 记忆巩固 |
| `context_log` | 查看当前日志 |
| `flush_log` | 手动归档日志 |

## 禁止

- 不记密码/Token
- 不自动退出
- 不暴露内部评分
- 不修改配置级文件

## Reference（按需 ReadFile）

- `memory/system/CONTEXT.md` — 压缩协议 + 生命周期
- `memory/system/SEARCH.md` — 搜索协议 + 三维排序
