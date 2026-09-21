# Role designation for iTerm2 tabs/windows
# Usage:
#   role <name>    - Designates the current tab to a role (e.g. role build, role git, role feat-x)
#   role clear     - Clears the role designation and restores project default
#   role           - Displays current role

role() {
  if [[ -z "$1" ]]; then
    if [[ -n "$TERMINAL_ROLE" ]]; then
      echo "Current role: $TERMINAL_ROLE"
    else
      echo "No role currently set."
    fi
    echo "Usage: role <name> | role clear"
    return 0
  fi

  if [[ "$1" == "clear" || "$1" == "reset" ]]; then
    unset TERMINAL_ROLE
    # Clear custom watermark badge (reverts to iTerm profile default badge, e.g. WORK, GANDALF)
    printf "\e]1337;SetBadgeFormat=\a"
    # Reset tab title to current directory
    local dir_name="$(basename "$PWD")"
    print -Pn "\e]1;${dir_name}\a\e]2;${dir_name}\a\e]0;${dir_name}\a"
    echo "Role cleared."
    return 0
  fi

  export TERMINAL_ROLE="$1"
  local role_upper="${(U)1}"

  # Set watermark badge in current pane (large visible text in top-right corner)
  printf "\e]1337;SetBadgeFormat=%s\a" "$(echo -n "$role_upper" | base64)"

  # Set window & tab title immediately
  local dir_name="$(basename "$PWD")"
  print -Pn "\e]1;[${TERMINAL_ROLE}] ${dir_name}\a\e]2;[${TERMINAL_ROLE}] ${dir_name}\a\e]0;[${TERMINAL_ROLE}] ${dir_name}\a"
  echo "Role set to: $1"
}

# Keep tab and window title updated on every prompt when a role is active
# (runs after oh-my-zsh termsupport so the role title persists across commands)
_role_title_precmd() {
  if [[ -n "$TERMINAL_ROLE" ]]; then
    local dir_name="$(basename "$PWD")"
    print -Pn "\e]1;[${TERMINAL_ROLE}] ${dir_name}\a\e]2;[${TERMINAL_ROLE}] ${dir_name}\a\e]0;[${TERMINAL_ROLE}] ${dir_name}\a"
  fi
}

# Update tab title with the active command while running
_role_title_preexec() {
  if [[ -n "$TERMINAL_ROLE" ]]; then
    local cmd="${1:-}"
    print -Pn "\e]1;[${TERMINAL_ROLE}] ${cmd:q}\a\e]2;[${TERMINAL_ROLE}] ${cmd:q}\a"
  fi
}

autoload -Uz add-zsh-hook
add-zsh-hook precmd _role_title_precmd
add-zsh-hook preexec _role_title_preexec

# Quick aliases for common developer roles
alias rbuild="role build"
alias rgit="role git"
alias rjetski="role jetski"
alias rclear="role clear"

