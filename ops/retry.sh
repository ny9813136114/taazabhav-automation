#!/usr/bin/env bash
# Run an install command with a time limit per try, and try again if it hangs or fails.
# Why: on 11 Nov 2026 `apt-get install ffmpeg` and `playwright install --with-deps`
# hung on GitHub runners until the job timed out, so the Bhav post and a video were lost.
#
# Usage: bash ops/retry.sh "<command>"
# Env:   RETRY_TRIES (default 3), RETRY_MINUTES per try (default 4), RETRY_WAIT seconds (default 15)
set -u
cmd="$*"
tries="${RETRY_TRIES:-3}"
minutes="${RETRY_MINUTES:-4}"
wait_s="${RETRY_WAIT:-15}"

for ((i = 1; i <= tries; i++)); do
  echo "retry.sh: try $i/$tries (limit ${minutes}m): $cmd"
  timeout --kill-after=30s "${minutes}m" bash -c "$cmd"
  code=$?
  if [ "$code" -eq 0 ]; then
    exit 0
  fi
  if [ "$code" -eq 124 ] || [ "$code" -eq 137 ]; then
    why="hung for ${minutes} min"
  else
    why="exit code $code"
  fi
  if [ "$i" -lt "$tries" ]; then
    echo "::warning::try $i/$tries $why, trying again: $cmd"
    # A killed apt can leave a half-done dpkg state; repair it before the next try.
    if [[ "$cmd" == *apt-get* || "$cmd" == *--with-deps* ]]; then
      sudo dpkg --configure -a || true
    fi
    sleep "$wait_s"
  else
    echo "::error::install failed after $tries tries ($why): $cmd"
    exit "$code"
  fi
done
