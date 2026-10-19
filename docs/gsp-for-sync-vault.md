# Brief: Adopting `gsp` in Obsidian Vault Synchronization (`sync_vault.sh`)

This brief specifies how to adopt `gsp` (`bin/git-safe-pull`) inside `/Users/pmatthews/Documents/Obsidian/pmatthews-work/scripts/sync_vault.sh`.

---

## 1. Purpose & Guarantees of `gsp`

`gsp` replaces fragile `git pull --rebase --autostash` sequences with safe, atomic synchronization:
- **Atomicity & Zero Code Loss**: Operations either complete 100% or cleanly roll back to `PRE_HEAD` restoring uncommitted/untracked stashes.
- **Backup Refs**: Pre-mutation state is saved at `refs/gsp/backup/<epoch>-<pid>/{head,stash}`.
- **In-Memory Conflict Resolution**: Only conflicts where every line matches declared rules in `.gsp-merge.toml` are resolved in memory (`git-meta-resolve`) into a single merge commit via `git commit-tree`. The worktree is never dirtied with markers.
- **Push by Default**: Pushes upstream after sync unless `--no-push` is set.
- **Non-Interactive & Hang-Free**: In headless environments (launchd), sets `GIT_TERMINAL_PROMPT=0`, `GIT_SSH_COMMAND="ssh -o BatchMode=yes -o ConnectTimeout=10"`, wraps network operations in a 60s watchdog, and exits `4` immediately on auth/credential lock instead of blocking.

---

## 2. Exit Code Contract & `sync_vault.sh` Handling

| Code | Meaning | `sync_vault.sh` Action |
|:---:|:---|:---|
| **0** | Clean success (synced & pushed) | Log `SUCCESS`. Clean up divergence markers (`_data/sync_divergence.json`). |
| **1** | Aborted / rolled back (worktree untouched) | If conflict: fall back to sidecar generation. Otherwise: log `WARN`/`ERROR` and alert if persistent. |
| **2** | Usage / config error | Log `ERROR`, trigger desktop notification loudly (`notify_user "Vault Sync Config Error"`), exit 1. |
| **3** | Synced locally, push failed | Log `WARN`. Local merge was parked at `refs/gsp/unpushed/<id>` and rolled back to `PRE_HEAD`. Retry automatically on next 5-min cycle. |
| **4** | SSH / signing key locked (no TTY) | Log `INFO`/`WARN`. Throttled notification (at most hourly via `/tmp/vault-sync-auth.notified`, mirroring divergence notifier). |

### Identifying Conflicted Files on Exit 1
When `gsp` exits 1 due to unresolvable conflicts, retrieve the exact conflict manifest in-memory without altering worktree state:
```bash
PLAN_JSON=$(git-meta-resolve plan --ours HEAD --theirs origin/main --json 2>/dev/null || echo "{}")
# Extract unresolvable files:
CONFLICT_FILES=$(python3 -c '
import sys, json
data = json.loads(sys.argv[1])
print("\n".join(f["path"] for f in data.get("files", []) if not f.get("resolvable")))
' "$PLAN_JSON")
```
If `CONFLICT_FILES` is non-empty, feed them into the existing sidecar note extractor; otherwise treat as general abort.

---

## 3. Proposed `sync_vault.sh` Flow (Diff Sketch)

Keep network reachability checks, `/tmp/vault-sync.lock`, and dirty note commits via `vault_save.py`. Replace lines ~230–288 with `gsp`:

```diff
- # 6. Pull latest canonical updates using linear rebase with autostash
- log "INFO" "Pulling latest remote updates (linear rebase with autostash)..."
- if ! PULL_OUTPUT=$(git pull --rebase --autostash origin main 2>&1); then
-     # [100+ lines of rebase abort, manual conflict diff, and git checkout --theirs]
- fi
- # 7. Push local commits to remote
- if ! git push origin main 2>&1; then ... fi

+ # 6. Synchronize and push via gsp (atomic pull + in-memory auto-resolve + push)
+ log "INFO" "Synchronizing vault with origin/main via gsp..."
+ GSP_OUT=""
+ set +e
+ GSP_OUT=$(gsp --auto-resolve 2>&1)
+ GSP_EXIT=$?
+ set -e
+
+ case "$GSP_EXIT" in
+     0)
+         log "SUCCESS" "Vault successfully synced and pushed: ${GSP_OUT}"
+         rm -f "${VAULT_DIR}/_data/sync_divergence.json" /tmp/vault-sync-divergence.notified 2>/dev/null || true
+         ;;
+     1)
+         # Check if failure was due to unresolvable merge conflicts
+         CONFLICT_FILES=$(python3 -c '
+ import sys, json
+ try:
+     data = json.loads(sys.argv[1])
+     print("\n".join(f["path"] for f in data.get("files", []) if not f.get("resolvable")))
+ except Exception: pass' "$(git-meta-resolve plan --ours HEAD --theirs origin/main --json 2>/dev/null || echo '{}')")
+         if [ -n "${CONFLICT_FILES}" ]; then
+             log "WARN" "Non-trivial conflicts detected; extracting sidecars..."
+             # Run existing sidecar extraction logic on $CONFLICT_FILES, commit sidecars, then retry gsp
+         else
+             log "ERROR" "gsp aborted or rolled back: ${GSP_OUT}"
+             exit 1
+         fi
+         ;;
+     2)
+         log "ERROR" "gsp configuration error: ${GSP_OUT}"
+         notify_user "Vault Sync Config Error" "Check .gsp-merge.toml syntax."
+         exit 1
+         ;;
+     3)
+         log "WARN" "Synced locally but push failed (network or remote rejected). Will retry next cycle: ${GSP_OUT}"
+         exit 0
+         ;;
+     4)
+         log "WARN" "SSH key locked in background session: ${GSP_OUT}"
+         LAST_AUTH_NOTIFY="/tmp/vault-sync-auth.notified"
+         if [ ! -f "${LAST_AUTH_NOTIFY}" ] || [ -n "$(find "${LAST_AUTH_NOTIFY}" -mmin +60 2>/dev/null)" ]; then
+             notify_user "Vault Sync Paused" "SSH credentials locked. Run ssh-add to resume background push."
+             touch "${LAST_AUTH_NOTIFY}"
+         fi
+         exit 0
+         ;;
+ esac
```

### Mutex & Lock Composition
- `/tmp/vault-sync.lock`: Script-level mutex guarding the entire 5-minute sync lifecycle, preventing overlapping launchd runs.
- `$GIT_DIR/gsp.lock`: Repository-level lock managed by `gsp` preventing concurrent git mutations (e.g. manual CLI `gsp` vs background sync). If held, `gsp` safely exits 1.
- **Early-Divergence Check**: `vault_save.py` commits all note edits beforehand. Any remaining uncommitted edits are stashed by `gsp` prior to pull. If uncommitted edits collide upon re-application, `gsp` rolls back to `PRE_HEAD` without data loss. The early-divergence check (`_data/sync_divergence.json`) can be safely retained as an informational guard, or retired once `gsp` handles collisions.

---

## 4. Vault `.gsp-merge.toml` Specification

Place this configuration at `/Users/pmatthews/Documents/Obsidian/pmatthews-work/.gsp-merge.toml`:

```toml
version = 1
auto = true
verify_skip = ["**/*.md"]

# 1. Frontmatter modified timestamp + coupled environment machine
[[rule]]
name = "last-modified"
files = ["**/*.md"]
line = '^\s*last_modified:\s*"(?P<value>[^"]+)"\s*$'
type = "timestamp"
strategy = "latest"
frontmatter_only = true
coupled = ['^\s*last_modified_env:\s*"(?P<value>[^"]+)"\s*$']

# 2. Envoy CLI Go source version constants
[[rule]]
name = "envoy-version-code"
files = ["scripts/go_entities/version.go"]
line = '^\s*EnvoyVersionCode\s*=\s*(?P<value>\d+)\s*$'
type = "counter"
strategy = "max"

[[rule]]
name = "envoy-version"
files = ["scripts/go_entities/version.go"]
line = '^\s*EnvoyVersion\s*=\s*"(?P<value>[0-9A-Za-z.+-]+)"\s*$'
type = "semver"
strategy = "max"

# 3. Envoy standalone version code file
[[rule]]
name = "version-code"
files = ["scripts/version_code"]
line = '^(?P<value>\d+)$'
type = "counter"
strategy = "max"
```

### Config Validation Note
Validated with `git-meta-resolve check-config .gsp-merge.toml` → `ok: 4 rules, 0 groups`. The Envoy rules match only `scripts/go_entities/version.go`, so no other `version.go` in the vault is ever auto-resolved. `auto = true` applies to every rule in this file, the Envoy version rules included.

---

## 5. Interaction with `update_last_modified.py`

- `gsp` constructs the auto-resolved merge using low-level plumbing (`git commit-tree`) in memory and performs a fast-forward (`git merge --ff-only`).
- No pre-commit hooks are invoked, no files are staged, and notes are not re-stamped with a new timestamp. This completely eliminates timestamp ping-pong loops between sync instances.
- The `--resolve-conflicts` branch in `update_last_modified.py` should be kept as a fallback for non-gsp manual rebases/merges.

---

## 6. Loop Safety & Convergence

1. **No Re-resolution**: Once an auto-resolved merge commit is pushed, remote peers fast-forward. The merge-base moves past the merge, preventing redundant resolutions.
2. **Concurrent Push Convergence**: If two machines resolve concurrently and push:
   - Winner fast-forwards upstream.
   - Loser receives a non-fast-forward rejection. `gsp` catches this, parks the unpushed commit at `refs/gsp/unpushed/<id>`, resets to `PRE_HEAD`, re-fetches the winner's commit, and re-evaluates the merge cleanly (up to 3 retries) without force-pushing.

---

## 7. Rollout Checklist

1. **Verify launchd PATH**: `~/Library/LaunchAgents/com.google.pmatthews.vault-sync.plist` specifies `PATH` under `EnvironmentVariables`. Ensure `/Users/pmatthews/src/dotfiles/bin` is in `PATH`, or symlink `gsp` and `git-meta-resolve` to `/usr/local/bin` or `/opt/homebrew/bin`.
2. **Commit Configuration**: Write and commit `.gsp-merge.toml` at the root of `pmatthews-work`.
3. **Dry-Run Check**: Run `gsp -n` in the vault root to verify configuration parsing and upstream connectivity.
4. **Collision Simulation** (Throwaway clone):
   ```bash
   git clone --bare /Users/pmatthews/Documents/Obsidian/pmatthews-work /tmp/vault-test-remote.git
   git clone /tmp/vault-test-remote.git /tmp/c1 && git clone /tmp/vault-test-remote.git /tmp/c2
   # Edit note frontmatter timestamp in c1, commit & push
   # Edit same note frontmatter with earlier timestamp in c2, commit
   (cd /tmp/c2 && gsp --auto-resolve) # Verify auto-resolved merge commit created & pushed
   rm -rf /tmp/vault-test-remote.git /tmp/c1 /tmp/c2
   ```
5. **Deploy Script & Monitor**: Apply changes to `scripts/sync_vault.sh`, then monitor logs:
   ```bash
   tail -f ~/Library/Logs/vault-sync.log
   ```
6. **Rollback Plan**: If unexpected failures occur, revert `sync_vault.sh` to git commit hash prior to change.

---

## 8. Recovery & Backup Refs

If `gsp` rolls back, it outputs a one-line recovery command:
```bash
git reset --hard refs/gsp/backup/<id>/head && git stash apply refs/gsp/backup/<id>/stash
```
- Pre-mutation refs: `refs/gsp/backup/<epoch>-<pid>/head` and `.../stash` (auto-pruned after 30 days).
- Failed auto-resolutions: parked at `refs/gsp/failed/<id>`.
- Unpushed local merges: parked at `refs/gsp/unpushed/<id>`.
