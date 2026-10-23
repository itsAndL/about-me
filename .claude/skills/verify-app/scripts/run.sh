#!/usr/bin/env bash
# verify-app runner: Launch → Doctor → Drive → Evidence → Cleanup for the static site.
#
# Usage (from anywhere inside the repo):
#   .claude/skills/verify-app/scripts/run.sh all        # the full loop, always cleans up
#   .claude/skills/verify-app/scripts/run.sh launch|doctor|drive|cleanup
#
# State lives in .fredrin/tmp/: verify-app.pid, verify-app.port, verify-app.evidence.
set -uo pipefail

ROOT="$(git -C "$(dirname "$0")" rev-parse --show-toplevel)"
SKILL="$ROOT/.claude/skills/verify-app"
TMP="$ROOT/.fredrin/tmp"
PID_FILE="$TMP/verify-app.pid"
PORT_FILE="$TMP/verify-app.port"
EVIDENCE_FILE="$TMP/verify-app.evidence"
mkdir -p "$TMP"

port_busy() { lsof -nP -iTCP:"$1" -sTCP:LISTEN >/dev/null 2>&1; }

find_chrome() {
  local mac="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
  if [ -x "$mac" ]; then echo "$mac"; return; fi
  command -v google-chrome || command -v chromium || command -v chromium-browser || true
}

launch() {
  local port=8765
  while port_busy "$port"; do port=$((port + 1)); done
  [ "$port" != 8765 ] && echo "NOTE  port 8765 is busy — using $port instead"
  (cd "$ROOT" && exec python3 -m http.server "$port" --bind 127.0.0.1 >"$TMP/verify-app.server.log" 2>&1) &
  echo $! >"$PID_FILE"
  disown
  echo "$port" >"$PORT_FILE"
  for _ in $(seq 1 20); do
    if curl -sf "http://127.0.0.1:$port/" | grep -q 'Ayoub Lkebch'; then
      echo "PASS  launched http.server pid $(cat "$PID_FILE") on http://127.0.0.1:$port/ (page serves 'Ayoub Lkebch')"
      return 0
    fi
    sleep 0.5
  done
  echo "FAIL  server not usable within 10s — see $TMP/verify-app.server.log"
  return 1
}

doctor() {
  echo "== Doctor"
  python3 "$SKILL/scripts/doctor.py" "$ROOT"
}

drive() {
  local port; port="$(cat "$PORT_FILE" 2>/dev/null)" || { echo "FAIL  not launched"; return 1; }
  local url="http://127.0.0.1:$port/"
  local out="$TMP/verify-app/$(date +%Y%m%d-%H%M%S)"
  mkdir -p "$out"
  echo "$out" >"$EVIDENCE_FILE"
  local status=0
  echo "== Drive ($url → $out)"

  curl -s "$url" >"$out/served.html"
  local chrome; chrome="$(find_chrome)"
  if [ -z "$chrome" ]; then
    echo "SKIP  no Chrome/Chromium found — screenshots skipped, asserting on the served HTML instead"
    python3 "$SKILL/scripts/check_content.py" "$out/served.html" | tee "$out/content-check.txt" || status=1
    write_summary "$out" "$url" "curl only (no Chrome)"
    return $status
  fi

  local headless=(--headless=new --disable-gpu --hide-scrollbars --no-first-run)
  "$chrome" "${headless[@]}" --virtual-time-budget=3000 --dump-dom "$url" >"$out/dom.html" 2>/dev/null
  "$chrome" "${headless[@]}" --force-dark-mode --virtual-time-budget=3000 --dump-dom "$url" >"$out/dom-dark.html" 2>/dev/null
  "$chrome" "${headless[@]}" --window-size=1280,1400 --screenshot="$out/desktop-light.png" "$url" 2>/dev/null
  "$chrome" "${headless[@]}" --force-dark-mode --window-size=1280,1400 --screenshot="$out/desktop-dark.png" "$url" 2>/dev/null

  python3 "$SKILL/scripts/check_content.py" "$out/dom.html" | tee "$out/content-check.txt" || status=1

  # Headless Chrome will not shrink a window below ~500px. With node, cdp.mjs emulates a
  # real 390px viewport; without it, the page loads in a 390px iframe inside a 500px window.
  if command -v node >/dev/null; then
    for scheme in light dark; do
      node "$SKILL/scripts/cdp.mjs" phone "$chrome" "$url" "$out/phone-$scheme.png" "$scheme" || status=1
    done
    node "$SKILL/scripts/cdp.mjs" tab "$chrome" "$url" "$out" | tee "$out/keyboard-check.txt" || status=1
  else
    echo "NOTE  node not found — phone view uses the iframe wrapper; keyboard (first Tab) check skipped"
    local frame_dir="$TMP/verify-app-frame"
    mkdir -p "$frame_dir"
    cat >"$frame_dir/phone.html" <<EOF
<!doctype html><html><head><meta charset="utf-8"><style>html,body{margin:0}iframe{border:0;width:390px;height:2400px;display:block}</style></head>
<body><iframe src="$url" title="phone viewport"></iframe></body></html>
EOF
    local phone_url="http://127.0.0.1:$port/.fredrin/tmp/verify-app-frame/phone.html"
    "$chrome" "${headless[@]}" --window-size=500,2400 --virtual-time-budget=3000 \
      --screenshot="$out/phone-light.png" "$phone_url" 2>/dev/null
    "$chrome" "${headless[@]}" --force-dark-mode --window-size=500,2400 --virtual-time-budget=3000 \
      --screenshot="$out/phone-dark.png" "$phone_url" 2>/dev/null
  fi
  write_summary "$out" "$url" "headless Chrome: $chrome"
  ls -1 "$out"
  return $status
}

write_summary() {
  local out="$1" url="$2" how="$3"
  local dom="$out/dom.html" projects links
  [ -f "$dom" ] || dom="$out/served.html"
  projects="$(grep -o 'class="project"' "$dom" | wc -l | tr -d ' ')"
  links="$(grep -o 'class="contact-link"' "$dom" | wc -l | tr -d ' ')"
  cat >"$out/SUMMARY.md" <<EOF
# verify-app run $(basename "$out")

- **Action:** served the repo with python3 http.server, loaded $url ($how) at 1280×1400 and 390px wide, light and dark, dumped the DOM, pressed Tab once.
- **State:** $(grep -c '^PASS' "$out/content-check.txt") content checks passed, $(grep -c '^FAIL' "$out/content-check.txt") failed; $(basename "$dom") holds \`.project\` × $projects and \`.contact-link\` × $links.
- **Keyboard:** $(cat "$out/keyboard-check.txt" 2>/dev/null || echo "not run")
- **Side effects:** none expected (static site; no requests leave the machine except the optional W3C checker POST in Doctor).
EOF
}

cleanup() {
  if [ -f "$PID_FILE" ]; then
    local pid; pid="$(cat "$PID_FILE")"
    if kill "$pid" 2>/dev/null; then echo "PASS  stopped http.server pid $pid"; else echo "NOTE  pid $pid already gone"; fi
    rm -f "$PID_FILE" "$PORT_FILE"
  else
    echo "NOTE  no pid file — nothing to stop"
  fi
  [ -f "$EVIDENCE_FILE" ] && echo "Evidence kept in $(cat "$EVIDENCE_FILE")"
}

case "${1:-all}" in
  launch) launch ;;
  doctor) doctor ;;
  drive) drive ;;
  cleanup) cleanup ;;
  all)
    trap cleanup EXIT
    rc=0
    doctor || rc=1
    launch || exit 1
    drive || rc=1
    echo "== Result: $([ $rc = 0 ] && echo PASS || echo FAIL)"
    exit $rc
    ;;
  *) echo "usage: $0 all|launch|doctor|drive|cleanup" >&2; exit 2 ;;
esac
