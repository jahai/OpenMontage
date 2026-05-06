#!/usr/bin/env bash
# WARNING: the next comment line is load-bearing.
#   serve.py uses it as HOOK_MARKER to recognize a hook as Latent Systems'.
#   Future template revisions MUST preserve the following line verbatim:
# Pre-commit hook installed by latent_systems tool_build v1
# Purpose: enforce AD-5 (canonical paths read-only to non-Joseph commits)
# Scope: projects/latent_systems/{shared,ep1,docs,tools}/ only
# Installed by: tool_build/serve.py --init
# Reference: projects/latent_systems/tool_build/v1_spec_proposal.md AD-5 v0.5 carve-out
#            projects/latent_systems/tool_build/phase1_design_notes.md Sections 4 + 6

set -e

REPO_ROOT="$(git rev-parse --show-toplevel)"
HOOK_DIR="$REPO_ROOT/.git/hooks"
LS_MARKER="# Pre-commit hook installed by latent_systems tool_build v1"

# Step 1: chain to most recent FOREIGN backup hook (preserves any
# existing OpenMontage discipline like lint/format/tests). Latent
# Systems backups are skipped — chaining to one would recurse, since
# its own chain logic would pick the same backup again.
BACKUP_HOOK=""
while IFS= read -r f; do
    [ -z "$f" ] && continue
    [ -x "$f" ] || continue
    if ! grep -q "$LS_MARKER" "$f" 2>/dev/null; then
        BACKUP_HOOK="$f"
        break
    fi
done < <(ls -t "$HOOK_DIR"/pre-commit.backup_* 2>/dev/null)

if [ -n "$BACKUP_HOOK" ]; then
    "$BACKUP_HOOK" || exit $?
fi

# Step 2: AD-5 enforcement
JOSEPH_NAME="@jahai"
JOSEPH_EMAIL="joseph.brightly@gmail.com"
CURRENT_NAME="$(git config user.name)"
CURRENT_EMAIL="$(git config user.email)"

CANONICAL_PATTERNS='^projects/latent_systems/(shared|ep1|docs|tools)/'

CHANGED=$(git diff --cached --name-only | grep -E "$CANONICAL_PATTERNS" || true)

if [ -n "$CHANGED" ]; then
    # Defensive guard: if no identity is configured at all, fail loud
    # rather than fall through to the OR check (which could match a
    # blank JOSEPH_NAME if the template were ever edited badly).
    if [ -z "$CURRENT_NAME" ] && [ -z "$CURRENT_EMAIL" ]; then
        echo "ERROR: git identity not configured." >&2
        echo "Set user.name and user.email before committing to canonical paths." >&2
        echo "Affected paths:" >&2
        echo "$CHANGED" | sed 's/^/  /' >&2
        exit 1
    fi
    if [ "$CURRENT_NAME" = "$JOSEPH_NAME" ] || [ "$CURRENT_EMAIL" = "$JOSEPH_EMAIL" ]; then
        # Joseph's commit — allow
        exit 0
    else
        echo "ERROR: AD-5 violation detected." >&2
        echo "Build process must not modify Latent Systems canonical paths." >&2
        echo "Current commit author: $CURRENT_NAME <$CURRENT_EMAIL>" >&2
        echo "Affected paths:" >&2
        echo "$CHANGED" | sed 's/^/  /' >&2
        echo "" >&2
        echo "Move changes to projects/latent_systems/tool_build/, OR" >&2
        echo "have Joseph commit canonical changes separately." >&2
        echo "" >&2
        echo "Override (only if you understand the risk): git commit --no-verify" >&2
        exit 1
    fi
fi

exit 0
