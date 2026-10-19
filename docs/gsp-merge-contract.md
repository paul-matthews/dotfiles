# gsp auto-merge: contract (Phase 0)

This is the single source of truth that every workstream builds against. It covers
the rule file, the resolver's module boundaries and CLI, its JSON output, the
verify helper, and how gsp behaves. Workstreams must not change the interfaces
here. If one has to change, ask the lead.

Background: `gsp` (`bin/git-safe-pull`) rolls back on any conflict. Many
conflicts are trivial: two machines bumped the same version counter, or
an Obsidian note's `last_modified` timestamp. This feature resolves **only**
conflicts in which every conflicting line matches a declared rule. It does so
in memory, before anything in the worktree or on the branch changes, and the
pull lands as a single merge commit.

---

## 1. Layout (one owner per file)

| Path | Owner | Notes |
|---|---|---|
| `bin/git-meta-resolve` | WS1b | Python entry point. Puts `<dotfiles>/git` on `sys.path` (via `os.path.realpath(__file__)`) and calls `gsp_merge.cli.main()` |
| `git/gsp_merge/__init__.py` | lead | empty |
| `git/gsp_merge/strategies.py` | WS2 | pure functions, no I/O, no git |
| `git/gsp_merge/config.py` | WS3 | TOML loading/validation, path matching |
| `git/gsp_merge/hunks.py` | WS1 | zdiff3 parsing + whitelist + file resolution (pure, no git) |
| `git/gsp_merge/cli.py`, `git/gsp_merge/gitops.py` | WS1b | git plumbing + argparse + JSON output |
| `git/gsp_merge/selftest.py` | WS1b | runs `strategies.SELF_TESTS` + every fixture |
| `git/gsp_merge/fixtures/<case>/` | lead (WS1/WS6 may ADD cases) | see §6 |
| `git/gsp-merge.toml.example` | WS3 | commented template |
| `bin/gsp-verify` | WS5 | bash |
| `bin/git-safe-pull`, `functions/_git-safe-pull` | WS4 | bash / zsh completion |
| `script/test-gsp` | WS6 | bash scenario harness, **not** called by gsp |
| `CLAUDE.md`, `CHEATSHEET.md`, `README.md` | WS7 | docs |
| `docs/gsp-for-sync-vault.md` | WS8 | agent hand-off |

Language rules:
- **Python 3.13 stdlib only** (`tomllib`, `re`, `json`, `dataclasses`, `pathlib`, `subprocess`, `datetime`). Keep imports lazy where it matters: startup must stay under 50ms.
- Bash scripts: `#!/usr/bin/env bash`, `set -eo pipefail`, portable between macOS (BSD userland, bash 3.2 is **not** guaranteed; assume Homebrew bash 5 is available via `env bash`) and Linux.
- Never use `git add -A`, `reset --hard` or `checkout` on the user's real index/worktree except where §8 says so.

---

## 2. Rule file: `.gsp-merge.toml` (committed at the repo root)

The rules are always read from the **working tree at PRE_HEAD** (the local
version), never from the incoming side. A pull therefore can't change the rules
that judge it.

```toml
version = 1                 # required, must be 1
auto = false                # optional. true = this repo may auto-apply without a TTY prompt
verify_skip = []            # optional globs. If EVERY path changed by the pull matches, script/test is skipped

[[rule]]
name = "envoy-version-code" # required, unique across rules+groups, [a-z0-9-]+
files = ["**/version.go"]   # required, non-empty list of globs (PurePosixPath.full_match semantics)
line = '^\s*EnvoyVersionCode\s*=\s*(?P<value>\d+)\s*$'   # required, Python re, exactly one named group "value"
type = "counter"            # required: counter | semver | timestamp
strategy = "max"            # optional, default per type (below)
frontmatter_only = false    # optional. true = only lines inside the leading YAML frontmatter (see §4.4)
coupled = []                # timestamp only: list of regexes (each with a "value" group) whose values follow the winner

[[group]]
name = "semver"
files = ["version.properties"]
type = "semver_split"       # only type allowed for groups
strategy = "max"            # optional, only value
major = '^version\.major=(?P<value>\d+)$'
minor = '^version\.minor=(?P<value>\d+)$'
patch = '^version\.patch=(?P<value>\d+)$'
frontmatter_only = false
```

Strategies:

| type | strategies (first is default) | meaning |
|---|---|---|
| `counter` | `max`, `max_unique` | non-negative decimal integers. `max` = max(ours, theirs). `max_unique` = max(ours, theirs) + 1 |
| `semver` | `max` | SemVer 2.0.0 precedence (`MAJOR.MINOR.PATCH[-pre][+build]`); build metadata ignored for ordering; on equal precedence keep ours |
| `timestamp` | `latest` | ISO-8601 with offset (`datetime.fromisoformat`); naive timestamps are an error. Later instant wins |
| `semver_split` | `max` | (major, minor, patch) compared as an integer tuple |

Validation (`config.ConfigError`, which makes the CLI exit 2): unknown keys; missing
required keys; bad regex; regex without exactly one `value` group; unknown
type or strategy; duplicate names; `coupled` on a non-timestamp rule; empty
`files`; `version != 1`.

---

## 3. Python module interfaces

### 3.1 `strategies.py` (WS2)

```python
class StrategyError(ValueError): ...          # unparsable value → hunk is unresolvable

DEFAULTS = {"counter": "max", "semver": "max", "timestamp": "latest", "semver_split": "max"}
VALID = {"counter": ("max", "max_unique"), "semver": ("max",), "timestamp": ("latest",), "semver_split": ("max",)}

def resolve_counter(base: str | None, ours: str, theirs: str, strategy: str = "max") -> str
def resolve_semver(base: str | None, ours: str, theirs: str, strategy: str = "max") -> str
def resolve_semver_split(base: tuple[str,str,str] | None, ours: tuple[str,str,str],
                         theirs: tuple[str,str,str], strategy: str = "max") -> tuple[str,str,str]
def pick_timestamp_winner(ours: str, theirs: str, ours_coupled: list[str], theirs_coupled: list[str],
                          strategy: str = "latest") -> str      # returns "ours" | "theirs"
    # tie (equal instants): the side whose coupled-values list is lexically smaller wins; full tie → "ours"

SELF_TESTS: list[tuple[str, callable]]   # (name, zero-arg fn that raises AssertionError on failure)
```
Returned values are strings formatted the way the **winning input** formatted
them. Never reformat: `"007"` stays `"007"`, and a `max_unique` result keeps the
width of the max input when it fits, otherwise it grows naturally.

### 3.2 `config.py` (WS3)

```python
class ConfigError(Exception): ...

@dataclass(frozen=True)
class Rule:
    name: str; files: tuple[str, ...]; line: re.Pattern; type: str; strategy: str
    frontmatter_only: bool; coupled: tuple[re.Pattern, ...]

@dataclass(frozen=True)
class Group:
    name: str; files: tuple[str, ...]; type: str; strategy: str
    major: re.Pattern; minor: re.Pattern; patch: re.Pattern; frontmatter_only: bool

@dataclass(frozen=True)
class Config:
    auto: bool; verify_skip: tuple[str, ...]; rules: tuple[Rule, ...]; groups: tuple[Group, ...]
    def for_path(self, path: str) -> tuple[tuple[Rule, ...], tuple[Group, ...]]   # rules/groups whose files match

CONFIG_NAME = ".gsp-merge.toml"
def path_matches(path: str, globs) -> bool        # PurePosixPath(path).full_match(g) for any g
def parse_config(text: str, source: str = "<string>") -> Config      # raises ConfigError
def load_config(repo_root: str) -> Config | None  # None if file absent; raises ConfigError if invalid
def template_path() -> str                        # <dotfiles>/git/gsp-merge.toml.example
```

### 3.3 `hunks.py` (WS1)

```python
MARKER_SIZE = 32
OURS_LABEL, BASE_LABEL, THEIRS_LABEL = "ours", "base", "theirs"

@dataclass
class Common:   lines: list[str]                                   # lines WITHOUT trailing "\n"
@dataclass
class Conflict: ours: list[str]; base: list[str]; theirs: list[str]

class ParseError(ValueError): ...
def parse_zdiff3(text: str, marker_size: int = MARKER_SIZE) -> list[Common | Conflict]
    # input: stdout of `git merge-file -p --zdiff3 --marker-size=32 -L ours -L base -L theirs O B T`
    # A marker line is exactly marker_size of the char, then " <label>" (or nothing for "=").
    # Any malformed or nested structure → ParseError.

@dataclass
class LineResolution: rule: str; base: str; ours: str; theirs: str; result: str      # values, not whole lines
@dataclass
class FileResult:
    path: str; resolvable: bool; reason: str | None
    lines: list[LineResolution]           # one per resolved line, in file order
    content: str | None                   # full resolved file text when resolvable

def resolve_file(path: str, merged: str, base_text: str, ours_text: str, theirs_text: str,
                 rules, groups) -> FileResult
    # merged = merge-file output. rules/groups = Config.for_path(path).
    # Must never raise for bad input: return resolvable=False with a reason.
```

---

## 4. The whitelist rule (hunks.resolve_file)

A file is resolvable only if **all** of the following hold. Otherwise
`resolvable=False`, with a human-readable `reason` that names the first failing hunk
(its 1-based ours line number) and why.

1. `parse_zdiff3` succeeds and there is at least one `Conflict`.
2. For every Conflict: `len(ours) == len(base) == len(theirs)` and the count is above 0. Line *i* in each section forms an **aligned triple**.
3. Each aligned triple with `ours == theirs` (byte-equal) passes through as `ours`.
4. Every other aligned triple must have **all three lines** fully matched (`re.fullmatch`, line without its `\n`; a trailing `\r` is stripped before matching and restored after) by **the same** rule line regex, or the same group component regex, or the same coupled regex of the same rule. The text outside the `value` span must be byte-identical across the three lines. Only the value may differ.
   If more than one rule or component matches, the file is unresolvable ("ambiguous rules").
5. Resolution:
   - `counter` / `semver` rule line: `result = resolve_*(base_v, ours_v, theirs_v, strategy)`.
   - `timestamp` rule (primary line or any coupled line in a hunk): the winner is decided **per file** from the full `ours_text` / `theirs_text`. The primary line (and each coupled line) must occur **exactly once** in each (within the frontmatter if `frontmatter_only`), otherwise the file is unresolvable. `pick_timestamp_winner(ours_v, theirs_v, ours_coupled_vs, theirs_coupled_vs)` decides it. Every primary or coupled triple then takes the winner's value.
   - `semver_split` group component: tuples are read **per file** from the full base/ours/theirs texts, with each component occurring exactly once (base may be missing → `None`). `resolve_semver_split` decides it. Every component triple takes the matching element of the winner tuple.
   - `StrategyError` → unresolvable.
6. The resolved line is `prefix + result + suffix`, using ours's text outside the value span (which is identical by rule 4).
7. Post-checks on the assembled `content`: no line starts with 7 or more of `<`, `|`, `=`, `>` followed by a space or end of line **unless** that exact line also appears in `ours_text` or `theirs_text`. Every resolved line must still `fullmatch` its regex. The line count must equal the number of lines in `merged` minus the marker and duplicate-section lines.
8. `frontmatter_only`: a file has frontmatter iff its first line is exactly `---`. The frontmatter runs up to the next line that is exactly `---`. A `frontmatter_only` regex only counts as matching when the line lies inside the frontmatter of **both** ours and theirs. Positions come from the line offsets that the Common/Conflict segments imply.

File-level trailing newline: preserve whether `merged` ends with `\n`.

---

## 5. CLI: `git-meta-resolve` (WS1b wires it; WS3 provides config bits)

Run from anywhere inside a work tree. Exit codes everywhere: **0** ok / resolvable / clean,
**1** not resolvable, **2** usage, config or git error.

```
git-meta-resolve plan --ours <rev> --theirs <rev> [--json] [--config <path>]
git-meta-resolve config [--json]            # prints {"present", "auto", "verify_skip"} for the repo at cwd
git-meta-resolve check-config [<path>]      # validate; prints "ok: N rules, M groups" or errors (exit 2)
git-meta-resolve init [--force]             # copy template to ./.gsp-merge.toml (repo root); refuse if exists
git-meta-resolve self-test                  # strategies + fixtures; prints summary; exit 0/1; must take < 1s
git-meta-resolve driver <O> <A> <B> <P>     # git merge-driver mode: writes result to <A>; exit 0 if resolved
```
`--self-test`, `--check-config`, `--init` are accepted as aliases.

### `plan` algorithm (gitops.py)
1. `git merge-tree --write-tree -z <ours> <theirs>`: exit 0 means clean. Output `{"clean": true, "resolvable": true, "tree": <oid>, ...}` and exit 0. Exit 1 means conflicts. Anything else exits 2.
   Parse with `-z`: `<tree>\0` then repeated `<mode> <oid> <stage>\t<path>\0`, terminated by an empty `\0`; after that come informational messages (ignore them).
2. Group by path. A path is a candidate only if it has stages 1, 2 and 3, all modes are equal and are `100644` or `100755`. Otherwise it is unresolvable, with a reason ("modify/delete", "add/add", "mode change", "symlink"…).
3. Fetch all stage blobs through **one** `git cat-file --batch` process. Any NUL byte in a blob means "binary", which is unresolvable.
4. Per candidate: write the three blobs to a temp dir and run `git merge-file -p --zdiff3 --marker-size=32 -L ours -L base -L theirs O B T` (exit 0 or more is fine; negative means error). Then `hunks.resolve_file(...)`.
5. If every file is resolvable: write the resolved blobs (`git hash-object -w --stdin-paths`, one process), then build the tree in a **temporary index**: `GIT_INDEX_FILE=<tmp> git read-tree <merge-tree-oid>`, `git update-index --index-info` (one process, `<mode> <blob>\t<path>` lines, which also clears stages), then `git write-tree`. Never touch the real index.
6. The config comes from `<toplevel>/.gsp-merge.toml` in the worktree (or `--config`). If it is absent, every conflicted file is unresolvable with the reason "no .gsp-merge.toml".

### `plan --json` output (stdout; human messages to stderr only)
```json
{
  "version": 1,
  "clean": false,
  "resolvable": true,
  "tree": "<oid or null>",
  "auto": false,
  "verify_skip": [],
  "files": [
    {"path": "cmd/envoy/version.go", "resolvable": true, "reason": null,
     "lines": [{"rule": "envoy-version-code", "base": "115", "ours": "117", "theirs": "116", "result": "117"}]}
  ],
  "summary": ["cmd/envoy/version.go: envoy-version-code 117|116→117"]
}
```
`summary` holds one string per LineResolution, in the format `<path>: <rule> <ours>|<theirs>→<result>`.
`tree` is non-null iff `resolvable` (or `clean`). Without `--json`, print an aligned table of the
same information to stdout.

---

## 6. Fixtures: `git/gsp_merge/fixtures/<case>/`

| file | meaning |
|---|---|
| `path` | repo-relative path used for glob matching (one line) |
| `rules.toml` | full `.gsp-merge.toml` |
| `base`, `ours`, `theirs` | the three versions |
| `expected` | resolved content (present iff it should resolve) |
| `unresolvable` | substring expected in `reason` (present iff it must NOT resolve) |

`self-test` runs `git merge-file` on each fixture, then `resolve_file`, and compares.

---

## 7. `bin/gsp-verify` (WS5)

```
gsp-verify [--force] [--changed-from <rev>]      # run inside the repo; exit 0 pass/skip/cached, 1 fail
```
- No executable `<toplevel>/script/test` → exit 0 silently.
- `GSP_NO_VERIFY=1` → print `⚠️  GSP_NO_VERIFY=1: skipping script/test.` to stderr, exit 0.
- `--changed-from <rev>`: if `git-meta-resolve config --json` returns a non-empty `verify_skip` and **every** path in `git diff --name-only <rev>` (the worktree versus rev) matches one of those globs, print `⏭️  script/test skipped: only verify_skip paths changed.` and exit 0. Match with the same `full_match` semantics: pipe the paths into a one-line `python3 -c` or a `git-meta-resolve` helper, never into bash globbing.
- Cache: `$GIT_DIR/gsp/verified`, lines of `<key> <epoch>`. The key is the sha256 of
  `tree=<worktree tree>\nhost=<hostname>\nprofile=<$DOTFILES_PROFILE>\n`. The worktree tree is computed with a temp index:
  `cp $GIT_DIR/index $tmp; GIT_INDEX_FILE=$tmp git add -A; GIT_INDEX_FILE=$tmp git write-tree`, so it includes script/test itself and any uncommitted edits.
  A hit within `GSP_VERIFY_TTL` seconds (default 43200) prints `✅ script/test passed (cached).` and exits 0, unless `--force`.
  Keep at most 50 lines (drop the oldest).
- Otherwise print `🧪 Verifying with script/test...`. On a pass, print `✅ script/test passed.`, store the key, and exit 0. On a failure, print the
  lines matching `✗|FAIL|^      ` to stderr and exit 1. (This is today's `run_verify` behaviour.)

---

## 8. gsp behaviour (WS4)

New flags: `-a|--auto-resolve`, `--no-resolve`, `--no-push`, `--verify` (passes `--force` to gsp-verify),
`--no-verify` (same as `GSP_NO_VERIFY=1`). Env: `GSP_AUTO_RESOLVE=1`, `GSP_NO_PUSH=1`. Existing `-v`, `-n`, `-h` are kept.
Helpers are found next to the script: `GSP_BIN="$(cd "$(dirname "$(realpath "$0")")" && pwd)"`.

**Exit codes:** 0 synced (pushed if anything was ahead); 1 aborted or rolled back, nothing changed;
2 usage/config error; 3 synced locally but the push failed; 4 credentials locked with no TTY, nothing changed.

**Interactive?** `[[ -t 0 && -t 1 ]]`. When not interactive: `export GIT_TERMINAL_PROMPT=0` and
`GIT_SSH_COMMAND="${GIT_SSH_COMMAND:-ssh} -o BatchMode=yes -o ConnectTimeout=10"`. All network git calls
(fetch, push) run under a 60s watchdog (bash: background + kill; no dependency on `timeout`).

Order of operations:
1. Pre-flight checks as today. Take the lock `$GIT_DIR/gsp.lock` (mkdir + pid file; a dead pid means stale). If it is held, exit 1 with "another gsp is running".
2. Stash as today. Create **backup refs** before any mutation: `refs/gsp/backup/<epoch>-<pid>/head` → PRE_HEAD and, if stashed, `.../stash` → STASH_SHA. Prune `refs/gsp/{backup,failed,unpushed}/<epoch>-*` older than 30 days.
3. Fetch. If not interactive and the fetch output matches `Permission denied|publickey|passphrase|Host key verification|could not read Username`, roll back and **exit 4** with the hint `unlock your key: ssh-add`.
4. Already up to date / dry-run as today, but verify through `gsp-verify` (cache-aware).
5. **Signing probe** (only if `LOCAL_AHEAD_COUNT > 0`): if `git config commit.gpgsign` is `true` and `gpg.format` is `ssh`, expand `user.signingkey` (`~`; it may be `key::<literal>` (literal → OK if it appears in `ssh-add -L`) or a path to `.pub` or a private key). The probe passes if the public key's base64 field appears in `ssh-add -L`, **or** the private key opens without a passphrase (`ssh-keygen -y -P "" -f <priv> >/dev/null`). Failure while not interactive → roll back, **exit 4**. While interactive → continue (ssh may prompt).
6. If `LOCAL_AHEAD_COUNT == 0` → ff-only as today.
   Otherwise, unless `--no-resolve`: run `git merge-tree --write-tree HEAD UPSTREAM` (just the exit code).
   - Clean (0) → rebase as today.
   - Conflict (1) → `git-meta-resolve plan --ours HEAD --theirs $UPSTREAM_HASH --json`.
     Not resolvable → print the file reasons and exit 1 via the abort path, **without** rebasing or resetting (nothing was touched; restore the stash).
     Resolvable → consent = `--auto-resolve` | `GSP_AUTO_RESOLVE=1` | plan `.auto`; else interactive Y/n showing `summary`; non-interactive without consent → abort exit 1.
     `--dry-run` → print the preview and stop.
     Build the commit: `git -c rerere.enabled=false commit-tree <tree> -p HEAD -p $UPSTREAM_HASH -F <msg>`, where msg =
     `Merge <UPSTREAM> into <branch> (gsp auto-resolved)\n\n` + one `Gsp-Auto-Resolved: <summary item>` trailer per line.
     Then `git merge --ff-only <commit>`, set `AUTO_RESOLVED=true`, and append one JSON line per resolution to `$GIT_DIR/gsp/log`.
     Parse the JSON in bash with `python3 -c` one-liners (no jq dependency).
7. Re-apply the stash as today (conflict → rollback).
8. Secrets sync as today. Verify: `gsp-verify --changed-from $PRE_HEAD` (+`--force` if `--verify`). On failure: if `AUTO_RESOLVED`, save the merge commit at `refs/gsp/failed/<epoch>-<pid>`, then roll back.
9. **Push** unless `--no-push`/`GSP_NO_PUSH=1`, and only if `git rev-list --count UPSTREAM..HEAD > 0`:
   `git push <remote> HEAD:<remote_branch>` under the watchdog.
   - A non-fast-forward rejection (the remote moved): if `AUTO_RESOLVED`, park the commit at `refs/gsp/unpushed/<id>`. Reset to PRE_HEAD and re-apply the stash (the normal rollback without its exit), then loop back to step 3. At most 3 attempts in total; after that, behave like any other push failure.
   - Any other failure: if `AUTO_RESOLVED`, park the commit at `refs/gsp/unpushed/<id>`, roll back to PRE_HEAD + stash, print the parked ref, and **exit 3**. If it was a clean rebase, keep the state, warn, and **exit 3**.
   - `--no-push` with `AUTO_RESOLVED`: warn that the next pull may stack on this unpushed merge.
10. Release the lock, remove the backup refs on success (keep them on any failure), and exit 0.

`rollback()` must keep its current behaviour and additionally print the recovery command
`git reset --hard refs/gsp/backup/<id>/head && git stash apply refs/gsp/backup/<id>/stash`, then release the lock.
It must accept an exit code (default 1).

---

## 9. Definition of done (all workstreams)

- `bin/git-meta-resolve self-test` passes in under 1s.
- `script/test-gsp` passes (all scenarios in the plan).
- `script/test` still passes (the lead adds the single self-test check).
- No new runtime dependencies beyond git ≥ 2.40, python3 ≥ 3.11, bash, and ssh tools.
