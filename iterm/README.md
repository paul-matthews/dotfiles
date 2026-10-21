# iTerm2

Tab colours, roles and SSH colouring work in any iTerm; see `CLAUDE.md`
("Tab colour system"). This file covers `wb`, the workbench.

## wb: a project's tabs in one tab group

A project is usually two to four tabs: the AI tool (claude at home, jetski at
work), a control tab for git and tests, sometimes a run tab. `wb` opens that
set in a named, coloured iTerm tab group and keeps tabs filed by project.

```sh
wb cosmic          # 🪐 Cosmic Clock: AI + control + run tabs, new group, this window
wb cosmic -w       # the same in a new window
wb                 # the project you are in (a worktree gets "· <branch>" in the name)
wb group           # file this window's ungrouped or misfiled tabs by project
wb add [project]   # this tab into its project's group (or the named one)
wb move [N]        # this tab's group to a new window, or window N from `wb ls`
wb focus cosmic    # drill in: expand it, collapse every other group
wb focus           # drill out: expand everything
wb ls              # groups and tabs in every window
wb doctor          # what is missing, if anything
```

Running `wb cosmic` again opens a second set; it never reuses a group. Tabs
join a group only when you run `wb`: a `cd` changes a tab's colour, not its
group. `wb group` leaves a tab alone if it is already in a group of its
project's name, so a second set and tabs added by hand stay where they are.

### Projects

Projects are the rows of `system/projects.yaml` (format in its header);
private ones go in `projects.private.sops.yaml` (`secrets pull` decrypts it,
edit `~/.config/dotfiles/projects.private.yaml`, `secrets push`, commit).
`template:` lists a project's tabs, default `[ai, control]`. `root:` is the
directory `wb <project>` opens; without it the first directory under `~/src/*`,
`~/src/*/*` or `~/*` that a glob matches is used. The group colour is the
average of the project's 8-colour palette; each tab keeps its own colour.

After editing the YAML, new shells rebuild the cache themselves; run
`projects-gen --committed` and commit `system/projects.gen` (the fallback for
machines without uv) alongside the YAML. `script/test` checks they agree.

### How it fits together

- `system/tabcolor.zsh` works out each tab's project at the prompt (only when
  the directory changes) and publishes it to iTerm as the user variables
  `wbGroup` and `wbColor`. That is how `wb group` knows a tab's project,
  including direnv overrides, without looking at directories itself.
- `iterm/wb.darwin.zsh` is the `wb` command: it resolves the project and
  passes names, colours and directories to
- `iterm/wb.py`, a `uv run` script that talks to iTerm's Python API: one
  connection per command, no retries.

New tabs start in the project directory. The AI tab gets `$DOTFILES_AI_TOOL`
typed into it (set in `system/ai-tabs*.zsh`, so it goes through the usual
wrappers and aliases); other tabs get ` role <name>`, so they read
`🪐 COS / control`.

### Setup (once per Mac)

1. iTerm 3.7.5 or later: **iTerm2 > Check for Updates**. 3.7.0 to 3.7.4 have
   tab groups but no API for them.
2. **iTerm2 > Settings > General > Magic > Enable Python API**.
3. Optional: **Allow all apps to connect** (same place, needs an admin
   password). Each `wb` command takes about 0.24s; with this on, about 0.1s,
   because it skips the AppleScript cookie request. Unattended work Macs need
   it (see `handoff/work-wb.md`).
4. `wb doctor`.

### Limits

- iTerm has no API to move a group between windows, so `wb move` moves the tabs
  and recreates the group (same name, colour and collapsed state).
- iTerm keeps a group's tabs together by reordering, so ⌘-number shortcuts can
  shift. A tab opened next to a grouped tab joins that group.
- A tab that has not shown a prompt since it started has no `wbGroup` yet;
  `wb group` reports it. SSH tabs clear theirs and stay ungrouped.
- iTerm restores groups after a restart by itself.
