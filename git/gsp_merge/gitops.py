"""Git operations and plan algorithm for gsp-merge."""

from __future__ import annotations

import os
import subprocess
import tempfile
from dataclasses import asdict, dataclass
from typing import Any

from gsp_merge.config import Config, ConfigError, load_config, parse_config
from gsp_merge.hunks import FileResult, LineResolution, resolve_file


class GitError(Exception):
    """Raised when a git command fails unexpectedly."""


@dataclass(frozen=True)
class PlanResult:
    version: int
    clean: bool
    resolvable: bool
    tree: str | None
    auto: bool
    verify_skip: list[str]
    files: list[dict[str, Any]]
    summary: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "clean": self.clean,
            "resolvable": self.resolvable,
            "tree": self.tree,
            "auto": self.auto,
            "verify_skip": self.verify_skip,
            "files": self.files,
            "summary": self.summary,
        }


def get_repo_root(cwd: str | None = None) -> str:
    """Find the top-level directory of the git working tree."""
    proc = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        cwd=cwd,
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        raise GitError(proc.stderr.strip() or "not a git repository")
    return proc.stdout.strip()


def load_repo_config(repo_root: str, config_path: str | None = None) -> Config | None:
    """Load configuration from repo root or an explicit path."""
    if config_path is not None:
        if not os.path.isabs(config_path):
            config_path = os.path.abspath(config_path)
        if not os.path.exists(config_path):
            raise ConfigError(f"config file not found: {config_path}")
        with open(config_path, "r", encoding="utf-8") as f:
            return parse_config(f.read(), source=config_path)
    return load_config(repo_root)


def cat_blobs(repo_root: str, oids: set[str]) -> dict[str, bytes]:
    """Fetch objects by OID in a single git cat-file --batch process."""
    if not oids:
        return {}

    proc = subprocess.Popen(
        ["git", "cat-file", "--batch"],
        cwd=repo_root,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
    )
    assert proc.stdin is not None
    assert proc.stdout is not None

    blobs: dict[str, bytes] = {}
    input_data = "".join(f"{oid}\n" for oid in oids).encode("ascii")
    proc.stdin.write(input_data)
    proc.stdin.close()

    for _ in range(len(oids)):
        header = proc.stdout.readline().decode("utf-8", errors="replace")
        if not header:
            break
        parts = header.strip().split()
        if len(parts) >= 2 and parts[1] == "missing":
            proc.stdout.close()
            proc.wait()
            raise GitError(f"missing git object: {parts[0]}")
        if len(parts) < 3:
            proc.stdout.close()
            proc.wait()
            raise GitError(f"invalid cat-file header: {header.strip()}")
        oid, obj_type, size_str = parts[0], parts[1], parts[2]
        size = int(size_str)
        data = proc.stdout.read(size)
        proc.stdout.read(1)  # trailing newline
        blobs[oid] = data

    proc.stdout.close()
    proc.wait()
    if proc.returncode != 0:
        raise GitError(f"git cat-file --batch exited with {proc.returncode}")

    return blobs


def plan(
    ours: str,
    theirs: str,
    config_path: str | None = None,
    cwd: str | None = None,
) -> PlanResult:
    """Execute the merge-tree planning algorithm according to contract §5."""
    repo_root = get_repo_root(cwd=cwd)
    cfg = load_repo_config(repo_root, config_path=config_path)

    proc = subprocess.run(
        ["git", "merge-tree", "--write-tree", "-z", ours, theirs],
        cwd=repo_root,
        capture_output=True,
    )

    if proc.returncode not in (0, 1):
        err_msg = proc.stderr.decode("utf-8", errors="replace").strip()
        raise GitError(f"git merge-tree failed (exit {proc.returncode}): {err_msg}")

    auto = cfg.auto if cfg is not None else False
    verify_skip = list(cfg.verify_skip) if cfg is not None else []

    # Clean merge
    if proc.returncode == 0:
        tokens = proc.stdout.split(b"\0")
        tree_oid = tokens[0].decode("ascii").strip()
        return PlanResult(
            version=1,
            clean=True,
            resolvable=True,
            tree=tree_oid,
            auto=auto,
            verify_skip=verify_skip,
            files=[],
            summary=[],
        )

    # Returncode 1: has conflicts
    tokens = proc.stdout.split(b"\0")
    base_tree_oid = tokens[0].decode("ascii").strip()

    # Parse stage entries: <mode> <oid> <stage>\t<path>
    # terminated by an empty \0
    conflicts_by_path: dict[str, dict[int, tuple[str, str]]] = {}
    for token in tokens[1:]:
        if not token:
            break
        if b"\t" not in token:
            continue
        meta, path_bytes = token.split(b"\t", 1)
        path = path_bytes.decode("utf-8", errors="surrogateescape")
        meta_parts = meta.decode("ascii").split(" ")
        if len(meta_parts) != 3:
            continue
        mode_str, oid_str, stage_str = meta_parts
        try:
            stage = int(stage_str)
        except ValueError:
            continue
        if path not in conflicts_by_path:
            conflicts_by_path[path] = {}
        conflicts_by_path[path][stage] = (mode_str, oid_str)

    candidate_paths: list[str] = []
    file_results_map: dict[str, FileResult] = {}
    candidate_modes: dict[str, str] = {}

    sorted_paths = sorted(conflicts_by_path.keys())
    for path in sorted_paths:
        stages = conflicts_by_path[path]
        if 1 not in stages or 2 not in stages or 3 not in stages:
            if 1 not in stages:
                reason = "add/add"
            else:
                reason = "modify/delete"
            file_results_map[path] = FileResult(
                path=path, resolvable=False, reason=reason, lines=[], content=None
            )
            continue

        modes = (stages[1][0], stages[2][0], stages[3][0])
        if modes[0] != modes[1] or modes[1] != modes[2]:
            file_results_map[path] = FileResult(
                path=path, resolvable=False, reason="mode change", lines=[], content=None
            )
            continue

        if modes[0] not in ("100644", "100755"):
            if modes[0] == "120000":
                reason = "symlink"
            elif modes[0] == "160000":
                reason = "submodule"
            else:
                reason = f"unsupported file mode {modes[0]}"
            file_results_map[path] = FileResult(
                path=path, resolvable=False, reason=reason, lines=[], content=None
            )
            continue

        if cfg is None:
            file_results_map[path] = FileResult(
                path=path, resolvable=False, reason="no .gsp-merge.toml", lines=[], content=None
            )
            continue

        candidate_paths.append(path)
        candidate_modes[path] = modes[0]

    # Fetch blobs for candidates
    oids_to_fetch: set[str] = set()
    for path in candidate_paths:
        stages = conflicts_by_path[path]
        for s in (1, 2, 3):
            oids_to_fetch.add(stages[s][1])

    blobs = cat_blobs(repo_root, oids_to_fetch) if oids_to_fetch else {}

    # Run merge-file and resolve_file for candidates
    with tempfile.TemporaryDirectory() as tmp_dir:
        for path in candidate_paths:
            stages = conflicts_by_path[path]
            base_bytes = blobs[stages[1][1]]
            ours_bytes = blobs[stages[2][1]]
            theirs_bytes = blobs[stages[3][1]]

            # Check binary
            if b"\0" in base_bytes or b"\0" in ours_bytes or b"\0" in theirs_bytes:
                file_results_map[path] = FileResult(
                    path=path, resolvable=False, reason="binary", lines=[], content=None
                )
                continue

            try:
                base_text = base_bytes.decode("utf-8")
                ours_text = ours_bytes.decode("utf-8")
                theirs_text = theirs_bytes.decode("utf-8")
            except UnicodeDecodeError:
                file_results_map[path] = FileResult(
                    path=path, resolvable=False, reason="binary", lines=[], content=None
                )
                continue

            # Write blobs to temp files for git merge-file
            base_f = os.path.join(tmp_dir, f"base_{len(file_results_map)}")
            ours_f = os.path.join(tmp_dir, f"ours_{len(file_results_map)}")
            theirs_f = os.path.join(tmp_dir, f"theirs_{len(file_results_map)}")

            with open(base_f, "wb") as f:
                f.write(base_bytes)
            with open(ours_f, "wb") as f:
                f.write(ours_bytes)
            with open(theirs_f, "wb") as f:
                f.write(theirs_bytes)

            mf_proc = subprocess.run(
                [
                    "git",
                    "merge-file",
                    "-p",
                    "--zdiff3",
                    "--marker-size=32",
                    "-L",
                    "ours",
                    "-L",
                    "base",
                    "-L",
                    "theirs",
                    ours_f,
                    base_f,
                    theirs_f,
                ],
                capture_output=True,
                text=True,
            )
            if mf_proc.returncode < 0:
                raise GitError(
                    f"git merge-file failed on {path} with code {mf_proc.returncode}: {mf_proc.stderr}"
                )

            assert cfg is not None
            rules, groups = cfg.for_path(path)
            res = resolve_file(path, mf_proc.stdout, base_text, ours_text, theirs_text, rules, groups)
            file_results_map[path] = res

        # Assemble list of all file results
        all_file_results = [file_results_map[p] for p in sorted_paths]
        all_resolvable = len(all_file_results) > 0 and all(f.resolvable for f in all_file_results)

        final_tree: str | None = None
        if all_resolvable:
            # Hash resolved contents
            resolved_tmp_paths: list[str] = []
            for i, f_res in enumerate(all_file_results):
                tmp_resolved = os.path.join(tmp_dir, f"res_{i}")
                with open(tmp_resolved, "wb") as f:
                    assert f_res.content is not None
                    f.write(f_res.content.encode("utf-8"))
                resolved_tmp_paths.append(tmp_resolved)

            hash_proc = subprocess.run(
                ["git", "hash-object", "-w", "--stdin-paths"],
                cwd=repo_root,
                input="\n".join(resolved_tmp_paths) + "\n",
                capture_output=True,
                text=True,
                check=True,
            )
            blob_oids = [line.strip() for line in hash_proc.stdout.strip().splitlines() if line.strip()]
            if len(blob_oids) != len(all_file_results):
                raise GitError("git hash-object --stdin-paths returned unexpected number of oids")

            # Build tree with temporary index
            tmp_index = os.path.join(tmp_dir, "temp_index")
            env = dict(os.environ, GIT_INDEX_FILE=tmp_index)

            subprocess.run(
                ["git", "read-tree", base_tree_oid],
                cwd=repo_root,
                env=env,
                check=True,
                capture_output=True,
            )

            update_info = []
            for f_res, blob_oid in zip(all_file_results, blob_oids):
                mode = candidate_modes[f_res.path]
                update_info.append(f"{mode} {blob_oid}\t{f_res.path}\n")

            subprocess.run(
                ["git", "update-index", "--index-info"],
                cwd=repo_root,
                env=env,
                input="".join(update_info).encode("utf-8"),
                check=True,
                capture_output=True,
            )

            write_tree_proc = subprocess.run(
                ["git", "write-tree"],
                cwd=repo_root,
                env=env,
                capture_output=True,
                text=True,
                check=True,
            )
            final_tree = write_tree_proc.stdout.strip()

    summary: list[str] = []
    for f_res in all_file_results:
        for line in f_res.lines:
            summary.append(f"{f_res.path}: {line.rule} {line.ours}|{line.theirs}→{line.result}")

    files_list = [
        {
            "path": f.path,
            "resolvable": f.resolvable,
            "reason": f.reason,
            "lines": [
                {
                    "rule": l.rule,
                    "base": l.base,
                    "ours": l.ours,
                    "theirs": l.theirs,
                    "result": l.result,
                }
                for l in f.lines
            ],
        }
        for f in all_file_results
    ]

    return PlanResult(
        version=1,
        clean=False,
        resolvable=all_resolvable,
        tree=final_tree,
        auto=auto,
        verify_skip=verify_skip,
        files=files_list,
        summary=summary,
    )


def driver(base_file: str, ours_file: str, theirs_file: str, pathname: str, cwd: str | None = None) -> int:
    """Git merge-driver implementation according to contract §5.

    Writes resolved result to ours_file and exits 0 if resolved,
    else writes standard marker output to ours_file and exits 1.
    """
    repo_root = get_repo_root(cwd=cwd)

    mf_proc = subprocess.run(
        [
            "git",
            "merge-file",
            "-p",
            "--zdiff3",
            "--marker-size=32",
            "-L",
            "ours",
            "-L",
            "base",
            "-L",
            "theirs",
            ours_file,
            base_file,
            theirs_file,
        ],
        capture_output=True,
        text=True,
    )
    if mf_proc.returncode < 0:
        raise GitError(f"git merge-file error: {mf_proc.stderr}")

    merged = mf_proc.stdout
    cfg = load_config(repo_root)
    if cfg is None:
        with open(ours_file, "w", encoding="utf-8", newline="") as f:
            f.write(merged)
        return 1

    try:
        with open(base_file, "r", encoding="utf-8") as f:
            base_text = f.read()
        with open(ours_file, "r", encoding="utf-8") as f:
            ours_text = f.read()
        with open(theirs_file, "r", encoding="utf-8") as f:
            theirs_text = f.read()
    except (UnicodeDecodeError, OSError):
        with open(ours_file, "w", encoding="utf-8", newline="") as f:
            f.write(merged)
        return 1

    rules, groups = cfg.for_path(pathname)
    res = resolve_file(pathname, merged, base_text, ours_text, theirs_text, rules, groups)
    if res.resolvable and res.content is not None:
        with open(ours_file, "w", encoding="utf-8", newline="") as f:
            f.write(res.content)
        return 0
    else:
        with open(ours_file, "w", encoding="utf-8", newline="") as f:
            f.write(merged)
        return 1
