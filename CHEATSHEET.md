# Dotfiles Cheatsheet

## 🤫 Secrets (SOPS + age)
Shell secrets (exports, aliases, real paths) shared by every machine, encrypted in the repo.

- **Pull (decrypt):** `secrets-pull` → `~/.localrc.secrets` (mode 600, sourced by zshrc)
- **Edit:** `~/.localrc.secrets` in plain text (never committed)
- **Push (encrypt):** `secrets-push` → `secrets.sops.yaml`, then commit. Refused if another machine pushed since your last pull: pull, merge by hand, push again
- **Status:** `secrets-status` (key, recipients, in sync?)

### New machine
`script/bootstrap` generates the machine's age key at `~/.config/sops/age/keys.txt` and prints its public key. Back the key up in 1Password, then on any machine that can already decrypt: `secrets add-recipient age1...` and commit. The new machine's next `secrets-pull` (or `script/bootstrap`) then works.

---

## 🎨 Tabs & Roles
Tab colour, title and badge follow the project: `.envrc` preset first, else the path map in `system/tabcolor-presets.sh`.

- `role device` → tab reads `🪐 COS / device`; `role` clears; `role -s` shows (`rgit`, `rbuild`, `rdevice`, `rclear`)
- `claude` / `jc` → darkened project colour, 🤖 title, tool badge; restored on exit
- `ssh host` → amber tab while connected, project colour back after
- `tabcolor <preset>` · `tabcolor danger` · `tabcolor reset` · `tabcolor-preview <preset>`
- `gsp` → verified pull: fetch, rebase, `script/test`, roll back on failure

---

## 🎨 Terminal Rendering
If you see unknown characters in `ls` or your prompt:
- **Reason:** `eza` and `starship` require a **Nerd Font**.
- **Fix:** Install a font from [nerdfonts.com](https://www.nerdfonts.com/) (e.g., JetBrainsMono) and set it in your Terminal/iTerm2 settings.

---

## Navigation & Search                          │  Git Basics
                                                │
z <partial>         smart cd (zoxide)           │  gs              status -sb
c <project>         cd ~/src/<project>          │  gpl             pull --prune
Ctrl-T              fzf file picker             │  gsp             safe pull (atomic)
Ctrl-R              fzf history search          │  gl              log (short)
Alt-C               fzf cd                      │  gp              push origin HEAD
rg <pattern>        ripgrep search              │  gc              commit
fd <pattern>        fast find                   │  gca             commit -a
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
,q              quit                            │  ## Tab Colors & Layouts (iTerm2)
gcc             toggle comment                  │
cs'"            change surround ' → "           │  tabcolor <preset>     set tab color
ds"             delete surrounding "            │  iterm-layout new <ly> split tab + cmd
ysiw"           surround word with "            │  iterm-layout apply <ly>apply split on active tab
gd              go to definition (CoC)          │  tabcolor reset        reset colors
]q  [q          next/prev quickfix              │
]b  [b          next/prev buffer                │

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
