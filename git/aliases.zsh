# Git aliases
alias gpl='git pull --prune'
alias gl='git log --oneline -n 15'
alias glog="git log --graph --pretty=format:'%Cred%h%Creset %an: %s - %Creset %C(yellow)%d%Creset %Cgreen(%cr)%Creset' --abbrev-commit --date=relative"
alias gp='git push origin HEAD'

# Use git diff directly (enables your configured side-by-side 'delta' pager)
alias gd='command git diff'
alias gg='lazygit'

alias gc='git commit'
alias gca='git commit -a'
alias gco='git checkout'
alias gcb='git copy-branch-name'
alias gb='git branch'
alias gs='command git status -sb' # upgrade your git if -sb breaks for you. it's fun.
alias gac='git add -A && git commit -m'
alias ge='git-edit-new'

# Wrapper function to print a tip when you type full Git commands
git() {
  if [[ -t 2 ]]; then # Only remind when outputting to an interactive terminal (not in scripts/pipes)
    if [[ "$1" == "status" ]]; then
      echo -e "\033[33m💡 Tip: You can use 'gs' instead of 'git status'\033[0m" >&2
    elif [[ "$1" == "diff" ]]; then
      echo -e "\033[33m💡 Tip: You can use 'gd' instead of 'git diff'\033[0m" >&2
    fi
  fi
  command git "$@"
}

#==============================================================================
# Git Keybindings
#==============================================================================

# Run git status widget (Ctrl-X + s)
git_status_widget() {
  echo ""
  command git status -sb
  zle redisplay
}
zle -N git_status_widget
bindkey -M viins '^Xs' git_status_widget
bindkey -M vicmd '^Xs' git_status_widget

# Run git diff widget (Ctrl-X + d)
git_diff_widget() {
  echo ""
  command git diff
  zle redisplay
}
zle -N git_diff_widget
bindkey -M viins '^Xd' git_diff_widget
bindkey -M vicmd '^Xd' git_diff_widget
