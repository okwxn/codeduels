#!/usr/bin/env bash
# Start a built image and check it serves the page, the problems and room creation.
set -euo pipefail
image=$1
base=http://localhost:18080

id=$(docker run -d -e PORT=8080 -p 18080:8080 "$image")
cleanup() {
  local rc=$?
  [ "$rc" -ne 0 ] && docker logs "$id"
  docker rm -f "$id" >/dev/null
}
trap cleanup EXIT

ready=
for _ in $(seq 30); do
  if curl -sf "$base/api/topics" >/dev/null; then ready=1; break; fi
  [ "$(docker inspect -f '{{.State.Running}}' "$id")" = true ] || { echo "container exited during startup"; exit 1; }
  sleep 1
done
[ -n "$ready" ] || { echo "server not ready after 30s"; exit 1; }

page=$(curl -sf "$base/")
grep -q "<title>CodeDuels</title>" <<<"$page" || { echo "index page missing"; exit 1; }

topics=$(curl -sf "$base/api/topics")
[ "$topics" != "{}" ] || { echo "no problems loaded"; exit 1; }

room=$(curl -sf -X POST -H 'content-type: application/json' -d '{}' "$base/api/rooms")
grep -q '"code"' <<<"$room" || { echo "room creation failed: $room"; exit 1; }

[ "$(docker exec "$id" whoami)" = app ] || { echo "container not running as app user"; exit 1; }

echo "smoke test passed"
