#!/usr/bin/env bash
# verify-app runner: Build → Launch → Doctor → Drive → Evidence → Cleanup for the Next.js
# static export, served under /about-me/ exactly as GitHub Pages serves it.
#
# Usage (from anywhere inside the repo):
#   .claude/skills/verify-app/scripts/run.sh all        # the full loop, always cleans up
#   .claude/skills/verify-app/scripts/run.sh build|launch|doctor|drive|cleanup
#
# State lives in .fredrin/tmp/: verify-app.pid, verify-app.port, verify-app.evidence, and the
# staged copy of out/ in site/about-me/.
set -uo pipefail

ROOT="$(git -C "$(dirname "$0")" rev-parse --show-toplevel)"
SKILL="$ROOT/.claude/skills/verify-app"
TMP="$ROOT/.fredrin/tmp"
PID_FILE="$TMP/verify-app.pid"
PORT_FILE="$TMP/verify-app.port"
EVIDENCE_FILE="$TMP/verify-app.evidence"
SITE="$TMP/site"
BASE_PATH="/about-me/"
mkdir -p "$TMP"

port_busy() { lsof -nP -iTCP:"$1" -sTCP:LISTEN >/dev/null 2>&1; }

# True when the pid file names a live process that is our http.server (not a reused PID).
our_server_alive() {
  [ -f "$PID_FILE" ] || return 1
  ps -p "$(cat "$PID_FILE")" -o command= 2>/dev/null | grep -Eq '[Pp]ython[0-9.]* -m http\.server '
}

# Stock macOS has no `timeout`; perl's alarm kills a hung Chrome so cleanup still runs.
with_timeout() { local secs="$1"; shift; perl -e 'alarm shift; exec @ARGV' "$secs" "$@"; }

node_ok() { command -v node >/dev/null && node -e 'process.exit(typeof WebSocket === "function" ? 0 : 1)'; }

expect_file() {
  if [ -s "$1" ]; then return 0; fi
  echo "FAIL  missing or empty $(basename "$1")"
  return 1
}

find_chrome() {
  local mac="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
  if [ -x "$mac" ]; then echo "$mac"; return; fi
  command -v google-chrome || command -v chromium || command -v chromium-browser || true
}

build() {
  echo "== Build"
  if our_server_alive; then
    echo "FAIL  a launched server is serving $SITE — run cleanup before rebuilding"
    return 2
  fi
  # Reinstall when node_modules is missing or older than the lockfile.
  if [ ! -f "$ROOT/node_modules/.package-lock.json" ] || [ "$ROOT/package-lock.json" -nt "$ROOT/node_modules/.package-lock.json" ]; then
    (cd "$ROOT" && npm ci --no-audit --no-fund) || { echo "FAIL  npm ci"; return 1; }
  fi
  (cd "$ROOT" && npm run build) >"$TMP/verify-app.build.log" 2>&1 || {
    tail -30 "$TMP/verify-app.build.log"
    echo "FAIL  npm run build — see $TMP/verify-app.build.log"
    return 1
  }
  [ -f "$ROOT/out/index.html" ] || { echo "FAIL  out/index.html missing after the build"; return 1; }
  # Pages serves the export under /about-me/, so stage it one level down and serve the parent.
  rm -rf "$SITE"
  mkdir -p "$SITE$BASE_PATH"
  cp -R "$ROOT/out/." "$SITE$BASE_PATH"
  echo "PASS  npm run build → out/, staged at $SITE$BASE_PATH"
}

launch() {
  if our_server_alive; then
    echo "FAIL  already launched (pid $(cat "$PID_FILE"), port $(cat "$PORT_FILE" 2>/dev/null)) — run cleanup first"
    return 2
  fi
  local port=8765
  while port_busy "$port"; do port=$((port + 1)); done
  [ "$port" != 8765 ] && echo "NOTE  port 8765 is busy — using $port instead"
  [ -f "$SITE$BASE_PATH/index.html" ] || { echo "FAIL  nothing staged — run build first"; return 1; }
  (cd "$SITE" && exec python3 -m http.server "$port" --bind 127.0.0.1 >"$TMP/verify-app.server.log" 2>&1) &
  echo $! >"$PID_FILE"
  disown
  echo "$port" >"$PORT_FILE"
  for _ in $(seq 1 20); do
    # A server that died (e.g. lost a port race) must not pass on someone else's server.
    if ! kill -0 "$(cat "$PID_FILE")" 2>/dev/null; then
      echo "FAIL  http.server exited — see $TMP/verify-app.server.log"
      rm -f "$PID_FILE" "$PORT_FILE"
      return 1
    fi
    if curl -sf "http://127.0.0.1:$port$BASE_PATH" | grep -q 'Ayoub Lkebch'; then
      echo "PASS  launched http.server pid $(cat "$PID_FILE") on http://127.0.0.1:$port$BASE_PATH (page serves 'Ayoub Lkebch')"
      return 0
    fi
    sleep 0.5
  done
  echo "FAIL  server not usable within 10s — see $TMP/verify-app.server.log"
  return 1
}

doctor() {
  echo "== Doctor"
  # With a live server it also fetches every referenced asset over HTTP.
  local served=()
  if our_server_alive; then served=(--served "http://127.0.0.1:$(cat "$PORT_FILE")"); fi
  python3 "$SKILL/scripts/doctor.py" "$ROOT" "${served[@]+"${served[@]}"}"
}

drive() {
  local port; port="$(cat "$PORT_FILE" 2>/dev/null)" || { echo "FAIL  not launched"; return 1; }
  local url="http://127.0.0.1:$port$BASE_PATH"
  local out="$TMP/verify-app/$(date +%Y%m%d-%H%M%S)"
  mkdir -p "$out"
  echo "$out" >"$EVIDENCE_FILE"
  local status=0
  echo "== Drive ($url → $out)"

  curl -s "$url" >"$out/served.html"
  expect_file "$out/served.html" || status=1
  local chrome; chrome="$(find_chrome)"
  if [ -z "$chrome" ]; then
    echo "SKIP  no Chrome/Chromium found — screenshots skipped, asserting on the served HTML instead"
    python3 "$SKILL/scripts/check_content.py" "$out/served.html" | tee "$out/content-check.txt" || status=1
    write_summary "$out" "fetched $url with curl only (no Chrome: no screenshots, no keyboard check)"
    return $status
  fi

  local headless=(--headless=new --disable-gpu --hide-scrollbars --no-first-run)
  with_timeout 60 "$chrome" "${headless[@]}" --virtual-time-budget=3000 --dump-dom "$url" >"$out/dom.html" 2>/dev/null
  with_timeout 60 "$chrome" "${headless[@]}" --force-dark-mode --virtual-time-budget=3000 --dump-dom "$url" >"$out/dom-dark.html" 2>/dev/null
  with_timeout 60 "$chrome" "${headless[@]}" --window-size=1280,1400 --screenshot="$out/desktop-light.png" "$url" 2>/dev/null
  with_timeout 60 "$chrome" "${headless[@]}" --force-dark-mode --window-size=1280,1400 --screenshot="$out/desktop-dark.png" "$url" 2>/dev/null

  python3 "$SKILL/scripts/check_content.py" "$out/dom.html" | tee "$out/content-check.txt" || status=1

  # Headless Chrome will not shrink a window below ~500px. With node, cdp.mjs emulates a
  # real 390px viewport; without it, the page loads in a 390px iframe inside a 500px window.
  local how="headless Chrome ($chrome): DOM dump and desktop 1280×1400, light and dark"
  if node_ok; then
    for scheme in light dark; do
      node "$SKILL/scripts/cdp.mjs" phone "$chrome" "$url" "$out/phone-$scheme.png" "$scheme" || status=1
    done
    node "$SKILL/scripts/cdp.mjs" tab "$chrome" "$url" "$out" | tee "$out/keyboard-check.txt" || status=1
    node "$SKILL/scripts/cdp.mjs" theme "$chrome" "$url" "$out" | tee "$out/theme-check.txt" || status=1
    how="$how; phone 390px via DevTools emulation, light and dark; pressed Tab once; clicked the theme toggle, reloaded, loaded with JS off"
  else
    echo "NOTE  node 22+ not found — phone view uses the iframe wrapper; keyboard (first Tab) NOT verified"
    echo "NOT VERIFIED — needs node 22+ for the real Tab key press" >"$out/keyboard-check.txt"
    echo "NOT VERIFIED — needs node 22+ to drive the theme toggle" >"$out/theme-check.txt"
    how="$how; phone via 390px iframe in a 500px window, light and dark; keyboard not checked (no node 22+)"
    local frame_dir="$SITE/verify-app-frame"
    mkdir -p "$frame_dir"
    cat >"$frame_dir/phone.html" <<EOF
<!doctype html><html><head><meta charset="utf-8"><style>html,body{margin:0}iframe{border:0;width:390px;height:2400px;display:block}</style></head>
<body><iframe src="$url" title="phone viewport"></iframe></body></html>
EOF
    local phone_url="http://127.0.0.1:$port/verify-app-frame/phone.html"
    with_timeout 60 "$chrome" "${headless[@]}" --window-size=500,2400 --virtual-time-budget=3000 \
      --screenshot="$out/phone-light.png" "$phone_url" 2>/dev/null
    with_timeout 60 "$chrome" "${headless[@]}" --force-dark-mode --window-size=500,2400 --virtual-time-budget=3000 \
      --screenshot="$out/phone-dark.png" "$phone_url" 2>/dev/null
  fi
  for f in dom.html dom-dark.html desktop-light.png desktop-dark.png phone-light.png phone-dark.png; do
    expect_file "$out/$f" || status=1
  done
  write_summary "$out" "built the static export (npm run build), served it under $BASE_PATH with python3 http.server and loaded $url in $how"
  ls -1 "$out"
  return $status
}

write_summary() {
  local out="$1" action="$2"
  local dom="$out/dom.html" projects links
  [ -f "$dom" ] || dom="$out/served.html"
  projects="$(grep -o 'class="project"' "$dom" | wc -l | tr -d ' ')"
  links="$(grep -o 'class="contact-link"' "$dom" | wc -l | tr -d ' ')"
  cat >"$out/SUMMARY.md" <<EOF
# verify-app run $(basename "$out")

- **Action:** $action.
- **State:** $(grep -c '^PASS' "$out/content-check.txt") content checks passed, $(grep -c '^FAIL' "$out/content-check.txt") failed; $(basename "$dom") holds \`.project\` × $projects and \`.contact-link\` × $links.
- **Keyboard:** $(cat "$out/keyboard-check.txt" 2>/dev/null || echo "not run")
- **Theme:** $(grep -c '^PASS' "$out/theme-check.txt" 2>/dev/null) passed, $(grep -c '^FAIL' "$out/theme-check.txt" 2>/dev/null) failed (see theme-check.txt)
- **Side effects:** \`out/\` rebuilt and staged into \`.fredrin/tmp/site/about-me/\`; nothing else written outside \`.fredrin/tmp/\`. No requests leave the machine except the optional W3C checker POST in Doctor.
EOF
}

cleanup() {
  if [ -f "$PID_FILE" ]; then
    local pid; pid="$(cat "$PID_FILE")"
    if our_server_alive && kill "$pid" 2>/dev/null; then
      echo "PASS  stopped http.server pid $pid"
    else
      echo "NOTE  pid $pid is gone or no longer an http.server — left alone"
    fi
    rm -f "$PID_FILE" "$PORT_FILE"
  else
    echo "NOTE  no pid file — nothing to stop"
  fi
  if [ -f "$EVIDENCE_FILE" ]; then echo "Evidence of the latest drive kept in $(cat "$EVIDENCE_FILE")"; fi
}

case "${1:-all}" in
  build) build ;;
  launch) launch ;;
  doctor) doctor ;;
  drive) drive ;;
  cleanup) cleanup ;;
  all)
    rc=0
    # Refuse (and leave the earlier server alone) when a launch is already live.
    our_server_alive && { launch; exit 1; }
    build || exit 1
    trap cleanup EXIT
    launch || exit 1
    doctor || rc=1
    drive || rc=1
    echo "== Result: $([ $rc = 0 ] && echo PASS || echo FAIL)"
    exit $rc
    ;;
  *) echo "usage: $0 all|build|launch|doctor|drive|cleanup" >&2; exit 2 ;;
esac
