#!/usr/bin/env bash
# Install ffmpeg + ffprobe. Try apt first; if apt hangs or fails, fall back to a
# static build from GitHub releases (BtbN/FFmpeg-Builds).
# Why: on 18 Nov 2026 apt hung 3 times in a row (12 min) and the 12:30 yojana
# video was lost, even with ops/retry.sh. GitHub downloads don't use the apt mirror.
#
# Env: FFMPEG_SOURCE=static skips apt (used by tests.yml so the fallback stays tested).
set -u
here="$(cd "$(dirname "$0")" && pwd)"

if [ "${FFMPEG_SOURCE:-apt}" != "static" ]; then
  if RETRY_TRIES=2 RETRY_MINUTES=3 bash "$here/retry.sh" "sudo apt-get update && sudo apt-get install -y ffmpeg"; then
    ffmpeg -version | head -1
    exit 0
  fi
  echo "::warning::apt could not install ffmpeg, using the static build from GitHub instead"
  sudo dpkg --configure -a || true
fi

url="https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-linux64-gpl.tar.xz"
tmp="$(mktemp -d)"
ok=0
for i in 1 2 3; do
  if curl -fsSL --retry 2 --max-time 240 -o "$tmp/ff.tar.xz" "$url" \
     && tar -xJf "$tmp/ff.tar.xz" -C "$tmp" --wildcards '*/bin/ffmpeg' '*/bin/ffprobe'; then
    ok=1
    break
  fi
  echo "::warning::static ffmpeg download try $i/3 failed"
  sleep 15
done
if [ "$ok" -ne 1 ]; then
  echo "::error::ffmpeg install failed (apt and static build)"
  exit 1
fi
sudo install -m 0755 "$tmp"/*/bin/ffmpeg "$tmp"/*/bin/ffprobe /usr/local/bin/
rm -rf "$tmp"
hash -r
ffmpeg -version | head -1
