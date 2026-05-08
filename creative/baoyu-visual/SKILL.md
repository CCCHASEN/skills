---
name: baoyu-visual
description: "Baoyu visual generation suite: knowledge comics (知识漫画) and infographics (信息图). Shared workflow for content analysis, reference-image extraction, and image_generate-based output. Diverges at Step 3: comics use storyboard+character pipelines; infographics use structured data+layout pipelines."
metadata:
  hermes:
    tags: [visual, comic, infographic, baoyu, image-generation]
    related_skills: []
---

# Baoyu Visual Suite

Visual content generation in the Baoyu style. Two output formats share a common foundation but diverge in structure.

## Output Format Router

| User Intent | Format | Key Characteristics |
|-------------|--------|---------------------|
| "知识漫画", "教育漫画", biography, tutorial, narrative | **Comic** | Multi-page, storyboard-driven, character consistency via text descriptions |
| "信息图", "可视化", visual summary, data graphic | **Infographic** | Single-page, layout-driven, data fidelity (no summarization) |

## Shared Foundation (Steps 1–2)

### Step 1: Content Analysis

1. **Ingest** source content (text, file, URL, or topic)
2. **Analyze**: topic, data type, complexity, tone, audience, language
3. **Save** source + analysis to output directory (`{topic-slug}/`)
4. **Handle conflicts**: if files exist, rename with `-backup-YYYYMMDD-HHMMSS`

### Step 2: Reference Images (optional)

When the user supplies reference images:
- Extract **text traits** (style, palette, composition) — never pass images to `image_generate`
- Copy refs to `refs/` for provenance
- Record usage mode (`style`, `palette`, `scene`) in prompt frontmatter

### Language Priority

1. User-specified language
2. Conversation language
3. Source content language

All output (storyboard, prompts, user messages) uses this language. Technical terms stay in English.

---

## Path A: Knowledge Comic

### Step 3: Storyboard + Characters

Generate `storyboard.md` and `characters/characters.md`:
- Define recurring characters with text descriptions
- Break narrative into pages/panels
- Choose visual dimensions:

| Dimension | Options |
|-----------|---------|
| Art style | `ligne-claire`, `manga`, `realistic`, `ink-brush`, `chalk`, `minimalist` |
| Tone | `neutral`, `warm`, `dramatic`, `romantic`, `energetic`, `vintage`, `action` |
| Layout | `standard`, `cinematic`, `dense`, `splash`, `mixed`, `webtoon`, `four-panel` |
| Presets | `ohmsha`, `wuxia`, `shoujo`, `concept-story`, `four-panel` (special rules apply) |

Auto-selection guidance: `references/comic/auto-selection.md`

### Step 4: Review Gates (conditional)

If user requested review in Step 2:
- Review storyboard outline before generating prompts
- Review prompts before generating images

### Step 5: Generate Prompts

Write each page's full prompt to `prompts/NN-{cover|page}-[slug].md` BEFORE calling `image_generate`.

**Character consistency**: embed text descriptions from `characters/characters.md` inline in every page prompt. `image_generate` is prompt-only and cannot accept images.

### Step 6: Generate Images

```bash
# Map aspect ratio
# 3:4, 9:16 → portrait | 4:3, 16:9 → landscape | 1:1 → square

# Download with ABSOLUTE path only
curl -fsSL "<image_url>" -o /abs/path/to/comic/{slug}/NN-page-{slug}.png
```

**Critical**: Never rely on persistent-shell CWD for `curl -o`. Always use fully-qualified paths.

### Step 7: Character Sheet (optional)

For multi-page comics with recurring characters, generate `characters/characters.png` (landscape) as a **human-facing review artifact**. The PNG aids visual verification and later regeneration — but page prompts already use the text descriptions from Step 3.

Full workflow details: `references/comic/workflow.md`

---

## Path B: Infographic

### Step 3: Structured Content

Transform content into `structured-content.md`:
- Title + learning objectives
- Sections: key concept, content (verbatim), visual element, text labels
- Data points: copy all statistics/quotes exactly (no summarization)
- Strip any credentials/secrets

### Step 4: Recommend Layout × Style

**Check keyword shortcuts first** — if user input matches a keyword, auto-select the associated layout and prioritize styles.

Otherwise recommend 3–5 combinations based on:
- Data structure → layout
- Content tone → style
- Audience expectations

| Layout | Best For |
|--------|----------|
| `bento-grid` | Multi-topic overview (default) |
| `linear-progression` | Timelines, processes |
| `binary-comparison` | A vs B, before-after |
| `hierarchical-layers` | Pyramids, priorities |
| `tree-branching` | Categories, taxonomies |
| `funnel` | Conversion, filtering |
| `dense-modules` | High-density data guides |

21 layouts: `references/infographic/layouts/<layout>.md`
21 styles: `references/infographic/styles/<style>.md`

### Step 5: Assemble Prompt

Combine:
1. Layout definition
2. Style definition
3. Base template (`references/infographic/base-prompt.md`)
4. Structured content
5. Confirmed language + aspect ratio

Save to `prompts/infographic.md`.

### Step 6: Generate Image

Use `image_generate` with assembled prompt. Map aspect ratio to `landscape`/`portrait`/`square`. Download to absolute path.

Full workflow details: `references/infographic.md`

---

## Common Pitfalls

| Issue | Rule |
|-------|------|
| **CWD drift** | Always use absolute paths for `curl -o` |
| **Data fidelity** | Infographic: never alter statistics ("73%" stays "73%") |
| **Prompt-first** | Always write prompt file BEFORE calling `image_generate` |
| **Image-only tool** | `image_generate` accepts prompt + aspect only. No reference images, no visual input |
| **Download verify** | Check file exists and is non-empty after every download |
| **Backup** | Rename existing files with `-backup-YYYYMMDD-HHMMSS` before overwriting |
