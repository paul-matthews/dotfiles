# Runbook: wb workbench on a work Mac

Read `handoff/README.md` first. Every step: command, what to expect, test.
Log as you go with `bin/handoff note` and `bin/handoff capture`.

`wb` (iterm/wb.darwin.zsh) puts a project's tabs into an iTerm tab group. It
needs the private project list (an encrypted file), iTerm 3.7.5 or later, and
iTerm's Python API turned on. This runbook gets as far as it can without a
person and reports what is left for one. It never restarts iTerm: you may be
running inside it.

## 1. Repo up to date, on your branch

Steps 1 and 2 of `handoff/work-darwin.md`, then:

```sh
bin/handoff note "runbook work-wb.md, run $(date +%F)"
```

## 2. Private projects

```sh
bin/handoff capture "bin/secrets pull 2>&1; bin/secrets check; echo rc=\$?"
bin/handoff capture "ls -l ~/.config/dotfiles/projects.private.yaml"
```

Expect: `rc=0` and the file listed with mode `-rw-------`. Do not capture its
contents. If `rc=2`, this machine is not a recipient: stop here and report.

## 3. iTerm version

```sh
bin/handoff capture "defaults read /Applications/iTerm.app/Contents/Info CFBundleShortVersionString"
```

Expect: `3.7.5` or later. If older:

```sh
bin/handoff capture "brew upgrade --cask --greedy iterm2 2>&1; defaults read /Applications/iTerm.app/Contents/Info CFBundleShortVersionString"
```

If it is still older than 3.7.5 (Homebrew can lag iTerm's own updater), do not
try anything else: note `human: iTerm2 > Check for Updates` for the report.

## 4. Python API

```sh
bin/handoff capture "defaults read com.googlecode.iterm2 EnableAPIServer 2>&1"
```

If it is not `1`:

```sh
bin/handoff capture "defaults write com.googlecode.iterm2 EnableAPIServer -bool true && defaults read com.googlecode.iterm2 EnableAPIServer"
```

Expect: `1`. iTerm reads this at launch, so note `human: restart iTerm` for the
report. Then note `human: iTerm2 > Settings > General > Magic > "Allow all apps
to connect"` if this file is missing (it needs an admin password, and without
it the first connection waits on a macOS permission prompt nobody is there to
click):

```sh
bin/handoff capture "ls -l \"\$HOME/Library/Application Support/iTerm2/disable-automation-auth\" 2>&1"
```

## 5. Check

```sh
bin/handoff capture "zsh -ic 'wb doctor' 2>&1"
bin/handoff capture "TERM=xterm-256color script/test 2>&1"
```

Expect: `wb doctor` lines are `ok` or `info`. Before the human steps above are
done, `api`/`socket`/`connect` may say `FAIL`; that is expected, report it.
`projects` should list the work projects. `script/test` ends in `PASS`.
Running `wb doctor` also fills uv's cache for wb (a first run downloads the
`iterm2` package); if it fails to download, report the error line.

## 6. Report

```sh
bin/handoff result "done" "<the human: steps you noted, or nothing>"
bin/handoff report
bin/handoff commit
```

If you stopped early: `bin/handoff result "stopped at step N" "<what happened>"`,
then `report` and `commit` the same way.
