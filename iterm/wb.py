#!/usr/bin/env -S uv run --quiet --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["iterm2>=2.24"]
# ///
"""wb.py: the iTerm side of `wb` (workbench). Called by the `wb` shell function
in iterm/wb.darwin.zsh, which resolves projects and passes everything in as
arguments; nothing here knows a project name or path.

Tabs say which project they belong to through the iTerm user variables
wbGroup and wbColor, set by the tab colour engine (system/tabcolor.zsh).

  start  --name N --color "R G B" --dir D --roles "ai control" --ai TOOL [--new-window|--new-tabs]
  group                 group this window's tabs by their wbGroup
  add    [--name N --color C]
                        put this tab in its project's group (or the named one)
  move   [--to new|N]   move this tab's group to a new window or window N
  focus  [--name N]     expand that group and collapse the rest; no name: expand all
  ls     [--json]       groups and tabs in every window
  ping                  connection facts for `wb doctor`
  _selftest             planner tests, no iTerm needed

Every verb takes --session $ITERM_SESSION_ID. One connection per run, never
retried: exit 0 ok, 1 failed, 2 usage.
"""

import asyncio
import json
import os
import sys
import time

CONNECT_TIMEOUT = 3.0


def die(msg, code=1):
    print(f"wb: {msg}", file=sys.stderr)
    sys.stdout.flush()
    os._exit(code)


# --- pure planning (tested by _selftest) -------------------------------------

def plan_group(tabs, groups):
    """Decide how `wb group` files tabs into groups.

    tabs:   [{"id", "want", "group"}] in tab order; want is the tab's wbGroup
            (None when the tab never published one, "" for no project); group
            is the id of the group it is in, or None
    groups: [{"id", "name"}] existing groups in tab order

    A tab moves only when it has a project and is ungrouped or in a group with
    another name; it joins the first group with its name, or a new one. Tabs
    already in a matching group stay put, which keeps a second set of the same
    project apart and keeps tabs added by hand.

    Returns (adds, creates, unknown): adds is [(tab id, group id)], creates is
    [(name, [tab ids])] in first-seen order, unknown is [tab id].
    """
    name_of = {g["id"]: g["name"] for g in groups}
    first_with = {}
    for g in groups:
        first_with.setdefault(g["name"], g["id"])
    adds, creates, unknown = [], {}, []
    for t in tabs:
        want = t["want"]
        if want is None:
            unknown.append(t["id"])
            continue
        if not want or name_of.get(t["group"]) == want:
            continue
        if want in first_with:
            adds.append((t["id"], first_with[want]))
        else:
            creates.setdefault(want, []).append(t["id"])
    return adds, list(creates.items()), unknown


def pick_group(groups, name, mine=None):
    """The group to use for `name`: the one holding this tab if it matches,
    else the first with that name. groups: [{"id", "name"}]; returns an id or None."""
    if mine and any(g["id"] == mine and g["name"] == name for g in groups):
        return mine
    return next((g["id"] for g in groups if g["name"] == name), None)


def plan_start_roles(roles, adopt_current=True):
    """Order roles for `wb start`: when adopting the current tab, the first
    non-ai role goes first so the existing shell becomes the control tab and
    AI opens in a new tab. Returns (ordered_roles, create_roles)."""
    if not adopt_current:
        return list(roles), list(roles)
    non_ai = [r for r in roles if r != "ai"]
    if non_ai:
        first = non_ai[0]
        idx = roles.index(first)
        ordered = [first] + roles[:idx] + roles[idx + 1:]
    else:
        ordered = list(roles)
    return ordered, ordered[1:]


def selftest():
    T = lambda i, want, group=None: {"id": i, "want": want, "group": group}
    G = lambda i, name: {"id": i, "name": name}
    cases = [
        # ungrouped tabs of one project form one new group
        ([T("a", "🪐 Cosmic"), T("b", "🪐 Cosmic")], [], ([], [("🪐 Cosmic", ["a", "b"])], [])),
        # no project, or never published: untouched; unknown reported
        ([T("a", ""), T("b", None)], [], ([], [], ["b"])),
        # a tab in the right group stays; an ungrouped one joins the first match
        ([T("a", "X", "g1"), T("b", "X", "g2"), T("c", "X")], [G("g1", "X"), G("g2", "X")],
         ([("c", "g1")], [], [])),
        # a tab that cd'd to another project moves; a hand-added tab stays
        ([T("a", "Y", "g1"), T("b", "", "g1")], [G("g1", "X")], ([], [("Y", ["a"])], [])),
        # misfiled tab joins an existing group of its own name
        ([T("a", "Y", "g1")], [G("g1", "X"), G("g2", "Y")], ([("a", "g2")], [], [])),
    ]
    failed = 0
    for n, (tabs, groups, want) in enumerate(cases, 1):
        got = plan_group(tabs, groups)
        if got != want:
            failed += 1
            print(f"plan_group case {n}: got {got}, want {want}")
    groups = [G("g1", "X"), G("g2", "X")]
    for mine, want in ((None, "g1"), ("g2", "g2"), ("g3", "g1")):
        if pick_group(groups, "X", mine) != want:
            failed += 1
            print(f"pick_group mine={mine}: got {pick_group(groups, 'X', mine)}, want {want}")
    if pick_group(groups, "Z") is not None:
        failed += 1
        print("pick_group: expected None for an unknown name")
    start_cases = [
        (["ai", "control"], True, (["control", "ai"], ["ai"])),
        (["ai", "control", "run"], True, (["control", "ai", "run"], ["ai", "run"])),
        (["ai"], True, (["ai"], [])),
        (["ai", "control"], False, (["ai", "control"], ["ai", "control"])),
    ]
    for roles, adopt, want in start_cases:
        got = plan_start_roles(roles, adopt)
        if got != want:
            failed += 1
            print(f"plan_start_roles({roles}, {adopt}): got {got}, want {want}")
    print(f"wb.py selftest: {'ok' if not failed else f'{failed} failed'}")
    return 1 if failed else 0


# --- iTerm ---------------------------------------------------------------------

def color(rgb):
    import iterm2
    r, g, b = (int(c) for c in rgb.split())
    return iterm2.Color(r, g, b)


async def connect():
    import iterm2
    try:
        return await asyncio.wait_for(iterm2.Connection.async_create(), CONNECT_TIMEOUT)
    except Exception as e:  # refused, missing socket, auth, timeout
        die(f"cannot reach iTerm's Python API ({type(e).__name__}: {e}). "
            "Run `wb doctor`.")


def session_id(raw):
    """ITERM_SESSION_ID is w0t0p0:<UUID>; the API wants the UUID."""
    return (raw or "").split(":")[-1]


def locate(app, raw_session):
    sid = session_id(raw_session)
    if not sid:
        die("not inside iTerm (no ITERM_SESSION_ID)")
    session = app.get_session_by_id(sid)
    if session is None:
        die("this session is not known to iTerm")
    window, tab = app.get_window_and_tab_for_session(session)
    return session, window, tab


async def want_of(tab):
    """A tab's wbGroup: None when never published, "" for no project."""
    session = tab.current_session
    if session is None:
        return None
    value = await session.async_get_variable("user.wbGroup")
    return None if value is None else str(value)


async def color_of(tab):
    session = tab.current_session
    value = await session.async_get_variable("user.wbColor") if session else None
    return str(value) if value else ""


def groups_in(window):
    return [{"id": g.group_id, "name": g.name, "obj": g} for g in window.tab_groups]


async def refreshed_window(app, window_id):
    await app.async_refresh()
    return next(w for w in app.windows if w.window_id == window_id)


async def cmd_start(conn, app, a):
    import iterm2
    _, window, cur_tab = locate(app, a["session"])
    profile = iterm2.LocalWriteOnlyProfile()
    profile.set_initial_directory_mode(iterm2.InitialWorkingDirectory.INITIAL_WORKING_DIRECTORY_CUSTOM)
    profile.set_custom_directory(a["dir"])
    raw_roles = a["roles"].split()
    adopt_current = not a.get("new-window") and not a.get("new-tabs")
    roles, roles_left = plan_start_roles(raw_roles, adopt_current)
    tabs = []
    if a.get("new-window"):
        window = await iterm2.Window.async_create(conn, profile_customizations=profile)
        if window is None:
            die("iTerm did not create a window")
        tabs.append(window.current_tab)
        roles_left = roles[1:]
    elif adopt_current:
        tabs.append(cur_tab)
    for _ in roles_left:
        tab = await window.async_create_tab(profile_customizations=profile, select=False)
        if tab is None:
            die("iTerm did not create a tab")
        tabs.append(tab)
    for idx, (role, tab) in enumerate(zip(roles, tabs)):
        if adopt_current and idx == 0:
            continue
        text = f"{a['ai']}\n" if role == "ai" else f" role {role} >/dev/null\n"
        await tab.current_session.async_send_text(text)
    window = await refreshed_window(app, window.window_id)
    fresh = [app.get_tab_by_id(t.tab_id) for t in tabs]
    await window.async_create_tab_group(a["name"], fresh, color(a["color"]))
    first = fresh[roles.index("ai")] if "ai" in roles else fresh[0]
    await first.async_activate()
    print(f"{a['name']}: {len(fresh)} tab(s) in {'a new window' if a.get('new-window') else 'this window'}")


async def cmd_group(conn, app, a):
    _, window, _ = locate(app, a["session"])
    tabs, colors = [], {}
    for tab in window.tabs:
        want = await want_of(tab)
        group = tab.tab_group
        tabs.append({"id": tab.tab_id, "want": want, "group": group.group_id if group else None})
        if want:
            colors.setdefault(want, await color_of(tab))
    groups = groups_in(window)
    adds, creates, unknown = plan_group(tabs, groups)
    by_id = {g["id"]: g["obj"] for g in groups}
    for tab_id, group_id in adds:
        await app.get_tab_by_id(tab_id).async_add_to_tab_group(by_id[group_id])
    for name, ids in creates:
        await window.async_create_tab_group(name, [app.get_tab_by_id(i) for i in ids],
                                            color(colors[name]) if colors.get(name) else None)
    # re-apply name colours to groups that gained tabs, so they track palette edits
    for _, group_id in adds:
        g = by_id[group_id]
        if colors.get(g.name):
            await g.async_set_color(color(colors[g.name]))
    moved = len(adds) + sum(len(ids) for _, ids in creates)
    print(f"grouped {moved} tab(s): {len(creates)} new group(s), {len(adds)} joined existing")
    if unknown:
        print(f"{len(unknown)} tab(s) have not reported a project yet (press return in them, then rerun)")


async def cmd_add(conn, app, a):
    _, window, tab = locate(app, a["session"])
    name = a.get("name") or await want_of(tab)
    if not name:
        die("this tab has no project; name one: wb add <project>")
    mine = tab.tab_group
    target = pick_group(groups_in(window), name, mine.group_id if mine else None)
    if mine and target == mine.group_id:
        print(f"already in {name}")
        return
    if target:
        await tab.async_add_to_tab_group(next(g for g in window.tab_groups if g.group_id == target))
    else:
        rgb = a.get("color") or await color_of(tab)
        await window.async_create_tab_group(name, [tab], color(rgb) if rgb else None)
    print(f"added to {name}")


async def cmd_move(conn, app, a):
    _, window, tab = locate(app, a["session"])
    group = tab.tab_group
    if group is None:
        die("this tab is not in a group (wb group, or wb add)")
    name, rgb, collapsed = group.name, group.color, group.collapsed
    members = [t for t in window.tabs if t.tab_group and t.tab_group.group_id == group.group_id]
    dest = a.get("to") or "new"
    if dest == "new":
        target = await members[0].async_move_to_window()
        rest = members[1:]
        if rest:
            await target.async_set_tabs([members[0]] + rest)
    else:
        try:
            target = app.windows[int(dest) - 1]
        except (ValueError, IndexError):
            die(f"no window {dest} (see: wb ls)", 2)
        if target.window_id == window.window_id:
            print("already in that window")
            return
        await target.async_set_tabs(list(target.tabs) + members)
    target = await refreshed_window(app, target.window_id)
    moved = [app.get_tab_by_id(t.tab_id) for t in members]
    if not all(t.tab_group and t.tab_group.name == name for t in moved):
        new = await target.async_create_tab_group(name, moved, rgb)
        if collapsed:
            await new.async_set_collapsed(True)
    await moved[0].async_activate()
    print(f"moved {name} ({len(moved)} tab(s))")


async def cmd_focus(conn, app, a):
    _, window, tab = locate(app, a["session"])
    name = a.get("name")
    if not name:
        for g in window.tab_groups:
            await g.async_set_collapsed(False)
        print("expanded every group")
        return
    groups = groups_in(window)
    mine = tab.tab_group
    target = pick_group(groups, name, mine.group_id if mine else None)
    if target is None:
        for w in app.windows:  # not here: is it in another window?
            target = pick_group(groups_in(w), name)
            if target:
                window, groups = w, groups_in(w)
                break
    if target is None:
        die(f"no group named {name} (wb {a.get('preset') or '<project>'} starts one)")
    for g in groups:
        if g["id"] != target:
            await g["obj"].async_set_collapsed(True)
    obj = next(g["obj"] for g in groups if g["id"] == target)
    await obj.async_set_collapsed(False)
    first = next(t for t in window.tabs if t.tab_group and t.tab_group.group_id == target)
    await first.async_activate()
    print(f"focused {name}")


async def cmd_ls(conn, app, a):
    here = None
    if a.get("session"):
        s = app.get_session_by_id(session_id(a["session"]))
        if s:
            here = app.get_window_and_tab_for_session(s)[0]
    out = []
    for i, w in enumerate(app.windows, 1):
        groups = [{"name": g.name, "tabs": sum(1 for t in w.tabs if t.tab_group and t.tab_group.group_id == g.group_id),
                   "collapsed": g.collapsed} for g in w.tab_groups]
        loose = sum(1 for t in w.tabs if t.tab_group is None)
        out.append({"window": i, "current": w is here, "groups": groups, "ungrouped": loose})
    if a.get("json"):
        print(json.dumps(out, ensure_ascii=False))
        return
    for w in out:
        print(f"window {w['window']}{' (this one)' if w['current'] else ''}")
        for g in w["groups"]:
            print(f"  {g['name']}  {g['tabs']} tab(s){'  [collapsed]' if g['collapsed'] else ''}")
        if w["ungrouped"]:
            print(f"  ({w['ungrouped']} ungrouped tab(s))")


async def cmd_ping(conn, app, a):
    from iterm2.capabilities import supports_tab_groups
    print(f"tab_groups={1 if supports_tab_groups(conn) else 0}")
    sid = session_id(a.get("session"))
    print(f"session={'found' if sid and app.get_session_by_id(sid) else 'missing'}")


VERBS = {"start": cmd_start, "group": cmd_group, "add": cmd_add, "move": cmd_move,
         "focus": cmd_focus, "ls": cmd_ls, "ping": cmd_ping}
VALUE_OPTS = {"session", "name", "color", "dir", "roles", "ai", "to", "preset"}
FLAG_OPTS = {"new-window", "new-tabs", "json"}


def parse(argv):
    a = {}
    it = iter(argv)
    for arg in it:
        key = arg[2:] if arg.startswith("--") else None
        if key in VALUE_OPTS:
            a[key] = next(it, None)
            if a[key] is None:
                die(f"--{key} needs a value", 2)
        elif key in FLAG_OPTS:
            a[key] = True
        else:
            die(f"unknown argument '{arg}'", 2)
    return a


async def amain(verb, a):
    import iterm2
    t0 = time.monotonic()
    conn = await connect()
    app = await iterm2.async_get_app(conn)
    if verb == "ping":
        print(f"connect_ms={int((time.monotonic() - t0) * 1000)}")
    if verb not in ("ls", "ping"):
        from iterm2.capabilities import supports_tab_groups
        if not supports_tab_groups(conn):
            die("this iTerm has no tab group API (needs 3.7.5 or later; run wb doctor)")
    await VERBS[verb](conn, app, a)


def main(argv):
    if not argv or argv[0] in ("-h", "--help"):
        print(__doc__.strip())
        return 0 if argv else 2
    verb, rest = argv[0], argv[1:]
    if verb == "_selftest":
        return selftest()
    if verb not in VERBS:
        die(f"unknown verb '{verb}'", 2)
    a = parse(rest)
    if verb == "start":
        missing = [k for k in ("name", "color", "dir", "roles", "ai") if not a.get(k)]
        if missing:
            die(f"start needs --{', --'.join(missing)}", 2)
    try:
        asyncio.run(amain(verb, a))
    except SystemExit:
        raise
    except Exception as e:  # RPC refusals and the like: one line, not a trace
        die(f"{verb} failed: {type(e).__name__}: {e}")
    sys.stdout.flush()
    os._exit(0)  # skip websocket teardown noise


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
