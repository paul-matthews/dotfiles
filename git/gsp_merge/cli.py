"""CLI entry point for git-meta-resolve."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
from typing import Sequence


def format_human_plan(result: dict) -> str:
    """Format plan result as human-readable aligned output."""
    lines: list[str] = []
    clean = result.get("clean", False)
    resolvable = result.get("resolvable", False)
    tree = result.get("tree")

    if clean:
        lines.append(f"Clean merge (tree: {tree})")
        return "\n".join(lines)

    if resolvable:
        lines.append(f"Resolvable (tree: {tree})")
    else:
        lines.append("Unresolvable")

    files = result.get("files", [])
    if files:
        lines.append("")
        lines.append("Files:")
        col_path_w = max(len("PATH"), max(len(f["path"]) for f in files))
        col_status_w = max(len("STATUS"), max(len("RESOLVED" if f["resolvable"] else "UNRESOLVED") for f in files))
        
        header = f"  { 'PATH'.ljust(col_path_w) }  { 'STATUS'.ljust(col_status_w) }  DETAILS"
        lines.append(header)
        lines.append("  " + "-" * (len(header) - 2))

        for f in files:
            path = f["path"]
            status = "RESOLVED" if f["resolvable"] else "UNRESOLVED"
            if f["resolvable"]:
                details = ", ".join(
                    f"{l['rule']} {l['ours']}|{l['theirs']}→{l['result']}" for l in f.get("lines", [])
                )
            else:
                details = f["reason"] or "conflict"
            lines.append(f"  {path.ljust(col_path_w)}  {status.ljust(col_status_w)}  {details}")

    summary = result.get("summary", [])
    if summary:
        lines.append("")
        lines.append("Summary:")
        for s in summary:
            lines.append(f"  {s}")

    return "\n".join(lines)


def main(argv: Sequence[str] | None = None) -> int:
    """Main CLI entry point. Returns exit code 0, 1, or 2."""
    if argv is None:
        argv = sys.argv[1:]
    else:
        argv = list(argv)

    # Alias rewriting: --self-test, --check-config, --init
    if "--self-test" in argv:
        idx = argv.index("--self-test")
        argv[idx] = "self-test"
    elif "--check-config" in argv:
        idx = argv.index("--check-config")
        argv[idx] = "check-config"
    elif "--init" in argv:
        idx = argv.index("--init")
        argv[idx] = "init"

    parser = argparse.ArgumentParser(
        prog="git-meta-resolve",
        description="Resolve well-known trivial merge conflicts declared in .gsp-merge.toml.",
    )
    subparsers = parser.add_subparsers(dest="subcommand", help="Available subcommands")

    # plan --ours <rev> --theirs <rev> [--json] [--config <path>]
    plan_parser = subparsers.add_parser("plan", help="Plan conflict resolution")
    plan_parser.add_argument("--ours", required=True, help="Ours revision (commit/branch)")
    plan_parser.add_argument("--theirs", required=True, help="Theirs revision (commit/branch)")
    plan_parser.add_argument("--json", action="store_true", help="Output JSON on stdout")
    plan_parser.add_argument("--config", default=None, help="Explicit path to config file")

    # config [--json]
    config_parser = subparsers.add_parser("config", help="Show repo config state")
    config_parser.add_argument("--json", action="store_true", help="Output JSON on stdout")

    # check-config [<path>]
    check_config_parser = subparsers.add_parser("check-config", help="Validate config file")
    check_config_parser.add_argument("path", nargs="?", default=None, help="Path to config file")

    # init [--force]
    init_parser = subparsers.add_parser("init", help="Copy template to ./.gsp-merge.toml")
    init_parser.add_argument("--force", action="store_true", help="Overwrite existing config")

    # self-test
    subparsers.add_parser("self-test", help="Run strategy tests and fixture scenarios")

    # driver <O> <A> <B> <P>
    driver_parser = subparsers.add_parser("driver", help="Git merge-driver mode")
    driver_parser.add_argument("O", help="Ancestor (base) file")
    driver_parser.add_argument("A", help="Current (ours) file")
    driver_parser.add_argument("B", help="Other (theirs) file")
    driver_parser.add_argument("P", help="File pathname")

    if not argv:
        parser.print_usage(sys.stderr)
        return 2

    try:
        args = parser.parse_args(argv)
    except SystemExit as e:
        return e.code if isinstance(e.code, int) else 2

    if args.subcommand is None:
        parser.print_usage(sys.stderr)
        return 2

    if args.subcommand == "self-test":
        from gsp_merge.selftest import run_self_tests

        return run_self_tests()

    if args.subcommand == "plan":
        from gsp_merge.config import ConfigError
        from gsp_merge.gitops import GitError, plan

        try:
            plan_res = plan(
                ours=args.ours,
                theirs=args.theirs,
                config_path=args.config,
            )
        except ConfigError as e:
            print(f"git-meta-resolve: config error: {e}", file=sys.stderr)
            return 2
        except GitError as e:
            print(f"git-meta-resolve: git error: {e}", file=sys.stderr)
            return 2
        except Exception as e:
            print(f"git-meta-resolve: unexpected error: {e}", file=sys.stderr)
            return 2

        plan_dict = plan_res.to_dict()
        if args.json:
            print(json.dumps(plan_dict, indent=2))
        else:
            print(format_human_plan(plan_dict))

        if plan_res.clean or plan_res.resolvable:
            return 0
        return 1

    if args.subcommand == "config":
        from gsp_merge.config import ConfigError, load_config
        from gsp_merge.gitops import GitError, get_repo_root

        try:
            repo_root = get_repo_root()
            cfg = load_config(repo_root)
        except (GitError, ConfigError) as e:
            print(f"git-meta-resolve: error: {e}", file=sys.stderr)
            return 2

        data = {
            "present": cfg is not None,
            "auto": cfg.auto if cfg is not None else False,
            "verify_skip": list(cfg.verify_skip) if cfg is not None else [],
        }

        if args.json:
            print(json.dumps(data, indent=2))
        else:
            print(f"present: {str(data['present']).lower()}")
            print(f"auto: {str(data['auto']).lower()}")
            print(f"verify_skip: {', '.join(data['verify_skip']) if data['verify_skip'] else '[]'}")
        return 0

    if args.subcommand == "check-config":
        from gsp_merge.config import ConfigError, parse_config
        from gsp_merge.gitops import GitError, get_repo_root

        target_path = args.path
        if target_path is None:
            try:
                repo_root = get_repo_root()
                target_path = os.path.join(repo_root, ".gsp-merge.toml")
            except GitError as e:
                print(f"git-meta-resolve: error: {e}", file=sys.stderr)
                return 2

        if not os.path.exists(target_path):
            print(f"check-config: error: file not found: {target_path}", file=sys.stderr)
            return 2

        try:
            with open(target_path, "r", encoding="utf-8") as f:
                text = f.read()
            cfg = parse_config(text, source=target_path)
            print(f"ok: {len(cfg.rules)} rules, {len(cfg.groups)} groups")
            return 0
        except ConfigError as e:
            print(f"check-config: error: {e}", file=sys.stderr)
            return 2

    if args.subcommand == "init":
        from gsp_merge.config import template_path
        from gsp_merge.gitops import GitError, get_repo_root

        try:
            repo_root = get_repo_root()
        except GitError as e:
            print(f"git-meta-resolve: error: {e}", file=sys.stderr)
            return 2

        target = os.path.join(repo_root, ".gsp-merge.toml")
        if os.path.exists(target) and not args.force:
            print(
                f"init: error: .gsp-merge.toml already exists (use --force to overwrite)",
                file=sys.stderr,
            )
            return 2

        tmpl = template_path()
        if not os.path.exists(tmpl):
            print(f"init: error: template not found: {tmpl}", file=sys.stderr)
            return 2

        shutil.copyfile(tmpl, target)
        print(f"Initialized .gsp-merge.toml at {target}")
        return 0

    if args.subcommand == "driver":
        from gsp_merge.gitops import GitError, driver

        try:
            return driver(args.O, args.A, args.B, args.P)
        except GitError as e:
            print(f"git-meta-resolve: git error: {e}", file=sys.stderr)
            return 2
        except Exception as e:
            print(f"git-meta-resolve: error: {e}", file=sys.stderr)
            return 2

    return 2
