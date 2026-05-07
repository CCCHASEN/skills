# CONTEXT — 上下文管理协议

## 五层架构加载优先级

1. `identity/SOUL.md` + `identity/USER.md` — 永不丢弃
2. `knowledge/KNOWLEDGE.md` + `context/ACTIVE.md` — 按需加载
3. `journal/current.md` — 每轮自动记录，定期归档
4. 当前会话历史（CLI 原生）— 中间轮次可摘要
5. 最近 3-5 轮 — 永不丢弃

## 压缩触发条件

- `context/ACTIVE.md` > 100 行
- `knowledge/KNOWLEDGE.md` > 500 行
- 多指标综合评分 >= 5/7
- Pre 返回 `"pressure": "high"`

## 压缩前 Flush

Pre 检测到 pressure=high 时：
1. 将 ACTIVE.md 关键条目保存到 `daily/YYYY-MM-DD.md`
2. 记录当前 session 状态
3. 使用自适应模板（coding/debugging/discussion/default）

## 上下文生命周期

| Lifetime | 含义 | 写入行为 | 示例 |
|----------|------|---------|------|
| `PERSISTENT` | 长期有效 | 正常写入 Markdown + DB | "我偏好 Python" |
| `SESSION` | 本 session 有效 | 仅入 SessionDB | "基于刚才的结果..." |
| `EPHEMERAL` | 只在本轮有效 | 不入任何存储 | "先不管这个" |

**检测规则**：
- "先不管"/"暂时"/"just for now" → EPHEMERAL
- "刚才"/"之前说的"/"基于刚才" → SESSION
- 默认 → PERSISTENT

## Tool Call 保护

压缩时**绝不拆分** assistant 的 tool_call 和对应的 tool_result。未完成工具对整体保留到 "永不丢弃" 层。

## 加载优先级（上下文不足时）

1. identity/SOUL.md + identity/USER.md
2. knowledge/KNOWLEDGE.md + context/ACTIVE.md
3. 当前会话最近 3-5 轮
4. 相关 Skill 内容
5. 工具原始输出（优先丢弃）
