---
name: obsidian-vault
description: "Master skill for all Obsidian vault operations — wiki management, note creation, Markdown formatting, CLI commands, and Bases. Load the appropriate reference based on the task at hand."
license: Proprietary
---

# Obsidian Vault Manager

Filesystem-first Obsidian vault operations. All vault work starts with resolving the vault path, then using the right file tool for the job.

## Vault Basics

### Resolve the Vault Path

Use a known or resolved vault path before calling file tools.

The documented convention is the `OBSIDIAN_VAULT_PATH` environment variable (from `~/.hermes/.env`). If unset, fall back to `~/Documents/Obsidian Vault`.

> **Important:** File tools do not expand shell variables. Resolve the path first (via `terminal` if needed), then pass the concrete absolute path to `read_file`, `write_file`, `patch`, or `search_files`.

### Read Notes

Use `read_file` with the resolved absolute path. Prefer this over `cat` — it provides line numbers and pagination.

### Search

Use `search_files` for both filename and content searches. Prefer this over `grep`, `find`, or `ls`.

- **Filenames:** `search_files` with `target: "files"` and a filename `pattern`.
- **Contents:** `search_files` with `target: "content"`, the content regex as `pattern`, and `file_glob: "*.md"` to restrict to markdown notes.

### Create & Edit

- **Create:** `write_file` with the resolved absolute path and full markdown content. Prefer this over shell heredocs to avoid quoting issues.
- **Append:** Read the note with `read_file`, then use `patch` for anchored appends (adding after a stable heading). Use `write_file` only when rewriting the whole note is clearer.
- **Targeted edits:** `patch` for focused changes when the current content gives stable context.

### Wikilinks

Obsidian links notes with `[[Note Name]]` syntax. Use these when creating notes to link related content.

---

## Generation Priority Hierarchy

1. **User's latest stated requirements** in the current conversation
2. **Existing patterns in the vault** — mirror what the vault already does
3. **Templates and rules in the references** — fallback when #1 and #2 are silent

When #1 is present, it overrides everything. Between #2 and #3, prefer #2.

---

## Task-to-Reference Map

| Task | Load This Reference | Why |
|------|---------------------|-----|
| First time working with this vault | **ARCHITECTURE.md** | Directory structure, atom rules, naming, quality checks |
| Create or modify an atom (05-Atoms/) | **CRAFT.md** + ARCHITECTURE.md | Atom templates and rules |
| Create or modify a course/domain index | **CRAFT.md** + ARCHITECTURE.md | Index and assembly templates |
| Create or modify Weekly Journal / Inspiration | **CRAFT.md** + ARCHITECTURE.md | Daily templates |
| Write or update an Explanation | **EXPLANATION.md** + CRAFT.md + ARCHITECTURE.md | Explanation standards and pedagogical requirements |
| Run /lint or answer /query | **WORKFLOWS.md** + all above | Workflow definitions |
| Manage deleted files or operation logs | **ARCHITECTURE.md** (Protocols section) | Maintenance protocols |
| Use Obsidian CLI commands | **TOOLS.md** (CLI section) | Command syntax and patterns |
| Format Markdown / wikilinks / callouts / embeds | **TOOLS.md** (Markdown section) | Syntax reference |
| Create or edit a .base database view | **TOOLS.md** (Bases section) | Filter, formula, and view syntax |

## Reference Dependency Graph

```
ARCHITECTURE.md          TOOLS.md
       |                      |
       v                      v
   CRAFT.md              (independent)
       |
       v
  EXPLANATION.md
       |
       v
  WORKFLOWS.md
```

- **ARCHITECTURE.md** has no prerequisites. Read it first for any vault operation.
- **CRAFT.md** requires ARCHITECTURE.md (naming conventions and atom rules must be known before using templates).
- **EXPLANATION.md** requires ARCHITECTURE.md and CRAFT.md (you cannot explain atoms you do not understand).
- **WORKFLOWS.md** requires ARCHITECTURE.md, CRAFT.md, and EXPLANATION.md (lint and query operate on files defined in the other references).
- **TOOLS.md** is independent. Load only the section (CLI / Markdown / Bases) relevant to the current task.

---

## Reference Index

### [ARCHITECTURE.md](references/ARCHITECTURE.md)
- Vault directory structure (00-Courses through 06-Recently-Deleted)
- Atom centralization rule and cardinality definition
- Content strategy (granularity, completeness, Connections, logging)
- Naming conventions (kebab-case, asset type patterns, attachment naming)
- Tag strategy (prioritize existing, kebab-case preferred)
- Source and date fields
- Quality Check checklist (9 items)
- Protocols: 06-Recently-Deleted/ naming and cleanup rules
- Log specification format and ordering

### [CRAFT.md](references/CRAFT.md)
- **Objective Atom** template — section titles are content-driven, `## Connections` mandatory
- **Subjective Atom** template — Core Proposition, Logic Chain, Application, Critique & Conflicts, Evolutionary Notes, Personal Notes
- **Master Index** template — vault-wide registry grouped by course and domain
- **Course Assembly** template — transclusion-based curriculum file
- **Course Index** template — navigation hub with module groupings
- **Domain Index** template — navigation hub for knowledge domains
- **Book Notes** template — reserved
- **Weekly Journal** template — voice-to-text weekly format with daily subsections
- **Inspiration** template — 4-section insight capture

### [EXPLANATION.md](references/EXPLANATION.md)
- Explanation file definition and content rules (Chinese-only, no YAML/Connections/wikilinks)
- Length standards: Simple 3–10×, Medium 10–30×, Hard 30×+ (no cap)
- Pedagogical requirements (analogy, derivations, worked examples, Tricks Box, prerequisite bridging, density check)
- Synchronization Rule — atom changes mandate immediate Explanation updates
- Key Rules Echo (90% Mastery Test, Synchronization, Length Standards)
- Explanation Quality Check

### [WORKFLOWS.md](references/WORKFLOWS.md)
- **/lint** — 5-stage pipeline: Scan → Auto-Repair → Conflict Arbitration → Weekly Merge → Final Verification
- **/query** — 7-step execution: Read Index → Read Atoms → Expand links → Check Explanation → Synthesize → Backfill → Log

### [TOOLS.md](references/TOOLS.md)
- **CLI Reference** — syntax, file/vault targeting, common commands, plugin development cycle, developer commands
- **Markdown Reference** — wikilinks, embeds, callouts, properties, tags, comments, LaTeX, Mermaid, footnotes, complete example
- **Bases Reference** — schema, filters, operators, file properties, formulas, key functions, duration/date arithmetic, view types (table/cards/list/map), summary formulas, 3 complete examples, YAML quoting rules, troubleshooting
