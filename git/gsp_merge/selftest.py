"""Self-test runner for gsp-merge: runs strategies.SELF_TESTS and all fixtures."""

from __future__ import annotations

import pathlib
import subprocess
import sys
from typing import TextIO

from gsp_merge.config import parse_config
from gsp_merge.hunks import resolve_file
from gsp_merge.strategies import SELF_TESTS


def run_self_tests(
    fixtures_dir: pathlib.Path | None = None,
    out: TextIO = sys.stdout,
    err: TextIO = sys.stderr,
) -> int:
    """Run all strategy tests and fixtures.

    Prints failure details and a one-line summary:
    'self-test: N passed, M failed'

    Returns 0 if all tests pass, 1 if any fail.
    """
    if fixtures_dir is None:
        fixtures_dir = pathlib.Path(__file__).resolve().parent / "fixtures"

    passed = 0
    failed = 0
    failures: list[str] = []

    # 1. Strategy tests
    for name, fn in SELF_TESTS:
        try:
            fn()
            passed += 1
        except Exception as e:
            failed += 1
            failures.append(f"strategy '{name}': {e}")

    # 2. Fixture tests
    if fixtures_dir.is_dir():
        for f in sorted(fixtures_dir.iterdir()):
            if not f.is_dir():
                continue
            path_file = f / "path"
            rules_file = f / "rules.toml"
            base_file = f / "base"
            ours_file = f / "ours"
            theirs_file = f / "theirs"

            if not (
                path_file.exists()
                and rules_file.exists()
                and base_file.exists()
                and ours_file.exists()
                and theirs_file.exists()
            ):
                continue

            relpath = path_file.read_text(encoding="utf-8").strip()
            rules_text = rules_file.read_text(encoding="utf-8")
            base_text = base_file.read_text(encoding="utf-8")
            ours_text = ours_file.read_text(encoding="utf-8")
            theirs_text = theirs_file.read_text(encoding="utf-8")

            try:
                cfg = parse_config(rules_text, source=str(rules_file))
            except Exception as e:
                failed += 1
                failures.append(f"fixture '{f.name}': failed to parse rules.toml: {e}")
                continue

            proc = subprocess.run(
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
                    str(ours_file),
                    str(base_file),
                    str(theirs_file),
                ],
                capture_output=True,
                text=True,
            )
            if proc.returncode < 0:
                failed += 1
                failures.append(
                    f"fixture '{f.name}': git merge-file error (returncode {proc.returncode}): {proc.stderr}"
                )
                continue

            rules, groups = cfg.for_path(relpath)
            res = resolve_file(relpath, proc.stdout, base_text, ours_text, theirs_text, rules, groups)

            expected_file = f / "expected"
            unresolvable_file = f / "unresolvable"

            if expected_file.is_file():
                expected = expected_file.read_text(encoding="utf-8")
                if not res.resolvable:
                    failed += 1
                    failures.append(
                        f"fixture '{f.name}': expected resolvable, got unresolvable: {res.reason}"
                    )
                elif res.content != expected:
                    failed += 1
                    failures.append(f"fixture '{f.name}': resolved content mismatch")
                else:
                    passed += 1
            elif unresolvable_file.is_file():
                expected_sub = unresolvable_file.read_text(encoding="utf-8").strip()
                if res.resolvable:
                    failed += 1
                    failures.append(
                        f"fixture '{f.name}': expected unresolvable ({expected_sub!r}), but got resolvable"
                    )
                elif expected_sub not in (res.reason or ""):
                    failed += 1
                    failures.append(
                        f"fixture '{f.name}': expected reason containing {expected_sub!r}, got {res.reason!r}"
                    )
                else:
                    passed += 1
            else:
                failed += 1
                failures.append(f"fixture '{f.name}': neither 'expected' nor 'unresolvable' file found")

    if failures:
        for fail in failures:
            print(f"FAIL: {fail}", file=err)

    print(f"self-test: {passed} passed, {failed} failed", file=out)
    return 0 if failed == 0 else 1
