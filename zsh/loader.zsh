# Dotfiles machine tags and topic loader.
#
# Sourced by zsh/zshrc.symlink. Kept out of zshrc so that if this file ever
# fails to parse, zshrc can fall back to a plain loader and a shell still
# comes up.
#
# Machine tags
#   DOTFILES_PROFILE  home | work, read from ~/.dotfiles-profile
#                     (written by `script/bootstrap --profile home|work`)
#   DOTFILES_TAGS     space-separated: the profile, the OS (darwin | linux),
#                     `pi` on a Raspberry Pi, plus any extra tags recorded in
#                     ~/.dotfiles-tags by `script/bootstrap --tag <name>`
#
# Topic files
#   A file is sourced only if every tag in its name is in DOTFILES_TAGS:
#     foo.zsh              everywhere
#     foo.work.zsh         work machines
#     foo.work.darwin.zsh  work Macs only
#     foo.linux.zsh        Pis and Linux boxes
#     foo.pi.zsh           Pis only
#   Tags are stripped before a file is classified, so path.work.zsh still
#   loads first and completion.work.zsh still loads last.
#
# Safe mode
#   DOTFILES_SAFE=1 zsh   skips every topic file, for repairing a broken setup.

#------------------------------------------------------------------------------
# Machine tags
#------------------------------------------------------------------------------
_dotfiles_build_tags() {
  local profile_file="$HOME/.dotfiles-profile"
  local profile=""
  [[ -r "$profile_file" ]] && profile="${$(<"$profile_file")//[[:space:]]/}"

  case "$profile" in
    home|work) ;;
    "")
      print -u2 "dotfiles: no ~/.dotfiles-profile, assuming home (run script/bootstrap --profile home|work)"
      profile=home ;;
    *)
      print -u2 "dotfiles: ~/.dotfiles-profile says '$profile', expected home or work; assuming home"
      profile=home ;;
  esac
  export DOTFILES_PROFILE="$profile"

  local os="${${$(uname -s):l}}"
  local -a tags=("$profile" "$os")

  if [[ "$os" == linux && -r /proc/device-tree/model ]] \
     && grep -qi 'raspberry pi' /proc/device-tree/model 2>/dev/null; then
    tags+=(pi)
  fi

  if [[ -r "$HOME/.dotfiles-tags" ]]; then
    tags+=(${=$(<"$HOME/.dotfiles-tags")})
  fi

  typeset -gUa _dotfiles_tags
  _dotfiles_tags=("${tags[@]}")
  export DOTFILES_TAGS="${(j: :)_dotfiles_tags}"
}

# True if every tag embedded in the file name is one of this machine's tags.
_dotfiles_file_enabled() {
  local base="${1:t:r}"
  local -a parts=("${(@s:.:)base}")
  local t
  for t in "${parts[@]:1}"; do
    (( ${_dotfiles_tags[(Ie)$t]} )) || return 1
  done
  return 0
}

# path | completion | topic, ignoring any tags in the name.
_dotfiles_file_kind() {
  local base="${1:t:r}"
  case "${base%%.*}" in
    path)       print -r -- path ;;
    completion) print -r -- completion ;;
    *)          print -r -- topic ;;
  esac
}

#------------------------------------------------------------------------------
# Topic loader
#------------------------------------------------------------------------------
_dotfiles_load_topics() {
  local -a config_files path_files topic_files completion_files
  local file
  typeset -U config_files
  config_files=($ZSH/**/*.zsh)

  for file in "${config_files[@]}"; do
    [[ "$file" == */antigen.zsh || "$file" == */zsh/loader.zsh ]] && continue
    _dotfiles_file_enabled "$file" || continue
    case "$(_dotfiles_file_kind "$file")" in
      path)       path_files+=("$file") ;;
      completion) completion_files+=("$file") ;;
      *)          topic_files+=("$file") ;;
    esac
  done

  for file in "${path_files[@]}" "${topic_files[@]}" "${completion_files[@]}"; do
    source "$file"
  done
}

_dotfiles_build_tags

if [[ -n "${DOTFILES_SAFE:-}" ]]; then
  print -u2 "dotfiles: DOTFILES_SAFE is set, topic files not loaded"
else
  _dotfiles_load_topics
fi

true
