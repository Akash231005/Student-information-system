#!/usr/bin/env bash
# Stop everything this project started, then prove it stopped.
#
#   ./stop.sh              stop the API and the sis-* containers
#   ./stop.sh --dry-run    print what would be stopped, change nothing
#
# Scope: only this project's API process and the sis-* containers. Unrelated services on this
# machine (other dev servers, other containers) are left alone on purpose.
#
# Data survives: containers are stopped, never removed, and no volume is ever pruned. `./run.sh`
# brings the same database back.
set -euo pipefail

ROOT=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
APP="$ROOT/sis-app"
RUN="$APP/.run"
API_PORT=${API_PORT:-8000}
CONTAINERS="sis-mongos sis-mongo-a sis-mongo-b sis-mongo-cfg sis-redis sis-postgres sis-verify-pg"
PORTS="5432 6379 27017 27019 27021 27022 $API_PORT"
DRY=0

say()  { printf '\n\033[1m==> %s\033[0m\n' "$*"; }
ok()   { printf '    \033[32m%s\033[0m\n' "$*"; }
warn() { printf '    \033[33m%s\033[0m\n' "$*"; }
port_open() { (exec 3<>"/dev/tcp/127.0.0.1/$1") 2>/dev/null; }
have() { command -v "$1" >/dev/null 2>&1; }

for arg in "$@"; do
  case "$arg" in
    --dry-run) DRY=1 ;;
    -h|--help) sed -n '2,12p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'; exit 0 ;;
    *) printf 'unknown option: %s (try --help)\n' "$arg" >&2; exit 2 ;;
  esac
done

is_our_api() {  # pid - true only when the process really is this app's uvicorn
  local pid=$1 cmd
  [ -r "/proc/$pid/cmdline" ] || return 1
  cmd=$(tr '\0' ' ' < "/proc/$pid/cmdline")
  case "$cmd" in
    *uvicorn*app.main:app*) return 0 ;;
    *) return 1 ;;
  esac
}

stop_api() {
  local pid killed=0
  if [ -f "$RUN/api.pid" ]; then
    pid=$(cat "$RUN/api.pid" 2>/dev/null || true)
    if [ -n "${pid:-}" ] && is_our_api "$pid"; then
      [ "$DRY" = 1 ] && { warn "would stop API pid $pid"; return 0; }
      kill "$pid" 2>/dev/null || true
      for _ in $(seq 20); do kill -0 "$pid" 2>/dev/null || break; sleep 0.3; done
      kill -0 "$pid" 2>/dev/null && kill -9 "$pid" 2>/dev/null || true
      ok "API stopped (pid $pid)"
      killed=1
    fi
    [ "$DRY" = 1 ] || rm -f "$RUN/api.pid"
  fi
  # Fallback for a server started by hand: match the argv, never the shell.
  for pid in $(pgrep -f 'uvicorn app[.]main:app' 2>/dev/null || true); do
    is_our_api "$pid" || continue
    [ "$DRY" = 1 ] && { warn "would stop stray API pid $pid"; continue; }
    kill "$pid" 2>/dev/null || true
    sleep 0.5
    kill -0 "$pid" 2>/dev/null && kill -9 "$pid" 2>/dev/null || true
    ok "stray API stopped (pid $pid)"
    killed=1
  done
  [ "$killed" = 0 ] && [ "$DRY" = 0 ] && ok "API was not running"
  return 0
}

stop_containers() {
  have podman || { warn "podman not installed - skipping containers"; return 0; }
  local name running
  for name in $CONTAINERS; do
    podman container exists "$name" 2>/dev/null || continue
    running=$(podman inspect -f '{{.State.Running}}' "$name" 2>/dev/null || echo false)
    [ "$running" = "true" ] || continue
    if [ "$DRY" = 1 ]; then warn "would stop container $name"; continue; fi
    podman stop -t 10 "$name" >/dev/null 2>&1 || true
    ok "container stopped: $name"
  done
  return 0
}

say "Stopping this project's services"
stop_api
stop_containers

if [ "$DRY" = 1 ]; then
  printf '\n\033[33mDry run: nothing was changed.\033[0m\n'
  exit 0
fi

say "Verifying nothing is left running"
leftover=0
printf '    %-8s %s\n' PORT STATE
for port in $PORTS; do
  if port_open "$port"; then
    printf '    %-8s \033[31mstill open\033[0m\n' "$port"
    leftover=1
  else
    printf '    %-8s \033[32mclosed\033[0m\n' "$port"
  fi
done

printf '\n    %-16s %s\n' PROCESS STATE
if pgrep -f 'uvicorn app[.]main:app' >/dev/null 2>&1; then
  printf '    %-16s \033[31mstill running\033[0m\n' "api" && leftover=1
else
  printf '    %-16s \033[32mstopped\033[0m\n' "api"
fi

if have podman; then
  still=$(podman ps --filter 'name=sis-' --format '{{.Names}}' 2>/dev/null | tr '\n' ' ' || true)
  if [ -n "${still// /}" ]; then
    printf '    %-16s \033[31mstill running: %s\033[0m\n' "containers" "$still" && leftover=1
  else
    printf '    %-16s \033[32mstopped\033[0m\n' "containers"
  fi
fi

if [ "$leftover" = 1 ]; then
  printf '\n\033[33mSomething is still up.\033[0m Check it with:\n'
  printf '  ss -ltnp | grep -E ":(5432|6379|27017|27019|27021|27022|%s)\\b"\n' "$API_PORT"
  printf '  podman ps --format "{{.Names}} {{.Status}}"\n'
  exit 1
fi

printf '\n\033[1;32mAll stopped.\033[0m Data volumes are untouched: ./run.sh brings the same database back.\n\n'
