# WORKFLOWS

**Scope**: /lint (5-stage pipeline) and /query (execution flow) workflows.

**Prerequisites**:
- [ARCHITECTURE.md](ARCHITECTURE.md) — vault structure
- [CRAFT.md](CRAFT.md) — file templates (lint checks them)
- [EXPLANATION.md](EXPLANATION.md) — Explanation standards (query may quote them)

---


## Workflows

### /lint

5-stage pipeline. Execute in order.

**Stage 1: Scan**
1. **Dead Links**: `[[link]]` → non-existent file. Remove reference from all citing files.
2. **Orphan Atoms**: Files in `05-Atoms/` with zero backlinks. Query user for deletion; if confirmed, move to `06-Recently-Deleted/{filename}-DELETED-{YYYYMMDD}.md`.
3. **Conflicts**: Extract `## Critique & Conflicts` from `conflict`-tagged files.
4. **Index Sync**: Ensure `index.md` reflects all `05-Atoms/` files.
5. **Attachments**: Delete unreferenced files in any `Attachments/` folder older than 30 days.
6. **Weekly Newcomers**: Flag files modified this week for Stage 4.

**Stage 2: Auto-Repair**
- Execute fixes for dead links, orphan atoms, index sync, and attachment cleanup identified in Stage 1.
- Log: `## [YYYY-MM-DD HH:MM] lint | Auto-fixed: X dead links, Y attachments cleaned | Index synced`

**Stage 3: Conflict Arbitration**
Present full `## Critique & Conflicts` text from all conflict-tagged atoms. Wait for user resolution.

**Stage 4: Weekly Merge**
Ask: "Analyze this week's newcomers for connections? [Y/N]"
If Y: Check conceptual integrity → suggest merges/links → execute after confirmation.

**Stage 5: Final Verification**
Rescan post-repairs.

### /query

**Execution Flow**:
1. **Read Index**: Scan `index.md` to locate relevant atoms.
2. **Read Atoms**: Targeted reads from `05-Atoms/`.
3. **Expand (max depth 2)**: Follow `[[links]]` in atoms.
4. **Check Explanation First**: If the relevant course/domain has an Explanation file and the question is covered, quote it directly. Do NOT summarize or精简 the quoted content — the Explanation was written to satisfy the 90% Mastery Test, and any truncation may break that standard.
5. **Synthesize (if not in Explanation)**:
   - Explain via analogy/metaphor (no concept stacking).
   - Cite `[[filename]]` only.
   - Inject user's personalized needs and context.
   - **Output must satisfy the full Explanation standard**: 90% Mastery Test, vivid analogy, step-by-step reasoning, plain-language restatement after every formula, and a Tricks Box if applicable. A `/query` answer is a mini-Explanation — do not lower the bar just because it is conversational.
6. **Backfill**:
   - Substantial: Ask "Save to Personal Notes of [[atom]] or create new Subjective Atom?"
   - Short: Append to relevant atom's `## Personal Notes`.
7. **Log**: `## [YYYY-MM-DD HH:MM] query | Question summary | Sources: [[atom1]], [[atom2]]`

**Citation Rule**: Only reference atoms that exist in `05-Atoms/`.

---
