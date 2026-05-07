# CRAFT

**Scope**: All file templates — Objective Atom, Subjective Atom, Master Index, Course Assembly, Course Index, Domain Index, Book Notes, Weekly Journal, Inspiration.

**Prerequisites**: [ARCHITECTURE.md](ARCHITECTURE.md) — must understand vault structure and naming conventions before creating files.

---


## File Templates

### 1. Objective Atom (`05-Atoms/`)

For technical, factual, curriculum-based knowledge. Section titles are **content-driven**, not fixed — choose headings that match the material (e.g., `## Definition`, `## Mechanism/Theory`, `## Key Theorems`, `## Historical Context`, `## Geometric Interpretation`).

**Mandatory closing section**:
- `## Connections` — Direct prerequisites, consequences, tightly coupled atoms

    ---
    title: "Stress Tensor Analysis"
    tags: [mechanics, solid-mechanics, mer]
    source: "MER101-Solid-Mechanics Lecture 3"
    modified: 2026-04-20
    ---

    ## Definition
    Second-order tensor describing internal force distribution...

    ## Mechanism/Theory
    - Cauchy stress principle
    - Equilibrium equations
    - Transformation laws

    ![[00-Courses/Grade-1/Solid-Mechanics-1/Attachments/mer-stress-tensor-diagram-20260420.png]]

    ## Connections
    - [[strain-tensor]] — Constitutive relationship
    - [[hookes-law]] — Linear elastic connection

### 2. Subjective Atom (`05-Atoms/`)

For interpretive concepts, psychological models, philosophical frameworks. **Default to subjective when uncertain.**

    ---
    title: "Efficient Market Hypothesis"
    tags: [finance, economics, conflict]
    source: "A Random Walk Down Wall Street, Chapter 2"
    modified: 2026-04-20
    ---

    ## Core Proposition
    Asset prices reflect all available information...

    ## Logic Chain
    1. Information arbitrage
    2. Price adjustment
    3. Random walk implications

    ## Application
    - Retail strategy design
    - Passive vs active management

    ## Critique & Conflicts
    - **Empirical Boundary**: Weak-form holds, strong-form violated by insider asymmetries
    - **Behavioral Conflict**: [[behavioral-bias]] documents anomalies

    ## Evolutionary Notes
    [EMH → Adaptive Market Hypothesis (AMH)]

    ## Personal Notes
    [Reserved for user only]

    ## Connections
    - [[random-walk-theory]] — Mathematical foundation
    - [[prospect-theory]] — Cognitive alternative

### 3. Master Index (`index.md`)

Vault-wide registry. Grouped by course and domain. Auto-update after any atom creation/deletion/rename.

    ---
    title: "Vault Index"
    tags: [index, meta]
    modified: 2026-04-27
    ---

    # Vault Master Registry

    ## 00-Courses

    ### Physics 1
    - [[vectors-fundamentals]] — Scalar, vector, unit vector, components, magnitude
    - [[kinematics]] — Position, velocity, acceleration, constant acceleration equations
    - ...

    ### Calculus 1M
    - [[functions-and-graphs]] — Function definition, domain/range, elementary function types
    - [[limits]] — Limit definition, laws, Sandwich Theorem
    - ...

    ## 01-Domains

    ### Finance
    - [[efficient-market-hypothesis]] — Information efficiency framework
    - ...

**Index Format Rule**: Strict `- [[filename]] — Description`. Mention cross-domain relevance if applicable.

### 4. Course Assembly (`00-Courses/Grade-1/Solid-Mechanics-1/Solid-Mechanics-1.md`)

Uses `![[ ]]` transclusion. Main curriculum file.

    ---
    title: "MER101: Solid Mechanics 1"
    tags: [course, mechanics, solid-mechanics, 2026-spring]
    modified: 2026-04-22
    ---

    # Solid Mechanics 1

    ## Prerequisites
    - ![[vectors-fundamentals]] — Vector basics and operations
    - ![[newtons-laws]] — Newton's three laws of motion

    ## Module 1: Introduction and Fundamentals
    ### 1.1 Mechanics Fundamentals
    ![[mechanics-fundamentals]]

    ## Module 2: Force Systems
    ### 2.1 Force Systems in 2D
    ![[force-systems-2d]]
    ![[00-Courses/Grade-1/Solid-Mechanics-1/Attachments/mer-plane-stress-chart-20260420.png]]

    ## Module 3: Equilibrium
    ### 3.1 Free-Body Diagrams
    ![[free-body-diagrams]]

### 5. Course Index (`00-Courses/Grade-1/Solid-Mechanics-1/index.md`)

Navigation hub for a single course. Lists all atoms by module, plus links to the assembly and Explanation files.

    ---
    title: "MER101: Solid Mechanics 1 Course Index"
    tags: [course, mechanics, solid-mechanics, index]
    modified: 2026-04-29
    ---

    # Solid Mechanics 1 Course Index

    ## Course Assembly
    - [[Solid-Mechanics-1|Solid Mechanics 1 Main Course File]] — Full curriculum assembly

    ## Explanation
    - [[Solid-Mechanics-1-Explanation|Solid Mechanics 1 Explanation]] — Detailed Chinese explanations

    ## Module 1: Introduction and Fundamentals
    - [[mechanics-fundamentals]] — Basic concepts, scalars/vectors, Newton's laws

    ## Module 2: Force Systems (2D and 3D)
    - [[force-systems-2d]] — Forces in two dimensions, components, projections
    - [[moment-and-couple-2d]] — Moments, couples, Varignon's theorem in 2D
    - ...

    ## Module 3: Equilibrium (2D and 3D)
    - [[free-body-diagrams]] — System isolation, FBD construction
    - ...

### 6. Domain Index (`01-Domains/Finance/Finance-atoms.md`)

Navigation hub, no transclusion. Auto-update immediately after creating any atom in this domain.

    ---
    title: "Finance Knowledge Index"
    tags: [finance, index]
    modified: 2026-04-20
    ---

    # Finance Atoms Index

    ## Market Theory
    - [[efficient-market-hypothesis]] — Information efficiency framework
    - [[random-walk-theory]] — Price movement stochastic model

    ## Valuation
    - [[tvm]] — Time value of money
    - [[dcf-model]] — Discounted cash flow

    ## Books
    - [[random-walk]] — Malkiel's synthesis

**Index Format Rule**: Strict `- [[filename]] — Description`. Mention cross-domain relevance if applicable.

### 7. Book Notes (`01-Domains/Finance/Books/Random-Walk.md`) — Reserved

    ---
    title: "A Random Walk Down Wall Street"
    tags: [book, finance, investment]
    author: "Burton Malkiel"
    modified: 2026-04-20
    ---

    # A Random Walk Down Wall Street

    ## Core Thesis and Summary
    
    Malkiel extends EMH to retail strategy...

    ## Module 1:XXXXXXXX
    ### 1.1 XXXX
    ![[XXXXX]]]

    ### 1.2 XXXXXXXX
    ![[XXXXXXXX]]
    ![[XXXXXXXXXXXX]]

    ## Module 2: XXXXXXXXX
    ![[XXXXXXXXX]]
    ![[XXXXXXXXXX]]


### 8. Weekly Journal (`03-Daily/Journal/YYYY-MM-DD-to-YYYY-MM-DD.md`)

Voice-to-text capture. User narrates; AI fills directly. Weekly format with daily subsections.

    ---
    title: "January 6 – January 12, 2026"
    tags: [journal, weekly]
    modified: 2026-01-12
    ---

    # January 6 – January 12, 2026

    ## Monday / Jan 6

    （按时间线排序：凌晨 → 上午 → 中午 → 下午 → 晚上。去除口水话，但不减少口述精度。保持第一人称，人名以用户第一次给出的为准。使叙述更有逻辑性，事件按因果或时间顺序排列。）

    ## Tuesday / Jan 7

    （同上）

    ## Wednesday / Jan 8

    （同上）

    ## Thursday / Jan 9

    （同上）

    ## Friday / Jan 10

    （同上）

    ## Saturday / Jan 11

    （同上）

    ## Sunday / Jan 12

    （同上）

    ---

    ## Importance

    （本周最重要的事件、决定或感悟，简要标注）

    ## Reflect

    （对本周的整体反思：做得好的、需要改进的、下周计划）

**Journal Rules**:
- Weekly file: `YYYY-MM-DD-to-YYYY-MM-DD.md`. Each day gets a subsection `## {Weekday} / {Month Day}`.
- Chronological order within each day: early morning → morning → noon → afternoon → evening → night.
- Remove filler words ("然后", "就是", "那个") but preserve all factual details and emotional content.
- Use first person. Names and pronouns must match the user's first mention exactly.
- Reorganize scattered thoughts into logical flow; do not lose information.
- No precise timestamps. Use time-of-day segments only.
- Attachments: `03-Daily/Attachments/daily-{desc}-{YYYYMMDD}.{ext}`.

### 9. Inspiration (`03-Daily/Inspiration/YYYY-MM-DD-{short-desc}.md`)

Capture sudden insights, life reflections, philosophical realizations.

    ---
    title: "Inspiration Title"
    captured: YYYY-MM-DD
    tags: [inspiration]
    ---

    # 核心感悟（一句话概括）

    ## 我的原始感悟详细展开
    （不限制形式，零散想法、自我对话均可。诚实记录"实际想到了什么"。去除口水话但不减少信息精度，按逻辑重新组织语言。）

    ## 这与现在的我在生活上的关联以及对现在的我意味着什么
    （和现状、处境、情绪的关系？击中了什么？与个人当前生活阶段的具体联系。）

    ## 深化后的思考结果及以后想怎么做
    （态度转变、具体行动、验证事项，或"先放着"。经过反思后的结论，而非原始冲动的复述。）

    ## 关联
    - [[...]]

**Inspiration Rules**:
- No forced environmental description.
- Remove filler words but preserve all original meaning and emotional nuance.
- Reorganize scattered thoughts into logical flow; do not lose information.
- Use first person. Names and pronouns must match the user's first mention exactly.
- Attachments: `03-Daily/Attachments/`.


---
