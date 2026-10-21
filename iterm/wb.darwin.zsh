# wb — workbench: a project's tabs in one iTerm tab group.
#
#   wb [<project>|.] [-w]   open the project's template tabs (default: AI + control)
#                           in a new group; -w puts them in a new window. Each tab
#                           starts in the project directory; only the AI tab runs
#                           anything ($DOTFILES_AI_TOOL). Again = a second set.
#   wb group                file this window's tabs into groups by project
#   wb add [<project>]      put this tab in its project's group (or the named one)
#   wb move [N]             move this tab's group to a new window, or window N
#   wb focus [<project>]    drill in: expand that group, collapse the rest;
#                           no project: drill out, expand everything
#   wb ls [--json]          groups and tabs in every window
#   wb doctor               check iTerm, its Python API and the project data
#
# Projects come from system/projects.yaml (+ the private file) through the tab
# colour engine (system/tabcolor.zsh), which also publishes each tab's group as
# an iTerm user variable. The iTerm work is done by iterm/wb.py over the Python
# API (iTerm 3.7.5+, Settings > General > Magic > Enable Python API).
# Exit: 0 ok, 1 failed, 2 usage. Paths are resolved at call time: this file
# loads before system/tabcolor.zsh, which sets _TC_DOTFILES.

# _wb_presets: reply = the presets active on this machine, in table order
_wb_presets() {
  reply=()
  local p tag
  local -a tags=(${=DOTFILES_TAGS})
  for p in "${_TC_ORDER[@]}"; do
    tag="${_TC_TAG[$p]}"
    [[ -n "$tag" ]] && (( ! ${tags[(Ie)$tag]} )) && continue
    reply+=("$p")
  done
}

# _wb_find <name>: REPLY = the active preset a name means: its key, its short
# name (any case) or a unique prefix of the key
_wb_find() {
  local want="${1:l}" p
  local -a hits
  _wb_presets
  for p in "${reply[@]}"; do
    [[ "$p" == "$want" || "${_TC_SHORT[$p]:l}" == "$want" ]] && { REPLY="$p"; return 0; }
  done
  for p in "${reply[@]}"; do [[ "$p" == "$want"* ]] && hits+=("$p"); done
  if (( ${#hits} == 1 )); then REPLY="${hits[1]}"; return 0; fi
  REPLY=""
  if (( ${#hits} > 1 )); then
    print -u2 "wb: '$1' could be ${(j:, :)hits}"
  else
    print -u2 "wb: no project '$1' here (projects: ${(j: :)reply})"
  fi
  return 1
}

_wb_py() {
  (( $+commands[uv] )) || { print -u2 "wb: uv is not installed (brew install uv)"; return 1; }
  [[ -n "${ITERM_SESSION_ID:-}" ]] || { print -u2 "wb: run this inside an iTerm tab"; return 1; }
  local verb="$1"; shift
  "$_TC_DOTFILES/iterm/wb.py" "$verb" --session "$ITERM_SESSION_ID" "$@"
}

_wb_start() {
  local arg="" newwin=0 a preset wt="" dir
  for a in "$@"; do
    case "$a" in
      -w|--window) newwin=1 ;;
      -*) print -u2 "wb: unknown option $a"; return 2 ;;
      *) [[ -n "$arg" ]] && { print -u2 "wb: one project at a time"; return 2; }; arg="$a" ;;
    esac
  done
  if [[ -z "$arg" || "$arg" == . ]]; then
    _tabcolor_resolve "$PWD" || { print -u2 "wb: $PWD is not in a project (add it to system/projects.yaml)"; return 1; }
    preset="$REPLY" wt="$_TC_WT"
    dir="$(git -C "$PWD" rev-parse --show-toplevel 2>/dev/null)" || dir="$PWD"
  else
    _wb_find "$arg" || return 2
    preset="$REPLY"
    if ! _tabcolor_root "$preset"; then
      if [[ -n "${_TC_ROOT[$preset]}" ]]; then
        print -u2 "wb: $preset's root: ${_TC_ROOT[$preset]} does not exist"
      else
        print -u2 "wb: $preset is not cloned on this machine (looked for ${_TC_GLOBS[$preset]} under ${${PROJECTS:-$HOME/src}/#$HOME/~}/*, ${${PROJECTS:-$HOME/src}/#$HOME/~}/*/* and ~/*); clone it, or set root: in projects.yaml"
      fi
      return 1
    fi
    dir="$REPLY"
  fi
  _tabcolor_group_name "$preset" "$wt"
  local -a opts=(--name "$REPLY" --color "${_TC_GROUP_RGB[$preset]}" --dir "$dir"
                 --roles "${_TC_TEMPLATE[$preset]}" --ai "${DOTFILES_AI_TOOL:-claude}")
  (( newwin )) && opts+=(--new-window)
  _wb_py start "${opts[@]}"
}

_wb_doctor() {
  local failed=0 v p
  _wb_doc() { printf '  %-5s %-12s %s\n' "$1" "$2" "$3"; [[ "$1" == FAIL ]] && failed=1; return 0; }
  autoload -Uz is-at-least

  if [[ "$(uname -s)" == Darwin ]]; then _wb_doc ok macOS "$(sw_vers -productVersion 2>/dev/null)"; else _wb_doc FAIL macOS "wb drives iTerm on macOS only"; fi

  if (( $+commands[uv] )); then _wb_doc ok uv "$(uv --version 2>/dev/null)"
  else _wb_doc FAIL uv "not installed (brew install uv)"; fi

  v="$(defaults read /Applications/iTerm.app/Contents/Info CFBundleShortVersionString 2>/dev/null)"
  if [[ -z "$v" ]]; then _wb_doc FAIL iTerm "not found in /Applications"
  elif is-at-least 3.7.5 "$v"; then _wb_doc ok iTerm "$v"
  else _wb_doc FAIL iTerm "$v: tab groups need 3.7.5+ (iTerm2 > Check for Updates)"; fi

  if [[ "$(defaults read com.googlecode.iterm2 EnableAPIServer 2>/dev/null)" == 1 ]]; then _wb_doc ok api "Python API enabled"
  else _wb_doc FAIL api "Python API off: iTerm2 > Settings > General > Magic > Enable Python API"; fi

  local sock="$HOME/Library/Application Support/iTerm2/private/socket"
  if [[ -S "$sock" ]]; then _wb_doc ok socket "present"
  else _wb_doc FAIL socket "no API socket (enable the API, then restart iTerm)"; fi

  if [[ -e "$HOME/Library/Application Support/iTerm2/disable-automation-auth" ]]; then
    _wb_doc info auth "\"Allow all apps to connect\" is on: ~0.1s per command"
  else
    _wb_doc info auth "per-command cookie via osascript (~0.14s); \"Allow all apps to connect\" skips it (needed on unattended Macs)"
  fi

  if [[ -z "${ITERM_SESSION_ID:-}" ]]; then
    _wb_doc warn session "not in an iTerm tab: connection not tested"
  elif (( ! failed )); then
    local out; out="$("$_TC_DOTFILES/iterm/wb.py" ping --session "$ITERM_SESSION_ID" 2>&1)"
    if [[ "$out" == *connect_ms=* ]]; then
      _wb_doc ok connect "${${out#*connect_ms=}%%$'\n'*}ms"
      [[ "$out" == *tab_groups=1* ]] && _wb_doc ok groups "tab group API available" || _wb_doc FAIL groups "this iTerm has no tab group API"
      [[ "$out" == *session=found* ]] && _wb_doc ok session "this tab is known to iTerm" || _wb_doc FAIL session "ITERM_SESSION_ID not found by the API"
    else
      _wb_doc FAIL connect "${out//$'\n'/ }"
    fi
  fi

  _wb_presets
  # Each project: where `wb <project>` would open it, and that the directory
  # maps back to the same project (an earlier row's glob could claim it first).
  local -a missing=()
  local where owner
  for p in "${reply[@]}"; do
    if _tabcolor_root "$p"; then
      where="${REPLY/#$HOME/~}"
      owner="$(TABCOLOR_PRESET= _tabcolor_preset_for "$REPLY")"
      if [[ "$owner" != "$p" ]]; then
        _wb_doc warn "$p" "$where matches ${owner:-no project} first (reorder projects.yaml or set root:)"
      else
        _wb_doc ok "$p" "$where${_TC_ROOT[$p]:+ (root:)}"
      fi
    elif [[ -n "${_TC_ROOT[$p]}" ]]; then
      _wb_doc warn "$p" "root: ${_TC_ROOT[$p]} does not exist"
    else
      missing+=("$p")
    fi
  done
  local cache="${XDG_CACHE_HOME:-$HOME/.cache}/dotfiles/projects.zsh"
  if [[ -e "$cache.failed" ]]; then
    _wb_doc warn cache "projects-gen failed at shell start; using an older list (see: projects-gen --check)"
  elif [[ ! -r "$cache" ]]; then
    _wb_doc info cache "no cache: public projects only (system/projects.gen)"
  fi
  _wb_doc ok projects "$(( ${#reply} - ${#missing} )) of ${#reply} for this machine ($DOTFILES_TAGS) are here"
  (( ${#missing} )) && _wb_doc info missing "not cloned on this machine: ${(j: :)missing}"
  if [[ -f "$_TC_DOTFILES/projects.private.sops.yaml" && ! -r "$HOME/.config/dotfiles/projects.private.yaml" ]]; then
    _wb_doc warn private "private projects not decrypted (run: secrets pull)"
  fi
  if (( $+functions[${DOTFILES_AI_TOOL:-claude}] || $+commands[${DOTFILES_AI_TOOL:-claude}] || $+aliases[${DOTFILES_AI_TOOL:-claude}] )); then
    _wb_doc ok ai "${DOTFILES_AI_TOOL:-claude}"
  else
    _wb_doc warn ai "${DOTFILES_AI_TOOL:-claude} is not installed here; AI tabs will fail to start it"
  fi
  unfunction _wb_doc
  return $failed
}

wb() {
  case "${1:-}" in
    -h|--help|help) sed -n '3,15p' "$_TC_DOTFILES/iterm/wb.darwin.zsh" | sed 's/^# \{0,1\}//' ;;
    doctor) _wb_doctor ;;
    group)  shift; _wb_py group "$@" ;;
    ls)     shift; _wb_py ls "$@" ;;
    move)   shift; _wb_py move ${1:+--to "$1"} ;;
    add|focus)
      local verb="$1"; shift
      if [[ -n "${1:-}" ]]; then
        _wb_find "$1" || return 2
        local preset="$REPLY"
        _tabcolor_group_name "$preset"
        _wb_py "$verb" --name "$REPLY" --color "${_TC_GROUP_RGB[$preset]}" --preset "$preset"
      else
        _wb_py "$verb"
      fi ;;
    *) _wb_start "$@" ;;
  esac
}

_wb() {
  _wb_presets
  if (( CURRENT == 2 )); then
    compadd -- doctor group add move focus ls help "${reply[@]}"
  elif [[ "${words[2]}" == (add|focus) ]] && (( CURRENT == 3 )); then
    compadd -- "${reply[@]}"
  fi
}
(( $+functions[compdef] )) && compdef _wb wb
