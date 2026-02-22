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

# Color palettes per project — each tab gets a different shade
# keyed by TABCOLOR_PRESET, rotated by shell PID
typeset -A _TABCOLOR_PALETTES
_TABCOLOR_PALETTES=(
  cosmic  "100,100,220 130,80,200 80,120,210 160,90,180 70,140,220 110,70,190 90,160,200 140,100,210"
  claude  "217,119,87 200,100,120 230,140,70 190,110,100 240,130,90 210,90,130 220,150,80 200,120,110"
  dotfiles "80,180,80 60,160,120 100,190,60 70,170,100 90,200,80 50,180,140 110,170,70 80,190,110"
  android "61,220,132 80,200,150 50,210,170 90,190,130 70,220,160 60,200,140 100,210,120 80,220,145"
)

# Named presets — the friendly command
tabcolor() {
  case "$1" in
    cosmic|claude|dotfiles|android)
      local palette=(${(s: :)_TABCOLOR_PALETTES[$1]})
      local idx=$(( $$ % ${#palette[@]} + 1 ))
      local rgb=(${(s:,:)palette[$idx]})
      set_tab_color ${rgb[1]} ${rgb[2]} ${rgb[3]}
      case "$1" in
        cosmic)   set_tab_title "Cosmic Clock" ; set_badge "PICO"    ;;
        claude)   set_tab_title "Claude: $(basename $PWD)" ; set_badge "CLAUDE" ;;
        dotfiles) set_tab_title "Dotfiles"     ; set_badge "SYS"     ;;
        android)  set_tab_title "Android"      ; set_badge "ANDROID" ;;
      esac
      ;;
    danger)    set_tab_color 255 50  50   ; set_tab_title "⚠ PRODUCTION"   ; set_badge "PROD"   ;;
    reset|"")  reset_tab_color            ; set_tab_title "$(basename $PWD)"; clear_badge        ;;
    *)         echo "Unknown preset: $1. Available: claude, cosmic, dotfiles, android, danger, reset" ;;
  esac
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
