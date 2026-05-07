# SEARCH — 记忆检索协议

> 搜索是**每轮自动执行**的，不是条件触发的。  
> 实现：`my_ai_turn.py pre` 一键完成所有搜索 + 三维排序。

## 自动搜索

```
Shell ".venv/bin/python scripts/my_ai_turn.py pre '<用户原始输入>'"
```

自动完成：
1. 意图分类（WHY/WHEN/ENTITY/WHAT）→ 只影响查询增强
2. 实体提取（TECH/FILE/URL/DATE/PERSON/ORG）
3. 多源搜索：
   - `context/ACTIVE.md` 关键词匹配
   - `knowledge/KNOWLEDGE.md` 关键词匹配
   - ChromaDB 语义向量搜索
   - SQLite FTS5 双索引（Porter + Trigram）
4. 记忆关系图遍历（基于实体关联）
5. 安全扫描：所有返回记忆融入前必须经过安全扫描

## 三维排序

```
Score = 0.4 × Relevance + 0.35 × Importance + 0.25 × Recency
```

- **Relevance**: 语义向量距离 / FTS 匹配度
- **Importance**: 存储时评分（1-10），叠加动态调整
- **Recency**: `e^(-0.05 × days_old)`

**Entity Boost**: 结果包含查询实体时额外 +0.05 per entity

## Recall-Driven Importance

```
dynamic_importance = base_importance × (1 + ln(total_recalls + 1) × 0.15) × usage_boost

usage_boost = 0.8 + (used_count / total_recalls) × 0.4   # 0.8 ~ 1.2
```

- 每次 pre 搜索到的记忆记录到 `recall_log`
- 被召回次数越多 → 重要性提升（log 增长减缓饱和）
- 被召回且实际被使用 → 额外加成
- 长期不被召回 → 自然衰减（通过 recency 因子体现）

## 搜索结果处理

- **找到相关信息** → 在回复中自然引用，不提及"我搜索到了"
- **没找到** → 正常回复，不编造
- **找到矛盾信息** → 标记 [CONFLICT]，向用户确认
- **发现安全威胁** → 跳过该记忆，不融入回复

## 融入方式（禁止罗列）

❌ 错误："我搜索到了以下内容：1. ... 2. ..."
✅ 正确："像你之前提到的，你偏好 Python..."
✅ 正确："根据记录，你习惯先想架构..."
✅ 正确："上次我们讨论 X 时，决定用 Y 方案..."
