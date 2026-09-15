#!/bin/sh
# Prove the probe server works over a real socket, before blaming Gallery.
#
# Run this in Termux while `probe_serve.py` is running in another Termux session
# (swipe from the left edge > NEW SESSION). If these checks pass but Gallery still
# cannot connect, the server is fine and the problem is on the app side -- which is
# exactly the distinction validation item V2 needs.
#
#   sh curl-checks.sh                          # default http://127.0.0.1:8765/mcp
#   sh curl-checks.sh http://localhost:8765/mcp
#
# POSIX sh. Needs curl (Termux: pkg install curl).

set -u

URL="${1:-http://127.0.0.1:8765/mcp}"
HERE=$(dirname "$0")

if [ -n "${PK_TOKEN:-}" ]; then
  TOKEN="$PK_TOKEN"
elif [ -f "$HERE/.probe-token" ]; then
  TOKEN=$(tr -d ' \t\n\r' < "$HERE/.probe-token")
else
  echo "No token found."
  echo "Start probe_serve.py first, or set PK_TOKEN=<token from the server banner>."
  exit 2
fi

PASS=0
FAIL=0

# check <name> <expected-status> <curl args...>
check() {
  name="$1"; expected="$2"; shift 2
  out=$(curl -s -o /tmp/pk-body.$$ -w '%{http_code}' "$@" 2>/dev/null)
  body=$(cat /tmp/pk-body.$$ 2>/dev/null)
  rm -f /tmp/pk-body.$$
  if [ "$out" = "$expected" ]; then
    PASS=$((PASS + 1))
    printf 'PASS  %-34s %s\n' "$name" "$out"
  else
    FAIL=$((FAIL + 1))
    printf 'FAIL  %-34s got %s, expected %s\n' "$name" "$out" "$expected"
  fi
  [ -n "$body" ] && printf '        %s\n' "$(echo "$body" | cut -c1-160)"
  return 0
}

post() {
  check "$1" "$2" -X POST "$URL" \
    -H 'Content-Type: application/json' \
    -H 'Accept: application/json, text/event-stream' \
    -H "Authorization: Bearer $TOKEN" \
    -d "$3"
}

echo "===================================================================="
echo " probe server checks"
echo " URL   : $URL"
echo " Token : $(echo "$TOKEN" | cut -c1-8)..."
echo "===================================================================="

post "initialize" 200 \
  '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-11-25","capabilities":{},"clientInfo":{"name":"curl-checks","version":"0"}}}'

post "notifications/initialized (202)" 202 \
  '{"jsonrpc":"2.0","method":"notifications/initialized"}'

post "ping" 200 '{"jsonrpc":"2.0","id":2,"method":"ping"}'

post "tools/list" 200 '{"jsonrpc":"2.0","id":3,"method":"tools/list"}'

post "tools/call vault_guide" 200 \
  '{"jsonrpc":"2.0","id":4,"method":"tools/call","params":{"name":"vault_guide","arguments":{}}}'

post "tools/call vault_read" 200 \
  '{"jsonrpc":"2.0","id":5,"method":"tools/call","params":{"name":"vault_read","arguments":{"path":"README.md"}}}'

post "unknown protocol version" 200 \
  '{"jsonrpc":"2.0","id":6,"method":"initialize","params":{"protocolVersion":"1999-01-01"}}'

check "GET is rejected (405)" 405 -X GET "$URL" -H "Authorization: Bearer $TOKEN"

check "no token is rejected (401)" 401 -X POST "$URL" \
  -H 'Content-Type: application/json' -d '{"jsonrpc":"2.0","id":7,"method":"ping"}'

check "bad token is rejected (401)" 401 -X POST "$URL" \
  -H 'Content-Type: application/json' -H 'Authorization: Bearer wrong' \
  -d '{"jsonrpc":"2.0","id":8,"method":"ping"}'

echo "--------------------------------------------------------------------"
echo " passed: $PASS   failed: $FAIL"
echo "===================================================================="

if [ "$FAIL" -gt 0 ]; then
  echo
  echo "The server itself is not healthy. Fix this before testing Gallery,"
  echo "otherwise a Gallery failure tells you nothing."
  exit 1
fi

echo
echo "Server is healthy. Now try connecting Gallery -- see probes/README.md, probe B."
exit 0
