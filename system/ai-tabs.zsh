# AI-tool tabs: wrap a CLI so its tab takes the project's colour, darkened,
# with a "🤖" title and a badge naming the tool, then restores the project tab
# when the tool exits. The wrapper never parses arguments; "$@" passes through.
#
# Shared: claude. Work machines add jc in system/ai-tabs.work.zsh.
# Add another tool with:  _ai_tab_wrap <command> <BADGE> "$@"

_ai_tab_wrap() {
  local name="$1" badge="$2"
  shift 2
  local preset rgb label
  preset="$(_tabcolor_preset_for "$PWD")" || preset=""
  if [[ -n "$preset" ]] && rgb="$(_tabcolor_rgb "$preset" darken)"; then
    label="$(_tabcolor_field "$preset" 3) $(_tabcolor_field "$preset" 2)"
  else
    rgb="$(( (100 + $$ % 16) * 3 / 4 )) $(( (120 + $$ % 16) * 3 / 4 )) $(( (170 + $$ % 16) * 3 / 4 ))"
    label="$(basename "$PWD")"
  fi
  [[ -n "${TERMINAL_ROLE:-}" ]] && label="$label / $TERMINAL_ROLE"
  set_tab_color ${=rgb}
  set_tab_title "🤖 $label"
  set_badge "$badge"

  command "$name" "$@"
  local rc=$?

  _TABCOLOR_LAST=""
  _tabcolor_hook
  return $rc
}

claude() { _ai_tab_wrap claude CLAUDE "$@"; }
