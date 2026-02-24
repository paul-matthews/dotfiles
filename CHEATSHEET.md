# Dotfiles Cheatsheet

## Navigation & Search                          │  Git Basics
                                                │
z <partial>         smart cd (zoxide)           │  gs              status -sb
c <project>         cd ~/src/<project>          │  gpl             pull --prune
Ctrl-T              fzf file picker             │  gl              log (short)
Ctrl-R              fzf history search          │  gp              push origin HEAD
Alt-C               fzf cd                      │  gc              commit
rg <pattern>        ripgrep search              │  gca             commit -a
fd <pattern>        fast find                   │  gac "msg"       add all + commit
                                                │  gco <branch>    checkout
## Git Aliases (gitconfig)                      │  gb              branch
                                                │  gcb             copy branch name
git up              pull --rebase --autostash   │  gd              diff (color)
git lg              log graph (all branches)    │  glog            pretty log graph
git last            log -1 HEAD                 │  git amend       commit --amend
git cb <name>       checkout -b                 │  git unstage     reset HEAD --
git co <branch>     checkout                    │  git count       shortlog -sn
git pf              pull --ff-only              │  lazygit         full git TUI

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
