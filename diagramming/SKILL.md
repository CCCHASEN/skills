---
name: diagramming
description: "Diagram generation: choose between dark-themed SVG architecture diagrams (formal, tech-focused) and hand-drawn Excalidraw sketches (informal, collaborative)."
metadata:
  hermes:
    tags: [diagram, visualization, architecture, excalidraw, SVG, flowchart]
    related_skills: []
---

# Diagramming Skill

Generate diagrams as self-contained files. No external tools, APIs, or rendering libraries needed.

## Tool Selection

```
What kind of diagram?
├── Formal technical architecture
│   ├── Cloud infrastructure (VPC, regions, managed services)
│   ├── Microservice topology / service mesh
│   ├── Database + API map, deployment diagrams
│   └── System layers (frontend / backend / storage)
│       → architecture-diagram (dark SVG/HTML)
│
└── Informal conceptual diagram
    ├── Flowchart, sequence diagram, decision tree
    ├── Architecture sketch, concept map
    ├── UI wireframe or whiteboard-style diagram
    └── Anything needing a hand-drawn aesthetic
        → excalidraw (JSON, open at excalidraw.com)
```

## Output Comparison

| | Architecture Diagram | Excalidraw |
|---|---|---|
| **Format** | `.html` (inline SVG + CSS) | `.excalidraw` (JSON) |
| **Aesthetic** | Dark, grid-backed, professional | Hand-drawn, whiteboard |
| **Open with** | Any browser | excalidraw.com |
| **Edit later** | Edit source HTML | Drag-and-drop at excalidraw.com |
| **Share** | Send the HTML file | Upload via script for shareable link |
| **Best for** | Tech docs, presentations, READMEs | Collaboration, brainstorming, RFCs |

---

## Workflow: Architecture Diagram

Generate a dark-themed SVG diagram as a standalone HTML file:

```bash
# Save the generated HTML, then open it
open ./my-architecture.html        # macOS
xdg-open ./my-architecture.html    # Linux
```

### Design System

**Color palette (semantic by component type):**

| Type | Fill | Stroke |
|------|------|--------|
| Frontend | `rgba(8,51,68,0.4)` | `#22d3ee` (cyan) |
| Backend | `rgba(6,78,59,0.4)` | `#34d399` (emerald) |
| Database | `rgba(76,29,149,0.4)` | `#a78bfa` (violet) |
| Cloud/AWS | `rgba(120,53,15,0.3)` | `#fbbf24` (amber) |
| Security | `rgba(136,19,55,0.4)` | `#fb7185` (rose) |
| Message Bus | `rgba(251,146,60,0.3)` | `#fb923c` (orange) |
| External | `rgba(30,41,59,0.5)` | `#94a3b8` (slate) |

**Typography:** JetBrains Mono, sizes 12px (names) / 9px (sublabels) / 8px (annotations)
**Background:** Slate-950 (`#020617`) with 40px grid pattern

### Structure

1. **Header** — title + pulsing status dot
2. **Main SVG** — diagram in rounded card
3. **Summary Cards** — 3-card grid below for high-level details
4. **Footer** — minimal metadata

For full rendering rules (z-order, arrow masking, spacing logic, legend placement) and the complete HTML template — `references/architecture-diagram.md` and `templates/architecture-template.html`.

---

## Workflow: Excalidraw

Generate a hand-drawn diagram as `.excalidraw` JSON:

```json
{
  "type": "excalidraw",
  "version": 2,
  "source": "hermes-agent",
  "elements": [ ... ],
  "appState": { "viewBackgroundColor": "#ffffff" }
}
```

Save with `write_file`, then drag onto [excalidraw.com](https://excalidraw.com) or upload for a shareable link:

```bash
python3 scripts/excalidraw-upload.py ~/diagrams/my_diagram.excalidraw
```

### Element Essentials

**Container-bound text** (the correct way to label shapes):
```json
{ "type": "rectangle", "id": "r1", "x": 100, "y": 100, "width": 200, "height": 80,
  "boundElements": [{ "id": "t_r1", "type": "text" }] },
{ "type": "text", "id": "t_r1", "x": 105, "y": 110, "width": 190, "height": 25,
  "text": "Label", "fontSize": 20, "fontFamily": 1, "containerId": "r1" }
```

**Arrow bindings:**
```json
{ "type": "arrow", "points": [[0,0],[150,0]],
  "startBinding": { "elementId": "r1", "fixedPoint": [1, 0.5] },
  "endBinding": { "elementId": "r2", "fixedPoint": [0, 0.5] } }
```

**Drawing order = z-order.** Emit progressively: background → shape → its text → its arrows → next shape.

For the full element reference, color palette, dark mode, sizing guidelines, and examples — `references/excalidraw.md`, `references/excalidraw-colors.md`, `references/excalidraw-examples.md`.
