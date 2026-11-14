#!/usr/bin/env bash
# Start the MES backend and frontend together. Ctrl+C stops everything.
#
#   ./start.sh        Pi / demo: backend on :5000 serves the built screens;
#                     frontend edits rebuild dist/ automatically (refresh the browser)
#   ./start.sh dev    Laptop: Vite dev server on :5173 with hot reload, proxying to :5000
#
# Backend .py edits and data/op10.json edits restart the backend automatically.
# A backend left running from an earlier run is stopped first, so you never
# need to hunt down the process holding port 5000.
set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND="$ROOT/Backend"
FRONTEND="$ROOT/Frontend"
PORT="${MES_PORT:-5000}"
MODE="${1:-pi}"

PY="$BACKEND/.venv/bin/python"
[ -x "$PY" ] || PY="$(command -v python3)"

say() { printf '\033[1m[start]\033[0m %s\n' "$*"; }

# ---------- process cleanup ----------
# Kill a process and all of its children (Flask's reloader and npm both spawn
# children that would otherwise survive and keep holding ports).
kill_tree() {
  local pid=$1 sig=${2:-TERM} child
  for child in $(pgrep -P "$pid" 2>/dev/null); do kill_tree "$child" "$sig"; done
  kill "-$sig" "$pid" 2>/dev/null
}

PIDS=()
cleanup() {
  trap - INT TERM EXIT
  say "stopping..."
  for pid in "${PIDS[@]}"; do kill_tree "$pid" TERM; done
  sleep 1
  for pid in "${PIDS[@]}"; do kill_tree "$pid" KILL; done   # anything that ignored TERM
  free_port quiet
  say "stopped"
  exit 0
}
trap cleanup INT TERM EXIT

# Stop whatever MES backend is still on the port from a previous run.
# Refuses to touch anything that isn't our backend.
free_port() {
  local pids pid cmd
  pids=$(ss -ltnpH "sport = :$PORT" 2>/dev/null | grep -o 'pid=[0-9]*' | cut -d= -f2 | sort -u)
  [ -z "$pids" ] && return 0
  for pid in $pids; do
    cmd=$(tr '\0' ' ' < "/proc/$pid/cmdline" 2>/dev/null)
    if [[ "$cmd" == *app.py* || "$cmd" == *flask* ]]; then
      [ "${1:-}" = quiet ] || say "stopping old backend on :$PORT (pid $pid)"
      kill_tree "$pid" TERM
    else
      say "port $PORT is used by something else (pid $pid: $cmd). Stop it or set MES_PORT."
      exit 1
    fi
  done
  for _ in 1 2 3 4 5 6; do
    ss -ltnH "sport = :$PORT" | grep -q . || return 0
    sleep 0.5
  done
  for pid in $pids; do kill_tree "$pid" KILL; done
}

# ---------- start ----------
free_port

if [ ! -d "$FRONTEND/node_modules" ]; then
  say "installing frontend packages (first run)"
  (cd "$FRONTEND" && npm ci) || exit 1
fi

if [ "$MODE" = dev ]; then
  say "frontend: Vite dev server on http://localhost:5173 (hot reload)"
  (cd "$FRONTEND" && exec npm run dev -- --host) &
  PIDS+=($!)
else
  say "frontend: building once, then rebuilding on every change"
  (cd "$FRONTEND" && npm run build) || exit 1
  (cd "$FRONTEND" && exec npm run build -- --watch >/dev/null) &
  PIDS+=($!)
fi

say "backend: http://localhost:$PORT (auto-restarts on code changes)"
(cd "$BACKEND" && MES_RELOAD=1 MES_PORT="$PORT" exec "$PY" app.py) &
PIDS+=($!)

say "running. Ctrl+C to stop everything."
# If either side crashes, stop the other too instead of leaving half a system up.
wait -n
say "a process exited on its own"
