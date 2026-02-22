# Cosmic Clock project commands
# These use $COSMIC_ROOT (set by direnv when in the project) and
# fall back to finding the project root if you're not in it.

_cosmic_root() {
  echo "${COSMIC_ROOT:-$HOME/src/pico/cosmic-clock}"
}

cpush()  { "$(_cosmic_root)/bin/cosmic-push" "$@"; }
clogs()  { "$(_cosmic_root)/bin/cosmic-logs" "$@"; }
ctime()  { "$(_cosmic_root)/bin/cosmic-logs" -l timeline "$@"; }
cbuild() { "$(_cosmic_root)/script/build-cosmic-push.sh" "$@"; }
cbq()    { "$(_cosmic_root)/script/build-cosmic-push.sh" --quick "$@"; }
cbp()    { cbuild --quick && cpush "$@"; }
