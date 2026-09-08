#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/../.."
python -m unittest discover -s tests -p 'test_agent_*.py' -v
shellcheck hooks/* scripts/checks/*.sh 2>/dev/null || [[ ! -d hooks ]]
