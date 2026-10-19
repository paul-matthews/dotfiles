"""Configuration loading and validation for gsp auto-merge.

See docs/gsp-merge-contract.md §2 and §3.2.
"""

from collections.abc import Iterable
from dataclasses import dataclass
import os
from pathlib import Path, PurePosixPath
import re
import tomllib
from typing import Any

# Default and valid strategies per type.
# Lazily synced with strategies module if available.
TYPE_DEFAULTS: dict[str, str] = {
    "counter": "max",
    "semver": "max",
    "timestamp": "latest",
    "semver_split": "max",
}

VALID_STRATEGIES: dict[str, tuple[str, ...]] = {
    "counter": ("max", "max_unique"),
    "semver": ("max",),
    "timestamp": ("latest",),
    "semver_split": ("max",),
}

try:
    from . import strategies
    TYPE_DEFAULTS = getattr(strategies, "DEFAULTS", TYPE_DEFAULTS)
    VALID_STRATEGIES = getattr(strategies, "VALID", VALID_STRATEGIES)
except Exception:
    pass

CONFIG_NAME: str = ".gsp-merge.toml"
NAME_PATTERN: re.Pattern = re.compile(r"^[a-z0-9-]+$")


class ConfigError(Exception):
    """Raised when configuration file fails validation."""


@dataclass(frozen=True)
class Rule:
    name: str
    files: tuple[str, ...]
    line: re.Pattern
    type: str
    strategy: str
    frontmatter_only: bool
    coupled: tuple[re.Pattern, ...]


@dataclass(frozen=True)
class Group:
    name: str
    files: tuple[str, ...]
    type: str
    strategy: str
    major: re.Pattern
    minor: re.Pattern
    patch: re.Pattern
    frontmatter_only: bool


@dataclass(frozen=True)
class Config:
    auto: bool
    verify_skip: tuple[str, ...]
    rules: tuple[Rule, ...]
    groups: tuple[Group, ...]

    @property
    def version(self) -> int:
        return 1

    def for_path(self, path: str) -> tuple[tuple[Rule, ...], tuple[Group, ...]]:
        """Return (matching_rules, matching_groups) for the given repo-relative path."""
        matched_rules = tuple(r for r in self.rules if path_matches(path, r.files))
        matched_groups = tuple(g for g in self.groups if path_matches(path, g.files))
        return (matched_rules, matched_groups)


def path_matches(path: str, globs: Iterable[str]) -> bool:
    """Return True if path matches any glob pattern using PurePosixPath.full_match semantics."""
    p = PurePosixPath(path)
    return any(p.full_match(g) for g in globs)


def template_path() -> str:
    """Resolve <dotfiles>/git/gsp-merge.toml.example relative to this file."""
    this_dir = os.path.dirname(os.path.realpath(__file__))
    return os.path.realpath(os.path.join(this_dir, "..", "gsp-merge.toml.example"))


def load_config(repo_root: str | Path) -> Config | None:
    """Load configuration from <repo_root>/.gsp-merge.toml.

    Returns None if the file is absent.
    Raises ConfigError if the file cannot be read or fails validation.
    """
    cfg_path = os.path.join(repo_root, CONFIG_NAME)
    if not os.path.exists(cfg_path):
        return None
    try:
        with open(cfg_path, "r", encoding="utf-8") as f:
            text = f.read()
    except OSError as e:
        raise ConfigError(f"{cfg_path}: failed to read configuration file: {e}") from e
    return parse_config(text, source=str(cfg_path))


def _validate_regex_with_value_group(
    pattern_str: Any,
    field_label: str,
    source: str,
    rule_or_group_label: str,
) -> re.Pattern:
    """Compile pattern_str and ensure it contains exactly one named group 'value'."""
    if not isinstance(pattern_str, str):
        raise ConfigError(
            f"{source}: {rule_or_group_label}: {field_label!r} must be a string regex"
        )
    try:
        compiled = re.compile(pattern_str)
    except re.error as e:
        raise ConfigError(
            f"{source}: {rule_or_group_label}: regex compilation error in {field_label!r}: {e}"
        ) from e

    named_groups = set(compiled.groupindex.keys())
    if named_groups != {"value"}:
        raise ConfigError(
            f"{source}: {rule_or_group_label}: regex in {field_label!r} must define exactly one named group 'value'"
        )
    return compiled


def parse_config(text: str, source: str = "<string>", **kwargs: Any) -> Config:
    """Parse and validate .gsp-merge.toml content.

    Raises ConfigError if validation fails.
    """
    if "source_path" in kwargs and kwargs["source_path"] is not None:
        source = str(kwargs["source_path"])

    try:
        data = tomllib.loads(text)
    except tomllib.TOMLDecodeError as e:
        raise ConfigError(f"{source}: TOML syntax error: {e}") from e

    if not isinstance(data, dict):
        raise ConfigError(f"{source}: configuration root must be a table")

    # Top-level unknown keys check
    allowed_top_keys = {"version", "auto", "verify_skip", "rule", "group"}
    for k in data:
        if k not in allowed_top_keys:
            raise ConfigError(f"{source}: unknown top-level key {k!r}")

    # Top-level required keys check: version
    if "version" not in data:
        raise ConfigError(f"{source}: missing required key 'version'")
    version = data["version"]
    if isinstance(version, bool) or not isinstance(version, int) or version != 1:
        raise ConfigError(f"{source}: 'version' must be integer 1 (got {version!r})")

    # auto
    auto = data.get("auto", False)
    if not isinstance(auto, bool):
        raise ConfigError(f"{source}: 'auto' must be a boolean (got {type(auto).__name__})")

    # verify_skip
    verify_skip_raw = data.get("verify_skip", [])
    if not isinstance(verify_skip_raw, list):
        raise ConfigError(f"{source}: 'verify_skip' must be a list of strings")
    for vs in verify_skip_raw:
        if not isinstance(vs, str):
            raise ConfigError(f"{source}: 'verify_skip' entries must be strings (got {type(vs).__name__})")
    verify_skip = tuple(verify_skip_raw)

    # Containers for rules and groups
    rules_raw = data.get("rule", [])
    if not isinstance(rules_raw, list):
        raise ConfigError(f"{source}: 'rule' must be a list of tables")

    groups_raw = data.get("group", [])
    if not isinstance(groups_raw, list):
        raise ConfigError(f"{source}: 'group' must be a list of tables")

    seen_names: set[str] = set()

    # Process [[rule]]
    rules: list[Rule] = []
    allowed_rule_keys = {
        "name",
        "files",
        "line",
        "type",
        "strategy",
        "frontmatter_only",
        "coupled",
    }
    required_rule_keys = ("name", "files", "line", "type")

    for idx, r in enumerate(rules_raw):
        if not isinstance(r, dict):
            raise ConfigError(f"{source}: rule[{idx}] must be a table")

        name = r.get("name")
        r_label = f"rule {name!r}" if isinstance(name, str) else f"rule[{idx}]"

        # Unknown keys
        for k in r:
            if k not in allowed_rule_keys:
                raise ConfigError(f"{source}: {r_label}: unknown key {k!r}")

        # Required keys
        for req in required_rule_keys:
            if req not in r:
                raise ConfigError(f"{source}: {r_label}: missing required key {req!r}")

        # Validate name
        if not isinstance(name, str) or not NAME_PATTERN.fullmatch(name):
            raise ConfigError(
                f"{source}: {r_label}: invalid name {name!r}, must match pattern '^[a-z0-9-]+$'"
            )
        if name in seen_names:
            raise ConfigError(f"{source}: {r_label}: duplicate name {name!r} across rules and groups")
        seen_names.add(name)

        # Validate files
        files_raw = r["files"]
        if not isinstance(files_raw, list):
            raise ConfigError(f"{source}: rule {name!r}: 'files' must be a list of globs")
        if len(files_raw) == 0:
            raise ConfigError(f"{source}: rule {name!r}: 'files' list cannot be empty")
        for f_glob in files_raw:
            if not isinstance(f_glob, str) or len(f_glob) == 0:
                raise ConfigError(f"{source}: rule {name!r}: 'files' entries must be non-empty strings")
        files = tuple(files_raw)

        # Validate type
        rule_type = r["type"]
        if not isinstance(rule_type, str):
            raise ConfigError(f"{source}: rule {name!r}: 'type' must be a string")
        if rule_type not in ("counter", "semver", "timestamp"):
            raise ConfigError(
                f"{source}: rule {name!r}: unknown type {rule_type!r} (expected counter, semver, or timestamp)"
            )

        # Validate strategy
        if "strategy" in r:
            strategy = r["strategy"]
            if not isinstance(strategy, str):
                raise ConfigError(f"{source}: rule {name!r}: 'strategy' must be a string")
            valid_strats = VALID_STRATEGIES.get(rule_type, ())
            if strategy not in valid_strats:
                raise ConfigError(
                    f"{source}: rule {name!r}: unknown strategy {strategy!r} for type {rule_type!r} (valid: {valid_strats})"
                )
        else:
            strategy = TYPE_DEFAULTS[rule_type]

        # Validate frontmatter_only
        frontmatter_only = r.get("frontmatter_only", False)
        if not isinstance(frontmatter_only, bool):
            raise ConfigError(f"{source}: rule {name!r}: 'frontmatter_only' must be a boolean")

        # Validate coupled
        if "coupled" in r and rule_type != "timestamp":
            raise ConfigError(
                f"{source}: rule {name!r}: 'coupled' is only allowed on timestamp rules (got type {rule_type!r})"
            )
        coupled_raw = r.get("coupled", [])
        if not isinstance(coupled_raw, list):
            raise ConfigError(f"{source}: rule {name!r}: 'coupled' must be a list of regex patterns")

        # Validate line regex
        line_pattern = _validate_regex_with_value_group(r["line"], "line", source, f"rule {name!r}")

        # Validate coupled regexes
        compiled_coupled: list[re.Pattern] = []
        for c_idx, c_pat_str in enumerate(coupled_raw):
            compiled_c = _validate_regex_with_value_group(
                c_pat_str, f"coupled[{c_idx}]", source, f"rule {name!r}"
            )
            compiled_coupled.append(compiled_c)

        rules.append(
            Rule(
                name=name,
                files=files,
                line=line_pattern,
                type=rule_type,
                strategy=strategy,
                frontmatter_only=frontmatter_only,
                coupled=tuple(compiled_coupled),
            )
        )

    # Process [[group]]
    groups: list[Group] = []
    allowed_group_keys = {
        "name",
        "files",
        "type",
        "strategy",
        "major",
        "minor",
        "patch",
        "frontmatter_only",
    }
    required_group_keys = ("name", "files", "type", "major", "minor", "patch")

    for idx, g in enumerate(groups_raw):
        if not isinstance(g, dict):
            raise ConfigError(f"{source}: group[{idx}] must be a table")

        name = g.get("name")
        g_label = f"group {name!r}" if isinstance(name, str) else f"group[{idx}]"

        # Unknown keys
        for k in g:
            if k not in allowed_group_keys:
                raise ConfigError(f"{source}: {g_label}: unknown key {k!r}")

        # Required keys
        for req in required_group_keys:
            if req not in g:
                raise ConfigError(f"{source}: {g_label}: missing required key {req!r}")

        # Validate name
        if not isinstance(name, str) or not NAME_PATTERN.fullmatch(name):
            raise ConfigError(
                f"{source}: {g_label}: invalid name {name!r}, must match pattern '^[a-z0-9-]+$'"
            )
        if name in seen_names:
            raise ConfigError(f"{source}: {g_label}: duplicate name {name!r} across rules and groups")
        seen_names.add(name)

        # Validate files
        files_raw = g["files"]
        if not isinstance(files_raw, list):
            raise ConfigError(f"{source}: group {name!r}: 'files' must be a list of globs")
        if len(files_raw) == 0:
            raise ConfigError(f"{source}: group {name!r}: 'files' list cannot be empty")
        for f_glob in files_raw:
            if not isinstance(f_glob, str) or len(f_glob) == 0:
                raise ConfigError(f"{source}: group {name!r}: 'files' entries must be non-empty strings")
        files = tuple(files_raw)

        # Validate type
        group_type = g["type"]
        if group_type != "semver_split":
            raise ConfigError(
                f"{source}: group {name!r}: invalid type {group_type!r} (groups only support 'semver_split')"
            )

        # Validate strategy
        if "strategy" in g:
            strategy = g["strategy"]
            if not isinstance(strategy, str):
                raise ConfigError(f"{source}: group {name!r}: 'strategy' must be a string")
            valid_strats = VALID_STRATEGIES.get("semver_split", ("max",))
            if strategy not in valid_strats:
                raise ConfigError(
                    f"{source}: group {name!r}: unknown strategy {strategy!r} for type 'semver_split' (valid: {valid_strats})"
                )
        else:
            strategy = TYPE_DEFAULTS.get("semver_split", "max")

        # Validate frontmatter_only
        frontmatter_only = g.get("frontmatter_only", False)
        if not isinstance(frontmatter_only, bool):
            raise ConfigError(f"{source}: group {name!r}: 'frontmatter_only' must be a boolean")

        # Validate major, minor, patch regexes
        major_pat = _validate_regex_with_value_group(g["major"], "major", source, f"group {name!r}")
        minor_pat = _validate_regex_with_value_group(g["minor"], "minor", source, f"group {name!r}")
        patch_pat = _validate_regex_with_value_group(g["patch"], "patch", source, f"group {name!r}")

        groups.append(
            Group(
                name=name,
                files=files,
                type=group_type,
                strategy=strategy,
                major=major_pat,
                minor=minor_pat,
                patch=patch_pat,
                frontmatter_only=frontmatter_only,
            )
        )

    return Config(
        auto=auto,
        verify_skip=verify_skip,
        rules=tuple(rules),
        groups=tuple(groups),
    )
