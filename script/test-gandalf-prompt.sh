#!/usr/bin/env zsh
# Automated tests for Gandalf CLI prompt integration
set -e

# Setup isolated environment
TEST_DIR="/tmp/gandalf-test-$(date +%s)"
TEST_HOME="$TEST_DIR/home"
TEST_BIN="$TEST_DIR/bin"
TEST_CWD="$TEST_HOME/project"

mkdir -p "$TEST_HOME" "$TEST_BIN" "$TEST_CWD"

# Copy compiled gandalf-prompt to test bin if it exists, otherwise build it
PROMPT_BIN="/Users/pmatthews/src/gandalf/build/gandalf-prompt"
if [[ ! -f "$PROMPT_BIN" ]]; then
  echo "Building gandalf-prompt..."
  (cd /Users/pmatthews/src/gandalf && swift build -c release)
  PROMPT_BIN="/Users/pmatthews/src/gandalf/.build/release/gandalf-prompt"
fi
cp "$PROMPT_BIN" "$TEST_BIN/gandalf-prompt"

# Set environment
export HOME="$TEST_HOME"
export PATH="$TEST_BIN:$PATH"

# Write mock gcertstatus script so we don't call the real gcertstatus which can hang
cat << 'EOF' > "$TEST_BIN/gcertstatus"
#!/bin/sh
echo "LOAS2:9999"
echo "corp/normal:8888"
EOF
chmod +x "$TEST_BIN/gcertstatus"

# Helper to assert output and exit code
assert_prompt() {
  local expected_exit="$1"
  local expected_out="$2"
  local msg="$3"
  
  local actual_out
  local actual_exit=0
  
  # Run command and capture stdout and exit code, avoiding set -e abort
  actual_out=$(gandalf-prompt 2>/dev/null) || actual_exit=$?
  
  if [[ "$actual_out" != "$expected_out" ]]; then
    echo "FAIL: $msg (Output mismatch)"
    echo "  Expected: '$expected_out'"
    echo "  Actual:   '$actual_out'"
    exit 1
  elif [[ "$actual_exit" -ne "$expected_exit" ]]; then
    echo "FAIL: $msg (Exit code mismatch)"
    echo "  Expected: $expected_exit"
    echo "  Actual:   $actual_exit"
    exit 1
  else
    echo "PASS: $msg"
  fi
}

echo "--- Running State Tests ---"

# Test 1: Disabled by default
export GANDALF_PROMPT_ENABLED="false"
(cd "$TEST_CWD" && assert_prompt 1 "" "Prompt output when disabled")

# Test 2: Enabled, but outside of dirs
export GANDALF_PROMPT_ENABLED="true"
export GANDALF_PROMPT_DIRS="$TEST_HOME/some-other-project"
(cd "$TEST_CWD" && assert_prompt 1 "" "Prompt output when outside of configured dirs")

# Test 3: Enabled, inside dirs, no cache file
export GANDALF_PROMPT_DIRS="$TEST_CWD"
# Should exit with 1 because no cache exists yet (but should trigger background update)
(cd "$TEST_CWD" && assert_prompt 1 "" "Prompt output when no cache exists")

# Verify background refresh was triggered and started writing cache
# Poll for up to 5 seconds
found=false
for i in {1..50}; do
  if [[ -f "$TEST_HOME/.gandalf/prompt_status.cache" ]]; then
    found=true
    break
  fi
  sleep 0.1
done

if [[ "$found" == "true" ]]; then
  echo "PASS: Cache file was written by background update"
else
  echo "FAIL: Cache file was not created"
  exit 1
fi

# Test 4: Authenticated state in cache
echo '{"is_authed": true, "loas2_seconds": 10000, "corp_normal_seconds": 10000, "last_checked": '$(date +%s)'}' > "$TEST_HOME/.gandalf/prompt_status.cache"
(cd "$TEST_CWD" && assert_prompt 0 "🔑" "Prompt output when authenticated")

# Test 5: Unauthenticated state in cache
echo '{"is_authed": false, "loas2_seconds": 0, "corp_normal_seconds": 0, "last_checked": '$(date +%s)'}' > "$TEST_HOME/.gandalf/prompt_status.cache"
(cd "$TEST_CWD" && assert_prompt 0 "🔒" "Prompt output when unauthenticated")

# Test 6: Mock gcertstatus and background update
# Reset cache to false/empty
echo '{"is_authed": false, "loas2_seconds": 0, "corp_normal_seconds": 0, "last_checked": 0}' > "$TEST_HOME/.gandalf/prompt_status.cache"

# Run update command directly
gandalf-prompt --background-update
sleep 0.2

# Verify updated cache has is_authed = true
cache_content=$(cat "$TEST_HOME/.gandalf/prompt_status.cache")
if [[ "$cache_content" == *'"is_authed":true'* ]]; then
  echo "PASS: Background update correctly set is_authed to true using mock gcertstatus"
else
  echo "FAIL: Cache did not update to true. Content: $cache_content"
  exit 1
fi

# Test 7: Zsh optimistic cache update on exit code 0
source /Users/pmatthews/src/dotfiles/zsh/gandalf.zsh

# Reset cache
rm -f "$TEST_HOME/.gandalf/prompt_status.cache"

# Simulate running gcert successfully
gandalf_prompt_preexec "gcert"
# Verify preexec set the variable
if [[ "$GANDALF_LAST_CMD_WAS_AUTH" == "1" ]]; then
  echo "PASS: preexec hook detected auth command"
else
  echo "FAIL: preexec hook failed to set flag"
  exit 1
fi

# Simulate precmd running with exit status 0 (success)
(exit 0)
gandalf_prompt_precmd

# Verify cache is now optimistically set to authed
cache_content=$(cat "$TEST_HOME/.gandalf/prompt_status.cache")
if [[ "$cache_content" == *'"is_authed": true'* ]]; then
  echo "PASS: Zsh precmd hook optimistically set cache to true"
else
  echo "FAIL: Zsh precmd failed to set cache. Content: $cache_content"
  exit 1
fi

# Clean up
rm -rf "$TEST_DIR"
echo "--- All Tests Passed Successfully! ---"
