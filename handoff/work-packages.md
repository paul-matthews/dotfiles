# Runbook: catch up on packages (work Macs)

Read `handoff/README.md` first. Every step: command, what to expect, test.
Log as you go with `bin/handoff note` and `bin/handoff capture`.

Packages added to `Brewfile` or `Brewfile.work` after a machine's last
`script/install` are never installed by a pull: `script/test` only reports
them as a skip. This runbook installs whatever is missing, and nothing else.
It does **not** upgrade anything already installed (that is what used to stop
on a password prompt).

## 1. Repo up to date, on your branch

Steps 1 and 2 of `handoff/work-darwin.md`, then:

```sh
bin/handoff note "runbook work-packages.md, run $(date +%F)"
```

## 2. What is missing

```sh
bin/handoff capture "brew bundle check --verbose --file=Brewfile 2>&1"
bin/handoff capture "brew bundle check --verbose --file=Brewfile.work 2>&1"
```

Expect: a list of missing formulae/casks (e.g. `tmux`, `neovim`), or
`The Brewfile's dependencies are satisfied.` If both are satisfied, go to step 4.

## 3. Install the missing ones

```sh
bin/handoff capture "HOMEBREW_BUNDLE_NO_UPGRADE=1 script/install 2>&1"
```

Expect: `brew bundle` installs only the missing packages, then each
`*/install.sh` runs (already-done steps say so). If anything asks for a
password or waits for input, stop: `bin/handoff result "stopped at step 3"
"brew asked for a password"`, then report. Do not retry with `sudo`.

## 4. Check

```sh
bin/handoff capture "brew bundle check --file=Brewfile 2>&1"
bin/handoff capture "brew bundle check --file=Brewfile.work 2>&1"
bin/handoff capture "TERM=xterm-256color script/test 2>&1"
bin/handoff capture "zsh -ic 'whence -p tmux nvim crank; crank doctor' 2>&1"
```

Expect: both checks satisfied; `script/test` ends in `PASS` with **no**
`not installed` skip; three paths printed; `crank doctor` with no failures.
Report any line that is not, without fixing it.

## 5. Report

```sh
bin/handoff result "done" "nothing"
bin/handoff report
bin/handoff commit
```

If you stopped early: `bin/handoff result "stopped at step N" "<what happened>"`,
then `report` and `commit` the same way.
