#!/usr/bin/env bash
# Smoke test: bring the stack up, run first-time setup, create an agent and use its token.
# Usage: scripts/smoke.sh [base_url]   (set SMOKE_KEEP=1 to leave the stack running)
# Stage 1.7 extends this with whoami and create_ticket over MCP.
set -euo pipefail

BASE_URL="${1:-http://localhost:${RADICLE_PORT:-8000}}"
JAR="$(mktemp)"
trap 'rm -f "$JAR"; [ "${SMOKE_KEEP:-0}" = 1 ] || docker compose down -v >/dev/null 2>&1' EXIT

fail() { echo "SMOKE FAIL: $*" >&2; exit 1; }
json() { python3 -c "import json,sys; print(json.load(sys.stdin)$1)"; }

echo "==> docker compose up"
docker compose up -d --build

echo "==> waiting for $BASE_URL/health"
for _ in $(seq 1 60); do
  if curl -fsS "$BASE_URL/health" >/dev/null 2>&1; then break; fi
  sleep 2
done
curl -fsS "$BASE_URL/health" | grep -q '"ok"' || fail "health check"

echo "==> SPA is served"
curl -fsS "$BASE_URL/" | grep -q '<div id="root">' || fail "SPA index"

echo "==> setup"
[ "$(curl -fsS "$BASE_URL/api/v1/setup/status" | json "['needs_setup']")" = "True" ] \
  || fail "instance is not fresh (run with a clean volume)"
curl -fsS -c "$JAR" -H 'Content-Type: application/json' "$BASE_URL/api/v1/setup" \
  -d '{"handle":"admin","display_name":"Admin","email":"admin@example.com","password":"smoke-password"}' \
  >/dev/null || fail "setup"
CSRF="$(awk '$6 == "radicle_csrf" {print $7}' "$JAR")"

echo "==> create agent"
TOKEN="$(curl -fsS -b "$JAR" -H "X-CSRF-Token: $CSRF" -H 'Content-Type: application/json' \
  "$BASE_URL/api/v1/agents" -d '{"handle":"agent-smoke","display_name":"Smoke agent"}' \
  | json "['token']['token']")"
[[ "$TOKEN" == rdc_* ]] || fail "agent token format"

echo "==> agent token authenticates"
[ "$(curl -fsS -H "Authorization: Bearer $TOKEN" "$BASE_URL/api/v1/me" | json "['kind']")" = "agent" ] \
  || fail "agent /me"

echo "SMOKE OK"
