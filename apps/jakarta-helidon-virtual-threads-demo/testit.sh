#!/usr/bin/env bash
set -euo pipefail

# Exercise the deployed service through the public gateway.
# Override BASE_URL when the gateway address changes.
BASE_URL="${BASE_URL:-http://193.122.233.175}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PAYLOAD="$SCRIPT_DIR/api/sample-requests/approved.json"
RESPONSE_FILE=""

cleanup() {
  [[ -n "$RESPONSE_FILE" ]] && rm -f "$RESPONSE_FILE"
}
trap cleanup EXIT

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
