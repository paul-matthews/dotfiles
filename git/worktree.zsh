# Git worktree helpers — all worktrees land in ~/src/.worktrees/reponame--branch
# This keeps ~/src/ clean while giving a central place to see all active work.

alias gwl='git worktree list'
alias gwr='git worktree remove'

# Create worktree + NEW branch, cd into it
gwa() {
  local branch="$1"
  local repo_name=$(basename $(git rev-parse --show-toplevel))
  local wt_dir="$HOME/src/.worktrees/${repo_name}--${branch}"
  git worktree add -b "$branch" "$wt_dir" && cd "$wt_dir"
  echo "Worktree: $wt_dir"
}

# Create worktree for EXISTING branch, cd into it
gwc() {
  local branch="$1"
  local repo_name=$(basename $(git rev-parse --show-toplevel))
  local wt_dir="$HOME/src/.worktrees/${repo_name}--${branch}"
  git worktree add "$wt_dir" "$branch" && cd "$wt_dir"
  echo "Worktree: $wt_dir"
}

# Fuzzy-jump to any worktree (uses fzf)
gwj() {
  local wt=$(git worktree list | fzf --height 40% | awk '{print $1}')
  [[ -n "$wt" ]] && cd "$wt"
}

# Jump back to main repo from any worktree
gwm() {
  cd "$(git worktree list | head -1 | awk '{print $1}')"
}

# Prune stale worktrees
gwp() {
  git worktree prune
  echo "Pruned stale worktrees"
  git worktree list
}
