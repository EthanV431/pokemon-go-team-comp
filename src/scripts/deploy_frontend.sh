#!/usr/bin/env bash
set -euo pipefail

if [ $# -lt 2 ]; then
  echo "usage: $0 <frontend-bucket> <api-base-url>"
  exit 1
fi

FRONTEND_BUCKET="$1"
API_BASE="$2"

SCRIPT_DIR="$(cd -- "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# Go two levels up: src/scripts -> (..) src -> (..) repo root
ROOT_DIR="$(realpath "${SCRIPT_DIR}/../..")"

cd "${ROOT_DIR}"

if [ ! -f package.json ]; then
  echo "Error: package.json not found in ${ROOT_DIR}"
  exit 1
fi

export REACT_APP_API_BASE="$API_BASE"

if [ -f package-lock.json ]; then
  npm ci
else
  npm install
fi

npm run build

aws s3 sync build/ "s3://${FRONTEND_BUCKET}/" --delete
echo "Deployed frontend to s3://${FRONTEND_BUCKET}/"