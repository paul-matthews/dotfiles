# SSH and Mosh wrappers for visual terminal awareness in iTerm2
# - Sets tab title to ☁️ <host>
# - Sets pane watermark badge to REMOTE
# - Hosts in _TABCOLOR_SSH_TABLE (system/tabcolor-presets.sh) get their own
#   colours, badge and title; every other host gets warm amber
# - Restores project styling when disconnected

# _ssh_host_row <args...>: the _TABCOLOR_SSH_TABLE row for the first argument
# naming a known host (user@ stripped), or nothing (exit 1).
_ssh_host_row() {
  local arg host row globs g
  for arg in "$@"; do
    [[ "$arg" == -* ]] && continue
    host="${${arg##*@}:l}"
    while IFS= read -r row; do
      [[ -z "$row" ]] && continue
      globs="${row##*|}"
      for g in ${=globs}; do
        if [[ "$host" == ${~g} ]]; then
          print -r -- "$row"
          return 0
        fi
      done
    done <<< "${_TABCOLOR_SSH_TABLE:-}"
  done
  return 1
}

_iterm_ssh_wrapper() {
  local cmd="$1"
  shift

  if [[ "$TERM_PROGRAM" == "iTerm.app" ]]; then
    # Extract destination target (last argument that doesn't start with -)
    local target=""
    for arg in "$@"; do
      [[ "$arg" != -* ]] && target="$arg"
    done
    [[ -z "$target" ]] && target="${*[-1]}"

    # Default: Warm Amber tab (205, 140, 65) on Deep Warm Charcoal (#1e1814)
    local -a rgb=(205 140 65) f
    local bg="1e1814" emoji="☁️" badge="☁️ Rem" row
    if row="$(_ssh_host_row "$@")"; then
      f=("${(@s:|:)row}")
      emoji="${f[3]}" badge="${f[3]} ${f[2]}" rgb=(${=f[4]}) bg="${f[5]}"
    fi

    echo -ne "\033]6;1;bg;red;brightness;${rgb[1]}\a"
    echo -ne "\033]6;1;bg;green;brightness;${rgb[2]}\a"
    echo -ne "\033]6;1;bg;blue;brightness;${rgb[3]}\a"
    printf "\033]11;#%s\007\033]1337;SetColors=bg=%s\007" "$bg" "$bg"
    printf "\e]1337;SetBadgeFormat=%s\a" "$(echo -n "$badge" | base64)"

    # Set window & tab title to show remote connection
    print -rn -- $'\e]1;'"${emoji}  ${target}"$'\a\e]2;'"${emoji}  ${target}"$'\a\e]0;'"${emoji}  ${target}"$'\a'
  fi

  command "$cmd" "$@"
  local ret=$?

  if [[ "$TERM_PROGRAM" == "iTerm.app" ]]; then
    # Reset chrome and background to profile defaults, then let the tab colour
    # engine restore the project colour, title and badge (role included)
    echo -ne "\033]6;1;bg;*;default\a"
    printf "\033]111\007\033]1337;SetColors=bg=default\007"
    _TABCOLOR_LAST=""
    (( $+functions[_tabcolor_hook] )) && _tabcolor_hook
  fi

  return $ret
}

ssh() {
  _iterm_ssh_wrapper ssh "$@"
}

if (( $+commands[mosh] )); then
  mosh() {
    _iterm_ssh_wrapper mosh "$@"
  }
fi
