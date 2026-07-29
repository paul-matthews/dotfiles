# Gandalf CLI Prompt Integration
zmodload zsh/datetime 2>/dev/null

gandalf_prompt_preexec() {
  local cmd=$1
  if [[ "$cmd" =~ ^(gcert|rw)(\ |$) ]]; then
    export GANDALF_LAST_CMD_WAS_AUTH=1
    mkdir -p ~/.gandalf 2>/dev/null
    # Write size > 0 to trigger menu bar app signal watcher
    echo "1" > ~/.gandalf/local_sync_signal 2>/dev/null
    echo "1" > ~/.gandalf/prompt_refresh_force 2>/dev/null
  fi
}

gandalf_prompt_precmd() {
  local exit_code=$?
  if [[ -n "$GANDALF_LAST_CMD_WAS_AUTH" ]]; then
    if [[ $exit_code -eq 0 ]]; then
      # Optimistically mark as authenticated to refresh the prompt instantly
      mkdir -p ~/.gandalf 2>/dev/null
      echo "{\"is_authed\": true, \"loas2_seconds\": 50000, \"corp_normal_seconds\": 50000, \"last_checked\": $EPOCHSECONDS}" > ~/.gandalf/prompt_status.cache 2>/dev/null
    fi
    unset GANDALF_LAST_CMD_WAS_AUTH
  fi
}

autoload -Uz add-zsh-hook
add-zsh-hook preexec gandalf_prompt_preexec
add-zsh-hook precmd gandalf_prompt_precmd
