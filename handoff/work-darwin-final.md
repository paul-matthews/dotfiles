# Runbook: final convergence (work Macs)

Read `handoff/README.md` first. This is the last runbook for a work Mac that has
already been set up with `work-darwin.md`. It brings the machine to the same state
as every other work Mac, sends one last report, and leaves it on `master`. After
it, the machine is in the steady state described in the README: `gsp`, then
`reload!`, and nothing else.

It covers what `work-packages.md` and `work-toolroll-install.md` would have done,
so run this one instead of those. Everything in it is idempotent.

Files outside the repo it may change: missing Homebrew packages are installed
(nothing is upgraded); tool-roll links skills into Jetski's skill dir and
`~/.local/bin`; and `~/.config/crank/config` is rewritten **only** if it was
written by the old installer, with the old file kept as
`~/.config/crank/config.pre-fix.bak`.

## 1. Clean, on master, up to date

```sh
cd ~/.dotfiles
git status --short
```

Expect: nothing. If anything prints, stop: `bin/handoff branch`, commit it there
as the README's decision table says, report, and do not go on.

```sh
git checkout master
bin/git-safe-pull --no-push
```

Expect: `Successfully synchronized` (or `Already up to date`) and `script/test
passed`. Anything else: stop and report.

## 2. Link and install what is missing

```sh
bin/handoff note "runbook work-darwin-final.md, run $(date +%F)"
bin/handoff capture "script/bootstrap 2>&1 | tail -20"
```

Expect: links `already in place`, possibly a new one such as `~/.zshenv`, and
`secrets` in sync. Bootstrap only adds; a `left alone` line is fine, note it.

Brew can refuse to work because of stale dependency data. Check for it:

```sh
bin/handoff capture "brew bundle check --verbose --file=Brewfile 2>&1 | grep -A3 'circular dependency'"
```

If that printed a `circular dependency` between `libtiff` and `webp`, run the
fix brew itself recommends (this exact one; any other pair: stop and report):

```sh
bin/handoff capture "brew update 2>&1 | tail -3"
bin/handoff capture "brew uninstall --ignore-dependencies --force libtiff webp 2>&1; brew install libtiff webp 2>&1 | tail -5"
```

Then install, through an interactive zsh so the secrets (`TOOL_ROLL_SKILL_DIRS`)
are loaded:

```sh
bin/handoff capture "zsh -ic 'HOMEBREW_BUNDLE_NO_UPGRADE=1 script/install' 2>&1 | tail -60"
```

Expect: `brew bundle` installs only missing packages, then each `*/install.sh`
runs. The tool-roll lines link skills into Jetski's dir with no `grill-me`, and
may say `crank: pre-fix config moved to ~/.config/crank/config.pre-fix.bak`
followed by `crank: created ~/.config/crank/config`. If anything asks for a
password, stop and report; do not retry with `sudo`. If it ends with
`brew bundle failed for: ...`, the installers still ran; carry on with step 3,
which records what is missing.

## 3. Check and report

```sh
exec zsh
bin/handoff capture "git log --oneline -1; bin/secrets status"
bin/handoff capture "brew bundle check --verbose --file=Brewfile 2>&1 | tail -20; brew bundle check --verbose --file=Brewfile.work 2>&1 | tail -20"
bin/handoff capture "TERM=xterm-256color script/test 2>&1"
bin/handoff capture "zsh -ic 'print -r -- \$CRANK_PROVIDER_INPUT \$TOOL_ROLL_SKILL_DIRS; crank doctor' 2>&1"
bin/handoff result "done" "nothing"
bin/handoff branch && bin/handoff report && bin/handoff commit
git checkout master
```

Expect:

- `state: in sync`, and both Brewfiles satisfied
- `script/test` ends in `PASS`; the only skip is `gandalf hook absent (work profile)`
- `stdin`, then the Jetski skill dir ending in `!grill-me`; `crank doctor` with no failures
- `pushed from/<id>`, and the repo back on `master`

If a check is not as expected, still report, with
`bin/handoff result "done, check failed" "<which check>"` in place of the
`result` line above.

From here on the machine stays on `master`; see "Steady state" in the README.
