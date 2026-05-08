---
name: github
description: "Complete GitHub workflow suite: auth detection, repository lifecycle, issues, PRs, code review, CI/CD, and codebase metrics. Uses gh CLI as primary, falls back to git+curl when gh is unavailable."
metadata:
  hermes:
    tags: [GitHub, git, gh-cli, PR, issues, code-review, CI/CD, repo-management]
    related_skills: []
---

# GitHub Workflow Suite

Complete GitHub automation from authentication through merge. This skill covers the full repository lifecycle with **gh CLI** as the primary path and **git + curl** as the universal fallback.

## 0. Authentication Detection (run this first)

Every GitHub workflow starts with auth detection. Run the helper script — it sets `$GH_AUTH_METHOD`, `$GITHUB_TOKEN`, `$GH_USER`, and repo variables automatically:

```bash
source scripts/gh-env.sh
```

**Decision tree after sourcing:**
- `GH_AUTH_METHOD=gh` → use `gh` commands for everything
- `GH_AUTH_METHOD=curl` → use `git` + `curl` with `$GITHUB_TOKEN`
- `GH_AUTH_METHOD=none` → load `references/auth-setup.md` to configure auth

If you need to set up auth from scratch (HTTPS token, SSH key, or gh login), see `references/auth-setup.md`.

---

## 1. Repository Lifecycle

### Clone / Create / Fork

```bash
# Clone (pure git — works everywhere)
git clone https://github.com/owner/repo.git

# Create repo (gh)
gh repo create my-project --public --clone

# Create repo (curl fallback)
curl -s -X POST -H "Authorization: token $GITHUB_TOKEN" \
  https://api.github.com/user/repos \
  -d '{"name":"my-project","private":false}'

# Fork (gh)
gh repo fork owner/repo --clone

# Fork (curl)
curl -s -X POST -H "Authorization: token $GITHUB_TOKEN" \
  https://api.github.com/repos/owner/repo/forks
```

For template repos, org repos, branch protection, secrets, and releases — see `references/repo-management.md`.

### Repository Settings & Actions

```bash
# List workflows and runs
gh workflow list
gh run list --limit 10
gh run view <RUN_ID> --log-failed

# Create a release
gh release create v1.0.0 --generate-notes
```

---

## 2. Issue Lifecycle

### View & Search

```bash
# List open issues
gh issue list --state open --label "bug"

# Search issues
gh issue list --search "authentication error" --state all

# View specific issue
gh issue view 42
```

### Create an Issue

Choose the right template from `templates/`, then create:

```bash
# Bug report
cat templates/issue-bug-report.md | gh issue create --title "..." --body-file -

# Feature request
cat templates/issue-feature-request.md | gh issue create --title "..." --body-file -
```

### Manage Issues

```bash
# Label and assign
gh issue edit 42 --add-label "priority:high,bug" --add-assignee @me

# Comment and close
gh issue comment 42 --body "Root cause found — working on fix."
gh issue close 42 --reason "completed"
```

For bulk operations, triage workflows, and the full curl fallback — see `references/issue-management.md`.

**Auto-close via PR:** Include `Closes #42`, `Fixes #42`, or `Resolves #42` in the PR body.

---

## 3. Pull Request Lifecycle

### Branch → Commit → Push

```bash
# Start from clean main
git checkout main && git pull origin main

# Create feature branch
git checkout -b feat/add-auth

# (make changes with file tools)

# Commit with conventional format
git commit -m "feat(auth): add JWT-based authentication

- Add login/register endpoints
- Add password hashing with argon2
- Add middleware for protected routes

Closes #42"

# Push
git push -u origin HEAD
```

For conventional commit type reference, see `references/conventional-commits.md`.

### Create PR

```bash
# Bugfix PR — use the bugfix template
cat templates/pr-body-bugfix.md | gh pr create --body-file -

# Feature PR — use the feature template
cat templates/pr-body-feature.md | gh pr create --body-file -
```

### Monitor CI

```bash
# Check status once
gh pr checks

# Watch until completion
gh pr checks --watch
```

If CI fails, see `references/ci-troubleshooting.md` for the auto-fix decision tree.

### Merge

```bash
# Squash merge + delete branch (cleanest)
gh pr merge --squash --delete-branch

# Or enable auto-merge
gh pr merge --auto --squash --delete-branch
```

For the complete PR workflow with curl fallbacks (create PR, poll CI, merge via API) — see `references/pr-workflow.md`.

---

## 4. Code Review

### Pre-Push Review (local)

Before pushing, review your own changes:

```bash
# Scope of changes
git diff main...HEAD --stat
git log main..HEAD --oneline

# Review file by file
git diff main...HEAD -- src/auth.py

# Check for common issues
git diff main...HEAD | grep -n "print(\|console\.log\|TODO\|FIXME\|debugger"
git diff main...HEAD | grep -in "password\|secret\|api_key\|private_key"
```

Use the structured review output format from `references/review-output-template.md`.

### PR Review (on GitHub)

```bash
# Check out PR locally for full context
git fetch origin pull/123/head:pr-123 && git checkout pr-123

# Review with checklist:
# 1. Correctness — does it do what it claims?
# 2. Security — no secrets, input validation, auth checks
# 3. Quality — clear naming, DRY, focused functions
# 4. Testing — new paths covered, happy + error cases
# 5. Performance — no N+1, blocking ops
# 6. Documentation — APIs documented, README updated
```

Submit the review atomically with inline comments:

```bash
gh pr review 123 --request-changes --body "See inline comments."
```

For the full end-to-end PR review recipe (checkout → read diff → run tests → atomic review with severity icons → cleanup) — see `references/code-review.md`.

---

## 5. Codebase Inspection

Analyze repository metrics before or after changes:

```bash
pip install pygount

# Language breakdown + LOC
pygount --format=summary \
  --folders-to-skip=".git,node_modules,venv,.venv,__pycache__,dist,build" \
  .
```

For detailed usage, exclusion lists by project type, and output interpretation — see `references/codebase-inspection.md`.

---

## 6. Advanced API Queries

When `gh` subcommands don't cover what you need, use `gh api` or raw `curl`:

```bash
# Structured query with jq
gh api repos/owner/repo/pulls/55 --jq '.title, .state, .user.login'

# List changed files in a PR
curl -s -H "Authorization: token $GITHUB_TOKEN" \
  https://api.github.com/repos/$GH_OWNER/$GH_REPO/pulls/123/files \
  | python3 -c "import sys,json; [print(f['filename']) for f in json.load(sys.stdin)]"
```

For the full REST API endpoint reference (repos, PRs, issues, actions, releases, secrets, branch protection) — see `references/api-cheatsheet.md`.

---

## Quick Decision Tree

```
Need to work with GitHub
├── Not authenticated? → source scripts/gh-env.sh
│   └── Still none? → references/auth-setup.md
├── Repo doesn't exist? → references/repo-management.md (create/fork/clone)
├── Need to file a bug/request? → templates/issue-*.md + Section 2
├── Starting new work? → Section 3 (branch → commit → PR)
├── CI failed? → references/ci-troubleshooting.md
├── Need to review code?
│   ├── Before push → Section 4 (pre-push)
│   └── PR review → references/code-review.md
├── Need repo metrics? → references/codebase-inspection.md
└── API not covered by gh? → references/api-cheatsheet.md
```
