#!/bin/sh
#
# This script ensures vim-plug is installed and provides instructions
# for installing the plugins.
#

# Check if vim-plug is already installed
if [ ! -f "$HOME/.vim/autoload/plug.vim" ]; then
  echo "  Installing vim-plug for you."
  # Download vim-plug
  curl -fLo "$HOME/.vim/autoload/plug.vim" --create-dirs \
    https://raw.githubusercontent.com/junegunn/vim-plug/master/plug.vim
fi

# Print instructions for the user
echo "  ------------------------------------------------------------------"
echo "  To complete the Vim setup, open Vim and run the following command:"
echo "  :PlugInstall"
echo "  ------------------------------------------------------------------"

