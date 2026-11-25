#!/usr/bin/env bash
# Install Playwright's Chromium. Try with system deps (apt) first; if apt hangs or
# fails, install the browser alone (downloaded from Playwright's CDN, no apt) and
# check it launches. GitHub's ubuntu runners already ship the libraries Chromium needs.
# Why: on 24 Nov 2026 `playwright install --with-deps` hung/failed 3 times and the
# 9:30 Daily Tool Post was lost, even with ops/retry.sh.
#
# Env: PLAYWRIGHT_SOURCE=nodeps skips apt (used by tests.yml so the fallback stays tested).
set -u
here="$(cd "$(dirname "$0")" && pwd)"

smoke() {
  python - <<'PY'
from playwright.sync_api import sync_playwright
with sync_playwright() as p:
    b = p.chromium.launch()
    pg = b.new_page()
    pg.set_content("<h1>किसान ok</h1>")
    assert "ok" in pg.inner_text("h1")
    b.close()
print("playwright chromium launches OK")
PY
}

if [ "${PLAYWRIGHT_SOURCE:-apt}" != "nodeps" ]; then
  if RETRY_TRIES=2 RETRY_MINUTES=3 bash "$here/retry.sh" "python -m playwright install --with-deps chromium"; then
    exit 0
  fi
  echo "::warning::playwright --with-deps failed, installing Chromium without apt deps instead"
  sudo dpkg --configure -a || true
fi

log="$(mktemp)"
RETRY_TRIES=3 RETRY_MINUTES=4 bash "$here/retry.sh" "python -m playwright install chromium" 2>&1 | tee "$log"
code=${PIPESTATUS[0]}
if [ "$code" -ne 0 ]; then
  # Show the reason in the job annotations (raw logs are not always readable).
  grep -iE "error|failed|denied|403|404|timeout" "$log" | grep -v -e "^retry.sh" -e "^::" | tail -4 \
    | while IFS= read -r line; do echo "::warning::playwright: ${line:0:300}"; done
  echo "::error::Chromium install failed (with and without apt deps)"
  exit 1
fi
smoke
