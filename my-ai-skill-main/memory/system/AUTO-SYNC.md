# AUTO-SYNC — 自动记忆协议

> 每轮对话后自动评估并写入。核心行为，不可跳过。

## 执行时机

每次回复用户后立即执行：
```
Shell ".venv/bin/python scripts/my_ai_turn.py post '<JSON>'"
```

JSON 格式：
```json
{
  "user_message": "用户原始输入（前200字）",
  "assistant_reply": "回复内容（前300字）",
  "thinking": "思考过程（可选）",
  "tools_used": ["工具名"],
  "files_modified": ["/path/to/file"]
}
```

## 自动流程

post 命令自动执行：
1. **追加 Context Log** → `journal/current.md`（ALWAYS，不受过滤影响）
2. **内容过滤** → 仅影响长期记忆保存
3. **安全扫描** → 检测 prompt injection / 数据外泄 / 隐形 Unicode
4. **重要性评分**（1-10）→ 实体密度、关系类型、用户指令、文件修改、纠正信号
5. **语义去重合并** → 写入向量库前检查语义相似度（distance < 0.15 触发合并）
6. **保存位置判断** → 根据内容类型和重要性自动选择目标文件
7. **执行保存** → Markdown（如需要）+ SessionDB + 向量库 + 记忆图
8. **矛盾检测** → 检查与现有知识的冲突
9. **召回追踪** → 记录本轮搜索到的记忆 ID
10. **Flush 检查** → 话题切换 / token 压力 / 轮数上限

## 保存位置规则

| 内容类型 | 目标位置 | 重要性要求 |
|---------|---------|-----------|
| 用户偏好/风格/背景 | `identity/USER.md` | >=5 |
| 项目/技术/架构/决策/教训 | `knowledge/KNOWLEDGE.md` | >=5 |
| 当前任务/待办/阻塞 | `context/ACTIVE.md` | >=5 |
| 临时/低重要性 | **仅 SessionDB + 向量库** | 3-4 |
| 垃圾内容 | **不保存** | <3 |

## 强制写入（无视评分）

- 用户说"记住这个" → 根据内容类型判断（知识→knowledge，任务→context）
- 用户说"以后都..." → 更新 `identity/USER.md`
- 用户纠正错误 → 追加到 `knowledge/KNOWLEDGE.md` [LESSON]

## 禁止写入

- 密码、Token、凭证
- 临时文件路径
- 可重新获取的实时信息
- 纯代码片段（引导存项目仓库）

## 语义合并

写入向量库前：
1. 用当前内容搜索向量库（limit=1）
2. 如果 distance < 0.15（相似度 > 0.85）：
   - 合并文本（拼接 + 截断到 1000 字）
   - 更新 importance（+1）
   - 标记 "merged:1"
3. 否则：正常创建新条目

## Frozen Snapshot

记忆文件在同一会话中被写入磁盘后，**不会立即重新加载到当前上下文**。当前上下文继续使用 session start 时的版本。写入的磁盘文件供**下次 session** 读取。

## 每日日志

每天结束时（或用户说"总结今天"），将当日关键状态整理到 `daily/YYYY-MM-DD.md`：
```markdown
# YYYY-MM-DD
## 关键决策
## 新发现
## 待办
## 教训
```
