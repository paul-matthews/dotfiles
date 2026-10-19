"""Merge strategies for gsp auto-merge (Phase 0).

Implements §3.1 of docs/gsp-merge-contract.md:
- resolve_counter: decimal integer counters (max, max_unique)
- resolve_semver: SemVer 2.0.0 precedence ordering (max)
- resolve_semver_split: (major, minor, patch) integer tuple compare (max)
- pick_timestamp_winner: ISO-8601 timestamps with timezone offset (latest)
"""

from __future__ import annotations

from datetime import datetime
import re
from typing import Callable

__all__ = [
    "StrategyError",
    "DEFAULTS",
    "VALID",
    "resolve_counter",
    "resolve_semver",
    "resolve_semver_split",
    "pick_timestamp_winner",
    "SELF_TESTS",
]


class StrategyError(ValueError):
    """Raised when input cannot be parsed or strategy is unknown (unresolvable hunk)."""


DEFAULTS: dict[str, str] = {
    "counter": "max",
    "semver": "max",
    "timestamp": "latest",
    "semver_split": "max",
}

VALID: dict[str, tuple[str, ...]] = {
    "counter": ("max", "max_unique"),
    "semver": ("max",),
    "timestamp": ("latest",),
    "semver_split": ("max",),
}

# Official SemVer 2.0.0 regex with named capture groups
SEMVER_REGEX = re.compile(
    r"^(?P<major>0|[1-9]\d*)\."
    r"(?P<minor>0|[1-9]\d*)\."
    r"(?P<patch>0|[1-9]\d*)"
    r"(?:-(?P<prerelease>(?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*)(?:\.(?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*))*))?"
    r"(?:\+(?P<buildmetadata>[0-9a-zA-Z-]+(?:\.[0-9a-zA-Z-]+)*))?$"
)


def _validate_counter(s: str) -> int:
    """Validate that string is a non-negative decimal integer."""
    if not isinstance(s, str) or not s.isascii() or not s.isdigit():
        raise StrategyError(f"Invalid counter (must be non-negative decimal digits): {s!r}")
    return int(s)


def resolve_counter(base: str | None, ours: str, theirs: str, strategy: str = "max") -> str:
    """Resolve counter conflict.

    Supported strategies:
      - 'max': returns max(ours, theirs)
      - 'max_unique': returns max(ours, theirs) + 1

    Preserves the winning input's formatting and zero-padding width where possible.
    """
    if strategy not in VALID["counter"]:
        raise StrategyError(f"Unknown strategy {strategy!r} for counter")

    if base is not None:
        _validate_counter(base)
    val_ours = _validate_counter(ours)
    val_theirs = _validate_counter(theirs)

    if strategy == "max":
        if val_theirs > val_ours:
            return theirs
        return ours
    elif strategy == "max_unique":
        if val_theirs > val_ours:
            winning = theirs
            val_max = val_theirs
        else:
            winning = ours
            val_max = val_ours
        res_val = val_max + 1
        width = len(winning)
        return f"{res_val:0{width}d}"
    else:
        raise StrategyError(f"Unknown strategy {strategy!r} for counter")


def _parse_semver(s: str) -> tuple[int, int, int, str | None]:
    """Parse SemVer 2.0.0 string into (major, minor, patch, prerelease)."""
    if not isinstance(s, str):
        raise StrategyError(f"Invalid semver type: {type(s)}")
    m = SEMVER_REGEX.match(s)
    if not m:
        raise StrategyError(f"Invalid SemVer 2.0.0 string: {s!r}")
    return (
        int(m.group("major")),
        int(m.group("minor")),
        int(m.group("patch")),
        m.group("prerelease"),
    )


def _compare_semver_precedence(
    v1: tuple[int, int, int, str | None],
    v2: tuple[int, int, int, str | None],
) -> int:
    """Compare two SemVer versions according to SemVer 2.0.0 precedence rules.

    Returns:
      -1 if v1 < v2
       0 if v1 == v2 (equal precedence)
       1 if v1 > v2
    """
    maj1, min1, pat1, pre1 = v1
    maj2, min2, pat2, pre2 = v2

    if (maj1, min1, pat1) != (maj2, min2, pat2):
        return -1 if (maj1, min1, pat1) < (maj2, min2, pat2) else 1

    # When major, minor, patch are equal, a normal version has higher precedence than prerelease
    if pre1 is None and pre2 is None:
        return 0
    if pre1 is None and pre2 is not None:
        return 1
    if pre1 is not None and pre2 is None:
        return -1

    # Both have prerelease: compare dot-separated identifiers
    assert pre1 is not None and pre2 is not None
    p1 = pre1.split(".")
    p2 = pre2.split(".")

    for id1, id2 in zip(p1, p2):
        if id1 == id2:
            continue
        is_num1 = id1.isdigit()
        is_num2 = id2.isdigit()
        if is_num1 and is_num2:
            n1, n2 = int(id1), int(id2)
            if n1 != n2:
                return -1 if n1 < n2 else 1
        elif is_num1 and not is_num2:
            # Numeric identifiers always have lower precedence than non-numeric
            return -1
        elif not is_num1 and is_num2:
            return 1
        else:
            # Non-numeric identifiers are compared lexically in ASCII sort order
            return -1 if id1 < id2 else 1

    # A larger set of pre-release fields has a higher precedence than a smaller set
    if len(p1) != len(p2):
        return -1 if len(p1) < len(p2) else 1

    return 0


def resolve_semver(base: str | None, ours: str, theirs: str, strategy: str = "max") -> str:
    """Resolve semver conflict according to SemVer 2.0.0 precedence.

    Build metadata is ignored for ordering.
    On equal precedence, keeps ours.
    Returns the winning side's original string.
    """
    if strategy not in VALID["semver"]:
        raise StrategyError(f"Unknown strategy {strategy!r} for semver")

    if base is not None:
        _parse_semver(base)
    v_ours = _parse_semver(ours)
    v_theirs = _parse_semver(theirs)

    if _compare_semver_precedence(v_theirs, v_ours) > 0:
        return theirs
    return ours


def _validate_split_tuple(t: tuple[str, str, str]) -> tuple[int, int, int]:
    """Validate (major, minor, patch) tuple of decimal integer strings."""
    if not isinstance(t, tuple) or len(t) != 3:
        raise StrategyError(f"Expected 3-tuple, got {t!r}")
    vals = []
    for elem in t:
        if not isinstance(elem, str) or not elem.isascii() or not elem.isdigit():
            raise StrategyError(f"Invalid integer in semver_split: {elem!r}")
        vals.append(int(elem))
    return (vals[0], vals[1], vals[2])


def resolve_semver_split(
    base: tuple[str, str, str] | None,
    ours: tuple[str, str, str],
    theirs: tuple[str, str, str],
    strategy: str = "max",
) -> tuple[str, str, str]:
    """Resolve (major, minor, patch) split conflict.

    Compares (major, minor, patch) as an integer tuple.
    Returns the winning side's original strings.
    On equal, keeps ours.
    """
    if strategy not in VALID["semver_split"]:
        raise StrategyError(f"Unknown strategy {strategy!r} for semver_split")

    if base is not None:
        _validate_split_tuple(base)
    ours_ints = _validate_split_tuple(ours)
    theirs_ints = _validate_split_tuple(theirs)

    if theirs_ints > ours_ints:
        return theirs
    return ours


def _parse_iso_timestamp(s: str) -> datetime:
    """Parse ISO-8601 timestamp with offset; naive timestamps raise StrategyError."""
    if not isinstance(s, str):
        raise StrategyError(f"Invalid timestamp type: {type(s)}")
    try:
        dt = datetime.fromisoformat(s)
    except Exception as e:
        raise StrategyError(f"Invalid ISO-8601 timestamp {s!r}: {e}") from e
    if dt.tzinfo is None or dt.utcoffset() is None:
        raise StrategyError(f"Timestamp is naive (no timezone offset): {s!r}")
    return dt


def _validate_coupled_list(lst: list[str]) -> list[str]:
    """Validate that coupled values are a list of strings."""
    if not isinstance(lst, (list, tuple)):
        raise StrategyError(f"Coupled values must be a list, got {type(lst)}")
    for item in lst:
        if not isinstance(item, str):
            raise StrategyError(f"Coupled value must be a str, got {type(item)}")
    return list(lst)


def pick_timestamp_winner(
    ours: str,
    theirs: str,
    ours_coupled: list[str],
    theirs_coupled: list[str],
    strategy: str = "latest",
) -> str:
    """Pick winning side ('ours' | 'theirs') for timestamp resolution.

    - Later instant wins across different UTC offsets.
    - Tie (equal instants): the side whose coupled-values list is lexically smaller wins.
    - Full tie → 'ours'.
    """
    if strategy not in VALID["timestamp"]:
        raise StrategyError(f"Unknown strategy {strategy!r} for timestamp")

    dt_ours = _parse_iso_timestamp(ours)
    dt_theirs = _parse_iso_timestamp(theirs)
    c_ours = _validate_coupled_list(ours_coupled)
    c_theirs = _validate_coupled_list(theirs_coupled)

    if dt_theirs > dt_ours:
        return "theirs"
    elif dt_ours > dt_theirs:
        return "ours"
    else:
        if c_theirs < c_ours:
            return "theirs"
        return "ours"


# ---------------------------------------------------------------------------
# Self-tests (≥25 thorough cases)
# ---------------------------------------------------------------------------

def _test_counter_max_ours_wins() -> None:
    assert resolve_counter("100", "117", "116", "max") == "117"


def _test_counter_max_theirs_wins() -> None:
    assert resolve_counter("100", "116", "117", "max") == "117"


def _test_counter_max_equal() -> None:
    assert resolve_counter(None, "42", "42", "max") == "42"


def _test_counter_max_preserves_zero_padding() -> None:
    assert resolve_counter(None, "007", "5", "max") == "007"
    assert resolve_counter(None, "5", "007", "max") == "007"
    assert resolve_counter(None, "042", "42", "max") == "042"


def _test_counter_max_unique_ours_wins() -> None:
    assert resolve_counter("115", "117", "116", "max_unique") == "118"


def _test_counter_max_unique_theirs_wins() -> None:
    assert resolve_counter("115", "116", "117", "max_unique") == "118"


def _test_counter_max_unique_equal() -> None:
    assert resolve_counter(None, "5", "5", "max_unique") == "6"


def _test_counter_max_unique_preserves_zero_padding() -> None:
    assert resolve_counter(None, "007", "006", "max_unique") == "008"
    assert resolve_counter(None, "007", "5", "max_unique") == "008"
    assert resolve_counter(None, "5", "007", "max_unique") == "008"
    assert resolve_counter(None, "000", "000", "max_unique") == "001"


def _test_counter_max_unique_width_growth() -> None:
    # Fits inside winning padding width
    assert resolve_counter(None, "099", "50", "max_unique") == "100"
    # Grows naturally when width overflows
    assert resolve_counter(None, "99", "50", "max_unique") == "100"
    assert resolve_counter(None, "0099", "50", "max_unique") == "0100"


def _test_counter_base_handling() -> None:
    assert resolve_counter(None, "1", "2") == "2"
    assert resolve_counter("0", "1", "2") == "2"


def _test_counter_invalid_values() -> None:
    for bad in ["-1", "+1", "abc", "1.0", "", " 1 ", "1a"]:
        try:
            resolve_counter(None, bad, "1")
            raise AssertionError(f"Expected StrategyError for {bad!r}")
        except StrategyError:
            pass
        try:
            resolve_counter(None, "1", bad)
            raise AssertionError(f"Expected StrategyError for {bad!r}")
        except StrategyError:
            pass
        try:
            resolve_counter(bad, "1", "2")
            raise AssertionError(f"Expected StrategyError for base={bad!r}")
        except StrategyError:
            pass


def _test_counter_unknown_strategy() -> None:
    try:
        resolve_counter(None, "1", "2", "min")
        raise AssertionError("Expected StrategyError for unknown strategy")
    except StrategyError:
        pass


def _test_semver_basic_precedence() -> None:
    assert resolve_semver(None, "2.0.0", "1.9.9") == "2.0.0"
    assert resolve_semver(None, "1.1.0", "1.2.0") == "1.2.0"
    assert resolve_semver(None, "1.0.1", "1.0.0") == "1.0.1"


def _test_semver_prerelease_chain() -> None:
    # 1.0.0-alpha < 1.0.0-alpha.1 < 1.0.0-alpha.beta < 1.0.0-beta < 1.0.0-beta.2 < 1.0.0-beta.11 < 1.0.0-rc.1 < 1.0.0
    chain = [
        "1.0.0-alpha",
        "1.0.0-alpha.1",
        "1.0.0-alpha.beta",
        "1.0.0-beta",
        "1.0.0-beta.2",
        "1.0.0-beta.11",
        "1.0.0-rc.1",
        "1.0.0",
    ]
    for i in range(len(chain) - 1):
        earlier = chain[i]
        later = chain[i + 1]
        assert resolve_semver(None, earlier, later) == later
        assert resolve_semver(None, later, earlier) == later


def _test_semver_numeric_vs_alphanumeric_identifiers() -> None:
    # Numeric has lower precedence than alphanumeric
    assert resolve_semver(None, "1.0.0-1", "1.0.0-alpha") == "1.0.0-alpha"
    assert resolve_semver(None, "1.0.0-alpha", "1.0.0-1") == "1.0.0-alpha"


def _test_semver_numeric_identifiers_numerical_order() -> None:
    # 2 < 11 numerically
    assert resolve_semver(None, "1.0.0-2", "1.0.0-11") == "1.0.0-11"
    assert resolve_semver(None, "1.0.0-11", "1.0.0-2") == "1.0.0-11"


def _test_semver_build_metadata_ignored() -> None:
    # Build metadata ignored for ordering; equal precedence keeps ours
    assert resolve_semver(None, "1.0.0+20130313144700", "1.0.0+exp.sha.5114f85") == "1.0.0+20130313144700"
    assert resolve_semver(None, "1.0.0+exp.sha.5114f85", "1.0.0+20130313144700") == "1.0.0+exp.sha.5114f85"
    assert resolve_semver(None, "1.0.0-beta+1", "1.0.0-beta+2") == "1.0.0-beta+1"


def _test_semver_equal_precedence_keeps_ours() -> None:
    assert resolve_semver(None, "1.0.0", "1.0.0") == "1.0.0"
    assert resolve_semver(None, "1.2.3-alpha", "1.2.3-alpha") == "1.2.3-alpha"


def _test_semver_with_base() -> None:
    assert resolve_semver("1.0.0", "1.1.0", "1.0.1") == "1.1.0"
    assert resolve_semver(None, "1.1.0", "1.0.1") == "1.1.0"


def _test_semver_invalid_formats() -> None:
    bad_versions = [
        "1",
        "1.0",
        "1.0.0.0",
        "v1.0.0",
        "01.0.0",
        "1.01.0",
        "1.0.01",
        "1.0.0-01",
        "1.0.0-",
        "1.0.0+",
        "1.0.0-alpha..1",
        "1.0.0-@",
        "",
        "not-a-version",
    ]
    for bad in bad_versions:
        try:
            resolve_semver(None, bad, "1.0.0")
            raise AssertionError(f"Expected StrategyError for ours={bad!r}")
        except StrategyError:
            pass
        try:
            resolve_semver(None, "1.0.0", bad)
            raise AssertionError(f"Expected StrategyError for theirs={bad!r}")
        except StrategyError:
            pass
        try:
            resolve_semver(bad, "1.0.0", "2.0.0")
            raise AssertionError(f"Expected StrategyError for base={bad!r}")
        except StrategyError:
            pass


def _test_semver_unknown_strategy() -> None:
    try:
        resolve_semver(None, "1.0.0", "2.0.0", "latest")
        raise AssertionError("Expected StrategyError for unknown semver strategy")
    except StrategyError:
        pass


def _test_semver_split_major_diff() -> None:
    assert resolve_semver_split(None, ("2", "0", "0"), ("1", "9", "9")) == ("2", "0", "0")
    assert resolve_semver_split(None, ("1", "9", "9"), ("2", "0", "0")) == ("2", "0", "0")


def _test_semver_split_minor_and_patch_diff() -> None:
    # Contract §3.1 example: (2,1,0) vs (2,0,3) -> (2,1,0)
    assert resolve_semver_split(None, ("2", "1", "0"), ("2", "0", "3")) == ("2", "1", "0")
    assert resolve_semver_split(None, ("2", "0", "3"), ("2", "1", "0")) == ("2", "1", "0")
    assert resolve_semver_split(None, ("1", "0", "5"), ("1", "0", "6")) == ("1", "0", "6")


def _test_semver_split_equal_keeps_ours() -> None:
    assert resolve_semver_split(None, ("2", "1", "0"), ("2", "1", "0")) == ("2", "1", "0")
    # Preserves winning original strings
    assert resolve_semver_split(None, ("02", "1", "0"), ("2", "1", "0")) == ("02", "1", "0")
    assert resolve_semver_split(None, ("2", "1", "0"), ("02", "1", "0")) == ("2", "1", "0")


def _test_semver_split_with_base() -> None:
    assert resolve_semver_split(
        ("1", "0", "0"),
        ("2", "1", "0"),
        ("2", "0", "3"),
    ) == ("2", "1", "0")


def _test_semver_split_invalid_inputs() -> None:
    bad_splits = [
        ("1", "0"),
        ("1", "0", "0", "0"),
        ("a", "1", "0"),
        ("-1", "1", "0"),
        ("1", "1.0", "0"),
    ]
    for bad in bad_splits:
        try:
            resolve_semver_split(None, bad, ("1", "0", "0"))  # type: ignore[arg-type]
            raise AssertionError(f"Expected StrategyError for {bad!r}")
        except StrategyError:
            pass
        try:
            resolve_semver_split(bad, ("1", "0", "0"), ("2", "0", "0"))  # type: ignore[arg-type]
            raise AssertionError(f"Expected StrategyError for base={bad!r}")
        except StrategyError:
            pass


def _test_semver_split_unknown_strategy() -> None:
    try:
        resolve_semver_split(None, ("1", "0", "0"), ("2", "0", "0"), "min")
        raise AssertionError("Expected StrategyError for unknown strategy")
    except StrategyError:
        pass


def _test_timestamp_same_offset() -> None:
    t1 = "2026-10-07T10:00:00+00:00"
    t2 = "2026-10-07T11:00:00+00:00"
    assert pick_timestamp_winner(t1, t2, [], []) == "theirs"
    assert pick_timestamp_winner(t2, t1, [], []) == "ours"


def _test_timestamp_different_offsets() -> None:
    # 09:48+01:00 (08:48 UTC) vs 09:30+00:00 (09:30 UTC) -> 09:30+00:00 is later
    ours = "2026-10-07T09:48:41.192829+01:00"
    theirs = "2026-10-07T09:30:00.000000+00:00"
    assert pick_timestamp_winner(ours, theirs, ["mac"], ["cloudtop"]) == "theirs"
    assert pick_timestamp_winner(theirs, ours, ["cloudtop"], ["mac"]) == "ours"


def _test_timestamp_microseconds() -> None:
    t1 = "2026-10-07T12:00:00.000001Z"
    t2 = "2026-10-07T12:00:00.000002Z"
    assert pick_timestamp_winner(t1, t2, [], []) == "theirs"
    assert pick_timestamp_winner(t2, t1, [], []) == "ours"


def _test_timestamp_tie_coupled_smaller_wins() -> None:
    t_ours = "2026-10-07T09:30:00+01:00"
    t_theirs = "2026-10-07T08:30:00+00:00"  # equal instants
    # theirs coupled is lexically smaller -> theirs wins
    assert pick_timestamp_winner(t_ours, t_theirs, ["zzz"], ["aaa"]) == "theirs"
    # ours coupled is lexically smaller -> ours wins
    assert pick_timestamp_winner(t_ours, t_theirs, ["aaa"], ["zzz"]) == "ours"


def _test_timestamp_full_tie_keeps_ours() -> None:
    t_ours = "2026-10-07T09:30:00+01:00"
    t_theirs = "2026-10-07T08:30:00+00:00"
    assert pick_timestamp_winner(t_ours, t_theirs, ["same"], ["same"]) == "ours"
    assert pick_timestamp_winner(t_ours, t_theirs, [], []) == "ours"


def _test_timestamp_naive_rejected() -> None:
    naive = "2026-10-07T10:00:00"
    aware = "2026-10-07T10:00:00+00:00"
    try:
        pick_timestamp_winner(naive, aware, [], [])
        raise AssertionError("Expected StrategyError for naive timestamp")
    except StrategyError:
        pass
    try:
        pick_timestamp_winner(aware, naive, [], [])
        raise AssertionError("Expected StrategyError for naive timestamp")
    except StrategyError:
        pass


def _test_timestamp_invalid_string() -> None:
    aware = "2026-10-07T10:00:00+00:00"
    for bad in ["not-a-date", "2026-99-99T00:00:00Z", ""]:
        try:
            pick_timestamp_winner(bad, aware, [], [])
            raise AssertionError(f"Expected StrategyError for {bad!r}")
        except StrategyError:
            pass


def _test_timestamp_invalid_coupled() -> None:
    aware = "2026-10-07T10:00:00+00:00"
    try:
        pick_timestamp_winner(aware, aware, "not-a-list", [])  # type: ignore[arg-type]
        raise AssertionError("Expected StrategyError for non-list coupled")
    except StrategyError:
        pass


def _test_timestamp_unknown_strategy() -> None:
    aware = "2026-10-07T10:00:00+00:00"
    try:
        pick_timestamp_winner(aware, aware, [], [], "earliest")
        raise AssertionError("Expected StrategyError for unknown strategy")
    except StrategyError:
        pass


SELF_TESTS: list[tuple[str, Callable[[], None]]] = [
    ("counter_max_ours_wins", _test_counter_max_ours_wins),
    ("counter_max_theirs_wins", _test_counter_max_theirs_wins),
    ("counter_max_equal", _test_counter_max_equal),
    ("counter_max_preserves_zero_padding", _test_counter_max_preserves_zero_padding),
    ("counter_max_unique_ours_wins", _test_counter_max_unique_ours_wins),
    ("counter_max_unique_theirs_wins", _test_counter_max_unique_theirs_wins),
    ("counter_max_unique_equal", _test_counter_max_unique_equal),
    ("counter_max_unique_preserves_zero_padding", _test_counter_max_unique_preserves_zero_padding),
    ("counter_max_unique_width_growth", _test_counter_max_unique_width_growth),
    ("counter_base_handling", _test_counter_base_handling),
    ("counter_invalid_values", _test_counter_invalid_values),
    ("counter_unknown_strategy", _test_counter_unknown_strategy),
    ("semver_basic_precedence", _test_semver_basic_precedence),
    ("semver_prerelease_chain", _test_semver_prerelease_chain),
    ("semver_numeric_vs_alphanumeric_identifiers", _test_semver_numeric_vs_alphanumeric_identifiers),
    ("semver_numeric_identifiers_numerical_order", _test_semver_numeric_identifiers_numerical_order),
    ("semver_build_metadata_ignored", _test_semver_build_metadata_ignored),
    ("semver_equal_precedence_keeps_ours", _test_semver_equal_precedence_keeps_ours),
    ("semver_with_base", _test_semver_with_base),
    ("semver_invalid_formats", _test_semver_invalid_formats),
    ("semver_unknown_strategy", _test_semver_unknown_strategy),
    ("semver_split_major_diff", _test_semver_split_major_diff),
    ("semver_split_minor_and_patch_diff", _test_semver_split_minor_and_patch_diff),
    ("semver_split_equal_keeps_ours", _test_semver_split_equal_keeps_ours),
    ("semver_split_with_base", _test_semver_split_with_base),
    ("semver_split_invalid_inputs", _test_semver_split_invalid_inputs),
    ("semver_split_unknown_strategy", _test_semver_split_unknown_strategy),
    ("timestamp_same_offset", _test_timestamp_same_offset),
    ("timestamp_different_offsets", _test_timestamp_different_offsets),
    ("timestamp_microseconds", _test_timestamp_microseconds),
    ("timestamp_tie_coupled_smaller_wins", _test_timestamp_tie_coupled_smaller_wins),
    ("timestamp_full_tie_keeps_ours", _test_timestamp_full_tie_keeps_ours),
    ("timestamp_naive_rejected", _test_timestamp_naive_rejected),
    ("timestamp_invalid_string", _test_timestamp_invalid_string),
    ("timestamp_invalid_coupled", _test_timestamp_invalid_coupled),
    ("timestamp_unknown_strategy", _test_timestamp_unknown_strategy),
]
