#!/bin/sh
#
# Homebrew
#
# Installs Homebrew on macOS if it is missing. Linux machines use apt via
# script/install and skip this.

if test "$(uname -s)" != "Darwin"
then
  exit 0
fi

if test ! "$(command -v brew)"
then
  echo "  Installing Homebrew for you."
  /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
fi

exit 0
