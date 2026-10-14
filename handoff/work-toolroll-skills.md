# Runbook: check tool-roll skills against Jetski (work machines)

Read `handoff/README.md` first. Every step: command, what to expect, test.
Log as you go with `bin/handoff note` and `bin/handoff capture`.

**This runbook only looks; it installs nothing.** tool-roll
(`paul-matthews/tool-roll`) links a curated set of agent skills into
`~/.claude/skills`, `~/.agents/skills` and any dirs in `TOOL_ROLL_SKILL_DIRS`.
Before any of that happens on a work machine, the author needs to know which
of those skill names clash with Jetski's own commands or skills (`grill-me` is
the suspected one). Do **not** run `script/install`, `script/setup`,
`toolroll/install.sh` or `~/src/tool-roll/script/install` without `--dry-run`
while following this runbook.

## 1. Repo up to date, on your branch

Steps 1 and 2 of `handoff/work-darwin.md` (macOS) or the same steps of
`handoff/work-linux.md` (Linux), then:

```sh
bin/handoff note "runbook work-toolroll-skills.md, run $(date +%F)"
```

## 2. Get tool-roll

```sh
ls -d ~/src/tool-roll ~/tool-roll 2>/dev/null
```

If neither exists:

```sh
git clone --recurse-submodules git@github.com:paul-matthews/tool-roll.git ~/src/tool-roll
```

Expect: a clone with `vendor/mattpocock-skills` populated. If the clone fails
(access denied, network policy), stop: `bin/handoff result "stopped at step 2"
"tool-roll clone refused"`, then report.

```sh
bin/handoff capture "git -C ~/src/tool-roll log --oneline -1"
bin/handoff capture "sed 's/#.*//' ~/src/tool-roll/skills/enabled.txt | xargs -n1 basename"
```

The second command lists the skill names that would be installed. Step 4
checks each of them.

## 3. Where Jetski reads skills from

Find out, from Jetski's own documentation or configuration, every directory
Jetski loads user-level skills from, and whether it also reads
`~/.claude/skills` or `~/.agents/skills`. Do not guess: if you cannot
establish it, write `unknown` and say what you checked.

```sh
bin/handoff note "jetski skill dirs: <paths, or unknown + what was checked>"
bin/handoff capture "ls -la ~/.claude/skills ~/.agents/skills 2>&1"
```

Also list what is already in each Jetski skill dir you found:

```sh
bin/handoff capture "ls -la <jetski skill dir>"
```

## 4. Collision check

For **every** name from step 2, decide whether Jetski already has something
with that name: a built-in slash command, a built-in skill, or a skill already
present in one of the step 3 dirs. Pay particular attention to `grill-me`,
`grilling`, `handoff` (this repo's runbooks are also called handoffs), `pr`,
`implement`, `teach`, `retro` and `wizard`.

Record the result as a table, one row per name, in the report:

```sh
bin/handoff note "collisions:
| name | clashes? | with what (built-in command / built-in skill / existing skill at <dir>) |
| grill-me | ... | ... |
..."
```

Every name gets a row, including the ones that do not clash.

## 5. Dry run against Jetski's dir

Only if step 3 found a Jetski skill dir. One dir per run:

```sh
bin/handoff capture "TOOL_ROLL_SKILL_DIRS=<jetski skill dir> ~/src/tool-roll/script/install --dry-run"
```

Expect: `would: link <name> ...` lines and `!!` warnings for anything already
present under the same name. Nothing is changed. Do not add the dir to the
secrets file or `~/.localrc`; the author decides that from your report.

## 6. Report

```sh
bin/handoff result "done" "decide tool-roll skill collisions for jetski"
bin/handoff report
bin/handoff commit
```

Use `"done" "nothing"` if step 4 found no clashes at all. Keep paths and
Jetski command names out of the result line (it goes into the public commit
message); they belong in the encrypted report.

If you stopped early: `bin/handoff result "stopped at step N" "<what happened>"`,
then `report` and `commit` the same way.
