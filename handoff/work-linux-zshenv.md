# Runbook: confirm ~/.zshenv for the work Linux box

Read `handoff/README.md` first. Every step: command, what to expect, test.
Log as you go with `bin/handoff note` and `bin/handoff capture`.

**This runbook only looks; it links nothing.** Every zsh reads `~/.zshenv`,
and the non-interactive `zsh -c` that `ssh host cmd` starts reads nothing
else, so tools installed outside the system dirs are missing there. The repo
now has a draft for this machine, `zsh/zshenv.work.linux.symlink` (only
`~/.local/bin` and `$ZSH/bin`, no Homebrew). Before `script/bootstrap` links
it, the author needs to know what this machine already has and needs. Do
**not** run `script/bootstrap`, `script/setup` or `script/install` while
following this runbook.

## 1. Repo up to date, on your branch

In the dotfiles directory (`cd ~/.dotfiles` if unsure):

```sh
bin/handoff note "runbook work-linux-zshenv.md, run $(date +%F)"
git checkout master
bin/git-safe-pull
bin/handoff branch
bin/handoff capture "git log --oneline -3"
```

Expect: `Successfully synchronized` (or `Already up to date`), a `script/test`
pass in which `bootstrap: 1 new link(s) pending` is a skip, not a failure,
then `on branch from/<id>`. A real failure: stop and report.

## 2. What zsh reads here today

```sh
bin/handoff capture "ls -la ~/.zshenv ~/.zprofile ~/.zshrc /etc/zshenv /etc/zsh/zshenv 2>&1"
bin/handoff capture "cat /etc/zshenv /etc/zsh/zshenv 2>&1"
bin/handoff capture "cat ~/.zshenv 2>&1"
```

Expect: `~/.zshrc` and `~/.zprofile` are links into the dotfiles. The rest
tells the author whether a managed zshenv already exists. If `~/.zshenv`
exists, bootstrap will leave it alone: say so prominently in the report.

## 3. PATH with and without the draft

```sh
bin/handoff capture "env -i HOME=\$HOME PATH=/usr/bin:/bin zsh -c 'print -r -- \$PATH'"
bin/handoff capture "env -i HOME=\$HOME PATH=/usr/bin:/bin zsh -fc 'source ~/.dotfiles/zsh/zshenv.work.linux.symlink; print -r -- \$PATH'"
bin/handoff capture "TERM=xterm-256color zsh -ic 'print -l \$path'"
bin/handoff capture "command -v brew; ls -d /home/linuxbrew/.linuxbrew ~/.linuxbrew 2>&1"
```

The first line is what `ssh host cmd` gets today, the second what it would
get with the draft, the third what an interactive shell has.

## 4. What must work from `ssh host cmd`

List the tools on this machine that you, the author's tooling or any agent
run non-interactively (over SSH, from cron, from scripts), and for each one
the directory it lives in. At least: `git`, `zsh`, `tmux`, `nvim`, `crank`
(if installed), `sops`, `age`, `jetski`, `jc`.

```sh
bin/handoff capture "for c in git zsh tmux nvim crank sops age; do printf '%s: ' \$c; TERM=xterm-256color zsh -ic \"whence -p \$c\" 2>/dev/null || echo missing; done"
bin/handoff note "non-interactive tools and dirs: <tool: dir, one per line>"
```

For each directory that is in the interactive PATH (step 3, third capture)
but not in the draft's (second capture), say whether it should be added.
Work-internal directory names go in the report only, never in the result line
or a commit message: if one is needed, the author puts it in the secrets file.

## 5. Report

```sh
bin/handoff result "done" "decide work linux zshenv contents"
bin/handoff report
bin/handoff commit
```

Use `"done" "nothing"` if the draft already covers everything in step 4 and
no `~/.zshenv` exists. If you stopped early:
`bin/handoff result "stopped at step N" "<what happened>"`, then `report`
and `commit` the same way.
