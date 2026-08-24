#!/usr/bin/env bash
set -euo pipefail

BASE_URL="http://193.122.233.175"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
PAYLOAD="$REPO_ROOT/api/sample-requests/approved.json"

for i in {1..50}; do
  echo "Run $i"

  curl -s "$BASE_URL/health/simple" > /dev/null

  curl -s -X POST "$BASE_URL/credit-decisions/evaluate" \
    -H 'content-type: application/json' \
    -d @"$PAYLOAD" > /dev/null

  RESPONSE=$(curl -s -X POST "$BASE_URL/credit-decisions" \
    -H 'content-type: application/json' \
    -d @"$PAYLOAD")

  DECISION_ID=$(echo "$RESPONSE" | jq -r '.decisionId')
  CUSTOMER_ID=$(echo "$RESPONSE" | jq -r '.customerId')

  curl -s "$BASE_URL/credit-decisions/$DECISION_ID" > /dev/null
  curl -s "$BASE_URL/credit-decisions/customer/$CUSTOMER_ID" > /dev/null
done
