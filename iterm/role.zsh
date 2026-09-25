# Terminal role: name what a tab is for within a project (git, device, build).
# The tab colour engine appends it to the title and badge, so a tab reads
# "🪐 COS / device". Colour is untouched.
#
#   role <name>   set this tab's role
#   role          clear it (back to the project alone)
#   role -s       show the current role

role() {
  case "${1:-}" in
    "")
      unset TERMINAL_ROLE
      echo "Role cleared." ;;
    -s|status|show)
      if [[ -n "${TERMINAL_ROLE:-}" ]]; then echo "Current role: $TERMINAL_ROLE"; else echo "No role set."; fi
      return 0 ;;
    *)
      export TERMINAL_ROLE="$1"
      echo "Role set to: $1" ;;
  esac
  # Re-apply title and badge now rather than at the next prompt
  _TABCOLOR_LAST=""
  (( $+functions[_tabcolor_hook] )) && _tabcolor_hook
}

# Quick aliases for common roles
alias rgit="role git"
alias rbuild="role build"
alias rdevice="role device"
alias rclear="role"
