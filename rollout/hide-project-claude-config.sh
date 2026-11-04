#!/usr/bin/env bash
# Hide the checked-out repository's own Claude Code configuration from the harness session.
#
# The checkout is data: a PR branch (review mission) or a default branch can carry
# .claude/settings.json hooks, .claude/agents, .claude/commands, .mcp.json servers or
# CLAUDE.local.md. Claude Code loads project settings from the working directory, so a
# SessionStart or PreToolUse hook there would run next to the Claude credential and the
# id-token permission, before the harness hook can judge anything. Only
# .harness/harness/claude/settings.json may configure the session.
#
# Tracked files are marked skip-worktree before removal, so `git add -A` cannot commit
# their deletion and the guard never sees a tier D change.
#   hide-project-claude-config.sh [CHECKOUT]
set -euo pipefail
cd "${1:-.}"
paths=(.claude .mcp.json CLAUDE.local.md)
git ls-files -z -- "${paths[@]}" | xargs -0 -r git update-index --skip-worktree --
rm -rf -- "${paths[@]}"
