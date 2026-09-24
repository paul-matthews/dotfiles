#!/usr/bin/env bash
#
# Ensure glow configuration is linked across macOS and Linux.
set -e

DOTFILES_ROOT="$(cd "$(dirname "$0")/.." && pwd -P)"

# 1. Linux & standard XDG location
mkdir -p "$HOME/.config/glow"
if [ ! -L "$HOME/.config/glow/glow.yml" ]; then
  ln -sf "$DOTFILES_ROOT/glow/glow.yml" "$HOME/.config/glow/glow.yml"
fi

# 2. macOS standard location
if [ "$(uname -s)" = "Darwin" ]; then
  mkdir -p "$HOME/Library/Preferences/glow"
  if [ ! -L "$HOME/Library/Preferences/glow/glow.yml" ]; then
    ln -sf "$DOTFILES_ROOT/glow/glow.yml" "$HOME/Library/Preferences/glow/glow.yml"
  fi
fi

# 3. Linux package check
if [ "$(uname -s)" = "Linux" ] && ! command -v glow >/dev/null 2>&1; then
  echo "  [glow] glow not found. Please install via your package manager (e.g. brew, apt, or pacman)."
fi
