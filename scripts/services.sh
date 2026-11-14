#!/usr/bin/env bash
# Dispatch docker compose actions across the services enabled in install config.
#
# Usage:
#   scripts/services.sh list                       # show catalog + enabled state
#   scripts/services.sh up [id ...]                # start enabled (or named) services
#   scripts/services.sh down [id ...]              # stop them
#   scripts/services.sh restart [id ...]
#   scripts/services.sh status                     # containers + health
#   scripts/services.sh logs <id> [-f]             # tail one service

set -euo pipefail

cd "$(dirname "$0")/.."

if ! command -v docker >/dev/null 2>&1; then
  echo "Error: docker not installed. Install Docker Desktop first." >&2
  exit 1
fi
if ! docker compose version >/dev/null 2>&1; then
  echo "Error: 'docker compose' (v2) not available. Update Docker Desktop." >&2
  exit 1
fi

PY=build/venv/bin/python
[[ -x "$PY" ]] || PY=python3

# Return the IDs of services enabled in the install config.
enabled_ids() {
  "$PY" - <<'PY' 2>/dev/null
try:
    from rag.install_config import load_effective_config
    eff = load_effective_config()
    for sid in (eff.get("services") or {}).keys():
        print(sid)
except Exception:
    pass
PY
}

# All services in the catalog.
catalog_ids() {
  "$PY" - <<'PY' 2>/dev/null
import yaml
with open("services/catalog.yaml") as f:
    for s in (yaml.safe_load(f) or {}).get("services") or []:
        print(s["id"])
PY
}

catalog_field() {
  local id="$1" field="$2"
  "$PY" - "$id" "$field" <<'PY' 2>/dev/null
import sys, yaml
want_id, want_field = sys.argv[1], sys.argv[2]
with open("services/catalog.yaml") as f:
    for s in (yaml.safe_load(f) or {}).get("services") or []:
        if s["id"] == want_id:
            print(s.get(want_field, ""))
            break
PY
}

compose_for() {
  local id="$1"
  local dir
  dir="$(catalog_field "$id" service_dir)"
  if [[ -z "$dir" || ! -d "services/$dir" ]]; then
    echo "  [err] unknown service id: $id" >&2
    return 1
  fi
  docker compose --project-directory "services/$dir" -f "services/$dir/docker-compose.yml" "${@:2}"
}

# Which services do we act on? Positional args win; else all enabled.
resolve_targets() {
  if [[ $# -gt 0 ]]; then
    echo "$@"; return
  fi
  enabled_ids
}

cmd="${1:-list}"
shift || true

case "$cmd" in
  list)
    enabled="$(enabled_ids | tr '\n' ' ')"
    printf "%-14s %-6s %s\n" "id" "state" "title"
    printf "%-14s %-6s %s\n" "--" "-----" "-----"
    while IFS= read -r id; do
      [[ -z "$id" ]] && continue
      state=$([[ " $enabled " == *" $id "* ]] && echo "on" || echo "off")
      title="$(catalog_field "$id" title)"
      printf "%-14s %-6s %s\n" "$id" "$state" "$title"
    done < <(catalog_ids)
    ;;

  up|down|restart)
    targets=( $(resolve_targets "$@") )
    if [[ ${#targets[@]} -eq 0 ]]; then
      echo "No services enabled. Run 'pergamon setup' or pass IDs explicitly." >&2
      exit 1
    fi
    for id in "${targets[@]}"; do
      echo "==> $cmd $id"
      case "$cmd" in
        up)      compose_for "$id" up -d ;;
        down)    compose_for "$id" down ;;
        restart) compose_for "$id" restart ;;
      esac
    done
    ;;

  status)
    docker ps --filter "name=pergamon-" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
    ;;

  logs)
    id="${1:-}"
    if [[ -z "$id" ]]; then
      echo "Usage: pergamon services logs <id> [-f]" >&2
      exit 2
    fi
    shift
    compose_for "$id" logs "$@"
    ;;

  *)
    echo "Usage: pergamon services {list|up|down|restart|status|logs}" >&2
    exit 2
    ;;
esac
