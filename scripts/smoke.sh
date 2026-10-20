#!/usr/bin/env bash
# Smoke test: bring the stack up, run first-time setup, create an agent and use its token.
# Usage: scripts/smoke.sh [base_url]   (set SMOKE_KEEP=1 to leave the stack running)
# It runs as its own Compose project on port 8001 and deletes its volumes at the end, so it
# never touches the stack you develop with.
set -euo pipefail

export COMPOSE_PROJECT_NAME="${SMOKE_PROJECT:-radicle-smoke}"
# Its own image too, so a smoke build never replaces the image of your everyday install.
export RADICLE_IMAGE="${SMOKE_IMAGE:-radicle-smoke}"
export RADICLE_PORT="${SMOKE_PORT:-8001}"
BASE_URL="${1:-http://localhost:${RADICLE_PORT}}"
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

echo "==> project PA with the agent as member"
curl -fsS -b "$JAR" -H "X-CSRF-Token: $CSRF" -H 'Content-Type: application/json' \
  "$BASE_URL/api/v1/projects" -d '{"key":"PA","name":"ProyectoA"}' >/dev/null || fail "project"
curl -fsS -b "$JAR" -H "X-CSRF-Token: $CSRF" -H 'Content-Type: application/json' -X PUT \
  "$BASE_URL/api/v1/projects/PA/members/agent-smoke" -d '{"role":"member"}' >/dev/null \
  || fail "member"

mcp() {
  curl -fsS "$BASE_URL/mcp" -H "Authorization: Bearer $TOKEN" \
    -H 'Content-Type: application/json' -H 'Accept: application/json, text/event-stream' \
    -H 'MCP-Protocol-Version: 2025-06-18' -d "$1"
}

echo "==> MCP initialize"
mcp '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-06-18","capabilities":{},"clientInfo":{"name":"smoke","version":"1"}}}' \
  | grep -q '"radicle"' || fail "MCP initialize"

echo "==> MCP whoami"
mcp '{"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"whoami","arguments":{}}}' \
  | grep -q 'agent-smoke' || fail "MCP whoami"

echo "==> MCP create_ticket"
mcp '{"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"create_ticket","arguments":{"project":"PA","type":"draft","classification":"idea","title":"From MCP"}}}' \
  | grep -q 'PA-1' || fail "MCP create_ticket"
[ "$(curl -fsS -H "Authorization: Bearer $TOKEN" "$BASE_URL/api/v1/tickets/PA-1" \
  | json "['reporter']['handle']")" = "agent-smoke" ] || fail "ticket reporter"

echo "==> MCP rejects a missing token"
[ "$(curl -s -o /dev/null -w '%{http_code}' -X POST "$BASE_URL/mcp" \
  -H 'Content-Type: application/json' -d '{}')" = "401" ] || fail "MCP without token"

echo "==> worker is running"
for _ in $(seq 1 30); do
  if docker compose logs worker 2>/dev/null | grep -qi "starting worker"; then break; fi
  sleep 2
done
[ "$(docker compose ps --status running --services | grep -c '^worker$')" = "1" ] \
  || fail "worker not running"

echo "==> template change reaches a linked project through the worker"
TEMPLATE="$(curl -fsS -b "$JAR" -H "X-CSRF-Token: $CSRF" -H 'Content-Type: application/json' \
  "$BASE_URL/api/v1/templates" -d '{"name":"Smoke"}')"
TEMPLATE_ID="$(echo "$TEMPLATE" | json "['id']")"
curl -fsS -b "$JAR" -H "X-CSRF-Token: $CSRF" -H 'Content-Type: application/json' \
  "$BASE_URL/api/v1/projects" -d "{\"key\":\"PS\",\"name\":\"Smoke\",\"template_id\":\"$TEMPLATE_ID\"}" \
  >/dev/null || fail "project from template"
CONFIG="$(echo "$TEMPLATE" | python3 -c "
import json, sys
config = json.load(sys.stdin)['config']
config['areas'].append({'name': 'Smoke area'})
print(json.dumps({'config': config}))")"
curl -fsS -b "$JAR" -H "X-CSRF-Token: $CSRF" -H 'Content-Type: application/json' -X PATCH \
  "$BASE_URL/api/v1/templates/$TEMPLATE_ID" -d "$CONFIG" >/dev/null || fail "template patch"
for _ in $(seq 1 30); do
  if curl -fsS -b "$JAR" "$BASE_URL/api/v1/projects/PS" | grep -q 'Smoke area'; then break; fi
  sleep 1
done
curl -fsS -b "$JAR" "$BASE_URL/api/v1/projects/PS" | grep -q 'Smoke area' || fail "template sync"

echo "SMOKE OK"
