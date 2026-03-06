#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
source /root/.openclaw/workspace/.venv/bin/activate
python scripts/mooc_requests_probe.py
python scripts/mooc_playwright_probe.py
