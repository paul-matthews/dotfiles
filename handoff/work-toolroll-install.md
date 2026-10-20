# Runbook: install tool-roll skills for Jetski (work Macs)

Read `handoff/README.md` first. Every step: command, what to expect, test.
Log as you go with `bin/handoff note` and `bin/handoff capture`.

This is the follow-up to `handoff/work-toolroll-skills.md`, which only looked.
The collision is decided: every enabled skill goes into Jetski's user skill
dir except `grill-me` (Jetski has its own). The dir and the exclusion come
from the secrets file as `TOOL_ROLL_SKILL_DIRS`; do not set it anywhere else.
This runbook **does** install: it creates symlinks in Jetski's skill dir and
in `~/.local/bin`, and nothing else outside the two repos.

Work Macs only. On Linux, stop at step 1 and report "not a Mac".

## 1. Repo up to date, on your branch

Steps 1 and 2 of `handoff/work-darwin.md`, then:

```sh
bin/handoff note "runbook work-toolroll-install.md, run $(date +%F)"
```

## 2. Secrets carry the skill dir

```sh
bin/secrets pull
bin/handoff capture "bin/secrets status"
bin/handoff capture "zsh -ic 'print -r -- \$TOOL_ROLL_SKILL_DIRS' 2>/dev/null"
```

Expect: `state: in sync`, and one path ending in `!grill-me`. If the second
command prints nothing, stop: `bin/handoff result "stopped at step 2"
"TOOL_ROLL_SKILL_DIRS not set by secrets"`, then report.

## 3. tool-roll up to date

If `~/src/tool-roll` does not exist, clone it as in step 2 of
`handoff/work-toolroll-skills.md`. Then:

```sh
git -C ~/src/tool-roll checkout main
git -C ~/src/tool-roll pull --ff-only
git -C ~/src/tool-roll submodule update --init
bin/handoff capture "git -C ~/src/tool-roll log --oneline -1"
git -C ~/src/tool-roll merge-base --is-ancestor 7b3a7ac HEAD && echo has-skip
```

Expect: `has-skip` (the installer that understands `!grill-me`). If the pull
is refused or `has-skip` is missing, stop and report.

## 4. Dry run

Run through an interactive zsh so the secrets are loaded:

```sh
bin/handoff capture "zsh -ic './toolroll/install.sh --dry-run' 2>&1"
```

Expect: `would: link <name> ...` for up to 16 skills into Jetski's dir, **no**
line for `grill-me`, possibly crank lines (`~/.local/bin`, `crank.app`, the
Alfred workflow) if those are not in place yet, and no `!!` warnings. If a
`grill-me` link or any `!!` line appears, stop and report.

## 5. Install

```sh
bin/handoff capture "zsh -ic './toolroll/install.sh' 2>&1"
```

Then check the result (`<dir>` is the path from step 2, without `!grill-me`):

```sh
bin/handoff capture "find <dir> -maxdepth 1 -type l | sort"
bin/handoff capture "ls <dir>"
```

Expect: 16 symlinks into `~/src/tool-roll/vendor/...`, no `grill-me`, and
whatever was already in the dir before (e.g. `reflect`) still there.

## 6. Jetski sees them

Start a new Jetski session and check, from Jetski's own skill listing, that
`tdd`, `grilling` and `handoff` are available as user skills and that
`/grill-me` is still the built-in one.

```sh
bin/handoff note "jetski sees: <skills listed, or what was missing>"
```

## 7. Report

```sh
bin/handoff result "done" "nothing"
bin/handoff report
bin/handoff commit
```

If you stopped early: `bin/handoff result "stopped at step N" "<what happened>"`,
then `report` and `commit` the same way. Keep paths out of the result line.
