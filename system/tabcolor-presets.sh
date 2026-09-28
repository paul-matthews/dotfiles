#!/bin/sh
# Tab colour presets: the single source of truth for project tab colours.
# POSIX sh so it can be sourced by zsh and by plain sh scripts.
# Not auto-sourced by the topic loader (.sh, not .zsh); system/tabcolor.zsh sources it.
#
# One row per preset:
#   preset|SHORT|emoji|Display name|tag|path globs
#
#   SHORT     3 characters (up to 8 only if a project cannot be told apart in 3)
#   tag       home | work | empty for every machine; a row is ignored unless the
#             tag is in DOTFILES_TAGS
#   globs     space-separated, lowercase, matched against the lowercased
#             working directory; the FIRST matching row wins, so list specific
#             paths before general ones (cosmic-clock before docker)
#
# A repo's .envrc may still `export TABCOLOR_PRESET=<preset>` to override the map.
# Adding a project is one row here plus a palette below.

_TABCOLOR_PRESET_TABLE='
cosmic|COS|🪐|Cosmic Clock|home|*/cosmic-clock*
sandbox|SBX|🧪|Sandbox|home|*/claude-sandbox*
picotools|PIC|🔧|Pico Tools|home|*/pico-tools*
spectra|SPE|🌈|Spectra|home|*/spectra*
dotfiles|DOT|📂|Dotfiles||*/dotfiles*
android|AND|📱|Android|home|*/android*
herd|HRD|🐑|Herd|home|*/herd*
planner|PLN|📆|Planner Tools|home|*/planner-tools*
obsidian|OBS|🔮|Obsidian|work|*obsidian* *-work* */work/*
gandalf|GAN|🧙|Gandalf|work|*gandalf*
docker|DOC|🐳|Docker|home|*/src/docker */src/docker/*
'

# _tabcolor_row <preset>: print that preset's row, or nothing.
_tabcolor_row() {
  printf '%s\n' "$_TABCOLOR_PRESET_TABLE" | grep "^$1|" | head -1
}

# _tabcolor_presets: every preset name, in table order.
_tabcolor_presets() {
  printf '%s\n' "$_TABCOLOR_PRESET_TABLE" | grep -v '^$' | cut -d'|' -f1
}

# _tabcolor_field <preset> <n>: field n (1 preset, 2 short, 3 emoji, 4 name, 5 tag, 6 globs)
_tabcolor_field() {
  _tabcolor_row "$1" | cut -d'|' -f"$2"
}

# _tabcolor_get_palette <preset>: 8 lines of "R G B" for per-tab rotation.
_tabcolor_get_palette() {
  case "$1" in
    cosmic)
      echo "100 100 220"
      echo "130 80 200"
      echo "80 120 210"
      echo "160 90 180"
      echo "70 140 220"
      echo "110 70 190"
      echo "90 160 200"
      echo "140 100 210"
      ;;
    dotfiles)
      echo "80 180 80"
      echo "60 160 120"
      echo "100 190 60"
      echo "70 170 100"
      echo "90 200 80"
      echo "50 180 140"
      echo "110 170 70"
      echo "80 190 110"
      ;;
    android)
      echo "61 220 132"
      echo "80 200 150"
      echo "50 210 170"
      echo "90 190 130"
      echo "70 220 160"
      echo "60 200 140"
      echo "100 210 120"
      echo "80 220 145"
      ;;
    docker)
      echo "70 130 190"
      echo "80 140 200"
      echo "60 120 180"
      echo "90 150 210"
      echo "75 135 195"
      echo "65 125 185"
      echo "85 145 205"
      echo "70 140 190"
      ;;
    spectra)
      echo "200 80 160"
      echo "180 60 180"
      echo "220 90 140"
      echo "190 70 170"
      echo "210 100 150"
      echo "170 60 190"
      echo "230 80 130"
      echo "185 75 175"
      ;;
    sandbox)
      echo "210 180 60"
      echo "200 170 70"
      echo "220 190 50"
      echo "190 160 80"
      echo "215 185 55"
      echo "205 175 65"
      echo "225 195 45"
      echo "195 165 75"
      ;;
    picotools)
      echo "50 190 190"
      echo "60 200 180"
      echo "40 180 200"
      echo "70 210 170"
      echo "55 195 195"
      echo "45 185 205"
      echo "65 205 175"
      echo "50 195 185"
      ;;
    herd)
      echo "200 150 80"
      echo "190 140 90"
      echo "210 160 70"
      echo "180 130 100"
      echo "205 155 75"
      echo "195 145 85"
      echo "215 165 65"
      echo "185 135 95"
      ;;
    planner)
      echo "180 110 120"
      echo "190 120 110"
      echo "170 100 130"
      echo "200 130 100"
      echo "185 115 125"
      echo "175 105 135"
      echo "195 125 105"
      echo "180 115 115"
      ;;
    obsidian)   # from the retired iTerm "Work" profile: 167 139 250
      echo "167 139 250"
      echo "150 125 240"
      echo "180 150 255"
      echo "140 115 230"
      echo "160 135 245"
      echo "175 145 250"
      echo "155 130 240"
      echo "170 140 255"
      ;;
    gandalf)    # from the retired iTerm "Gandalf" profile: 0 184 245
      echo "0 184 245"
      echo "20 170 230"
      echo "40 195 250"
      echo "10 160 220"
      echo "30 185 240"
      echo "0 175 235"
      echo "50 200 250"
      echo "20 180 240"
      ;;
  esac
}

# _tabcolor_get_emoji <preset>: kept for callers of the old palettes file.
_tabcolor_get_emoji() {
  _tabcolor_field "$1" 3
}
