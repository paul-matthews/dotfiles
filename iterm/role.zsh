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
    printf "\e]0;%s\a" "$(basename "$PWD")"
    echo "Role cleared."
    return 0
  fi

  export TERMINAL_ROLE="$1"
  local role_upper="${(U)1}"

  # Set watermark badge in current pane (large visible text in top-right corner)
  printf "\e]1337;SetBadgeFormat=%s\a" "$(echo -n "$role_upper" | base64)"

  # Set window & tab title
  printf "\e]0;[%s] %s\a" "$1" "$(basename "$PWD")"
  echo "Role set to: $1"
}

# Quick aliases for common developer roles
alias rbuild="role build"
alias rgit="role git"
alias rjetski="role jetski"
alias rclear="role clear"
