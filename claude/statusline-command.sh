#!/bin/bash

# Read JSON input from stdin
input=$(cat)

# Extract values from JSON
remaining=$(echo "$input" | jq -r '.context_window.remaining_percentage // empty')
current_dir=$(echo "$input" | jq -r '.workspace.current_dir // ""')
cost=$(echo "$input" | jq -r '.cost.total_cost_usd // empty')


# Get last 2 path components for CWD
if [ -n "$current_dir" ]; then
    cwd=$(echo "$current_dir" | awk -F/ '{if (NF>1) print $(NF-1)"/"$NF; else print $NF}')
else
    cwd="~"
fi

# Build status line components
output=""

# Context remaining (green if >50%, yellow if 20-50%, red if <20%)
if [ -n "$remaining" ]; then
    remaining_int=$(printf "%.0f" "$remaining")
    if [ "$remaining_int" -gt 50 ]; then
        context=$(printf "\033[32m%d%% ctx\033[0m" "$remaining_int")
    elif [ "$remaining_int" -gt 20 ]; then
        context=$(printf "\033[33m%d%% ctx\033[0m" "$remaining_int")
    else
        context=$(printf "\033[31m%d%% ctx\033[0m" "$remaining_int")
    fi
    output="$context"
fi

# Session cost (if > $0.00)
if [ -n "$cost" ]; then
    cost_check=$(echo "$cost > 0" | bc -l 2>/dev/null || echo "0")
    if [ "$cost_check" = "1" ]; then
        cost_fmt=$(printf "%.2f" "$cost")
        if [ -n "$output" ]; then output="$output │ "; fi
        output="$output\033[35m\$$cost_fmt\033[0m"
    fi
fi

# CWD (dimmed)
if [ -n "$output" ]; then output="$output │ "; fi
output="$output\033[2m$cwd\033[0m"

# Print the status line (echo -e interprets ANSI escape codes)
echo -e "$output"
