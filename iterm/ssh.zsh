# SSH and Mosh wrappers for visual terminal awareness in iTerm2
# - Sets tab title to ☁️ <host>
# - Sets pane watermark badge to REMOTE
# - Restores project styling when disconnected

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

    # Set tab chrome color to Warm Amber (205, 140, 65)
    echo -ne "\033]6;1;bg;red;brightness;205\a"
    echo -ne "\033]6;1;bg;green;brightness;140\a"
    echo -ne "\033]6;1;bg;blue;brightness;65\a"

    # Set background color to Deep Warm Charcoal / Espresso (#1e1814)
    printf "\033]11;#1e1814\007\033]1337;SetColors=bg=1e1814\007"

    # Set watermark badge to ☁️ Rem
    printf "\e]1337;SetBadgeFormat=%s\a" "$(echo -n "☁️ Rem" | base64)"

    # Set window & tab title to show remote connection
    print -Pn "\e]1;☁️  ${target}\a\e]2;☁️  ${target}\a\e]0;☁️  ${target}\a"
  fi

  command "$cmd" "$@"
  local ret=$?

  if [[ "$TERM_PROGRAM" == "iTerm.app" ]]; then
    # Reset tab chrome color and background color to profile defaults
    echo -ne "\033]6;1;bg;*;default\a"
    printf "\033]111\007\033]1337;SetColors=bg=default\007"

    if [[ -n "$TERMINAL_ROLE" ]]; then
      role "$TERMINAL_ROLE" > /dev/null
    else
      # Clear badge override to let profile default badge show
      printf "\e]1337;SetBadgeFormat=\a"
      local dir_name="$(basename "$PWD")"
      print -Pn "\e]1;${dir_name}\a\e]2;${dir_name}\a\e]0;${dir_name}\a"
    fi
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
