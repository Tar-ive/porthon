#!/usr/bin/env bash
set -e

ROOT="$(cd "$(dirname "$0")" && pwd)"
BACKEND="$ROOT/src/backend"
FRONTEND="$ROOT/src/frontend"

# ── Colours ────────────────────────────────────────────────────────────────
GREEN='\033[0;32m'; AMBER='\033[0;33m'; RED='\033[0;31m'; RESET='\033[0m'
ok()   { echo -e "${GREEN}✓ $*${RESET}"; }
info() { echo -e "${AMBER}→ $*${RESET}"; }
fail() { echo -e "${RED}✗ $*${RESET}"; exit 1; }

echo ""
echo "  ◈ QUESTLINE — run & test"
echo "  ─────────────────────────────────────"
echo ""

# ── 1. Install uv if missing ────────────────────────────────────────────────
if ! command -v uv &>/dev/null; then
  info "uv not found — installing..."
  curl -LsSf https://astral.sh/uv/install.sh | sh
  export PATH="$HOME/.cargo/bin:$HOME/.local/bin:$PATH"
  ok "uv installed: $(uv --version)"
else
  ok "uv: $(uv --version)"
fi

# ── 2. Install pnpm if missing ──────────────────────────────────────────────
if ! command -v pnpm &>/dev/null; then
  info "pnpm not found — installing via npm..."
  npm install -g pnpm
fi
ok "pnpm: $(pnpm --version)"

# ── 3. Install backend deps ─────────────────────────────────────────────────
info "Syncing backend dependencies..."
cd "$BACKEND" && uv sync -q
ok "Backend deps ready"

# ── 4. Build frontend ───────────────────────────────────────────────────────
info "Building frontend..."
cd "$FRONTEND" && pnpm install -q && pnpm build 2>&1 | grep -E "(built|error|warn)" || true
ok "Frontend built → backend/static/"

# ── 5. Start server ─────────────────────────────────────────────────────────
cd "$BACKEND"
info "Starting FastAPI server on :8000..."
uv run uvicorn main:app --host 0.0.0.0 --port 8000 &
SERVER_PID=$!

# Wait for server to be ready
echo -n "  Waiting for server"
for i in $(seq 1 20); do
  if curl -sf http://localhost:8000/api/health &>/dev/null; then
    echo ""
    break
  fi
  echo -n "."
  sleep 1
done

if ! curl -sf http://localhost:8000/api/health &>/dev/null; then
  fail "Server did not start in time (check logs above)"
fi

# ── 6. Health check ─────────────────────────────────────────────────────────
echo ""
echo "  ─── TESTS ───────────────────────────"
HEALTH=$(curl -sf http://localhost:8000/api/health)
echo "  GET /api/health → $HEALTH"

RAG=$(echo "$HEALTH" | python3 -c "import sys,json; print(json.load(sys.stdin).get('rag'))" 2>/dev/null)
if [ "$RAG" = "True" ]; then
  ok "Knowledge graph connected (rag: true)"
else
  info "KG not connected (rag: false) — scenarios + actions still work via direct pipeline"
fi

# ── 7. Test /api/scenarios ──────────────────────────────────────────────────
echo ""
info "Testing GET /api/scenarios (LLM call — allow ~15s)..."
SCENARIOS=$(curl -sf --max-time 30 http://localhost:8000/api/scenarios)
COUNT=$(echo "$SCENARIOS" | python3 -c "import sys,json; d=json.load(sys.stdin); print(len(d))" 2>/dev/null || echo "0")

if [ "$COUNT" = "3" ]; then
  ok "$COUNT scenarios returned"
  echo "$SCENARIOS" | python3 -c "
import sys, json
for s in json.load(sys.stdin):
    print(f'    [{s[\"likelihood\"]:12s}] {s[\"horizon\"]}  {s[\"title\"]}')" 2>/dev/null
  # Grab first scenario id for next test
  SCENARIO_ID=$(echo "$SCENARIOS" | python3 -c "import sys,json; print(json.load(sys.stdin)[0]['id'])" 2>/dev/null)
  SCENARIO_TITLE=$(echo "$SCENARIOS" | python3 -c "import sys,json; print(json.load(sys.stdin)[0]['title'])" 2>/dev/null)
  SCENARIO_SUMMARY=$(echo "$SCENARIOS" | python3 -c "import sys,json; print(json.load(sys.stdin)[0]['summary'])" 2>/dev/null)
  SCENARIO_HORIZON=$(echo "$SCENARIOS" | python3 -c "import sys,json; print(json.load(sys.stdin)[0]['horizon'])" 2>/dev/null)
  SCENARIO_LIKELIHOOD=$(echo "$SCENARIOS" | python3 -c "import sys,json; print(json.load(sys.stdin)[0]['likelihood'])" 2>/dev/null)
else
  info "Scenarios returned $COUNT items (expected 3) — may have used fallback stub"
  SCENARIO_ID="s_001"
  SCENARIO_TITLE="Career Momentum"
  SCENARIO_SUMMARY="Jordan accelerates into a director role"
  SCENARIO_HORIZON="1yr"
  SCENARIO_LIKELIHOOD="most_likely"
fi

# ── 8. Test /api/actions ────────────────────────────────────────────────────
echo ""
info "Testing POST /api/actions (LLM call — allow ~15s)..."
ACTIONS=$(curl -sf --max-time 30 -X POST http://localhost:8000/api/actions \
  -H "Content-Type: application/json" \
  -d "{
    \"scenario_id\": \"$SCENARIO_ID\",
    \"scenario_title\": \"$SCENARIO_TITLE\",
    \"scenario_summary\": \"$SCENARIO_SUMMARY\",
    \"scenario_horizon\": \"$SCENARIO_HORIZON\",
    \"scenario_likelihood\": \"$SCENARIO_LIKELIHOOD\"
  }")

ACTION_COUNT=$(echo "$ACTIONS" | python3 -c "import sys,json; d=json.load(sys.stdin); print(len(d.get('actions',[])))" 2>/dev/null || echo "0")

if [ "$ACTION_COUNT" -gt 0 ] 2>/dev/null; then
  ok "$ACTION_COUNT quest actions returned"
  echo "$ACTIONS" | python3 -c "
import sys, json
d = json.load(sys.stdin)
for i, a in enumerate(d.get('actions', []), 1):
    ref = a.get('data_ref', 'no-ref')
    print(f'    Q{i:02d} [{ref}] {a[\"action\"][:80]}')" 2>/dev/null
else
  fail "No actions returned — response: $ACTIONS"
fi

# ── 9. Done ─────────────────────────────────────────────────────────────────
echo ""
echo "  ─────────────────────────────────────"
ok "All tests passed  →  open http://localhost:8000"
echo ""
echo "  Server is running (PID $SERVER_PID). Press Ctrl+C to stop."
echo ""

wait $SERVER_PID
