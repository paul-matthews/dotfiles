# gsp auto-resolve: deferred items

Known, low-severity issues deliberately not fixed. Pick one up only if it bites.

## Verify cache ignores gitignored files (LOW)
`bin/gsp-verify` keys its cache on the worktree tree built with `git add -A` in a
temp index, which honours `.gitignore`. If a repo's `script/test` depends on an
ignored file (`.env`, local config), editing that file won't invalidate the cache
and a test run could be skipped for up to `GSP_VERIFY_TTL` (12h).
- Workaround today: `gsp --verify` (forces a run) or `GSP_VERIFY_TTL=0`.
- Possible fix: per-repo `verify_inputs = [...]` globs hashed into the key.
- Rejected fix: `HEAD` + `status --porcelain` as key — misses content changes to
  an already-modified file (more stale hits, not fewer).
- Side note: each run may write loose blobs for modified files; `git gc` prunes them.

## `git-meta-resolve plan` latency ~200ms (LOW)
Only paid on the divergent path (never on up-to-date / ff). Likely Python startup +
several git subprocesses. Profile with `python3 -X importtime` and count spawns
if it ever matters.

## shellcheck not run
Not installed on this machine. Run `shellcheck -S warning bin/git-safe-pull
bin/gsp-verify script/test-gsp` once available.
