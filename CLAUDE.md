# Dotfiles — Claude Guide

Paul's dotfiles, forked from [holman/dotfiles](https://github.com/holman/dotfiles). Managed at `~/src/system/dotfiles`, symlinked to `~/.dotfiles`.

## Architecture

### Topic structure
Each top-level directory is a "topic" (git, vim, system, cosmic, etc.). The topic loader in `zsh/loader.zsh` (sourced by `zsh/zshrc.symlink`, with a plain-glob fallback if it fails) auto-sources `*.zsh` files:

1. `*/path.zsh` — loaded first (PATH modifications)
2. `**/*.zsh` — loaded next, skipping `path.zsh`, `completion.zsh`, `antigen.zsh` and `loader.zsh`
3. `*/completion.zsh` — loaded last
4. `*.symlink` — symlinked to `~/.<name>` by `script/bootstrap`; `*.configlink` to `~/.config/<name>`

### Machine profile and tags
A file is sourced only if every tag in its name is one of this machine's tags. `DOTFILES_TAGS` is built once per shell from: the profile (`home` or `work`, read from `~/.dotfiles-profile`, written by `script/bootstrap --profile X`), the OS from `uname` (`darwin` or `linux`), `pi` when `/proc/device-tree/model` names a Raspberry Pi, and any extra tags in `~/.dotfiles-tags` (`script/bootstrap --tag X`). So `foo.zsh` loads everywhere, `foo.work.zsh` on work machines, `foo.work.linux.zsh` on the work Linux box, `foo.pi.zsh` on Pis. Tags are stripped before a file is classified, so `path.work.zsh` still loads first. Guard by existence for tools, by tag for machines.

`DOTFILES_SAFE=1 zsh` starts a shell with no topic files, for repairing a broken setup.

### Key files
- `zsh/zshrc.symlink` → `~/.zshrc` — main shell config, antigen plugins, topic loader, tool integrations (fzf, zoxide, direnv)
- `git/gitconfig.symlink` → `~/.gitconfig` — git config with SSH signing, delta pager, rebase defaults
- `vim/vimrc.symlink` → `~/.vimrc` — vim-plug with tpope plugins, fzf.vim, CoC LSP
- `system/tabcolor.zsh` — iTerm2 tab color system with per-PID rotation
- `system/_path.zsh` — PATH setup (underscore prefix = loads first alphabetically)
- `git/aliases.zsh` — shell aliases (gs, gl, gpl, gp, gac, etc.)
- `git/worktree.zsh` — worktree helpers (gwa, gwc, gwj, gwm, gwr, gwp)
- `cosmic/aliases.zsh` — cosmic-clock project commands (cpush, cbuild, ctime, etc.)
- `zsh/loader.zsh` — machine tags and the tag-aware topic loader
- `script/bootstrap` — links symlinks, records the profile, installs the pre-commit hook; additive and idempotent, `--dry-run` shows what it would do
- `script/pre-commit` — installed as the repo's git hook; blocks private keys, unencrypted secrets files and values from `~/.localrc.secrets`
- `script/setup` — the one command for a new or existing machine: bootstrap, install, bootstrap again (secrets), test
- `bin/handoff` + `handoff/` — runbooks and reporting helpers for work machines driven by an agent with no chat channel; they commit to `from/<machine-id>`, never master, and reports are SOPS-encrypted. Keep the runbooks in step with any bootstrap or setup change
- `script/test` — starts a fresh interactive zsh in a pseudo-terminal and checks the promises below; `gsp` runs it after every pull
- `script/install` — packages: `brew bundle` on the core `Brewfile` then `Brewfile.<profile>` (`Brewfile.home` / `Brewfile.work`) on macOS; `linux/packages.txt` plus `linux/packages.pi.txt` via apt on any apt-based Linux (`name|fallback` per line); then every `*/install.sh`
- `bin/secrets` — SOPS + age secrets shared across machines: `pull`, `push`, `status`, `keygen`, `add-recipient`; aliased as `secrets-pull` etc.
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
- **`bin/` is tracked normally** — the global gitignore (`git/gitignore.symlink`) no longer excludes it, so plain `git add` works
- **SSH signing is active** — all commits are signed with Ed25519 key. The `allowedSignersFile` is at `~/.ssh/allowed_signers`
- **direnv controls per-project env** — `.envrc` files set `TABCOLOR_PRESET` and `PATH`. Tab colors are applied by a `precmd` hook in `system/tabcolor.zsh` that reads the env var (since direnv runs in a subshell and can't emit escape codes directly). The work machines' iTerm dynamic profiles under `iterm/` coexist with this for now; phase 4 of the normalisation plan replaces both with a single path map
- **EDITOR is vim** — set in both `editors/env.zsh` and `zsh/zshrc.symlink`
- **No `./bin` in PATH** — removed for security. Use explicit `./bin/something` for project-local scripts
- **Secrets live in `secrets.sops.yaml`**, encrypted with age to one key per machine (recipients in `.sops.yaml`). `secrets-pull` decrypts to `~/.localrc.secrets` (mode 600), which zshrc sources; `secrets-push` re-encrypts and refuses if another machine pushed since your last pull, because encrypted files cannot be merged. Bootstrap generates a machine's key at `~/.config/sops/age/keys.txt` and prints the public key; a machine that can decrypt adds it with `secrets add-recipient`. Anything not for a public repo (tokens, work-internal names, real paths) goes here, as exports or aliases
- **`gsp` is a verified pull** — after fetching and rebasing it runs `script/test` and rolls back to the previous head if the test fails, so a bad commit can never strand a machine. `GSP_NO_VERIFY=1` skips it in an emergency

## Tab colour system

One engine, `system/tabcolor.zsh`, on every machine. A precmd hook asks `_tabcolor_preset_for "$PWD"`, which returns `TABCOLOR_PRESET` if a repo's `.envrc` exported one, else the first row of `system/tabcolor-presets.sh` whose glob matches the directory (rows tagged `home` or `work` only apply on that profile). That file is the single source of truth: preset, 3-character short name, emoji, display name, tag, globs, and an 8-colour palette; per-tab rotation picks a palette entry by shell PID. Tab title and badge read `<emoji> <SHORT>`, plus ` / <role>` after `role <name>` (`iterm/role.zsh`); bare `role` clears it.

AI tools get the darkened project colour through shell wrappers in `system/ai-tabs.zsh` (`claude`) and `system/ai-tabs.work.zsh` (`jc`), which pass `"$@"` through untouched and hand the tab back to the engine on exit. `iterm/ssh.zsh` colours SSH sessions amber and hands back the same way. Manual: `tabcolor <preset>`, `tabcolor danger`, `tabcolor reset`, `tabcolor-preview <preset>`.

iTerm keeps exactly one dynamic profile, `iterm/DynamicProfiles/dotfiles-default.json`, carrying the Nerd Font; bootstrap links it and makes it the default profile. Automatic profile switching is not used. `claude/hooks.json` is the repo copy of the Claude Code hooks (installed by `bin/claude-hooks`, home profile only) and `claude/statusline-command.sh` the status line script.

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

Run `script/test`. It starts a fresh interactive zsh under a pseudo-terminal and checks that:

1. the shell reaches the prompt and writes nothing to stderr
2. `EDITOR` is `vim` and `PROJECTS` is `~/src`
3. `PATH` contains neither `./bin` nor `/Users/holman/`
4. `DOTFILES_PROFILE` matches `~/.dotfiles-profile` and `DOTFILES_TAGS` carries the profile and OS; work-only files stay unloaded on a home profile
5. topic functions are defined: `tabcolor`, `gwa`, `cpush`, `role`, and the `reload!` and `gsp` aliases; `DOTFILES_SAFE=1` gives a shell with none of them
6. no references to the old `Code` projects directory remain, `bin/` is not gitignored, every tracked zsh file parses, and files removed by a phase stay gone
7. `script/bootstrap --dry-run` has nothing left to do, and the pre-commit hook is installed and blocks a private key
8. secrets are decrypted and in sync, and `secrets push` refuses to overwrite a repo file that changed since the last pull

`gsp` runs the same script after every pull. Add a check whenever a change makes a new promise.
