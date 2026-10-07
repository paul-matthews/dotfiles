"""zdiff3 parsing, whitelist rule, and file resolution for gsp auto-merge.

See docs/gsp-merge-contract.md §3.3 and §4.
"""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any, Sequence

from . import strategies

MARKER_SIZE = 32
OURS_LABEL = "ours"
BASE_LABEL = "base"
THEIRS_LABEL = "theirs"


@dataclass
class Common:
    lines: list[str]  # lines WITHOUT trailing "\n"


@dataclass
class Conflict:
    ours: list[str]
    base: list[str]
    theirs: list[str]


class ParseError(ValueError):
    """Raised when git merge-file zdiff3 output cannot be parsed."""


def parse_zdiff3(text: str, marker_size: int = MARKER_SIZE) -> list[Common | Conflict]:
    """Parse output of `git merge-file -p --zdiff3 --marker-size=... -L ours -L base -L theirs O B T`.

    Returns a list of Common and Conflict segments.
    Raises ParseError on any malformed or nested structure.
    """
    if text.endswith("\n"):
        raw_lines = text[:-1].split("\n")
    elif text:
        raw_lines = text.split("\n")
    else:
        raw_lines = []

    ours_marker = f"{'<' * marker_size} {OURS_LABEL}"
    base_marker = f"{'|' * marker_size} {BASE_LABEL}"
    sep_marker = "=" * marker_size
    theirs_marker = f"{'>' * marker_size} {THEIRS_LABEL}"

    state = "COMMON"
    common_buf: list[str] = []
    ours_buf: list[str] = []
    base_buf: list[str] = []
    theirs_buf: list[str] = []
    segments: list[Common | Conflict] = []

    for line_idx, line in enumerate(raw_lines, start=1):
        clean = line[:-1] if line.endswith("\r") else line

        has_marker_prefix = any(
            clean.startswith(ch * marker_size) for ch in ("<", "|", "=", ">")
        )
        if has_marker_prefix:
            if clean not in (ours_marker, base_marker, sep_marker, theirs_marker):
                raise ParseError(f"line {line_idx}: malformed marker line: {clean!r}")

        if state == "COMMON":
            if clean == ours_marker:
                if common_buf:
                    segments.append(Common(lines=common_buf))
                    common_buf = []
                ours_buf = []
                state = "OURS"
            elif clean in (base_marker, sep_marker, theirs_marker):
                raise ParseError(f"line {line_idx}: unexpected marker {clean!r} in common section")
            else:
                common_buf.append(line)

        elif state == "OURS":
            if clean == base_marker:
                base_buf = []
                state = "BASE"
            elif clean == ours_marker:
                raise ParseError(f"line {line_idx}: nested conflict marker {clean!r}")
            elif clean in (sep_marker, theirs_marker):
                raise ParseError(f"line {line_idx}: unexpected marker {clean!r} in ours section")
            else:
                ours_buf.append(line)

        elif state == "BASE":
            if clean == sep_marker:
                theirs_buf = []
                state = "THEIRS"
            elif clean == ours_marker:
                raise ParseError(f"line {line_idx}: nested conflict marker {clean!r}")
            elif clean in (base_marker, theirs_marker):
                raise ParseError(f"line {line_idx}: unexpected marker {clean!r} in base section")
            else:
                base_buf.append(line)

        elif state == "THEIRS":
            if clean == theirs_marker:
                segments.append(Conflict(ours=ours_buf, base=base_buf, theirs=theirs_buf))
                ours_buf = []
                base_buf = []
                theirs_buf = []
                state = "COMMON"
            elif clean == ours_marker:
                raise ParseError(f"line {line_idx}: nested conflict marker {clean!r}")
            elif clean in (base_marker, sep_marker):
                raise ParseError(f"line {line_idx}: unexpected marker {clean!r} in theirs section")
            else:
                theirs_buf.append(line)

    if state != "COMMON":
        raise ParseError(f"unclosed conflict section at end of input (state: {state})")

    if common_buf:
        segments.append(Common(lines=common_buf))

    return segments


@dataclass
class LineResolution:
    rule: str
    base: str
    ours: str
    theirs: str
    result: str  # values, not whole lines


@dataclass
class FileResult:
    path: str
    resolvable: bool
    reason: str | None
    lines: list[LineResolution]  # one per resolved line, in file order
    content: str | None  # full resolved file text when resolvable


@dataclass(frozen=True)
class _Candidate:
    rule_name: str
    pattern: re.Pattern
    rule_type: str
    strategy: str
    frontmatter_only: bool
    kind: str  # "rule", "coupled", "group_major", "group_minor", "group_patch"
    rule_obj: Any
    coupled_index: int | None = None


def _get_frontmatter_range(text: str) -> tuple[int, int] | None:
    """Return (start_line, end_line) 1-based inclusive range of frontmatter in text.

    Returns None if text has no frontmatter (does not start with '---' or has no closing '---').
    """
    if text.endswith("\n"):
        lines = text[:-1].split("\n")
    elif text:
        lines = text.split("\n")
    else:
        return None

    if not lines:
        return None
    first = lines[0][:-1] if lines[0].endswith("\r") else lines[0]
    if first != "---":
        return None

    for idx in range(1, len(lines)):
        clean = lines[idx][:-1] if lines[idx].endswith("\r") else lines[idx]
        if clean == "---":
            return (1, idx + 1)
    return None


def _is_in_frontmatter(line_num: int, fm_range: tuple[int, int] | None) -> bool:
    """Check if 1-based line number falls within the frontmatter range."""
    return fm_range is not None and fm_range[0] <= line_num <= fm_range[1]


def _extract_search_lines(
    text: str, fm: tuple[int, int] | None, frontmatter_only: bool
) -> list[str] | None:
    """Extract candidate lines for per-file rule search, scoped to frontmatter if required."""
    if text.endswith("\n"):
        lines = text[:-1].split("\n")
    elif text:
        lines = text.split("\n")
    else:
        lines = []

    if frontmatter_only:
        if fm is None:
            return None
        return lines[fm[0] - 1 : fm[1]]
    return lines


def _resolve_timestamp_file(
    path: str,
    rule: Any,
    ours_text: str,
    theirs_text: str,
    ours_fm: tuple[int, int] | None,
    theirs_fm: tuple[int, int] | None,
    hunk_start_ours: int,
) -> tuple[str, str, str, list[str], list[str]] | FileResult:
    """Resolve timestamp winner and values per file.

    Returns (winner, ours_v, theirs_v, ours_coupled_vs, theirs_coupled_vs) or FileResult on failure.
    """
    ours_lines = _extract_search_lines(ours_text, ours_fm, rule.frontmatter_only)
    if ours_lines is None:
        return FileResult(
            path=path,
            resolvable=False,
            reason=f"hunk at line {hunk_start_ours}: timestamp rule '{rule.name}' is frontmatter_only but ours has no frontmatter",
            lines=[],
            content=None,
        )

    theirs_lines = _extract_search_lines(theirs_text, theirs_fm, rule.frontmatter_only)
    if theirs_lines is None:
        return FileResult(
            path=path,
            resolvable=False,
            reason=f"hunk at line {hunk_start_ours}: timestamp rule '{rule.name}' is frontmatter_only but theirs has no frontmatter",
            lines=[],
            content=None,
        )

    # Primary line in ours
    ours_p_matches = [
        rule.line.fullmatch(l[:-1] if l.endswith("\r") else l)
        for l in ours_lines
        if rule.line.fullmatch(l[:-1] if l.endswith("\r") else l)
    ]
    if len(ours_p_matches) != 1:
        return FileResult(
            path=path,
            resolvable=False,
            reason=f"hunk at line {hunk_start_ours}: timestamp rule '{rule.name}' primary line must occur exactly once in ours (found {len(ours_p_matches)})",
            lines=[],
            content=None,
        )
    ours_v = ours_p_matches[0].group("value")

    # Coupled lines in ours
    ours_c_vals: list[str] = []
    for c_idx, c_pat in enumerate(rule.coupled):
        c_matches = [
            c_pat.fullmatch(l[:-1] if l.endswith("\r") else l)
            for l in ours_lines
            if c_pat.fullmatch(l[:-1] if l.endswith("\r") else l)
        ]
        if len(c_matches) != 1:
            return FileResult(
                path=path,
                resolvable=False,
                reason=f"hunk at line {hunk_start_ours}: timestamp rule '{rule.name}' coupled line {c_idx} must occur exactly once in ours (found {len(c_matches)})",
                lines=[],
                content=None,
            )
        ours_c_vals.append(c_matches[0].group("value"))

    # Primary line in theirs
    theirs_p_matches = [
        rule.line.fullmatch(l[:-1] if l.endswith("\r") else l)
        for l in theirs_lines
        if rule.line.fullmatch(l[:-1] if l.endswith("\r") else l)
    ]
    if len(theirs_p_matches) != 1:
        return FileResult(
            path=path,
            resolvable=False,
            reason=f"hunk at line {hunk_start_ours}: timestamp rule '{rule.name}' primary line must occur exactly once in theirs (found {len(theirs_p_matches)})",
            lines=[],
            content=None,
        )
    theirs_v = theirs_p_matches[0].group("value")

    # Coupled lines in theirs
    theirs_c_vals: list[str] = []
    for c_idx, c_pat in enumerate(rule.coupled):
        c_matches = [
            c_pat.fullmatch(l[:-1] if l.endswith("\r") else l)
            for l in theirs_lines
            if c_pat.fullmatch(l[:-1] if l.endswith("\r") else l)
        ]
        if len(c_matches) != 1:
            return FileResult(
                path=path,
                resolvable=False,
                reason=f"hunk at line {hunk_start_ours}: timestamp rule '{rule.name}' coupled line {c_idx} must occur exactly once in theirs (found {len(c_matches)})",
                lines=[],
                content=None,
            )
        theirs_c_vals.append(c_matches[0].group("value"))

    try:
        winner = strategies.pick_timestamp_winner(
            ours_v, theirs_v, ours_c_vals, theirs_c_vals, strategy=rule.strategy
        )
    except Exception as exc:
        return FileResult(
            path=path,
            resolvable=False,
            reason=f"hunk at line {hunk_start_ours}: timestamp error: {exc}",
            lines=[],
            content=None,
        )

    return (winner, ours_v, theirs_v, ours_c_vals, theirs_c_vals)


def _resolve_semver_split_file(
    path: str,
    group: Any,
    base_text: str,
    ours_text: str,
    theirs_text: str,
    ours_fm: tuple[int, int] | None,
    theirs_fm: tuple[int, int] | None,
    hunk_start_ours: int,
) -> tuple[str, str, str] | FileResult:
    """Resolve (major, minor, patch) tuple per file.

    Returns winning (major, minor, patch) tuple or FileResult on failure.
    """
    ours_lines = _extract_search_lines(ours_text, ours_fm, group.frontmatter_only)
    if ours_lines is None:
        return FileResult(
            path=path,
            resolvable=False,
            reason=f"hunk at line {hunk_start_ours}: group '{group.name}' is frontmatter_only but ours has no frontmatter",
            lines=[],
            content=None,
        )

    theirs_lines = _extract_search_lines(theirs_text, theirs_fm, group.frontmatter_only)
    if theirs_lines is None:
        return FileResult(
            path=path,
            resolvable=False,
            reason=f"hunk at line {hunk_start_ours}: group '{group.name}' is frontmatter_only but theirs has no frontmatter",
            lines=[],
            content=None,
        )

    def find_matches(lines: list[str], pat: re.Pattern) -> list[re.Match]:
        return [
            pat.fullmatch(l[:-1] if l.endswith("\r") else l)
            for l in lines
            if pat.fullmatch(l[:-1] if l.endswith("\r") else l)
        ]

    # Ours
    o_maj = find_matches(ours_lines, group.major)
    o_min = find_matches(ours_lines, group.minor)
    o_pat = find_matches(ours_lines, group.patch)
    if len(o_maj) != 1 or len(o_min) != 1 or len(o_pat) != 1:
        return FileResult(
            path=path,
            resolvable=False,
            reason=f"hunk at line {hunk_start_ours}: group '{group.name}' components must occur exactly once in ours",
            lines=[],
            content=None,
        )
    ours_tuple = (o_maj[0].group("value"), o_min[0].group("value"), o_pat[0].group("value"))

    # Theirs
    t_maj = find_matches(theirs_lines, group.major)
    t_min = find_matches(theirs_lines, group.minor)
    t_pat = find_matches(theirs_lines, group.patch)
    if len(t_maj) != 1 or len(t_min) != 1 or len(t_pat) != 1:
        return FileResult(
            path=path,
            resolvable=False,
            reason=f"hunk at line {hunk_start_ours}: group '{group.name}' components must occur exactly once in theirs",
            lines=[],
            content=None,
        )
    theirs_tuple = (t_maj[0].group("value"), t_min[0].group("value"), t_pat[0].group("value"))

    # Base (may be missing → None)
    base_fm = _get_frontmatter_range(base_text) if base_text else None
    base_lines = _extract_search_lines(base_text, base_fm, group.frontmatter_only)
    base_tuple: tuple[str, str, str] | None = None
    if base_lines is not None and len(base_lines) > 0:
        b_maj = find_matches(base_lines, group.major)
        b_min = find_matches(base_lines, group.minor)
        b_pat = find_matches(base_lines, group.patch)
        if len(b_maj) == 1 and len(b_min) == 1 and len(b_pat) == 1:
            base_tuple = (b_maj[0].group("value"), b_min[0].group("value"), b_pat[0].group("value"))
        elif len(b_maj) == 0 and len(b_min) == 0 and len(b_pat) == 0:
            base_tuple = None
        else:
            return FileResult(
                path=path,
                resolvable=False,
                reason=f"hunk at line {hunk_start_ours}: group '{group.name}' components in base are inconsistent",
                lines=[],
                content=None,
            )

    try:
        resolved_tuple = strategies.resolve_semver_split(
            base_tuple, ours_tuple, theirs_tuple, strategy=group.strategy
        )
    except Exception as exc:
        return FileResult(
            path=path,
            resolvable=False,
            reason=f"hunk at line {hunk_start_ours}: semver_split error: {exc}",
            lines=[],
            content=None,
        )

    return resolved_tuple


def resolve_file(
    path: str,
    merged: str,
    base_text: str,
    ours_text: str,
    theirs_text: str,
    rules: Sequence[Any],
    groups: Sequence[Any],
) -> FileResult:
    """Resolve conflicts in `merged` using the declared rules and groups.

    Never raises for bad input: returns FileResult(resolvable=False, reason=...).
    """
    try:
        return _resolve_file_impl(
            path, merged, base_text, ours_text, theirs_text, rules, groups
        )
    except Exception as exc:
        return FileResult(
            path=path,
            resolvable=False,
            reason=f"unexpected error in hunk: {exc}",
            lines=[],
            content=None,
        )


def _resolve_file_impl(
    path: str,
    merged: str,
    base_text: str,
    ours_text: str,
    theirs_text: str,
    rules: Sequence[Any],
    groups: Sequence[Any],
) -> FileResult:
    # 1. parse_zdiff3 succeeds and there is at least one Conflict.
    try:
        segments = parse_zdiff3(merged)
    except ParseError as exc:
        return FileResult(
            path=path,
            resolvable=False,
            reason=f"hunk parse error: {exc}",
            lines=[],
            content=None,
        )

    conflicts = [s for s in segments if isinstance(s, Conflict)]
    if not conflicts:
        return FileResult(
            path=path,
            resolvable=False,
            reason="no conflict hunks found in merged text",
            lines=[],
            content=None,
        )

    # Frontmatter ranges for ours and theirs
    ours_fm = _get_frontmatter_range(ours_text)
    theirs_fm = _get_frontmatter_range(theirs_text)

    # Build list of candidates
    candidates: list[_Candidate] = []
    for r in rules:
        candidates.append(
            _Candidate(
                rule_name=r.name,
                pattern=r.line,
                rule_type=r.type,
                strategy=r.strategy,
                frontmatter_only=r.frontmatter_only,
                kind="rule",
                rule_obj=r,
                coupled_index=None,
            )
        )
        for c_idx, c_pat in enumerate(r.coupled):
            candidates.append(
                _Candidate(
                    rule_name=r.name,
                    pattern=c_pat,
                    rule_type=r.type,
                    strategy=r.strategy,
                    frontmatter_only=r.frontmatter_only,
                    kind="coupled",
                    rule_obj=r,
                    coupled_index=c_idx,
                )
            )

    for g in groups:
        candidates.append(
            _Candidate(
                rule_name=g.name,
                pattern=g.major,
                rule_type=g.type,
                strategy=g.strategy,
                frontmatter_only=g.frontmatter_only,
                kind="group_major",
                rule_obj=g,
                coupled_index=None,
            )
        )
        candidates.append(
            _Candidate(
                rule_name=g.name,
                pattern=g.minor,
                rule_type=g.type,
                strategy=g.strategy,
                frontmatter_only=g.frontmatter_only,
                kind="group_minor",
                rule_obj=g,
                coupled_index=None,
            )
        )
        candidates.append(
            _Candidate(
                rule_name=g.name,
                pattern=g.patch,
                rule_type=g.type,
                strategy=g.strategy,
                frontmatter_only=g.frontmatter_only,
                kind="group_patch",
                rule_obj=g,
                coupled_index=None,
            )
        )

    # Cache for per-file resolutions
    timestamp_cache: dict[str, tuple[str, str, str, list[str], list[str]]] = {}
    semver_split_cache: dict[str, tuple[str, str, str]] = {}

    line_resolutions: list[LineResolution] = []
    resolved_lines_info: list[tuple[str, re.Pattern]] = []
    all_resolved_lines: list[str] = []

    ours_line_num = 1
    theirs_line_num = 1

    for seg in segments:
        if isinstance(seg, Common):
            all_resolved_lines.extend(seg.lines)
            ours_line_num += len(seg.lines)
            theirs_line_num += len(seg.lines)
            continue

        assert isinstance(seg, Conflict)
        hunk_start_ours = ours_line_num
        hunk_start_theirs = theirs_line_num

        # 2. For every Conflict: len(ours) == len(base) == len(theirs) and count > 0.
        if (
            len(seg.ours) != len(seg.base)
            or len(seg.ours) != len(seg.theirs)
            or len(seg.ours) == 0
        ):
            return FileResult(
                path=path,
                resolvable=False,
                reason=(
                    f"hunk at line {hunk_start_ours}: unaligned conflict sections "
                    f"({len(seg.ours)} ours, {len(seg.base)} base, {len(seg.theirs)} theirs)"
                ),
                lines=[],
                content=None,
            )

        hunk_resolved_lines: list[str] = []

        for i in range(len(seg.ours)):
            o_line = seg.ours[i]
            b_line = seg.base[i]
            t_line = seg.theirs[i]
            cur_ours_line = hunk_start_ours + i
            cur_theirs_line = hunk_start_theirs + i

            # 3. Each aligned triple with ours == theirs passes through as ours.
            if o_line == t_line:
                hunk_resolved_lines.append(o_line)
                continue

            # 4. Every other aligned triple must have all three lines fully matched
            # by the same rule line regex, group component regex, or coupled regex.
            cr_o = o_line.endswith("\r")
            cr_b = b_line.endswith("\r")
            cr_t = t_line.endswith("\r")
            clean_o = o_line[:-1] if cr_o else o_line
            clean_b = b_line[:-1] if cr_b else b_line
            clean_t = t_line[:-1] if cr_t else t_line

            matching: list[tuple[_Candidate, re.Match, re.Match, re.Match, str, str, bool]] = []
            fm_rejected: list[_Candidate] = []
            span_rejected: list[_Candidate] = []

            for cand in candidates:
                m_o = cand.pattern.fullmatch(clean_o)
                m_b = cand.pattern.fullmatch(clean_b)
                m_t = cand.pattern.fullmatch(clean_t)
                if not (m_o and m_b and m_t):
                    continue

                if cand.frontmatter_only:
                    in_o = _is_in_frontmatter(cur_ours_line, ours_fm)
                    in_t = _is_in_frontmatter(cur_theirs_line, theirs_fm)
                    if not (in_o and in_t):
                        fm_rejected.append(cand)
                        continue

                if not (cr_o == cr_b == cr_t):
                    span_rejected.append(cand)
                    continue

                s_o, e_o = m_o.span("value")
                s_b, e_b = m_b.span("value")
                s_t, e_t = m_t.span("value")

                pref_o, suff_o = clean_o[:s_o], clean_o[e_o:]
                pref_b, suff_b = clean_b[:s_b], clean_b[e_b:]
                pref_t, suff_t = clean_t[:s_t], clean_t[e_t:]

                if pref_o != pref_b or pref_o != pref_t or suff_o != suff_b or suff_o != suff_t:
                    span_rejected.append(cand)
                    continue

                matching.append((cand, m_o, m_b, m_t, pref_o, suff_o, cr_o))

            if len(matching) > 1:
                return FileResult(
                    path=path,
                    resolvable=False,
                    reason=f"hunk at line {hunk_start_ours}: ambiguous rules for line",
                    lines=[],
                    content=None,
                )

            if len(matching) == 0:
                if fm_rejected:
                    return FileResult(
                        path=path,
                        resolvable=False,
                        reason=(
                            f"hunk at line {hunk_start_ours}: rule '{fm_rejected[0].rule_name}' "
                            f"is frontmatter_only but conflict is outside frontmatter"
                        ),
                        lines=[],
                        content=None,
                    )
                if span_rejected:
                    return FileResult(
                        path=path,
                        resolvable=False,
                        reason=(
                            f"hunk at line {hunk_start_ours}: text outside value span "
                            f"differs across base/ours/theirs"
                        ),
                        lines=[],
                        content=None,
                    )
                return FileResult(
                    path=path,
                    resolvable=False,
                    reason=f"hunk at line {hunk_start_ours}: no rule matched line {clean_o!r}",
                    lines=[],
                    content=None,
                )

            cand, m_o, m_b, m_t, pref, suff, had_cr = matching[0]
            val_o = m_o.group("value")
            val_b = m_b.group("value")
            val_t = m_t.group("value")

            # 5. Resolution
            if cand.kind == "rule" and cand.rule_type == "counter":
                try:
                    res_val = strategies.resolve_counter(
                        val_b, val_o, val_t, strategy=cand.strategy
                    )
                except Exception as exc:
                    return FileResult(
                        path=path,
                        resolvable=False,
                        reason=f"hunk at line {hunk_start_ours}: counter error: {exc}",
                        lines=[],
                        content=None,
                    )

            elif cand.kind == "rule" and cand.rule_type == "semver":
                try:
                    res_val = strategies.resolve_semver(
                        val_b, val_o, val_t, strategy=cand.strategy
                    )
                except Exception as exc:
                    return FileResult(
                        path=path,
                        resolvable=False,
                        reason=f"hunk at line {hunk_start_ours}: semver error: {exc}",
                        lines=[],
                        content=None,
                    )

            elif cand.rule_type == "timestamp":
                if cand.rule_name not in timestamp_cache:
                    t_res = _resolve_timestamp_file(
                        path,
                        cand.rule_obj,
                        ours_text,
                        theirs_text,
                        ours_fm,
                        theirs_fm,
                        hunk_start_ours,
                    )
                    if isinstance(t_res, FileResult):
                        return t_res
                    timestamp_cache[cand.rule_name] = t_res

                winner, ours_v, theirs_v, ours_c, theirs_c = timestamp_cache[cand.rule_name]
                if cand.kind == "rule":
                    res_val = ours_v if winner == "ours" else theirs_v
                else:
                    assert cand.coupled_index is not None
                    res_val = (
                        ours_c[cand.coupled_index]
                        if winner == "ours"
                        else theirs_c[cand.coupled_index]
                    )

            elif cand.rule_type == "semver_split":
                if cand.rule_name not in semver_split_cache:
                    s_res = _resolve_semver_split_file(
                        path,
                        cand.rule_obj,
                        base_text,
                        ours_text,
                        theirs_text,
                        ours_fm,
                        theirs_fm,
                        hunk_start_ours,
                    )
                    if isinstance(s_res, FileResult):
                        return s_res
                    semver_split_cache[cand.rule_name] = s_res

                winner_tuple = semver_split_cache[cand.rule_name]
                if cand.kind == "group_major":
                    res_val = winner_tuple[0]
                elif cand.kind == "group_minor":
                    res_val = winner_tuple[1]
                elif cand.kind == "group_patch":
                    res_val = winner_tuple[2]
                else:
                    return FileResult(
                        path=path,
                        resolvable=False,
                        reason=f"hunk at line {hunk_start_ours}: unknown group component {cand.kind}",
                        lines=[],
                        content=None,
                    )
            else:
                return FileResult(
                    path=path,
                    resolvable=False,
                    reason=f"hunk at line {hunk_start_ours}: unknown candidate type {cand.rule_type}",
                    lines=[],
                    content=None,
                )

            # 6. Resolved line is prefix + result + suffix
            resolved_line = pref + res_val + suff + ("\r" if had_cr else "")
            hunk_resolved_lines.append(resolved_line)
            line_resolutions.append(
                LineResolution(
                    rule=cand.rule_name,
                    base=val_b,
                    ours=val_o,
                    theirs=val_t,
                    result=res_val,
                )
            )
            resolved_lines_info.append((resolved_line, cand.pattern))

        all_resolved_lines.extend(hunk_resolved_lines)
        ours_line_num += len(seg.ours)
        theirs_line_num += len(seg.theirs)

    # 7. Post-checks
    # 7.1 No line starts with 7+ markers followed by space or end of line
    # unless that exact line also appears in ours_text or theirs_text.
    marker_re = re.compile(r"^(<{7,}|\|{7,}|={7,}|>{7,})( |$)")
    ours_raw_set = set(ours_text.split("\n"))
    theirs_raw_set = set(theirs_text.split("\n"))
    ours_clean_set = {l[:-1] if l.endswith("\r") else l for l in ours_raw_set}
    theirs_clean_set = {l[:-1] if l.endswith("\r") else l for l in theirs_raw_set}

    for r_line in all_resolved_lines:
        clean_r = r_line[:-1] if r_line.endswith("\r") else r_line
        if marker_re.match(clean_r):
            if (
                r_line not in ours_raw_set
                and r_line not in theirs_raw_set
                and clean_r not in ours_clean_set
                and clean_r not in theirs_clean_set
            ):
                return FileResult(
                    path=path,
                    resolvable=False,
                    reason="hunk post-check failed: conflict marker found in resolved content",
                    lines=[],
                    content=None,
                )

    # 7.2 Every resolved line must still fullmatch its regex.
    for r_line, pat in resolved_lines_info:
        clean_r = r_line[:-1] if r_line.endswith("\r") else r_line
        if not pat.fullmatch(clean_r):
            return FileResult(
                path=path,
                resolvable=False,
                reason=f"hunk post-check failed: resolved line {clean_r!r} does not match regex",
                lines=[],
                content=None,
            )

    # 7.3 Line count check.
    expected_line_count = sum(
        len(s.lines) for s in segments if isinstance(s, Common)
    ) + sum(len(s.ours) for s in segments if isinstance(s, Conflict))

    if len(all_resolved_lines) != expected_line_count:
        return FileResult(
            path=path,
            resolvable=False,
            reason="hunk post-check failed: line count mismatch",
            lines=[],
            content=None,
        )

    # Trailing newline preservation
    content = "\n".join(all_resolved_lines)
    if merged.endswith("\n"):
        content += "\n"

    return FileResult(
        path=path,
        resolvable=True,
        reason=None,
        lines=line_resolutions,
        content=content,
    )
