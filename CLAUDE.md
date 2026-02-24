# Dotfiles — Claude Guide

Paul's dotfiles, forked from [holman/dotfiles](https://github.com/holman/dotfiles). Managed at `~/src/system/dotfiles`, symlinked to `~/.dotfiles`.

## Architecture

### Topic structure
Each top-level directory is a "topic" (git, vim, system, cosmic, etc.). The topic loader in `zsh/zshrc.symlink` auto-sources all `*.zsh` files:

1. `*/path.zsh` — loaded first (PATH modifications)
2. `**/*.zsh` — loaded next, skipping `path.zsh`, `completion.zsh`, `zshrc.symlink`, and `antigen.zsh`
3. `*.symlink` — symlinked to `~/.<name>` by `script/bootstrap`

### Key files
- `zsh/zshrc.symlink` → `~/.zshrc` — main shell config, antigen plugins, topic loader, tool integrations (fzf, zoxide, direnv)
- `git/gitconfig.symlink` → `~/.gitconfig` — git config with SSH signing, delta pager, rebase defaults
- `vim/vimrc.symlink` → `~/.vimrc` — vim-plug with tpope plugins, fzf.vim, CoC LSP
- `system/tabcolor.zsh` — iTerm2 tab color system with per-PID rotation
- `system/_path.zsh` — PATH setup (underscore prefix = loads first alphabetically)
- `git/aliases.zsh` — shell aliases (gs, gl, gpl, gp, gac, etc.)
- `git/worktree.zsh` — worktree helpers (gwa, gwc, gwj, gwm, gwr, gwp)
- `cosmic/aliases.zsh` — cosmic-clock project commands (cpush, cbuild, ctime, etc.)
- `bin/cheat` — colored cheatsheet script (run `cheat` to view)
- `bin/sync-upstream` — rebase onto holman/master

### Antigen guard
Antigen is wrapped in `if [[ -z "$_ANTIGEN_LOADED" ]]` to prevent prompt breakage on `reload!` (source ~/.zshrc). Do not remove this guard.

## Paul's workflow

- **Primary tools:** Claude CLI (multiple instances in iTerm2 tabs), git+GitHub, vim for quick edits
- **Main project:** Cosmic Clock — MicroPython on Raspberry Pi Pico, with a Go binary (`cosmic-push`) for uploading
- **Terminal:** iTerm2 for work, Ghostty for Claude chat sessions
- **Multiple Claude tabs:** Each gets a unique color from a rotating palette (per-PID, per-directory). Worktrees (`gwa`) give each Claude instance its own branch/directory

## Important conventions

- **Don't edit `~/.gitconfig` directly** — edit `git/gitconfig.symlink` and it gets symlinked
- **`bin/` is gitignored** — use `git add -f bin/<script>` to add new scripts
- **SSH signing is active** — all commits are signed with Ed25519 key. The `allowedSignersFile` is at `~/.ssh/allowed_signers`
- **direnv controls per-project env** — `.envrc` files set `TABCOLOR_PRESET` and `PATH`. Tab colors are applied by a `precmd` hook in `system/tabcolor.zsh` that reads the env var (since direnv runs in a subshell and can't emit escape codes directly)
- **EDITOR is vim** — set in both `editors/env.zsh` and `zsh/zshrc.symlink`
- **No `./bin` in PATH** — removed for security. Use explicit `./bin/something` for project-local scripts

## Tab color system

Colors rotate per-tab using shell PID (`$$`). Each project preset has an 8-color palette defined in `_TABCOLOR_PALETTES` in `system/tabcolor.zsh`. Projects set `export TABCOLOR_PRESET=<name>` in their `.envrc`.

Available presets: `claude`, `cosmic`, `dotfiles`, `android`, `danger`, `reset`

Claude CLI sessions use `~/.claude/session-tab-color.sh` (SessionStart hook) with a separate rotation using `PPID`.

## Git configuration

- Pull: rebase by default with autostash
- Merge conflicts: zdiff3 style
- Diff: histogram algorithm, colorMoved
- Pager: delta (side-by-side, line numbers)
- rerere: enabled (remembers conflict resolutions)
- Signing: SSH format with Ed25519 key

## Stale/removed topics

These were removed during the audit: `ruby/`, `sublime/`, `xcode/`. The `vendor/` directory has old pathogen submodules (vim-plug is used now).

## New machine setup reminder

When Paul mentions setting up a new machine or syncing dotfiles to another device, remind him to check the manual steps in README.md (e.g., setting iTerm2 font to MesloLGS Nerd Font).

## Testing changes

After modifying shell config:
1. `source ~/.zshrc` (or `reload!`) — should produce no errors
2. `echo $EDITOR` → should be `vim`
3. `echo $PATH` — should not contain `./bin` or `/Users/holman/`
4. Topic functions should be available: `type tabcolor`, `type gwa`, `type cpush`
