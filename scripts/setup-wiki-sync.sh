#!/usr/bin/env bash

################################################################################
# Setup GitHub Actions Wiki Sync Workflow
################################################################################
#
# DESCRIPTION
# -----------
# Automates the creation and deployment of a GitHub Actions workflow that
# synchronizes Markdown documentation from a repository's docs/ directory
# into its GitHub Wiki. This script uses the `gh` CLI to programmatically
# create the workflow, merge the feature branch, and trigger initial sync.
#
# IMPLEMENTATION DETAILS
# ----------------------
#
# 1. WORKFLOW DESIGN (`.github/workflows/wiki-autogen.yml`)
#    - Triggers on: push to main touching docs/, driver source, or config
#    - Validates docs build with `mkdocs build` before sync
#    - Syncs Markdown from docs/ tree into Wiki repository
#    - Handles GitHub Wiki limitations:
#      * Flattens nested paths (e.g., api/visa/dl3021 → dl3021)
#      * Rewrites internal .md links to wiki-safe page targets
#      * Detects case-insensitive collisions and disambiguates (e.g., ARCHITECTURE-2)
#      * Maps docs/index.md → Wiki Home.md
#      * Auto-generates _Sidebar.md and _Footer.md navigation
#
# 2. LINK REWRITING ALGORITHM
#    - Parses all [label](target) Markdown links
#    - Skips external URLs (http://, https://, mailto:) and anchors
#    - Resolves relative paths (handles ../, ./) during path normalization
#    - Maps source relative paths to flat wiki page names via collision detection
#    - Result: docs/api/visa/dl3021.md → wiki link (dl3021) not (api/visa/dl3021)
#
# 3. COLLISION DETECTION & RESOLUTION
#    - Scans all source doc files by stem name (filename without extension)
#    - Detects case-insensitive duplicates (architecture vs ARCHITECTURE)
#    - Resolves collisions by converting to hierarchical names (api-visa-dl3021)
#    - Ensures unique page names via suffix counter (ARCHITECTURE-2 if needed)
#
# 4. WORKFLOW TRIGGERING & MONITORING
#    - Uses `gh workflow run` to dispatch on-demand
#    - Uses `gh run view` and `gh run list` to monitor execution
#    - Validates wiki repo exists before full sync attempt
#    - Commits to wiki only if content changed (skip ci to prevent loops)
#
# 5. GITHUB WIKI PREREQUISITES
#    - Wiki must be initialized via GitHub UI (create one page manually)
#    - Creates <repo>.wiki.git that workflow can push to
#    - Cannot be automated via API; requires one-time manual step
#
# REQUIREMENTS
# -----------
# - bash 4.0+
# - `gh` CLI authenticated (gh auth login)
# - git command available
# - Repository must have mkdocs.yml + docs/ directory
# - GitHub Wiki must be initialized in UI (one-time manual step)
#
# USAGE
# -----
#   ./setup-wiki-sync.sh <owner>/<repo>
#
# EXAMPLE
# -------
#   ./setup-wiki-sync.sh unearth4334/lab-drivers
#
# RETURNS
# -------
#   0 on success
#   1 on error (invalid repo, auth failure, workflow trigger failure, etc.)
#
################################################################################

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Script configuration
WORKFLOW_FILE=".github/workflows/wiki-autogen.yml"
WORKFLOW_NAME="Sync Docs to GitHub Wiki"
BRANCH_NAME="explore/wiki-autogen"

################################################################################
# Utility Functions
################################################################################

log_info() {
    echo -e "${GREEN}[INFO]${NC} $*"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $*"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $*" >&2
}

fail() {
    log_error "$@"
    exit 1
}

check_command() {
    if ! command -v "$1" &>/dev/null; then
        fail "Command not found: $1"
    fi
}

################################################################################
# Validation & Setup
################################################################################

main() {
    local repo="${1:-}"
    
    if [[ -z "$repo" ]]; then
        fail "Usage: $0 <owner>/<repo>"
    fi
    
    # Validate required commands
    check_command gh
    check_command git
    check_command mkdocs
    
    log_info "Starting Wiki sync setup for: $repo"
    
    # Verify gh authentication
    if ! gh auth status &>/dev/null; then
        fail "Not authenticated with gh CLI. Run: gh auth login"
    fi
    log_info "GitHub CLI authenticated"
    
    # Verify repo exists and is accessible
    if ! gh repo view "$repo" &>/dev/null; then
        fail "Repository not found or not accessible: $repo"
    fi
    log_info "Repository verified: $repo"
    
    # Get repo details
    local repo_http=$(gh repo view "$repo" --json url --query url | tr -d '"')
    local repo_ssh=$(gh repo view "$repo" --json sshUrl --query sshUrl | tr -d '"')
    
    log_info "Repository URL (SSH): $repo_ssh"
    
    # Clone or navigate to repo
    if [[ ! -d "$repo" && ! -d .git ]]; then
        log_info "Cloning repository..."
        git clone "$repo_ssh" "$repo"
        cd "$repo"
    elif [[ -d .git ]]; then
        log_info "Using current repository"
    else
        log_info "Navigating to repository directory..."
        cd "$repo"
    fi
    
    # Verify mkdocs and docs structure
    if [[ ! -f mkdocs.yml ]]; then
        fail "mkdocs.yml not found. Initialize MkDocs first: mkdocs new ."
    fi
    if [[ ! -d docs ]]; then
        fail "docs/ directory not found. Create with sample content first."
    fi
    log_info "MkDocs configuration verified"
    
    # Verify docs build
    log_info "Validating MkDocs build..."
    if ! mkdocs build --quiet 2>/dev/null; then
        fail "MkDocs build failed. Fix documentation errors first."
    fi
    log_info "MkDocs build successful"
    
    # Create or update feature branch
    log_info "Setting up feature branch: $BRANCH_NAME"
    git fetch origin 2>/dev/null || true
    
    if git rev-parse --verify "$BRANCH_NAME" &>/dev/null; then
        log_warn "Branch $BRANCH_NAME already exists, checking out..."
        git checkout "$BRANCH_NAME"
    else
        git checkout -b "$BRANCH_NAME"
    fi
    
    # Generate workflow file
    log_info "Generating workflow file: $WORKFLOW_FILE"
    mkdir -p "$(dirname "$WORKFLOW_FILE")"
    generate_workflow_file > "$WORKFLOW_FILE"
    
    # Stage and commit
    git add "$WORKFLOW_FILE"
    git commit -m "ci(wiki): initialize github actions docs-to-wiki sync" || log_warn "No changes to commit"
    
    log_info "Pushing feature branch..."
    git push -u origin "$BRANCH_NAME" 2>&1 | grep -v "^hint:" || true
    
    # Create pull request
    log_info "Creating pull request..."
    local pr_url=$(gh pr create \
        --base main \
        --head "$BRANCH_NAME" \
        --title "ci(wiki): sync docs to GitHub Wiki via Actions" \
        --body "$(generate_pr_body)" \
        --web \
        2>&1 | tail -1)
    
    # Merge PR
    log_info "Merging pull request..."
    if ! gh pr merge "$BRANCH_NAME" --merge --delete-branch 2>/dev/null; then
        log_warn "Could not auto-merge PR. Please merge manually at: $pr_url"
    else
        log_info "Pull request merged and branch deleted"
    fi
    
    # Fetch updated main
    git checkout main
    git pull origin main
    
    # Verify workflow is registered
    log_info "Verifying workflow registration..."
    if ! gh workflow list | grep -q "$WORKFLOW_NAME"; then
        fail "Workflow not found after merge. Check repository for errors."
    fi
    log_info "Workflow registered successfully"
    
    # Manual wiki initialization prompt
    log_warn "MANUAL STEP REQUIRED:"
    log_warn "GitHub Wiki is not initialized. Please:"
    log_warn "  1. Open: https://github.com/$repo/wiki"
    log_warn "  2. Create the first Wiki page (content can be empty)"
    log_warn "  3. Return here and press Enter to continue"
    read -p "Press Enter when Wiki is initialized..."
    
    # Verify wiki was initialized
    if ! git ls-remote "https://github.com/$repo.wiki.git" &>/dev/null; then
        fail "Wiki repository still not accessible. Verify it was created."
    fi
    log_info "Wiki repository verified"
    
    # Trigger workflow
    log_info "Triggering initial wiki sync..."
    gh workflow run "$WORKFLOW_NAME" --ref main
    
    # Wait for workflow to complete
    log_info "Waiting for workflow to complete..."
    sleep 5
    
    local run_id=$(gh run list --workflow wiki-autogen.yml --limit 1 --json databaseId --query ".[0].databaseId" 2>/dev/null || echo "")
    
    if [[ -n "$run_id" ]]; then
        log_info "Workflow run ID: $run_id"
        log_info "Monitoring workflow..."
        
        local max_wait=300
        local elapsed=0
        local poll_interval=10
        
        while [[ $elapsed -lt $max_wait ]]; do
            local status=$(gh run view "$run_id" --json conclusion --query conclusion 2>/dev/null || echo "")
            
            if [[ "$status" == "success" ]]; then
                log_info "Workflow completed successfully!"
                break
            elif [[ "$status" == "failure" ]]; then
                log_error "Workflow failed. Check logs:"
                log_error "  https://github.com/$repo/actions/runs/$run_id"
                return 1
            elif [[ -z "$status" ]]; then
                echo -n "."
                sleep $poll_interval
                ((elapsed += poll_interval))
            fi
        done
    fi
    
    log_info "Wiki sync setup complete!"
    log_info "Wiki URL: https://github.com/$repo/wiki"
    log_info "Workflow file: $WORKFLOW_FILE"
    log_info "Workflow will auto-sync on commits to main that touch docs/, driver source, or config."
    
    return 0
}

################################################################################
# Template Generation
################################################################################

generate_workflow_file() {
    cat <<'EOF'
name: Sync Docs to GitHub Wiki

on:
  push:
    branches:
      - main
    paths:
      - 'docs/**'
      - 'src/**/*.py'
      - 'mkdocs.yml'
      - 'pyproject.toml'
  workflow_dispatch:

concurrency:
  group: wiki-sync-${{ github.ref }}
  cancel-in-progress: true

jobs:
  sync-wiki:
    runs-on: ubuntu-latest
    permissions:
      contents: write

    steps:
      - name: Checkout main repository
        uses: actions/checkout@v4
        with:
          token: ${{ secrets.GITHUB_TOKEN }}

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
          cache: 'pip'

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install mkdocs mkdocs-material "mkdocstrings[python]" pymdown-extensions

      - name: Validate documentation build
        run: mkdocs build

      - name: Checkout Wiki repository
        id: checkout_wiki
        uses: actions/checkout@v4
        with:
          repository: ${{ github.repository }}.wiki
          token: ${{ secrets.GITHUB_TOKEN }}
          path: wiki-repo
        continue-on-error: true

      - name: Fail if Wiki is not initialized
        if: steps.checkout_wiki.outcome == 'failure'
        run: |
          echo "GitHub Wiki repository not found for this repo."
          echo "Initialize Wiki once from the GitHub UI, then rerun this workflow."
          exit 1

      - name: Generate Wiki pages from docs markdown
        run: |
          python3 << 'PYTHON_EOF'
          import shutil
          import re
          from collections import Counter
          from pathlib import Path
          from pathlib import PurePosixPath

          docs_dir = Path("docs")
          wiki_dir = Path("wiki-repo")

          if not docs_dir.exists():
              raise SystemExit("docs/ directory not found")

          for item in wiki_dir.iterdir():
              if item.name == ".git":
                  continue
              if item.is_dir():
                  shutil.rmtree(item)
              else:
                  item.unlink()

          source_pages = sorted(docs_dir.rglob("*.md"))
          relative_pages = [src.relative_to(docs_dir).as_posix() for src in source_pages]

          candidate_names = {}
          for rel in relative_pages:
              rel_path = PurePosixPath(rel)
              if rel == "index.md":
                  candidate_names[rel] = "Home"
              else:
                  candidate_names[rel] = rel_path.stem

          collisions = {
              name
              for name, count in Counter(name.lower() for name in candidate_names.values()).items()
              if count > 1
          }

          page_name_by_rel = {}
          used_page_names = set()
          for rel in relative_pages:
              base_name = candidate_names[rel]
              if base_name.lower() in collisions:
                  page_name = PurePosixPath(rel).with_suffix("").as_posix().replace("/", "-")
              else:
                  page_name = base_name

              unique_name = page_name
              suffix = 2
              while unique_name.lower() in used_page_names:
                  unique_name = f"{page_name}-{suffix}"
                  suffix += 1

              used_page_names.add(unique_name.lower())
              page_name_by_rel[rel] = unique_name

          def normalize_rel_path(base_rel: str, link_rel: str) -> str:
              if link_rel.startswith("/"):
                  candidate = PurePosixPath(link_rel.lstrip("/"))
              else:
                  candidate = PurePosixPath(base_rel).parent / link_rel
              parts = []
              for part in candidate.parts:
                  if part in ("", "."):
                      continue
                  if part == "..":
                      if parts:
                          parts.pop()
                      continue
                  parts.append(part)
              return PurePosixPath(*parts).as_posix()

          def rewrite_links(markdown: str, base_rel: str) -> str:
              pattern = re.compile(r'\[(?P<label>[^\]]+)\]\((?P<target>[^)]+)\)')

              def _replace(match):
                  label = match.group("label")
                  target = match.group("target").strip()

                  if target.startswith(("http://", "https://", "mailto:", "#")):
                      return match.group(0)

                  path_part, sep, fragment = target.partition("#")
                  if not path_part.endswith(".md"):
                      return match.group(0)

                  normalized = normalize_rel_path(base_rel, path_part)
                  page_name = page_name_by_rel.get(normalized)
                  if not page_name:
                      page_name = PurePosixPath(path_part).stem

                  rewritten_target = f"{page_name}{sep}{fragment}" if sep else page_name
                  return f"[{label}]({rewritten_target})"

              return pattern.sub(_replace, markdown)

          copied_pages = []
          for src in source_pages:
              rel = src.relative_to(docs_dir)

              page_name = page_name_by_rel[rel.as_posix()]
              dst = wiki_dir / f"{page_name}.md"

              dst.parent.mkdir(parents=True, exist_ok=True)
              content = src.read_text(encoding="utf-8")
              content = rewrite_links(content, rel.as_posix())
              banner = "_Auto-generated from `docs/` in the main repository. Edit source files, not the Wiki directly._\n\n"
              dst.write_text(banner + content, encoding="utf-8")
              copied_pages.append(dst.relative_to(wiki_dir))

          sidebar_lines = ["# Documentation", "", "- [[Home]]"]
          for page in sorted(copied_pages):
              if str(page) == "Home.md":
                  continue
              page_name = str(page.with_suffix(""))
              sidebar_lines.append(f"- [[{page_name}|{page_name}]]")

          (wiki_dir / "_Sidebar.md").write_text("\n".join(sidebar_lines) + "\n", encoding="utf-8")

          footer = (
              "This Wiki is synchronized by GitHub Actions from the repository docs. "
              "Create pull requests against `docs/` to update content."
          )
          (wiki_dir / "_Footer.md").write_text(footer + "\n", encoding="utf-8")
          PYTHON_EOF

      - name: Commit and push to Wiki
        run: |
          cd wiki-repo
          git config user.name "github-actions[bot]"
          git config user.email "github-actions[bot]@users.noreply.github.com"

          if git status --porcelain | grep . >/dev/null; then
            git add .
            git commit -m "docs(wiki): sync from docs/ [skip ci]"
            git push origin HEAD:master
          else
            echo "No changes to commit"
          fi
EOF
}

generate_pr_body() {
    cat <<'EOF'
## Summary
- Add GitHub Actions workflow to sync `docs/` markdown into GitHub Wiki
- Validate docs with `mkdocs build` before wiki sync
- Handle GitHub Wiki URL limitations: flatten nested paths, rewrite links, detect/resolve case collisions
- Map `docs/index.md` to `Home.md` and generate `_Sidebar.md`/`_Footer.md`

## Files
- `.github/workflows/wiki-autogen.yml` — Production workflow

## Rollout Checklist
- [ ] Initialize Wiki once in GitHub UI (create first Wiki page)
- [ ] Merge this PR to `main`
- [ ] Verify `Sync Docs to GitHub Wiki` workflow triggers and succeeds
- [ ] Check Wiki pages (`Home`, sidebar, content) populated correctly

## Notes
- Wiki content is generated from `docs/`; contributors should edit `docs/` in PRs, not the Wiki directly.
- Workflow validates `mkdocs build` before syncing to ensure docs are always valid.
- Auto-commits to Wiki only when content changed (includes `[skip ci]` to prevent loops).
EOF
}

################################################################################
# Main
################################################################################

main "$@"
