#!/usr/bin/env bash
#
# Hand off to tool-roll's installer (AI skills etc.), if tool-roll is here.
#
# Looks only in these places, first verified one wins:
#   $TOOL_ROLL_DIR, ~/src/tool-roll (primary), ~/tool-roll (fallback)
# A candidate must be owned by you, with a script/install nobody else can
# write, and a git origin of paul-matthews/tool-roll. Ownership is checked
# before git runs inside it. Always exits 0: dotfiles never fails because of
# tool-roll. Arguments (e.g. --dry-run) go to script/install.
# Interface: docs/install-contract.md in tool-roll.

info () { printf "  [ \033[00;34m..\033[0m ] %s\n" "$1"; }
warn () { printf "  [ \033[0;33m!!\033[0m ] %s\n" "$1"; }

# verify <dir>: succeed if dir is a tool-roll we trust; say why not otherwise
verify () {
  local dir="$1" inst="$1/script/install" url
  [ -d "$dir" ] || return 1
  if [ ! -O "$dir" ]; then warn "tool-roll: $dir not owned by $USER; skipped"; return 1; fi
  if [ ! -f "$inst" ] || [ -L "$inst" ] || [ ! -O "$inst" ]; then
    warn "tool-roll: $inst missing, a symlink, or not owned by $USER; skipped"; return 1
  fi
  if [ -n "$(find "$inst" -maxdepth 0 \( -perm -020 -o -perm -002 \))" ]; then
    warn "tool-roll: $inst is group/world-writable (permissions); skipped"; return 1
  fi
  url="$(git -C "$dir" remote get-url origin 2>/dev/null)"
  case "$url" in
    git@github.com:paul-matthews/tool-roll|git@github.com:paul-matthews/tool-roll.git) ;;
    ssh://git@github.com/paul-matthews/tool-roll|ssh://git@github.com/paul-matthews/tool-roll.git) ;;
    https://github.com/paul-matthews/tool-roll|https://github.com/paul-matthews/tool-roll.git) ;;
    *) warn "tool-roll: $dir origin is '${url:-none}', not paul-matthews/tool-roll (origin mismatch); skipped"; return 1 ;;
  esac
  [ -x "$inst" ] || { warn "tool-roll: $inst not executable; skipped"; return 1; }
}

found=""
for dir in ${TOOL_ROLL_DIR:+"$TOOL_ROLL_DIR"} "$HOME/src/tool-roll" "$HOME/tool-roll"; do
  verify "$dir" || continue
  if [ -z "$found" ]; then
    found="$dir"
  elif [ "$dir" != "$found" ]; then
    warn "tool-roll: second copy at $dir ignored (using $found)"
  fi
done

if [ -z "$found" ]; then
  info "tool-roll not found (looked in ${TOOL_ROLL_DIR:+$TOOL_ROLL_DIR, }~/src/tool-roll, ~/tool-roll); skipping"
  exit 0
fi

info "tool-roll: $found/script/install"
"$found/script/install" "$@" || warn "tool-roll: installer finished with problems (exit $?)"
exit 0
