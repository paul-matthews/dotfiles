# Link-file rules, shared by script/bootstrap and script/test. Sourced, not run.
#
# A *.symlink or *.configlink file may end in machine tags, the same rule the
# zsh loader applies to *.zsh: it is linked only if every tag is one of this
# machine's tags, and the tags are dropped from the link's name.
#
#   zsh/zshrc.symlink              ~/.zshrc on every machine
#   zsh/zshenv.darwin.symlink      ~/.zshenv on Macs
#   zsh/zshenv.work.linux.symlink  ~/.zshenv on work Linux boxes
#
# Only the built-in tags count in link names (LINK_TAGS), so names that
# simply contain dots keep working: gitconfig.local.symlink is ~/.gitconfig.local.
# Two files that would claim the same link on one machine are an error.
#
# Bash 3.2 compatible (macOS /bin/bash).

LINK_TAGS="home work darwin linux pi"

# machine_tags: this machine's tags, one per line, built the way
# zsh/loader.zsh builds DOTFILES_TAGS (keep the two in step): the profile
# ($PROFILE, else ~/.dotfiles-profile, else home), the OS, pi on a Raspberry
# Pi, ~/.dotfiles-tags, and any tags in the TAGS array. BOOTSTRAP_TAGS
# (space-separated) replaces all of it; script/test uses that.
machine_tags () {
  if [ -n "${BOOTSTRAP_TAGS:-}" ]
  then
    printf '%s\n' $BOOTSTRAP_TAGS
    return 0
  fi
  local profile="${PROFILE:-}" os t
  if [ -z "$profile" ] && [ -r "$HOME/.dotfiles-profile" ]
  then
    profile="$(tr -d '[:space:]' < "$HOME/.dotfiles-profile")"
  fi
  case "$profile" in
    home|work) ;;
    *) profile=home ;;
  esac
  os="$(uname -s | tr '[:upper:]' '[:lower:]')"
  echo "$profile"
  echo "$os"
  if [ "$os" = linux ] && [ -r /proc/device-tree/model ] && grep -qi 'raspberry pi' /proc/device-tree/model 2>/dev/null
  then
    echo pi
  fi
  if [ -r "$HOME/.dotfiles-tags" ]
  then
    tr -s '[:space:]' '\n' < "$HOME/.dotfiles-tags"
  fi
  for t in ${TAGS[@]+"${TAGS[@]}"}
  do
    echo "$t"
  done
  return 0
}

# link_variant <name>: split trailing built-in tags off a link file's name
# (extension already removed). Sets VARIANT_NAME and VARIANT_TAGS.
link_variant () {
  VARIANT_NAME="$1"
  VARIANT_TAGS=""
  local last
  while [ "${VARIANT_NAME#*.}" != "$VARIANT_NAME" ]
  do
    last="${VARIANT_NAME##*.}"
    case " $LINK_TAGS " in
      *" $last "*) ;;
      *) break ;;
    esac
    VARIANT_TAGS="$last $VARIANT_TAGS"
    VARIANT_NAME="${VARIANT_NAME%.*}"
  done
}

# link_plan <root> <ext> <dst-prefix> <machine tags>: print "src<TAB>dst" for
# every <root>/*/*.<ext> (and <root>/*.<ext>) whose tags all match. If two
# files want the same dst, print why and return 1.
link_plan () {
  local root="$1" ext="$2" prefix="$3" have=" $4 " src dst t ok plan="" seen=""
  for src in $(find -H "$root" -maxdepth 2 -name "*.$ext" -not -path '*.git*' | LC_ALL=C sort)
  do
    link_variant "$(basename "${src%.*}")"
    ok=true
    for t in $VARIANT_TAGS
    do
      case "$have" in
        *" $t "*) ;;
        *) ok=false ;;
      esac
    done
    [ "$ok" = true ] || continue
    dst="$prefix$VARIANT_NAME"
    case "$seen" in
      *"	$dst	"*)
        echo "two files want $dst on this machine (tags:$have): $(printf '%s' "$plan" | awk -F'\t' -v d="$dst" '$2 == d {print $1}') and $src"
        return 1 ;;
    esac
    seen="$seen	$dst	"
    plan="$plan$src	$dst
"
  done
  printf '%s' "$plan"
}
