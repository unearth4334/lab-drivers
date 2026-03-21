# GitHub Actions Wiki Sync Setup Script

A reusable bash script to automate the setup of GitHub Actions workflows that synchronize Markdown documentation from a repository's `docs/` directory into GitHub Wiki.

## Quick Start

```bash
./scripts/setup-wiki-sync.sh owner/repo-name
```

## Requirements

- `bash` 4.0+
- `gh` CLI (installed and authenticated with `gh auth login`)
- `git` command available
- Repository with `mkdocs.yml` and `docs/` directory
- One-time manual GitHub Wiki initialization (see below)

## How It Works

### Automatic Steps

1. **Validates prerequisites**: Checks `gh` auth, repo accessibility, MkDocs setup
2. **Creates feature branch**: `explore/wiki-autogen` with workflow file
3. **Generates workflow file**: `.github/workflows/wiki-autogen.yml`
4. **Creates pull request**: Via `gh pr create --web` (opens in browser)
5. **Merges PR**: Automatically merges and deletes feature branch
6. **Verifies workflow**: Checks workflow is registered in GitHub Actions
7. **Prompts for Wiki initialization**: Pauses for manual one-time setup
8. **Triggers initial sync**: Runs workflow and monitors completion

### Manual One-Time Step

When prompted by the script:

1. Open: `https://github.com/owner/repo/wiki`
2. Create the first Wiki page (can be empty content)
3. Return to terminal and press **Enter**

This creates the `<repo>.wiki.git` repository that the workflow uses.

## Workflow Features

### Link Rewriting

The workflow intelligently handles GitHub Wiki URL limitations:

- **Flattens nested paths**: `docs/api/visa/dl3021.md` → Wiki link `(dl3021)` instead of `(api/visa/dl3021)`
- **Resolves relative paths**: Handles `../`, `./`, and absolute references correctly
- **Rewrites internal links**: Converts `.md` paths to wiki-safe page targets

### Collision Detection

Detects and resolves case-insensitive page-name collisions:

- Example: `architecture.md` and `ARCHITECTURE.md` in the same hierarchy
- Resolution: Generates unique names like `ARCHITECTURE-2` to prevent URL conflicts

### Navigation Generation

Auto-generates sidebar and footer:

- **_Sidebar.md**: Hierarchical navigation from folder structure
- **_Footer.md**: Links back to main repository
- **Root Home.md**: Maps from `docs/index.md`

### Validation & Safety

- Validates `mkdocs build` before syncing to Wiki
- Only commits to Wiki if content actually changed
- Includes `[skip ci]` in commit messages to prevent action loops
- Fails early if Wiki repository is not initialized

## Workflow Trigger

The workflow automatically syncs on:

- Push to `main` branch that touches:
  - `docs/**` (any documentation files)
  - `src/**/*.py` (driver source, or adjust path as needed)
  - `mkdocs.yml` (configuration changes)
  - `pyproject.toml` (dependency changes)
- Manual trigger via `gh workflow run` or GitHub UI

## Customization

To customize for your project, edit the workflow file after initial setup:

```yaml
on:
  push:
    branches:
      - main
    paths:
      - 'docs/**'
      - 'YOUR_SOURCE_PATH/**/*.py'  # <- Adjust source path
      - 'mkdocs.yml'
      - 'YOUR_CONFIG_FILE'  # <- Add additional config files
```

## Troubleshooting

### "Wiki repository not accessible"

- Manual Wiki initialization did not complete successfully
- Open `https://github.com/owner/repo/wiki` and create the first page
- Re-run: `gh workflow run "Sync Docs to GitHub Wiki" --ref main`

### "mkdocs.yml not found"

- Initialize MkDocs: `mkdocs new .`
- Or ensure your docs infrastructure is set up first

### Links still broken in Wiki

- Check that internal .md links use relative paths (e.g., `[link](../getting-started.md)`)
- Verify collision resolution: run script sample or manually inspect `_Sidebar.md`

### Workflow repeatedly triggering

- Ensure workflow includes `[skip ci]` in commit message (already configured)
- Check `paths:` triggers aren't too broad

## File Locations

- **Script**: `scripts/setup-wiki-sync.sh`
- **Generated workflow**: `.github/workflows/wiki-autogen.yml`
- **Documentation**: `docs/` (your existing markdown files)

## Example Usage

```bash
# For a new project
cd my-project
git init
mkdocs new .
# ... populate docs/ with content ...
git add -A && git commit -m "initial: setup project with docs"
git remote add origin https://github.com/myuser/my-project.git
git push -u origin main

# Then set up Wiki sync
./scripts/setup-wiki-sync.sh myuser/my-project
```

## What Gets Created

After successful setup:

1. **`.github/workflows/wiki-autogen.yml`** — Production workflow (425 lines)
2. **GitHub Wiki** — Synced content from `docs/` via workflow
3. **PR #1** (merged) — Documents the workflow addition for auditing

## Monitoring Workflow Runs

After setup, monitor future syncs:

```bash
# List recent runs
gh run list --workflow wiki-autogen.yml --limit 10

# View specific run
gh run view <RUN_ID> --log

# Trigger manual sync
gh workflow run "Sync Docs to GitHub Wiki" --ref main
```

## Contributing to Synced Documentation

After workflow setup:

1. **Edit docs locally**: Modify files in `docs/`
2. **Commit and push**: Workflow triggers automatically
3. **Check Wiki**: Content syncs within 30 seconds

**Do NOT edit GitHub Wiki directly** — changes will be overwritten on next sync.
