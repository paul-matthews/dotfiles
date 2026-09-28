# Runbook: work Linux box

Read `handoff/README.md` first. Every step: command, what to expect, test.
Log as you go with `bin/handoff note` and `bin/handoff capture`.

This machine is special in three ways, and the order of steps below exists
because of them. Do not reorder.

1. It has been tracking the `linux` branch, not `master`. Master now contains
   everything that branch had, but this checkout may hold commits or edits that
   were never pushed. They must be carried, not discarded.
2. It holds the only plain-text copy of the old shared secrets at
   `~/.localrc.secrets`. That content must be published before anything pulls.
3. Its age key from the old setup is at `~/.age/key.txt`, and `~/.localrc`
   exports that path. The new tooling adopts that key; it must not generate a
   second one.

Any apt-based distro is supported. `script/install` needs `sudo apt-get`; if sudo
asks for a password you cannot give, use the `--no-install` variant in step 5.

## 1. Record the starting state

In the dotfiles directory (`cd ~/.dotfiles` if unsure):

```sh
bin/handoff note "runbook work-linux.md, run $(date +%F)"
bin/handoff capture "cat /etc/os-release"
bin/handoff capture "uname -a"
bin/handoff capture "echo \$SHELL; ls -la ~/.dotfiles"
bin/handoff capture "git branch --show-current"
bin/handoff capture "git status --short"
bin/handoff capture "git fetch origin && git log --oneline origin/linux..HEAD"
bin/handoff capture "ls ~"
bin/handoff capture "ls -la ~/.age ~/.config/sops/age 2>&1; grep -n SOPS_AGE_KEY_FILE ~/.localrc"
bin/handoff capture "grep -vc '^[[:space:]]*#' ~/.localrc.secrets 2>&1"
```

Expect: branch `linux`; the `origin/linux..HEAD` list is usually empty (unpushed
local commits if not); `~/.age/key.txt` exists; the last line is a count of real
lines in the old secrets file (`0` or an error means nothing to restore).

## 2. Move to your branch, carrying everything local

Stay on `linux`; do **not** check out master first. `bin/handoff branch` creates
`from/<id>` from the branch you are on, so unpushed commits and uncommitted edits
come along.

```sh
bin/handoff branch
git add -A && git commit -m "local changes found on $(bin/handoff id) before setup" || true
git merge --no-edit origin/master
bin/handoff capture "git log --oneline -3"
```

Expect: `on branch from/<id>`, then either a merge commit or `Already up to date`.
A conflict means stop: `bin/handoff capture "git status"`, report, do not resolve.

## 3. Adopt the old key

```sh
bin/secrets keygen
bin/handoff capture "bin/secrets status"
```

Expect: `adopted the existing age key from /home/<you>/.age/key.txt` and
`recipient: yes`. If it says `generated` instead, stop and report: the old key
was not found where expected.

## 4. Publish the old secrets before anything pulls

Only if step 1's count was greater than 0:

```sh
bin/secrets push --force
bin/handoff capture "bin/secrets status"
git add secrets.sops.yaml && git commit -m "secrets: restore content from $(bin/handoff id)"
```

Expect: `encrypted ... for N recipient(s); commit it` and `state: in sync`.
This replaces the placeholder the other machines currently have with the real
content, encrypted for every machine. If the count was 0, skip this step and
`bin/handoff note "no old secrets content to restore"`.

## 5. Set the machine up

```sh
script/setup --profile work
```

If `script/install` stops on a sudo prompt: `script/setup --profile work --no-install`
and `bin/handoff note "install skipped: sudo not available"`.

Expect: bootstrap output (`already in place` lines are fine; note anything
`left alone`), apt output with one `OK` per package (a `no installable package`
warning is fine, note it), bootstrap again ending in `secrets decrypted` or
`secrets: kept the existing ~/.localrc.secrets`, then `script/test` ending in
`PASS`.

```sh
bin/handoff capture "script/test"
```

`FAIL` means stop; the captured output is the report.

## 6. Check what this machine looks like from the new shell

```sh
bin/handoff capture "TERM=xterm-256color zsh -ic 'echo PROFILE=\$DOTFILES_PROFILE TAGS=\$DOTFILES_TAGS PROJECTS=\$PROJECTS; whence -w jc jetski agy'"
```

Expect: `PROFILE=work TAGS=work linux`, `PROJECTS=/home/<you>/src`, and the three
tools as `function`. If your repos do not live in `~/src`, say so in the report.

## 7. Report

```sh
bin/handoff key
bin/handoff result "done" "nothing"
bin/handoff report
bin/handoff commit
```

If you stopped early: `bin/handoff result "stopped at step N" "<what happened>"`,
then `report` and `commit` exactly the same way.

## After home has merged

You will be told to run again. Then, and only then, switch to master:

```sh
git checkout master && bin/git-safe-pull && bin/handoff branch
script/setup --profile work
bin/handoff capture "script/test"
bin/handoff result "done" "nothing" && bin/handoff report && bin/handoff commit
```
