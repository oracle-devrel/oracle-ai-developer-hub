#!/usr/bin/env bash
set -euo pipefail

# Exercise the deployed service through a temporary local kubectl port-forward.
NAMESPACE="${NAMESPACE:-obaas}"
SERVICE="${SERVICE:-helidon-credit-service}"
LOCAL_PORT="${LOCAL_PORT:-18080}"
BASE_URL="http://127.0.0.1:${LOCAL_PORT}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PAYLOAD="$SCRIPT_DIR/api/sample-requests/approved.json"
RESPONSE_FILE=""
PORT_FORWARD_PID=""

cleanup() {
  [[ -n "$RESPONSE_FILE" ]] && rm -f "$RESPONSE_FILE"
  [[ -n "$PORT_FORWARD_PID" ]] && kill "$PORT_FORWARD_PID" 2>/dev/null || true
}
trap cleanup EXIT

kubectl port-forward -n "$NAMESPACE" "svc/$SERVICE" "${LOCAL_PORT}:8080" >/dev/null 2>&1 &
PORT_FORWARD_PID=$!

for _ in {1..30}; do
  if curl --silent --fail "$BASE_URL/health/simple" >/dev/null; then
    break
  fi
  sleep 1
done

if ! curl --silent --fail "$BASE_URL/health/simple" >/dev/null; then
  echo "Could not reach $SERVICE through $BASE_URL" >&2
  exit 1
fi

call_endpoint() {
  local label="$1"
  local method="$2"
  local path="$3"
  local body_file
  local status
  local -a curl_args

  body_file=$(mktemp)
  curl_args=(--silent --show-error --output "$body_file" --write-out '%{http_code}')
  if [[ "$method" == "POST" ]]; then
    curl_args+=(-X POST "$BASE_URL$path" -H 'content-type: application/json' -d @"$PAYLOAD")
  else
    curl_args+=("$BASE_URL$path")
  fi

  if ! status=$(curl "${curl_args[@]}"); then
    echo "  FAIL  $label: could not reach $BASE_URL$path" >&2
    rm -f "$body_file"
    exit 1
  fi

  if [[ ! "$status" =~ ^2[0-9][0-9]$ ]]; then
    echo "  FAIL  $label: $method $path -> HTTP $status" >&2
    echo "  Response:" >&2
    sed 's/^/    /' "$body_file" >&2
    rm -f "$body_file"
    exit 1
  fi

  RESPONSE_FILE="$body_file"
  echo "  PASS  $label: $method $path -> HTTP $status"
}

for i in {1..50}; do
  echo "Run $i/50"

  call_endpoint "Health check" GET "/health/simple"
  rm -f "$RESPONSE_FILE"

  call_endpoint "Evaluate without persistence" POST "/credit-decisions/evaluate"
  rm -f "$RESPONSE_FILE"

  call_endpoint "Create and persist decision" POST "/credit-decisions"
  DECISION_ID=$(jq -er '.decisionId' "$RESPONSE_FILE")
  CUSTOMER_ID=$(jq -er '.customerId' "$RESPONSE_FILE")
  echo "        decisionId=$DECISION_ID customerId=$CUSTOMER_ID"
  rm -f "$RESPONSE_FILE"

  call_endpoint "Read created decision" GET "/credit-decisions/$DECISION_ID"
  rm -f "$RESPONSE_FILE"

  call_endpoint "Read customer decisions" GET "/credit-decisions/customer/$CUSTOMER_ID"
  rm -f "$RESPONSE_FILE"
done

echo "Completed 50 successful workflows against $BASE_URL"
