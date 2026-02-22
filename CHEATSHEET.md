# Dotfiles Cheatsheet

## Navigation
z <partial>        # zoxide: smart cd (learns from usage)
c <project>        # cd to ~/src/<project>
Ctrl-T             # fzf: fuzzy file picker (inserts path)
Alt-C              # fzf: fuzzy cd

## Search
rg <pattern>       # ripgrep: fast recursive grep
fd <pattern>       # fd: fast find by filename
Ctrl-R             # fzf: fuzzy history search

## Git
gs                 # git status -sb
gl                 # git pull --prune
gp                 # git push origin HEAD
glog               # pretty git log graph
gac "msg"          # git add -A && commit
lazygit            # full git TUI

## Git Worktrees
gwl                # list worktrees
gwa <branch>       # new worktree + new branch → ~/src/.worktrees/
gwc <branch>       # worktree for existing branch
gwj                # fuzzy-jump to any worktree (fzf)
gwm                # jump back to main repo
gwr <path>         # remove worktree
gwp                # prune stale worktrees

## Vim
,f                 # fzf files
,r                 # fzf ripgrep
,b                 # fzf buffers
,g                 # git changed files
,gs                # git status (fugitive)
,n                 # NERDTree toggle
,w                 # save
,q                 # quit
gcc                # toggle comment
cs'"               # change surrounding ' to "
gd                 # go to definition (CoC)

## Cosmic Clock (active when cd'd into project via direnv)
cpush              # cosmic-push
cbuild             # full build with checks
cbq                # quick build (skip lint)
cbp upload         # build + push in one step
clogs              # cosmic-logs
ctime              # cosmic-logs -l timeline

## Tab Colors (iTerm2)
tabcolor claude    # orange tab + CLAUDE badge
tabcolor cosmic    # purple/blue + PICO badge
tabcolor dotfiles  # green + SYS badge
tabcolor android   # teal + ANDROID badge
tabcolor danger    # red + PROD badge
tabcolor reset     # back to default

## Dotfiles
dot                # update dotfiles + brew + defaults
reload!            # source ~/.zshrc
sync-upstream      # rebase onto holman/master
pubkey             # copy SSH public key

## Reading Files
bat <file>         # cat with syntax highlighting
delta              # better git diffs (automatic via gitconfig)
