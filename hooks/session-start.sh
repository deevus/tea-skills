#!/usr/bin/env bash
# SessionStart hook for tea-skills plugin
# Detects tea login status and worktree context

set -euo pipefail

context_parts=()

# Check if tea CLI is available
if ! command -v tea &>/dev/null; then
    context_parts+=("tea CLI is not installed. Install it before using tea skills.")
fi

# Check if tea has any logins configured
if command -v tea &>/dev/null; then
    login_count=$(tea login list -o csv 2>/dev/null | tail -n +2 | wc -l)
    if [ "$login_count" -eq 0 ]; then
        context_parts+=("No tea logins configured. Run: tea login add")
    fi
fi

# Detect git worktree context
if git rev-parse --is-inside-work-tree &>/dev/null; then
    git_common_dir=$(git rev-parse --git-common-dir 2>/dev/null)
    git_dir=$(git rev-parse --git-dir 2>/dev/null)

    # In a worktree, --git-dir points to worktrees/<name> inside --git-common-dir
    if [ "$git_dir" != "$git_common_dir" ]; then
        # We're in a worktree — tea won't auto-detect the login
        remote_url=$(git remote get-url origin 2>/dev/null || echo "")
        login_name=""

        if [ -n "$remote_url" ]; then
            # Extract hostname from remote URL (ssh:// or git@ or https://)
            login_name=$(echo "$remote_url" | sed -E 's|^(ssh\|https?)://([^@]*@)?||; s|^[^@]*@||; s|[:/].*||')
        fi

        if [ -n "$login_name" ]; then
            context_parts+=("WORKTREE DETECTED: tea CLI does not auto-detect logins in git worktrees. Append --login $login_name to all tea commands in this session.")
        else
            context_parts+=("WORKTREE DETECTED: tea CLI does not auto-detect logins in git worktrees. Append --login <server> to all tea commands. Run tea login list to find the server name.")
        fi
    fi
fi

# Build output
if [ ${#context_parts[@]} -eq 0 ]; then
    # Everything is fine — minimal output
    context="tea CLI is configured and ready."
else
    context=$(printf '%s\n' "${context_parts[@]}")
fi

# Escape for JSON
escape_for_json() {
    local input="$1"
    local output=""
    local i char
    for (( i=0; i<${#input}; i++ )); do
        char="${input:$i:1}"
        case "$char" in
            $'\\') output+='\\' ;;
            '"') output+='\"' ;;
            $'\n') output+='\n' ;;
            $'\r') output+='\r' ;;
            $'\t') output+='\t' ;;
            *) output+="$char" ;;
        esac
    done
    printf '%s' "$output"
}

escaped_context=$(escape_for_json "$context")

cat <<EOF
{
  "hookSpecificOutput": {
    "hookEventName": "SessionStart",
    "additionalContext": "$escaped_context"
  }
}
EOF

exit 0
