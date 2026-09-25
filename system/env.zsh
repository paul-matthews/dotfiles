# XDG Base Directory specification
export XDG_CONFIG_HOME="$HOME/.config"

# Pager configuration
# -R: Raw ANSI colors
# -F: Automatically exit if the entire file fits on the screen
# -X: Do not clear screen / initialize terminal screen buffer on exit
export PAGER="less -RFX"
export LESS="-RFX"

# SOPS/age key for the shared secrets (see bin/secrets); same path on every OS
export SOPS_AGE_KEY_FILE="${SOPS_AGE_KEY_FILE:-$HOME/.config/sops/age/keys.txt}"
