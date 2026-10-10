#!/bin/zsh
set -e
cd "$(dirname "$0")"
echo "Starting Safe Route Finder at http://127.0.0.1:8000/frontend/index.html"
command -v python3 >/dev/null || { echo "Python 3 is required."; exit 1; }
[ -f data/roads.graphml ] || { echo "Missing data/roads.graphml"; exit 1; }
[ -f data/streetlights.csv ] || { echo "Missing data/streetlights.csv"; exit 1; }
python3 backend/server.py &
server_pid=$!
trap 'kill "$server_pid" 2>/dev/null || true' EXIT INT TERM
sleep 2
open "http://127.0.0.1:8000/frontend/index.html" 2>/dev/null || true
wait "$server_pid"
