# ls aliases
# Use eza if available for a modern experience, otherwise fallback to ls
if command -v eza >/dev/null 2>&1
then
  alias ls="eza --icons --group-directories-first"
  alias l="eza -lAh --icons --group-directories-first"
  alias ll="eza -l --icons --group-directories-first"
  alias la="eza -A --icons --group-directories-first"
elif command -v gls >/dev/null 2>&1
then
  # Mac with coreutils
  alias ls="gls -F --color"
  alias l="gls -lAh --color"
  alias ll="gls -l --color"
  alias la='gls -A --color'
else
  # Default ls (Linux or Mac without coreutils)
  alias ls="ls -F --color=auto"
  alias l="ls -lAh --color=auto"
  alias ll="ls -l --color=auto"
  alias la='ls -A --color=auto'
fi

# Cheatsheet (colored script in bin/, markdown in CHEATSHEET.md for GitHub)
alias cheat='$ZSH/bin/cheat | less -R'

# Secret management (SOPS + age): see bin/secrets
alias secrets-pull='secrets pull'
alias secrets-push='secrets push'
alias secrets-status='secrets status'
