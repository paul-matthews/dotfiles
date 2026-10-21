# iTerm2 tab colours: one engine for every machine.
#
# Which preset a tab gets:
#   1. TABCOLOR_PRESET, if a repo's .envrc exported one (direnv), else
#   2. the first project in system/projects.yaml (then the private projects
#      file) whose glob matches $PWD; a git worktree under ~/src/.worktrees
#      matches as its main checkout
# The precmd hook applies it when it changes; the AI wrappers in
# system/ai-tabs.zsh ask the same function. Per-tab rotation picks one of the
# preset's 8 palette entries by shell PID, so several tabs on one project differ.
#
# Tab title and badge read "<emoji> <SHORT>" plus " / <terminal role>" when
# `role <name>` has been set (iterm/role.zsh). In iTerm the tab also publishes
# user variables wbGroup ("<emoji> <name>[ · <worktree>]") and wbColor (the
# palette's average) for `wb` (iterm/wb.darwin.zsh) to group tabs by.
#
# Project data comes from a generated zsh cache (bin/projects-gen), never from
# YAML at runtime. Functions here return through REPLY rather than stdout so
# the per-prompt path never forks.
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
  printf "\e]1337;SetBadgeFormat=%s\a" ""
}

# _tabcolor_uservars <group> <rgb>: publish wbGroup/wbColor to iTerm, only when
# they change (base64 forks, so never on an unchanged prompt). Empty clears.
_TABCOLOR_UV=""
_tabcolor_uservars() {
  _tabcolor_in_iterm || return 0
  [[ "$1|$2" == "$_TABCOLOR_UV" ]] && return 0
  _TABCOLOR_UV="$1|$2"
  printf "\e]1337;SetUserVar=wbGroup=%s\a" "$(print -rn -- "$1" | base64)"
  printf "\e]1337;SetUserVar=wbColor=%s\a" "$(print -rn -- "$2" | base64)"
}

# --- project data -----------------------------------------------------------
# The cache (~/.cache/dotfiles/projects.zsh) is rebuilt by bin/projects-gen when
# the public or private YAML is newer; the `-nt` tests are builtins, so a shell
# start with a fresh cache costs one `source`. With no cache and no uv (a fresh
# Pi) the committed system/projects.gen is used: public projects only.
_TC_DOTFILES="${ZSH:-${${(%):-%x}:A:h:h}}"

_tabcolor_load_projects() {
  local src="$_TC_DOTFILES/system/projects.yaml"
  local priv="$HOME/.config/dotfiles/projects.private.yaml"
  local cache="${XDG_CACHE_HOME:-$HOME/.cache}/dotfiles/projects.zsh"
  # A failed rebuild (bad YAML, or uv cannot fetch PyYAML) leaves a stamp and
  # is not retried until a YAML changes again; shell start stays silent and
  # `wb doctor` reports it.
  local stamp="$cache.failed"
  if [[ ! -r "$cache" || "$src" -nt "$cache" || ( -r "$priv" && "$priv" -nt "$cache" ) ]]; then
    if (( $+commands[uv] )) && [[ ! -e "$stamp" || "$src" -nt "$stamp" || ( -r "$priv" && "$priv" -nt "$stamp" ) ]]; then
      if "$_TC_DOTFILES/bin/projects-gen" --out "$cache" >/dev/null 2>&1; then
        [[ -e "$stamp" ]] && command rm -f -- "$stamp"
      else
        [[ -d "${cache:h}" ]] || command mkdir -p -- "${cache:h}"
        : >| "$stamp"
      fi
    fi
    [[ -r "$cache" ]] || cache="$_TC_DOTFILES/system/projects.gen"
  fi
  source "$cache"
}
_tabcolor_load_projects

# _tabcolor_resolve <dir>: REPLY = preset for a directory ("" and exit 1 when
# none); _TC_WT = worktree name when <dir> is in a ~/src/.worktrees checkout.
_tabcolor_resolve() {
  REPLY="" _TC_WT=""
  if [[ -n "${TABCOLOR_PRESET:-}" ]]; then
    REPLY="$TABCOLOR_PRESET"
    return 0
  fi
  local dir="$1" wtbase="${PROJECTS:-$HOME/src}/.worktrees/"
  if [[ "$dir" == "$wtbase"?* ]]; then
    # Match a worktree as its main checkout: its .git file names the main repo.
    local wt="${${dir#$wtbase}%%/*}" rest="${${dir#$wtbase}#*/}" line=""
    [[ "$rest" == "${dir#$wtbase}" ]] && rest=""
    _TC_WT="${wt#*--}"
    if [[ -r "$wtbase$wt/.git" ]] && IFS= read -r line < "$wtbase$wt/.git" \
       && [[ "$line" == "gitdir: "*"/.git/worktrees/"* ]]; then
      dir="${${line#gitdir: }%/.git/worktrees/*}"
    else
      dir="${PROJECTS:-$HOME/src}/${wt%%--*}"
    fi
    [[ -n "$rest" ]] && dir="$dir/$rest"
  fi
  dir="${dir:l}"
  local p g tag
  local -a tags=(${=DOTFILES_TAGS})
  for p in "${_TC_ORDER[@]}"; do
    tag="${_TC_TAG[$p]}"
    [[ -n "$tag" ]] && (( ! ${tags[(Ie)$tag]} )) && continue
    for g in ${=_TC_GLOBS[$p]}; do
      if [[ "$dir" == ${~g} ]]; then
        REPLY="$p"
        return 0
      fi
    done
  done
  _TC_WT=""
  return 1
}

# _tabcolor_preset_for <dir>: print the preset (for scripts and tests).
_tabcolor_preset_for() {
  _tabcolor_resolve "$1" || return 1
  print -r -- "$REPLY"
}

# _tabcolor_group_name <preset> [worktree]: REPLY = "<emoji> <name>[ · <worktree>]"
_tabcolor_group_name() {
  REPLY="${_TC_EMOJI[$1]} ${_TC_NAME[$1]}"
  [[ -n "${2:-}" ]] && REPLY="$REPLY · $2"
  return 0
}

# _tabcolor_label <preset>: REPLY = "<emoji> <SHORT>" (+ " / <role>"); the
# directory name when no preset
_tabcolor_label() {
  if [[ -n "$1" && -n "${_TC_SHORT[$1]}" ]]; then
    REPLY="${_TC_EMOJI[$1]} ${_TC_SHORT[$1]}"
  else
    REPLY="${PWD:t}"
  fi
  [[ -n "${TERMINAL_ROLE:-}" ]] && REPLY="$REPLY / $TERMINAL_ROLE"
  return 0
}

# _tabcolor_rgb <preset> [darken]: REPLY = this tab's palette entry "R G B",
# optionally darkened 75% (floor 40); exit 1 for an unknown preset
_tabcolor_rgb() {
  REPLY=""
  local -a pal=("${(@s:|:)_TC_PALETTE[$1]}")
  [[ -n "${_TC_PALETTE[$1]}" ]] || return 1
  local -a rgb=(${=pal[$(( $$ % ${#pal} + 1 ))]})
  if [[ "${2:-}" == darken ]]; then
    local c i
    for i in 1 2 3; do
      c=$(( rgb[$i] * 3 / 4 )); (( c < 40 )) && c=40
      rgb[$i]=$c
    done
  fi
  REPLY="${rgb[1]} ${rgb[2]} ${rgb[3]}"
}

# _tabcolor_root <preset>: REPLY = the project's directory: `root:` from the
# YAML, else the first directory under $PROJECTS/*, $PROJECTS/*/* or ~/* that
# one of its globs matches. Exit 1 when none exists. Not on the prompt path.
_tabcolor_root() {
  REPLY=""
  local root="${_TC_ROOT[$1]}" d g
  if [[ -n "$root" ]]; then
    REPLY="${~root}"
    [[ -d "$REPLY" ]]
    return
  fi
  # A candidate counts only if it resolves to this project, so a folder inside
  # another project (dotfiles' own android/ topic) is never taken for it.
  local base="${PROJECTS:-$HOME/src}" TABCOLOR_PRESET=""
  for d in "$base"/*(N/) "$base"/*/*(N/) "$HOME"/*(N/); do
    for g in ${=_TC_GLOBS[$1]}; do
      if [[ "${d:l}" == ${~g} ]]; then
        _tabcolor_resolve "$d" && [[ "$REPLY" == "$1" ]] && { REPLY="$d"; return 0; }
        break
      fi
    done
  done
  REPLY=""
  return 1
}

# _tabcolor_apply <preset|empty> [worktree]: colour, title, badge and wb user
# variables for the current tab
_tabcolor_apply() {
  local preset="$1" label
  _tabcolor_label "$preset"; label="$REPLY"
  if [[ -n "$preset" ]] && _tabcolor_rgb "$preset"; then
    set_tab_color ${=REPLY}
    set_badge "$label"
    _tabcolor_group_name "$preset" "${2:-}"
    _tabcolor_uservars "$REPLY" "${_TC_GROUP_RGB[$preset]}"
  else
    reset_tab_color
    if [[ -n "${TERMINAL_ROLE:-}" ]]; then set_badge "$TERMINAL_ROLE"; else clear_badge; fi
    _tabcolor_uservars "" ""
  fi
  set_tab_title "$label"
}

# --- commands ---------------------------------------------------------------
tabcolor() {
  case "${1:-}" in
    danger)   set_tab_color 255 50 50; set_tab_title "⚠ PRODUCTION"; set_badge "PROD" ;;
    reset|"") _TABCOLOR_LAST=""; _tabcolor_apply "" ;;
    *)
      if [[ -n "${_TC_SHORT[$1]}" ]]; then
        _TABCOLOR_LAST="$1||${TERMINAL_ROLE:-}"
        _tabcolor_apply "$1"
      else
        echo "Unknown preset: $1. Available: ${_TC_ORDER[*]} danger reset"
        return 1
      fi ;;
  esac
}

# Preview a preset's palette: work tab vs darkened AI tab
tabcolor-preview() {
  local preset="${1:-}"
  if [[ -z "$preset" || -z "${_TC_PALETTE[$preset]}" ]]; then
    echo "Usage: tabcolor-preview <preset>"
    echo "Presets: ${_TC_ORDER[*]}"
    return 1
  fi
  echo ""
  echo "  ${_TC_EMOJI[$preset]} ${_TC_SHORT[$preset]} (${_TC_NAME[$preset]}) — work tab vs 🤖 AI tab"
  echo "  ─────────────────────────────────────────"
  echo ""
  local entry
  for entry in "${(@s:|:)_TC_PALETTE[$preset]}"; do
    local -a rgb=(${=entry})
    local r=${rgb[1]} g=${rgb[2]} b=${rgb[3]}
    local dr=$(( r * 3 / 4 )); (( dr < 40 )) && dr=40
    local dg=$(( g * 3 / 4 )); (( dg < 40 )) && dg=40
    local db=$(( b * 3 / 4 )); (( db < 40 )) && db=40
    printf "  \033[48;2;%d;%d;%dm    \033[0m %3d %3d %3d  work" "$r" "$g" "$b" "$r" "$g" "$b"
    printf "     \033[48;2;%d;%d;%dm    \033[0m %3d %3d %3d  ai\n" "$dr" "$dg" "$db" "$dr" "$dg" "$db"
  done
  local -a grp=(${=_TC_GROUP_RGB[$preset]})
  printf "\n  \033[48;2;%d;%d;%dm    \033[0m %3d %3d %3d  tab group\n\n" ${grp[1]} ${grp[2]} ${grp[3]} ${grp[1]} ${grp[2]} ${grp[3]}
}

# --- precmd hook ------------------------------------------------------------
# Resolves the preset only when $PWD (or TABCOLOR_PRESET) changes, applies it
# when the preset, worktree or role changes, and re-applies the title on every
# prompt because other hooks (oh-my-zsh termsupport) overwrite it. Set
# _TABCOLOR_LAST="" to force a full re-apply (role.zsh, ssh.zsh, ai-tabs.zsh
# do).
_TABCOLOR_LAST=""
_TABCOLOR_PWD=""
_TABCOLOR_WANT=""
_TABCOLOR_WANT_WT=""

_tabcolor_hook() {
  local key="$PWD|${TABCOLOR_PRESET:-}"
  if [[ "$key" != "$_TABCOLOR_PWD" ]]; then
    _TABCOLOR_PWD="$key"
    _tabcolor_resolve "$PWD"
    _TABCOLOR_WANT="$REPLY" _TABCOLOR_WANT_WT="$_TC_WT"
  fi
  local state="$_TABCOLOR_WANT|$_TABCOLOR_WANT_WT|${TERMINAL_ROLE:-}"
  if [[ "$state" != "$_TABCOLOR_LAST" ]]; then
    _tabcolor_apply "$_TABCOLOR_WANT" "$_TABCOLOR_WANT_WT"
    _TABCOLOR_LAST="$state"
  else
    _tabcolor_label "$_TABCOLOR_WANT"
    set_tab_title "$REPLY"
  fi
}

autoload -Uz add-zsh-hook
add-zsh-hook precmd _tabcolor_hook
