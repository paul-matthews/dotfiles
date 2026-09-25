# Runbook: work Linux box

Read `handoff/README.md` first. Every step: command, what to expect, test.
Log as you go with `bin/handoff note` and `bin/handoff capture`.

Any apt-based distro is supported. `script/install` needs `sudo apt-get`; if sudo
asks for a password you cannot give, stop at that step and report it.

## 1. Get the repo onto master and up to date

Fresh machine only (skip if `~/src/system/dotfiles` exists):

```sh
sudo apt-get install -y git zsh
git clone git@github.com:paul-matthews/dotfiles.git ~/src/system/dotfiles
ln -s ~/src/system/dotfiles ~/.dotfiles
```

Then, in `~/src/system/dotfiles`:

```sh
bin/handoff note "runbook work-linux.md, run $(date +%F)"
bin/handoff capture "cat /etc/os-release"
bin/handoff capture "uname -a"
bin/handoff capture "git status --short"
bin/handoff capture "git log --oneline -3"
bin/handoff capture "git branch --show-current"
bin/handoff capture "ls ~"
```

This machine previously tracked the `linux` branch. Master now contains everything
that branch had. If `git branch --show-current` is not `master`:

```sh
git checkout master
```

If `git status --short` printed anything, do **not** discard it. Go to step 2 first,
commit it there, then come back.

```sh
bin/git-safe-pull
```

Expect: `Already up to date` or `Successfully synchronized`. Anything else: stop and report.

## 2. Move to your branch

```sh
bin/handoff branch
```

Expect: `on branch from/<id>`. Commit any pre-existing changes now:

```sh
git add -A && git commit -m "local changes found on $(bin/handoff id) before setup"
```

## 3. Set the machine up

```sh
script/setup --profile work
```

Expect, in order: bootstrap output, `apt-get update` then one `OK` line per package
from `linux/packages.txt` (a `no installable package among:` warning is fine, note
it), starship's installer if missing, bootstrap again (prints your public age key the
first time), then `script/test` ending in `PASS`.

This machine already holds an age key from the old setup. If `~/.config/sops/age/keys.txt`
is missing but `~/.age/key.txt` or another key exists, do not generate a new one: stop
and report where the existing key is.

Test: the last line of output is `PASS: N checks passed, M skipped`.

```sh
bin/handoff capture "script/test"
```

If your login shell is not zsh, note it in the report rather than changing it
(`chsh` needs a password): `bin/handoff capture "echo $SHELL"`.

## 4. Restore the secrets this machine held

This machine could decrypt the previous `secrets.sops.yaml` and may still have the
plain-text copy at `~/.localrc.secrets`. If that file exists and contains more than
comments, publish it so the other machines get it back:

```sh
bin/handoff capture "grep -vc '^#' ~/.localrc.secrets"
bin/secrets push --force
git add secrets.sops.yaml
```

Expect: `encrypted ... for 2 recipient(s)` or more. If the file does not exist or has
only comments, skip this step and say so.

## 5. Check what this machine looks like from the new shell

```sh
bin/handoff capture "zsh -ic 'echo PROFILE=\$DOTFILES_PROFILE TAGS=\$DOTFILES_TAGS PROJECTS=\$PROJECTS; whence -w jc'"
```

Expect: `PROFILE=work TAGS=work linux`, `PROJECTS=/home/<you>/src`, `jc: function`.
If your repos do not live in `~/src`, say so in the report.

## 6. Report

```sh
bin/handoff key
bin/handoff result "done" "add my key as a secrets recipient if secrets did not decrypt: handoff/keys/$(bin/handoff id).age.pub"
bin/handoff report
bin/handoff commit
```

If you stopped early: `bin/handoff result "stopped at step N" "<what happened>"`, then
`report` and `commit` exactly the same way.
