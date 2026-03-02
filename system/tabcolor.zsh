# iTerm2 tab color via escape codes (no-op in other terminals)
set_tab_color() {
  if [[ "$TERM_PROGRAM" == "iTerm.app" || -n "$ITERM_SESSION_ID" ]]; then
    echo -ne "\033]6;1;bg;red;brightness;$1\a"
    echo -ne "\033]6;1;bg;green;brightness;$2\a"
    echo -ne "\033]6;1;bg;blue;brightness;$3\a"
  fi
}

# Reset iTerm2 tab color to default
reset_tab_color() {
  if [[ "$TERM_PROGRAM" == "iTerm.app" || -n "$ITERM_SESSION_ID" ]]; then
    echo -ne "\033]6;1;bg;*;default\a"
  fi
}

# Set terminal tab/window title (works in iTerm2, Ghostty, and most terminals)
set_tab_title() {
  printf '\033]0;%s\007' "$1"
}

# iTerm2 badge (large watermark text behind terminal content)
set_badge() {
  if [[ "$TERM_PROGRAM" == "iTerm.app" || -n "$ITERM_SESSION_ID" ]]; then
    printf "\e]1337;SetBadgeFormat=%s\a" "$(echo -n "$1" | base64)"
  fi
}

clear_badge() {
  if [[ "$TERM_PROGRAM" == "iTerm.app" || -n "$ITERM_SESSION_ID" ]]; then
    printf "\e]1337;SetBadgeFormat=%s\a" "$(echo -n "" | base64)"
  fi
}

# Source shared palette data (POSIX sh, used by both zsh and Claude's bash hook)
source "${0:h}/tabcolor-palettes.sh"

# Map preset name to display name
_tabcolor_display_name() {
  case "$1" in
    cosmic)    echo "Cosmic Clock" ;;
    dotfiles)  echo "Dotfiles" ;;
    android)   echo "Android" ;;
    docker)    echo "Docker" ;;
    spectra)   echo "Spectra" ;;
    sandbox)   echo "Sandbox" ;;
    picotools) echo "Pico Tools" ;;
    herd)      echo "Herd" ;;
  esac
}

# Map preset name to badge text
_tabcolor_badge() {
  case "$1" in
    cosmic)    echo "PICO" ;;
    dotfiles)  echo "SYS" ;;
    android)   echo "ANDROID" ;;
    docker)    echo "DOCKER" ;;
    spectra)   echo "SPECTRA" ;;
    sandbox)   echo "SANDBOX" ;;
    picotools) echo "PICOTOOLS" ;;
    herd)      echo "HERD" ;;
  esac
}

# Named presets — the friendly command
tabcolor() {
  case "$1" in
    cosmic|dotfiles|android|docker|spectra|sandbox|picotools|herd)
      # Read palette lines into zsh array
      local lines=()
      while IFS= read -r line; do
        lines+=("$line")
      done < <(_tabcolor_get_palette "$1")

      local idx=$(( $$ % ${#lines[@]} + 1 ))
      local rgb=(${=lines[$idx]})
      set_tab_color ${rgb[1]} ${rgb[2]} ${rgb[3]}

      local emoji=$(_tabcolor_get_emoji "$1")
      local name=$(_tabcolor_display_name "$1")
      set_tab_title "$emoji $name"
      set_badge "$(_tabcolor_badge "$1")"
      ;;
    danger)    set_tab_color 255 50  50   ; set_tab_title "⚠ PRODUCTION"   ; set_badge "PROD"   ;;
    reset|"")  reset_tab_color            ; set_tab_title "$(basename $PWD)"; clear_badge        ;;
    *)         echo "Unknown preset: $1. Available: cosmic, dotfiles, android, docker, spectra, sandbox, picotools, herd, danger, reset" ;;
  esac
}

# Preview work vs Claude (75% darkened) colors for a preset
tabcolor-preview() {
  local preset="$1"
  if [[ -z "$preset" ]]; then
    echo "Usage: tabcolor-preview <preset>"
    echo "Presets: cosmic dotfiles android docker spectra sandbox picotools herd"
    return 1
  fi

  local emoji=$(_tabcolor_get_emoji "$preset")
  local name=$(_tabcolor_display_name "$preset")
  if [[ -z "$name" ]]; then
    echo "Unknown preset: $preset"
    return 1
  fi

  echo ""
  echo "  $emoji $name — work tab vs 🤖 Claude tab"
  echo "  ─────────────────────────────────────────"
  echo ""

  local i=0
  while IFS= read -r line; do
    local rgb=(${=line})
    local r=${rgb[1]} g=${rgb[2]} b=${rgb[3]}

    # Darken by 75% for Claude tab (floor at 40)
    local dr=$(( r * 3 / 4 )); [[ $dr -lt 40 ]] && dr=40
    local dg=$(( g * 3 / 4 )); [[ $dg -lt 40 ]] && dg=40
    local db=$(( b * 3 / 4 )); [[ $db -lt 40 ]] && db=40

    printf "  \033[48;2;%d;%d;%dm    \033[0m %3d %3d %3d  work" "$r" "$g" "$b" "$r" "$g" "$b"
    printf "     \033[48;2;%d;%d;%dm    \033[0m %3d %3d %3d  claude\n" "$dr" "$dg" "$db" "$dr" "$dg" "$db"
    i=$(( i + 1 ))
  done < <(_tabcolor_get_palette "$preset")

  echo ""
}

# Auto-apply tab color from TABCOLOR_PRESET env var (set by direnv),
# or reset when leaving a direnv-managed directory.
# Tracks last-applied preset to avoid redundant escape codes on every prompt.
_TABCOLOR_LAST=""

_tabcolor_hook() {
  local want="${TABCOLOR_PRESET:-}"
  [[ -z "$DIRENV_DIR" ]] && want=""

  # Only act when the preset changes
  [[ "$want" == "$_TABCOLOR_LAST" ]] && return

  if [[ -n "$want" ]]; then
    tabcolor "$want"
  else
    reset_tab_color
    clear_badge
    set_tab_title "$(basename $PWD)"
  fi
  _TABCOLOR_LAST="$want"
}

# precmd fires after every command (including after direnv updates env).
# chpwd alone isn't enough because direnv's hook runs after chpwd.
autoload -Uz add-zsh-hook
add-zsh-hook precmd _tabcolor_hook
