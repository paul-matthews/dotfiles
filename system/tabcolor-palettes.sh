#!/bin/sh
# Shared tab color palettes — POSIX sh, sourceable by both zsh and bash.
# Not auto-sourced by the topic loader (.sh extension, not .zsh).

# Output 8 lines of "R G B" triplets for a given preset.
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
  esac
}

# Output the emoji for a given preset.
_tabcolor_get_emoji() {
  case "$1" in
    cosmic)    echo "🪐" ;;
    dotfiles)  echo "📂" ;;
    android)   echo "📱" ;;
    docker)    echo "🐳" ;;
    spectra)   echo "🌈" ;;
    sandbox)   echo "🧪" ;;
    picotools) echo "🔧" ;;
    herd)      echo "🐑" ;;
    planner)   echo "📆" ;;
  esac
}
