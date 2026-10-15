#!/usr/bin/env bash
# Start a built image and check it serves the page, the problems and room creation.
set -euo pipefail
image=$1

# Create first and trap before starting, so a failed start is still cleaned up
id=$(docker create -e PORT=8080 -p 127.0.0.1::8080 "$image")
cleanup() {
  local rc=$?
  [ "$rc" -ne 0 ] && docker logs "$id"
  docker rm -f "$id" >/dev/null
}
trap cleanup EXIT
docker start "$id" >/dev/null
# Let Docker pick a free host port
base=http://$(docker port "$id" 8080/tcp | head -n1)

ready=
for _ in $(seq 30); do
  if curl -sf --max-time 5 "$base/api/topics" >/dev/null; then ready=1; break; fi
  [ "$(docker inspect -f '{{.State.Running}}' "$id")" = true ] || { echo "container exited during startup"; exit 1; }
  sleep 1
done
[ -n "$ready" ] || { echo "server not ready after 30s"; exit 1; }

page=$(curl -sf --max-time 5 "$base/")
grep -q "<title>CodeDuels</title>" <<<"$page" || { echo "index page missing"; exit 1; }

topics=$(curl -sf --max-time 5 "$base/api/topics")
[ "$topics" != "{}" ] || { echo "no problems loaded"; exit 1; }

room=$(curl -sf --max-time 5 -X POST -H 'content-type: application/json' -d '{}' "$base/api/rooms")
grep -q '"code"' <<<"$room" || { echo "room creation failed: $room"; exit 1; }

[ "$(docker exec "$id" whoami)" = app ] || { echo "container not running as app user"; exit 1; }

echo "smoke test passed"
