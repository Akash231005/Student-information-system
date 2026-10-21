#!/usr/bin/env bash
# Start every state store the app needs: PostgreSQL, Redis and a real MongoDB sharded cluster.
#
# Rootless podman on this host cannot publish ports (its "pasta" network backend is broken),
# so every container runs with --network=host and binds its own loopback port:
#
#   postgres   5432     redis               6379     mongos (router)      27017
#   configsvr  27019    shard-a / shard-b   27021 / 27022
#
# Re-running is safe: existing containers are started, running replica sets keep their
# config, and an already-registered shard is left alone.
set -euo pipefail

MONGO_IMAGE=${MONGO_IMAGE:-docker.io/library/mongo:7.0}
REDIS_IMAGE=${REDIS_IMAGE:-docker.io/library/redis:7-alpine}
PG_IMAGE=${PG_IMAGE:-docker.io/library/postgres:17-alpine}
CACHE_GB=${CACHE_GB:-0.25}   # WiredTiger cache per mongod; 0.25 is the server minimum

log() { printf '\n\033[1m==> %s\033[0m\n' "$*"; }

container_up() {
  local name=$1 image=$2
  shift 2
  if podman container exists "$name"; then
    if [ "$(podman inspect -f '{{.State.Running}}' "$name")" = "true" ]; then
      echo "    $name already running"
    else
      podman start "$name" >/dev/null
      echo "    $name restarted"
    fi
  else
    podman run -d --name "$name" --network=host "$image" "$@" >/dev/null
    echo "    $name created"
  fi
}

wait_port() {
  local port=$1 name=$2 tries=${3:-60}
  for _ in $(seq "$tries"); do
    if (exec 3<>"/dev/tcp/127.0.0.1/$port") 2>/dev/null; then
      exec 3>&- 3<&-
      return 0
    fi
    sleep 1
  done
  echo "timed out waiting for $name on port $port" >&2
  podman logs --tail 20 "$name" >&2 || true
  return 1
}

mongo_eval() {  # container port js
  podman exec "$1" mongosh --quiet --port "$2" --eval "$3"
}

wait_primary() {  # container port label
  for _ in $(seq 60); do
    if [ "$(mongo_eval "$1" "$2" 'db.hello().isWritablePrimary' 2>/dev/null | tr -d '[:space:]')" = "true" ]; then
      echo "    $3 has a primary"
      return 0
    fi
    sleep 1
  done
  echo "$3 never elected a primary" >&2
  return 1
}

init_replicaset() {  # container port setname extra-config
  local container=$1 port=$2 setname=$3
  mongo_eval "$container" "$port" \
    "try { rs.initiate({_id: '$setname', members: [{_id: 0, host: '127.0.0.1:$port'}]}); }
     catch (e) { if (e.codeName !== 'AlreadyInitialized') throw e; }" >/dev/null
  wait_primary "$container" "$port" "$setname"
}

log "PostgreSQL (authoritative records)"
if ! podman container exists sis-postgres; then
  echo "    sis-postgres is missing; recreate it from the old volume with:" >&2
  echo "    podman run -d --name sis-postgres --network=host -e POSTGRES_DB=sis \\" >&2
  echo "      -e POSTGRES_USER=sis -e POSTGRES_PASSWORD=sis_dev_only \\" >&2
  echo "      -v <old-pgdata-volume>:/var/lib/postgresql/data $PG_IMAGE" >&2
  exit 1
fi
container_up sis-postgres "$PG_IMAGE"
wait_port 5432 sis-postgres

log "Redis (shared rate-limit buckets, cache, ID worker slots)"
container_up sis-redis "$REDIS_IMAGE" \
  redis-server --maxmemory 128mb --maxmemory-policy allkeys-lru \
  --save '' --appendonly no --bind 127.0.0.1
wait_port 6379 sis-redis

log "MongoDB config server (chunk metadata)"
container_up sis-mongo-cfg "$MONGO_IMAGE" \
  mongod --configsvr --replSet sis-cfg --port 27019 --bind_ip 127.0.0.1 \
  --dbpath /data/db --wiredTigerCacheSizeGB "$CACHE_GB"
wait_port 27019 sis-mongo-cfg
init_replicaset sis-mongo-cfg 27019 sis-cfg

log "MongoDB shards"
container_up sis-mongo-a "$MONGO_IMAGE" \
  mongod --shardsvr --replSet sis-shard-a --port 27021 --bind_ip 127.0.0.1 \
  --dbpath /data/db --wiredTigerCacheSizeGB "$CACHE_GB"
wait_port 27021 sis-mongo-a
init_replicaset sis-mongo-a 27021 sis-shard-a

container_up sis-mongo-b "$MONGO_IMAGE" \
  mongod --shardsvr --replSet sis-shard-b --port 27022 --bind_ip 127.0.0.1 \
  --dbpath /data/db --wiredTigerCacheSizeGB "$CACHE_GB"
wait_port 27022 sis-mongo-b
init_replicaset sis-mongo-b 27022 sis-shard-b

log "mongos (query router)"
container_up sis-mongos "$MONGO_IMAGE" \
  mongos --configdb sis-cfg/127.0.0.1:27019 --port 27017 --bind_ip 127.0.0.1
wait_port 27017 sis-mongos

log "Registering shards with the cluster"
for shard in sis-shard-a/127.0.0.1:27021 sis-shard-b/127.0.0.1:27022; do
  mongo_eval sis-mongos 27017 \
    "try { sh.addShard('$shard'); } catch (e) {
       if (!/already exists/.test(e.message)) throw e; }" >/dev/null
  echo "    $shard registered"
done

log "Cluster state"
mongo_eval sis-mongos 27017 \
  "print('shards: ' + db.adminCommand({listShards: 1}).shards.map(s => s._id).join(', '));
   print('mongos: ' + db.hello().me)"
echo "    redis: $(podman exec sis-redis redis-cli info server | grep redis_version)"

printf '\n\033[1;32mStack ready.\033[0m  Start the API with:\n'
printf '  cd sis-app && uv run uvicorn app.main:app --host 127.0.0.1 --port 8000\n'
