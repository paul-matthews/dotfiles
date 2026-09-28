# Runbook: work Mac

Read `handoff/README.md` first. Every step: command, what to expect, test.
Log as you go with `bin/handoff note` and `bin/handoff capture`.

## 1. Get the repo onto master and up to date

Fresh machine only (skip if `~/src/system/dotfiles` exists):

```sh
git clone git@github.com:paul-matthews/dotfiles.git ~/src/system/dotfiles
ln -s ~/src/system/dotfiles ~/.dotfiles
```

Then, in `~/src/system/dotfiles`:

```sh
bin/handoff note "runbook work-darwin.md, run $(date +%F)"
bin/handoff capture "sw_vers"
bin/handoff capture "git status --short"
bin/handoff capture "git log --oneline -3"
bin/handoff capture "ls ~"
```

If `git status --short` printed anything, do **not** discard it. Go to step 2 first,
commit it there, then come back.

```sh
git checkout master
bin/git-safe-pull
```

Expect: `Already up to date` or `Successfully synchronized`, followed by
`script/test passed` if the repo already had `script/test`. Anything else: stop and report.

## 2. Move to your branch

```sh
bin/handoff branch
```

Expect: `on branch from/<id>`. Commit any pre-existing changes now:

```sh
git add -A && git commit -m "local changes found on $(bin/handoff id) before setup"
```

(skip if nothing was pending; the hook may block a commit, in which case stop and report)

## 3. Set the machine up

```sh
script/setup --profile work
```

Expect, in order: bootstrap output (links made or `already in place`; a `left alone`
list is fine, note it), `brew bundle` on `Brewfile` then `Brewfile.work` (installs
packages, may take a while), bootstrap again (prints your public age key the first
time, and `secrets: this machine cannot decrypt yet` until your key is a recipient),
then `script/test` ending in `PASS`.

Test: the last line of output is `PASS: N checks passed, M skipped`. `FAIL` means
stop; capture the output and report.

```sh
bin/handoff capture "script/test"
```

## 4. Retire the old iTerm profile switching (once)

```sh
rm -f "$HOME/Library/Application Support/iTerm2/DynamicProfiles/projects.json"
bin/handoff capture "ls -la \"$HOME/Library/Application Support/iTerm2/DynamicProfiles/\""
```

Expect: only `dotfiles-default.json` remains. The tab colours now come from the
shell; no iTerm profile switching is needed.

## 5. Check what this machine looks like from the new shell

```sh
bin/handoff capture "TERM=xterm-256color zsh -ic 'echo PROFILE=\$DOTFILES_PROFILE TAGS=\$DOTFILES_TAGS PROJECTS=\$PROJECTS; whence -w jc jetski agy gandalf_prompt_precmd'"
bin/handoff capture "TERM=xterm-256color zsh -ic 'whence -v jc; grep -n \"alias jc\" ~/.localrc ~/.localrc.secrets ~/.zlogin ~/.zshenv ~/.zprofile ~/.zshrc.local /etc/zshrc /etc/zprofile 2>/dev/null'"
```

Expect: `PROFILE=work TAGS=work darwin`, `PROJECTS=/Users/<you>/src`, `jc: function`,
`jetski: function`, and `gandalf_prompt_precmd: function` only if Gandalf is installed.
The second command shows where `jc` is defined; capture it whatever it says. If your repos do not
live in `~/src`, say so in the report: `PROJECTS` will need a work override.

## 6. Report

```sh
bin/handoff key
bin/handoff result "done" "add my key as a secrets recipient: handoff/keys/$(bin/handoff id).age.pub"
bin/handoff report
bin/handoff commit
```

On a later run, when your key is already a recipient, step 3 decrypts secrets and
the result line is `bin/handoff result "done" "nothing"`.

If you stopped early: `bin/handoff result "stopped at step N" "<what happened>"`, then
`report` and `commit` exactly the same way.
