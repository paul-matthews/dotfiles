# Handoff: setting up a work machine without a human in the loop

This directory is for an agent (jetski) running on a work Mac or the work Linux
box. There is no chat channel back to the author. Everything you need is in this
repo, and everything you have to say goes back as a commit on your own branch.

## Read in this order

1. This file, to the end.
2. `CLAUDE.md` at the repo root: what the repo is and the promises `script/test` checks.
3. The runbook for this machine: `handoff/work-darwin.md` on macOS, `handoff/work-linux.md` on Linux.

## The rules

- **Never commit to `master`.** Every commit you make goes to `from/<machine-id>`
  (`bin/handoff branch` puts you there). The author reviews and merges it at home.
- **Never use `git push --force`, `git reset --hard`, `git stash drop`, `git clean`,
  or `--no-verify`.** If a hook blocks a commit, stop and report what it blocked.
- **Never delete or overwrite a file outside the repo.** `script/setup` only adds;
  if it reports a file it left alone, list it in the report and move on.
- **Follow the runbook's steps in order.** Every step has a command, what to expect,
  and a test. Do not improvise a fix outside the runbook.
- **Report everything you decided.** The decision table below covers the likely
  situations; anything else means stop, describe it, commit, push.

## Decisions you make without asking

| Situation on arrival | What you do |
| --- | --- |
| Uncommitted or unstaged changes in the repo | `bin/handoff branch`, then commit them all on `from/<id>` with a message describing what they are; name them in the report. Never stash-and-forget, never discard |
| Untracked files | Same, unless gitignored |
| Local commits not on origin | They come along to `from/<id>` when you branch; never rebase master onto them |
| `gsp` reports a conflict or is not a fast-forward | Stop; `bin/handoff capture "git status"` and `bin/handoff capture "git log --oneline -5"`; report |
| A test fails | Stop at that step; capture the command and its output; report. Do not attempt a fix |
| A step is already done | Note it as done and continue (everything is idempotent) |
| The pre-commit hook blocks a commit | Stop; report what it blocked; never `--no-verify` |
| Anything the runbook does not cover | Stop; describe it; commit; push |

## How to report

`bin/handoff` keeps a plain-text log at `~/.dotfiles-handoff-report.md` on this
machine only. Add to it as you go:

```sh
bin/handoff note "starting runbook work-darwin.md"
bin/handoff capture "sw_vers"            # runs the command, appends its output
bin/handoff capture "script/test"
bin/handoff result "done" "nothing"      # or: result "stopped at step 5" "add my key: see handoff/keys/"
```

Then publish it:

```sh
bin/handoff key       # your public age key -> handoff/keys/<id>.age.pub (first run only)
bin/handoff report    # encrypts the log -> handoff/reports/<id>.sops.md
bin/handoff commit    # commits both, pushes from/<id>
```

The report is encrypted to the author's machines, so it may contain command output,
paths and usernames. The `RESULT:` and `NEEDS:` lines are repeated in the commit
message, which is public, so keep them free of anything internal.

`RESULT:` is `done` or `stopped at <step>`. `NEEDS:` is `nothing` or the one thing
the author must do before you can continue (typically "add my key as a recipient").

## What happens next

The author merges `from/<id>` into master and, if you asked for it, adds your key as
a secrets recipient. You will be told to run the runbook again. Everything in it is
idempotent, so the second run simply picks up what became possible, usually
`secrets` decrypting. Report the same way.

## Machine id

`bin/handoff id` prints it and creates it on first use: `<profile>-<os>-<6 random
characters>`, stored in `~/.dotfiles-machine-id`. It never contains a hostname.
