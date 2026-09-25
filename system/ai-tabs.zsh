# AI-tool tabs: wrap a CLI so its tab takes the project's colour, darkened,
# with a "🤖" title and a badge naming the tool, then restores the project tab
# when the tool exits. The wrapper never parses arguments; "$@" passes through.
#
# Shared: claude, agy. Work machines add jc and jetski in system/ai-tabs.work.zsh.
# Add another tool by appending name:BADGE to _AI_TAB_CMDS.

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

# Commands to wrap, as name:BADGE. Work machines append to this in ai-tabs.work.zsh.
# _ai_tabs_finalize (called at the end of zshrc) defines a wrapper function for
# each name, converting an alias of that name if ~/.localrc defined one.
#   claude  Claude Code
#   agy     Antigravity CLI (the public one, installed to ~/.local/bin)
typeset -ga _AI_TAB_CMDS
_AI_TAB_CMDS=(claude:CLAUDE agy:ANTIGRAVITY)

# Some tools are aliases (jc on work machines, defined in ~/.localrc, which
# loads after the topic files). An alias wins over a function of the same
# name, so zshrc calls _ai_tabs_finalize last: it turns each wrapped alias
# into a function that runs the alias's expansion inside the wrapper.
_ai_tab_run() {
  local expansion="$1" badge="$2"
  shift 2
  _ai_tab_wrap_expansion "$expansion" "$badge" "$@"
}

_ai_tab_wrap_expansion() {
  local expansion="$1" badge="$2"
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

  eval "$expansion" '"$@"'
  local rc=$?

  _TABCOLOR_LAST=""
  _tabcolor_hook
  return $rc
}

_ai_tabs_finalize() {
  local entry name badge expansion
  for entry in "${_AI_TAB_CMDS[@]}"; do
    name="${entry%%:*}"; badge="${entry##*:}"
    if (( ${+aliases[$name]} )); then
      expansion="${aliases[$name]}"
      unalias "$name"
      eval "$name() { _ai_tab_run ${(q)expansion} ${(q)badge} \"\$@\"; }"
    elif ! (( ${+functions[$name]} )); then
      eval "$name() { _ai_tab_wrap ${(q)name} ${(q)badge} \"\$@\"; }"
    fi
  done
}

