# ARCHITECTURE

**Scope**: Vault directory structure, atom rules, content strategy, naming conventions, quality checks, and maintenance protocols.

**Prerequisites**: None. Read this first before any other reference.

---


## Vault Architecture

**Language**: English for all vault content **except** Daily (Journal & Inspiration) and Explanation files, which are in Chinese.

**Directory Structure** (Fixed):

    .
    ├── index.md                    # Master registry
    ├── log.md                      # Append-only operation log — every operation MUST be logged
    ├── 00-Courses/                 # Curriculum assembly (transclusion layers)
    │   ├── Grade-1/                # Categorized by academic level
    │   │   └── {Course-Name}/
    │   │       ├── {Course-Name}.md
    │   │       ├── {Course-Name}-Explanation.md
    │   │       ├── index.md
    │   │       └── Attachments/
    │   ├── CFA/                    # Professional certification courses
    │   └── Python/                 # Standalone skill courses
    ├── 01-Domains/                 # Knowledge domains
    │   ├── Finance/
    │   │   ├── Finance-atoms.md
    │   │   ├── Books/
    │   │   └── Attachments/
    │   ├── Economy/
    │   ├── MentalOS/
    │   └── SocialDynamics/
    ├── 02-Project/                 # Project workspace
    │   └── Attachments/
    ├── 03-Daily/                   # Daily life
    │   ├── Journal/
    │   ├── Inspiration/
    │   └── Attachments/
    ├── 04-Anything/                # Temporary / incoming / automation staging
    │   └── Attachments/
    ├── 05-Atoms/                   # Centralized atomic knowledge (flat, no subdirs)
    │   ├── stress-tensor.md
    │   ├── behavioral-bias.md
    │   └── binary-search.md
    └── 06-Recently-Deleted/        # 3-month recovery backup

**Atom Centralization Rule**: All atomic knowledge files must reside exclusively in `05-Atoms/`. Flat structure; no subdirectories. No exceptions.

**Atom Cardinality Definition**:
An atom is a **pure conceptual unit** — definitions, formulas, structural relationships, and **worked mathematical examples** (multi-step derivations or standard problem walkthroughs) are all permitted. What atoms must NOT contain are **gratuitous real-life anecdotes** (e.g., "imagine you're shopping for apples...") that do not advance conceptual understanding. Formulas must be written with LaTeX; the atom itself remains concept-only. All extended applied examples and exam-style problem drilling belong in the course's Explanation file.

**Content Strategy**:

| Principle | Rule |
|-----------|------|
| **Granularity** | One atom = one conceptual unit. Judge by conceptual integrity, not word count. Sub-concepts live as sections within a single atom, not as separate files. |
| **Completeness** | Initial capture must be **complete**. Do not omit concepts, examples, formulas, proofs, or procedural details due to laziness or token-saving. The quality check is verification, not a substitute for careful first draft. |
| **No Redundant Application** | Objective atoms do NOT contain standalone `## Application` that merely lists exercise templates. Conceptual analogies and problem-solving strategies belong in `## Mechanism/Theory`. |
| **No Personal Notes (AI)** | AI-created atoms must NOT include `## Personal Notes`. Integrate insights into `## Mechanism/Theory` or `## Definition` instead. |
| **High-Relevance Connections** | In `## Connections`, link ONLY to direct prerequisites, direct consequences, or tightly coupled counterparts. Quality > quantity. |
| **Assembly Layers** | `00-Courses/` and `01-Domains/Books/` use `![[atom-name]]` transclusion. Domain indices (`X-atoms.md`) use `[[links]]` only. |
| **Log Every Operation** | Every create/modify/delete/move MUST be appended to `log.md` immediately. Never skip. |

**Attachments**:
- Stored in the `Attachments/` subfolder of the course/domain/workspace where they first appear.
- Absolute vault-root paths: `![[00-Courses/Grade-1/Solid-Mechanics-1/Attachments/sm-desc-YYYYMMDD.ext]]`.
- Naming: `{domain}-{description}-{YYYYMMDD}.{ext}`. Domain = field of first appearance (e.g., `sm-`, `mer-`, `calculus-`).

---

## Operations & Navigation

**Before any vault operation**:
1. Read `index.md` first to locate relevant atoms.
2. Use Shell `obsidian` CLI or direct filesystem operations as appropriate.
3. Inspect existing files of the same type before creating new ones. Mirror existing patterns precisely.
4. Do not invent new conventions. If the vault uses `Course-Name/index.md` + `Course-Name.md`, follow it exactly.
5. Avoid bulk file reading. Use targeted reads based on `index.md` and `[[links]]` only. Max link-follow depth = 2.

**Naming Convention (Kebab-Case)**:
- All lowercase. Spaces/special chars → single hyphens.
- Numbers as words unless part of a standard term (`binary-search`, `cfa-level-1`).
- Proper nouns lowercased: `newton-laws`, `schrodinger-equation`.

**Naming Standards by Asset Type**:

| Asset | Pattern | Example |
|-------|---------|---------|
| **Atom filename** | `kebab-case.md` | `stress-tensor.md`, `capitalist-mode-production.md` |
| **Course/Domain directory** | `Pascal-Case` | `Solid-Mechanics-1`, `Economy-and-Social-Change`, `Finance` |
| **Course assembly file** | `{Directory-Name}.md` | `Solid-Mechanics-1.md` — must match parent directory name exactly |
| **Course Explanation** | `{Directory-Name}-Explanation.md` | `Solid-Mechanics-1-Explanation.md` |
| **Course index** | `index.md` | — |
| **Domain index** | `{Domain}-atoms.md` | `Finance-atoms.md` |
| **Journal** | `YYYY-MM-DD-to-YYYY-MM-DD.md` | `2026-01-06-to-2026-01-12.md` |
| **Inspiration** | `YYYY-MM-DD-{short-desc}.md` | `2026-01-08-on-focus.md` |

**Attachment Naming**:
- Pattern: `{domain-prefix}-{description}-{YYYYMMDD}.{ext}`
- Multi-image sequences: `{domain-prefix}-{description}-{NN}-{YYYYMMDD}.{ext}` (`NN` = 01, 02, ...)
- Domain prefix examples: `sm-` (solid-mechanics), `calculus-`, `physics-`, `chemistry-`, `python-`, `mer-`
- Description: concise, kebab-case, describes the image content
- Storage: inside the `Attachments/` folder of the course/domain where the image first appears
- Vault-root reference: `![[00-Courses/Grade-1/Solid-Mechanics-1/Attachments/sm-beams-analysis-01-20260422.jpg]]`

**Tag Strategy**:
- **Prioritize existing tags** — reuse tags that already appear in the vault before inventing new ones.
- Prefer kebab-case lowercase; domain-specific proper nouns (e.g., `rosa`, `marx`, `python`) may retain their original form.
- Both inline array `[a, b]` and YAML list formats are acceptable.
- No synonymous duplicates.

**Date Field**: YAML `modified: YYYY-MM-DD`, updated automatically on any edit.

**Source Field**:
- Record the origin of the knowledge. Common formats:
  - `"{Course-Code} Lecture Notes"` — e.g., `"MER101-Solid-Mechanics Lecture Notes"`
  - `"{Course-Name}, Lesson {N}"` — e.g., `"Economy and Social Change: Cross-Cultural Perspective, Lesson 1"`
  - `"{Textbook}, Chapter {N}"` — e.g., `"Thomas' Calculus 14th Ed., Chapter 2"`
  - `"{Textbook}, Sections {X}–{Y}"` — for specific section ranges
  - `"Physics 1 Class Exercise {N}"` — for problem sets or exercises
- Be specific enough to locate the source again.

---

## Quality Check (Mandatory)

After generating or modifying **any** atom, run this checklist before declaring complete:

1. **Knowledge accuracy**: Formulas, theorems, definitions are mathematically/scientifically correct.
2. **Completeness**: All knowledge points from source material are fully captured. **Do not omit** sub-concepts, formulas, proofs, or procedural details.
3. **Presentation quality**: No broken Markdown, unclosed math delimiters, or malformed links.
4. **Attachment integrity**: All embedded images exist in the correct `Attachments/` folder with exact filenames and absolute vault-root paths.
5. **Link validity**: All `[[wikilinks]]` point to existing atoms or valid course/domain files.
6. **Consistency**: Heading structure, YAML fields, and writing style align with existing atoms.
7. **Section appropriateness**: Section titles match the content type (e.g., `## Definition` for definitions, `## Key Mechanisms` for processes, `## Core Ideas` for frameworks). `## Connections` is mandatory.
8. **No gratuitous real-life anecdotes in atoms**: Atoms remain concept-focused; extended applied scenarios and exam-style problem drilling belong in the Explanation file.
9. **Overall readability**: Smooth flow, proper formatting, clear structure.

Fix errors immediately. Report unresolved issues to the user.

---

## Protocols

### 06-Recently-Deleted/

- **Purpose**: 3-month recovery window for deleted/modified atoms.
- **Location**: Sibling to `05-Atoms/`.
- **Naming**:
  - Deleted: `{original-name}-DELETED-{YYYYMMDD}.md` (tag: `recently-deleted`)
  - Modified backup: `{original-name}-MODIFIED-{YYYYMMDD}.md` (tag: `recently-modified`)
- **Cleanup**: Delete entries older than 3 months during routine maintenance.

### Log Specification

**Format**:
```markdown
## [YYYY-MM-DD HH:MM] | Action | Target | Summary
- Detail line 1
- Detail line 2
```

**Ordering**: **Reverse chronological** — newest entry at the **top**, immediately after `# Vault Operation Log` heading. Never append to the bottom.

**Rules**:
- Group all details of a single operation under one timestamp.
- Be concise but specific (file counts, atoms affected, attachments processed).
- Auto-purge entries older than 3 months during maintenance.


---
