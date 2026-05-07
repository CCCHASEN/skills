# EXPLANATION

**Scope**: Explanation file standards — content rules, length multipliers, pedagogical requirements, synchronization rules, quality checks.

**Prerequisites**:
- [ARCHITECTURE.md](ARCHITECTURE.md) — vault structure and atom rules
- [CRAFT.md](CRAFT.md) — atom templates (Explanation explains atoms, so you must know the atom structure first)

---


## Explanation Files

Every **course** MUST have a `{Name}-Explanation.md` in the same folder as its `index.md`. Domain Explanation files are optional — create only when the domain has substantial content requiring detailed pedagogical exposition. Explanation files are **living documents** — any change to a course atom MUST be immediately reflected in the Explanation.

### What It Is
- Detailed **Chinese-only** explanations for every atom in that course/domain.
- Canonical reference for `/query`: if a user question is covered, quote it directly.
- **Not an atom**: No YAML, no `## Connections`, no wikilinks. Pure explanatory text in a single file, ordered to match the course assembly.

### Content Rules
- **No English original text**.
- **No YAML, no Connections, no wikilinks**.
- **One file per course/domain**.

### Length Standards

Compute **effective text length**: atom Markdown body, strip index formulas and LaTeX markup delimiters/commands (e.g., `$`, `\begin`, `\frac`, `\left`, `\right`). Only the semantic mathematical content counts; typesetting symbols do not. **1 English word ≈ 1.5 Chinese characters**.

| Difficulty | Length Multiplier |
|---|---|
| **Simple** | 3–10× |
| **Medium** | 10–30× |
| **Hard** | 30×+ (no cap) |

- **Never skimp**: When in doubt, write more. Do not stop early due to time or token concerns.
- **90% Mastery Test overrides everything**: A student who has never seen the material must score **90%+** on a standard exam after studying the explanation. If not, expand — regardless of multiplier.
- **Quality over quantity — but quantity is necessary for quality**: The multiplier is a *minimum* threshold, not a target. Every additional sentence must carry pedagogical weight. No filler, no repetition, no generic statements that do not advance understanding.

### Pedagogical Requirements
- **Teach, do not recite**: Enable both understanding AND application.
- **One vivid analogy per concept**: Concrete, relatable, tightly mapped. A bad analogy is worse than none.
- **Step-by-step derivations**: Every symbol explained. After deriving, restate in plain language: "In plain language, this says..."
- **Worked examples**: Every example gets individual full explanation — what is being tested, what + why for each line, decision points, pitfalls, parameter variations.
- **Tricks Box**: Actionable pattern summary with explicit decision logic: "If condition A → use method 1. If condition B → use method 2."
- **Prerequisite bridging**: Explicitly re-introduce prerequisite definitions. Do NOT assume the reader remembers them.
- **Zero tolerance for empty explanations**: Every paragraph must contain at least one of: (a) a new analogy or intuition, (b) a derivation step with symbol-by-symbol commentary, (c) a worked example with explicit reasoning, (d) a decision rule or trick, (e) a common pitfall and how to avoid it, (f) a connection to a prerequisite concept. If a sentence does not do one of these six things, delete it.
- **Density check**: After drafting any section, ask: "If I removed this paragraph, would a student's exam score drop?" If the answer is no, remove or replace it.
- **Knowledge-point-first, examples optional**: Explanations should primarily focus on deep, thorough exposition of the knowledge points (concepts, definitions, theorems, derivations, formulas, and their intuition). Worked examples are supplementary and may be used selectively to illuminate a difficult point or demonstrate a standard procedure. Do NOT pad length with excessive examples that merely repeat the same pattern.
- **No out-of-scope supplementation**: Do NOT introduce topics, formulas, or concepts that do not appear in the source course material (lecture notes, assigned textbook chapters, or official syllabus). The Explanation must be a faithful, expanded teaching of what the course actually covers — not a broader reference manual.

### Synchronization Rule (Mandatory)

| Atom Action | Required Explanation Update |
|-------------|----------------------------|
| **New atom created** | Append full Chinese explanation in correct course sequence. Do NOT skip or delay. |
| **Atom modified** | Update corresponding section. Re-evaluate length multiplier if difficulty changes. |
| **Atom deleted** | Remove corresponding section. Do NOT leave orphaned explanations. |
| **Atom reordered** | Reorder explanations to match new course sequence. |

**This is NOT optional.** The Explanation update is part of the same task and must finish before the task is considered complete. Log both actions under the same timestamp in `log.md`.

### Key Rules Echo
These three rules apply to **all** content generation in this vault — atoms, Explanations, and `/query` responses:

1. **90% Mastery Test**: A student who has never seen the material must score **90%+** on a standard exam. If your output does not meet this, expand it.
2. **Synchronization Rule**: Atom changed → Explanation changed. Same task, same timestamp.
3. **Length Standards**: Simple 3–10×, Medium 10–30×, Hard 30×+ (no cap). When in doubt, write more.

### Explanation Quality Check
- Every atom covered.
- Length multipliers met.
- All analogies concrete and structurally faithful.
- Every formula has plain-language restatement.
- No English original, no YAML, no Connections, no wikilinks.


---
