# Dotfiles Cheatsheet

## Navigation & Search                          │  Git Basics
                                                │
z <partial>         smart cd (zoxide)           │  gs              status -sb
c <project>         cd ~/src/<project>          │  gl              pull --prune
Ctrl-T              fzf file picker             │  gp              push origin HEAD
Ctrl-R              fzf history search          │  gc              commit
Alt-C               fzf cd                      │  gca             commit -a
rg <pattern>        ripgrep search              │  gac "msg"       add all + commit
fd <pattern>        fast find                   │  gco <branch>    checkout
                                                │  gb              branch
## Git Aliases (gitconfig)                      │  gcb             copy branch name
                                                │  gd              diff (color)
git up              pull --rebase --autostash   │  glog            pretty log graph
git lg              log graph (all branches)    │  git amend       commit --amend
git last            log -1 HEAD                 │  git unstage     reset HEAD --
git cb <name>       checkout -b                 │  git count       shortlog -sn
git co <branch>     checkout                    │  lazygit         full git TUI
git pf              pull --ff-only              │

## Git Worktrees                                │  Worktree Flow
                                                │
gwl                 list worktrees              │  1. gwa feature-x      create branch + worktree
gwa <branch>        new branch + worktree       │  2. do work, commit, push
gwc <branch>        existing branch             │  3. gwm                back to main repo
gwj                 fzf jump to any tree        │  4. gwr <path>         cleanup when done
gwm                 back to main repo           │
gwr <path>          remove worktree             │  Claude parallel flow:
gwp                 prune stale trees           │    Tab1: gwa feat-a → work → push
                                                │    Tab2: gwa feat-b → work → push
                                                │    Both: gwj to jump between them

## Vim                                          │  Cosmic Clock (via direnv)
                                                │
,f              fzf files                       │  cpush           cosmic-push
,r              fzf ripgrep                     │  cbuild          full build with checks
,b              fzf buffers                     │  cbq             quick build (skip lint)
,g              git changed files               │  cbp upload      build + push in one step
,gs             git status (fugitive)           │  clogs           cosmic-logs
,n              NERDTree toggle                 │  ctime           cosmic-logs -l timeline
,w              save                            │
,q              quit                            │  ## Tab Colors (iTerm2)
gcc             toggle comment                  │
cs'"            change surround ' → "           │  tabcolor claude       orange + CLAUDE
ds"             delete surrounding "            │  tabcolor cosmic       purple + PICO
ysiw"           surround word with "            │  tabcolor dotfiles     green + SYS
gd              go to definition (CoC)          │  tabcolor android      teal + ANDROID
]q  [q          next/prev quickfix              │  tabcolor danger       red + PROD
]b  [b          next/prev buffer                │  tabcolor reset        default

## Dotfiles & Tools                             │  Reading Files
                                                │
dot             update dotfiles                 │  bat <file>      cat + syntax highlighting
reload!         source ~/.zshrc                 │  delta           better diffs (auto in git)
sync-upstream   rebase onto holman              │  bat -l json     pretty-print JSON
pubkey          copy SSH pub key                │
cheat           show this file                  │  ## Keyboard (zsh vi mode)
                                                │
## Shell                                        │  ESC             normal mode
                                                │  /pattern        search history
d               dirs -v (stack)                 │  v               edit command in $EDITOR
pu / po         pushd / popd                    │  Ctrl-A/E        beginning/end of line
