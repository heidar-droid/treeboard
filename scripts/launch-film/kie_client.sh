#!/bin/bash
# Kie.ai API client helpers for the Treeboard launch film
set -euo pipefail

KIE_API_KEY="${KIE_API_KEY:-$(grep '^KIE_API_KEY=' "/Users/smb/Infinivo AI Workspace/.env" | head -1 | cut -d= -f2)}"
KIE_BASE="https://api.kie.ai/api/v1"

kie_post() {
  local path="$1"
  local body="$2"
  curl -s -X POST "${KIE_BASE}${path}" \
    -H "Authorization: Bearer ${KIE_API_KEY}" \
    -H "Content-Type: application/json" \
    -d "${body}"
}

kie_get() {
  local path="$1"
  curl -s -X GET "${KIE_BASE}${path}" \
    -H "Authorization: Bearer ${KIE_API_KEY}"
}

export -f kie_post kie_get
export KIE_API_KEY KIE_BASE
