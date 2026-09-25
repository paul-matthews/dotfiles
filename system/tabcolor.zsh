# iTerm2 tab colours: one engine for every machine.
#
# Which preset a tab gets:
#   1. TABCOLOR_PRESET, if a repo's .envrc exported one (direnv), else
#   2. the first row of system/tabcolor-presets.sh whose glob matches $PWD
# The precmd hook applies it on every prompt change; the AI wrappers in
# system/ai-tabs.zsh ask the same function. Per-tab rotation picks one of the
# preset's 8 palette entries by shell PID, so several tabs on one project differ.
#
# Tab title and badge read "<emoji> <SHORT>" plus " / <terminal role>" when
# `role <name>` has been set (iterm/role.zsh).
#
# Manual: tabcolor <preset> | tabcolor danger | tabcolor reset | tabcolor-preview <preset>

# --- escape-code helpers (no-ops outside iTerm2) -----------------------------
_tabcolor_in_iterm() { [[ "$TERM_PROGRAM" == "iTerm.app" || -n "$ITERM_SESSION_ID" ]]; }

set_tab_color() {
  _tabcolor_in_iterm || return 0
  echo -ne "\033]6;1;bg;red;brightness;$1\a"
  echo -ne "\033]6;1;bg;green;brightness;$2\a"
  echo -ne "\033]6;1;bg;blue;brightness;$3\a"
}

reset_tab_color() {
  _tabcolor_in_iterm || return 0
  echo -ne "\033]6;1;bg;*;default\a"
}

# Works in iTerm2, Ghostty and most terminals
set_tab_title() {
  printf '\033]0;%s\007' "$1"
}

set_badge() {
  _tabcolor_in_iterm || return 0
  printf "\e]1337;SetBadgeFormat=%s\a" "$(echo -n "$1" | base64)"
}

clear_badge() {
  _tabcolor_in_iterm || return 0
  printf "\e]1337;SetBadgeFormat=%s\a" "$(echo -n "" | base64)"
}

# --- preset data ------------------------------------------------------------
source "${0:h}/tabcolor-presets.sh"

# _tabcolor_preset_for <dir>: the preset for a directory, or nothing (exit 1).
_tabcolor_preset_for() {
  if [[ -n "${TABCOLOR_PRESET:-}" ]]; then
    print -r -- "$TABCOLOR_PRESET"
    return 0
  fi
  local dir="${1:l}" row preset tag globs g
  local -a tags=(${=DOTFILES_TAGS})
  while IFS= read -r row; do
    [[ -z "$row" ]] && continue
    preset="${row%%|*}"
    tag="$(print -r -- "$row" | cut -d'|' -f5)"
    if [[ -n "$tag" ]] && (( ! ${tags[(Ie)$tag]} )); then
      continue
    fi
    globs="$(print -r -- "$row" | cut -d'|' -f6)"
    for g in ${=globs}; do
      if [[ "$dir" == ${~g} ]]; then
        print -r -- "$preset"
        return 0
      fi
    done
  done <<< "$_TABCOLOR_PRESET_TABLE"
  return 1
}

# _tabcolor_label <preset>: "<emoji> <SHORT>" (+ " / <role>"); the directory name when no preset
_tabcolor_label() {
  local label
  if [[ -n "$1" ]]; then
    label="$(_tabcolor_field "$1" 3) $(_tabcolor_field "$1" 2)"
  else
    label="$(basename "$PWD")"
  fi
  [[ -n "${TERMINAL_ROLE:-}" ]] && label="$label / $TERMINAL_ROLE"
  print -r -- "$label"
}

# _tabcolor_rgb <preset> [darken]: this tab's palette entry, optionally darkened 75% (floor 40)
_tabcolor_rgb() {
  local -a lines
  local line
  while IFS= read -r line; do lines+=("$line"); done < <(_tabcolor_get_palette "$1")
  (( ${#lines[@]} )) || return 1
  local idx=$(( $$ % ${#lines[@]} + 1 ))
  local -a rgb=(${=lines[$idx]})
  if [[ "${2:-}" == darken ]]; then
    local c i
    for i in 1 2 3; do
      c=$(( rgb[$i] * 3 / 4 )); (( c < 40 )) && c=40
      rgb[$i]=$c
    done
  fi
  print -r -- "${rgb[1]} ${rgb[2]} ${rgb[3]}"
}

# _tabcolor_apply <preset|empty>: colour, title and badge for the current tab
_tabcolor_apply() {
  local preset="$1" label rgb
  label="$(_tabcolor_label "$preset")"
  if [[ -n "$preset" ]] && rgb="$(_tabcolor_rgb "$preset")"; then
    set_tab_color ${=rgb}
    set_badge "$label"
  else
    reset_tab_color
    if [[ -n "${TERMINAL_ROLE:-}" ]]; then set_badge "$TERMINAL_ROLE"; else clear_badge; fi
  fi
  set_tab_title "$label"
}

# --- commands ---------------------------------------------------------------
tabcolor() {
  case "${1:-}" in
    danger)   set_tab_color 255 50 50; set_tab_title "⚠ PRODUCTION"; set_badge "PROD" ;;
    reset|"") _TABCOLOR_LAST=""; _tabcolor_apply "" ;;
    *)
      if [[ -n "$(_tabcolor_row "$1")" ]]; then
        _TABCOLOR_LAST="$1"
        _tabcolor_apply "$1"
      else
        echo "Unknown preset: $1. Available: $(_tabcolor_presets | tr '\n' ' ')danger reset"
        return 1
      fi ;;
  esac
}

# Preview a preset's palette: work tab vs darkened AI tab
tabcolor-preview() {
  local preset="${1:-}"
  if [[ -z "$preset" || -z "$(_tabcolor_row "$preset")" ]]; then
    echo "Usage: tabcolor-preview <preset>"
    echo "Presets: $(_tabcolor_presets | tr '\n' ' ')"
    return 1
  fi
  echo ""
  echo "  $(_tabcolor_field "$preset" 3) $(_tabcolor_field "$preset" 2) ($(_tabcolor_field "$preset" 4)) — work tab vs 🤖 AI tab"
  echo "  ─────────────────────────────────────────"
  echo ""
  local line
  while IFS= read -r line; do
    local -a rgb=(${=line})
    local r=${rgb[1]} g=${rgb[2]} b=${rgb[3]}
    local dr=$(( r * 3 / 4 )); (( dr < 40 )) && dr=40
    local dg=$(( g * 3 / 4 )); (( dg < 40 )) && dg=40
    local db=$(( b * 3 / 4 )); (( db < 40 )) && db=40
    printf "  \033[48;2;%d;%d;%dm    \033[0m %3d %3d %3d  work" "$r" "$g" "$b" "$r" "$g" "$b"
    printf "     \033[48;2;%d;%d;%dm    \033[0m %3d %3d %3d  ai\n" "$dr" "$dg" "$db" "$dr" "$dg" "$db"
  done < <(_tabcolor_get_palette "$preset")
  echo ""
}

# --- precmd hook ------------------------------------------------------------
# Applies the preset when it changes, and re-applies the title on every prompt
# because other hooks (oh-my-zsh termsupport) overwrite it. Set
# _TABCOLOR_LAST="" to force a full re-apply (role.zsh, ssh.zsh, ai-tabs.zsh do).
_TABCOLOR_LAST=""

_tabcolor_hook() {
  local want
  want="$(_tabcolor_preset_for "$PWD")" || want=""
  if [[ "$want" != "$_TABCOLOR_LAST" ]]; then
    _tabcolor_apply "$want"
    _TABCOLOR_LAST="$want"
  else
    set_tab_title "$(_tabcolor_label "$want")"
  fi
}

autoload -Uz add-zsh-hook
add-zsh-hook precmd _tabcolor_hook
