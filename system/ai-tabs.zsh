# AI-tool tabs: wrap a CLI so its tab takes the project's colour, darkened,
# with a "🤖" title while preserving the project and role badge, then restores
# the project tab when the tool exits. The wrapper never parses arguments;
# "$@" passes through.
#
# Shared: claude, agy. Work machines add jc and jetski in system/ai-tabs.work.zsh.
#
# DOTFILES_AI_TOOL names this machine's AI tool: the command `wb` types into a
# workbench's AI tab. claude here, jetski on work machines (ai-tabs.work.zsh);
# the secrets file may override it.
# Add another tool by appending name:BADGE to _AI_TAB_CMDS.

# _ai_tab_style: the project's colour darkened, "🤖" title, project badge
_ai_tab_style() {
  local preset="" rgb
  _tabcolor_resolve "$PWD" && preset="$REPLY"
  if [[ -n "$preset" ]] && _tabcolor_rgb "$preset" darken; then
    rgb="$REPLY"
  else
    rgb="$(( (100 + $$ % 16) * 3 / 4 )) $(( (120 + $$ % 16) * 3 / 4 )) $(( (170 + $$ % 16) * 3 / 4 ))"
  fi
  _tabcolor_label "$preset"
  set_tab_color ${=rgb}
  set_tab_title "🤖 $REPLY"
  set_badge "$REPLY"
}

_ai_tab_wrap() {
  local name="$1" badge="$2"
  shift 2
  _ai_tab_style

  command "$name" "$@"
  local rc=$?

  _TABCOLOR_LAST=""
  _tabcolor_hook
  return $rc
}

# Commands to wrap, as name:BADGE. Work machines append to this in ai-tabs.work.zsh.
# _ai_tabs_finalize (called at the end of zshrc) defines a wrapper function for
# each name that is installed here, converting an alias of that name if
# ~/.localrc or ~/.localrc.secrets defined one. A name that is neither is left
# undefined.
#   claude  Claude Code
#   agy     Antigravity CLI (the public one, installed to ~/.local/bin)
typeset -gaU _AI_TAB_CMDS
_AI_TAB_CMDS+=(claude:CLAUDE agy:ANTIGRAVITY)
DOTFILES_AI_TOOL=claude

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
  _ai_tab_style

  eval "$expansion" '"$@"'
  local rc=$?

  _TABCOLOR_LAST=""
  _tabcolor_hook
  return $rc
}

# Run finalize once more at the first prompt: that is after zshrc, ~/.localrc,
# ~/.zlogin and anything else that may define one of these names as an alias.
_ai_tabs_finalize_once() {
  _ai_tabs_finalize
  add-zsh-hook -d precmd _ai_tabs_finalize_once
}
autoload -Uz add-zsh-hook
add-zsh-hook precmd _ai_tabs_finalize_once

_ai_tabs_finalize() {
  local entry name badge expansion
  for entry in "${_AI_TAB_CMDS[@]}"; do
    name="${entry%%:*}"; badge="${entry##*:}"
    if (( ${+aliases[$name]} )); then
      expansion="${aliases[$name]}"
      unalias "$name"
      eval "$name() { _ai_tab_run ${(q)expansion} ${(q)badge} \"\$@\"; }"
    elif ! (( ${+functions[$name]} )) && (( ${+commands[$name]} )); then
      eval "$name() { _ai_tab_wrap ${(q)name} ${(q)badge} \"\$@\"; }"
    fi
    # A registered name that is neither an alias nor on PATH gets no wrapper,
    # so `whence -w` tells the truth about a tool that is not installed here.
    # A tool installed mid-session is wrapped at the next shell.
  done
}

