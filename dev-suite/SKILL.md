---
name: dev-suite
description: "Development tools: MCP server building, React/Next.js optimization, parallel Codex workers, HTML artifacts, Rust code sync, and git worktree management. Use for coding tasks, server building, frontend optimization, or repository management."
---

# Development Suite

Unified skill for software development and repository management.

## Task-to-Reference Map

| Task | Load This Reference |
|------|---------------------|
| Build MCP (Model Context Protocol) servers | [MCP-BUILDER.md](references/mcp-builder.md) |
| React/Next.js performance optimization | [VERCEL-REACT-BEST-PRACTICES.md](references/vercel-react-best-practices.md) |
| Parallel Codex CLI agent management | [CODEX-WORKER.md](references/codex-worker.md) |
| Git worktree audit and cleanup | [WORKTREE-STATUS.md](references/worktree-status.md) |
| Rust code sync with Python changes | [GEN-RUST.md](references/gen-rust.md) |
| Complex HTML artifacts (React + Tailwind) | [WEB-ARTIFACTS-BUILDER.md](references/web-artifacts-builder.md) |

## Reference Index

### [MCP-BUILDER.md](references/mcp-builder.md)
Guide for creating MCP servers to integrate external APIs, in Python (FastMCP) or Node/TypeScript (MCP SDK).

### [VERCEL-REACT-BEST-PRACTICES.md](references/vercel-react-best-practices.md)
React and Next.js performance optimization guidelines from Vercel Engineering.

### [CODEX-WORKER.md](references/codex-worker.md)
Spawn and manage multiple Codex CLI agents via tmux for parallel task execution.

### [WORKTREE-STATUS.md](references/worktree-status.md)
Audit git worktrees — check merge status, uncommitted changes, and cleanup candidates.

### [GEN-RUST.md](references/gen-rust.md)
Sync Rust implementation with Python changes — review, map modules, port logic, update tests.

### [WEB-ARTIFACTS-BUILDER.md](references/web-artifacts-builder.md)
Elaborate multi-component HTML artifacts using React, Tailwind CSS, and shadcn/ui.
