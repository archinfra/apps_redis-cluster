#!/usr/bin/env bash
set -Eeuo pipefail

IMAGE="${1:-}"
[[ -n "${IMAGE}" ]] || {
  echo "usage: $0 <redis-cluster-image>" >&2
  exit 2
}

PREFIX="redis-runtime-e2e-${RANDOM}-$$"
NETWORK="${PREFIX}-net"
SECRET_DIR="$(mktemp -d)"
PASSWORD='Arch #"\ cluster pass 8.10.1'
SECRET_FILE="${SECRET_DIR}/redis-password"
NODES=()
VOLUMES=()

for i in 0 1 2 3 4 5; do
  NODES+=("${PREFIX}-${i}")
  VOLUMES+=("${PREFIX}-data-${i}")
done

REDIS_NODES="${NODES[*]}"

cleanup() {
  set +e
  docker rm -f "${PREFIX}-ip-holder" >/dev/null 2>&1 || true
  for node in "${NODES[@]}"; do
    docker rm -f "${node}" >/dev/null 2>&1 || true
  done
  for volume in "${VOLUMES[@]}"; do
    docker volume rm "${volume}" >/dev/null 2>&1 || true
  done
  docker network rm "${NETWORK}" >/dev/null 2>&1 || true
  rm -rf "${SECRET_DIR}"
}
trap cleanup EXIT

retry() {
  local attempts="$1"
  local sleep_seconds="$2"
  shift 2
  local n=1
  until "$@"; do
    if (( n >= attempts )); then
      return 1
    fi
    sleep "${sleep_seconds}"
    n=$((n + 1))
  done
}

redis_exec() {
  local node="$1"
  shift
  docker exec -e "REDISCLI_AUTH=${PASSWORD}" "${node}" redis-cli --no-auth-warning "$@"
}

cluster_is_ok() {
  local info
  info="$(redis_exec "${NODES[0]}" cluster info 2>/dev/null || true)"
  grep -q '^cluster_state:ok' <<<"${info}" \
    && grep -q '^cluster_slots_assigned:16384' <<<"${info}" \
    && grep -q '^cluster_slots_ok:16384' <<<"${info}" \
    && grep -q '^cluster_known_nodes:6' <<<"${info}"
}

run_node() {
  local index="$1"
  local creator="${2:-no}"
  local node="${NODES[$index]}"
  local volume="${VOLUMES[$index]}"

  local -a args=(
    docker run -d
    --name "${node}"
    --hostname "${node}"
    --network "${NETWORK}"
    -v "${volume}:/bitnami/redis/data"
    -v "${SECRET_FILE}:/run/secrets/redis-password:ro"
    -e "REDIS_PASSWORD_FILE=/run/secrets/redis-password"
    -e "REDIS_NODES=${REDIS_NODES}"
    -e "REDIS_AOF_ENABLED=yes"
    -e "REDIS_CLUSTER_DYNAMIC_IPS=yes"
    -e "REDIS_CLUSTER_DNS_LOOKUP_RETRIES=120"
    -e "REDIS_CLUSTER_DNS_LOOKUP_SLEEP=1"
  )

  if [[ "${creator}" == "yes" ]]; then
    args+=(
      -e "REDIS_CLUSTER_CREATOR=yes"
      -e "REDIS_CLUSTER_REPLICAS=1"
      -e "REDISCLI_AUTH=${PASSWORD}"
    )
  fi

  args+=("${IMAGE}")
  "${args[@]}" >/dev/null
}

printf '%s' "${PASSWORD}" >"${SECRET_FILE}"
chmod 0600 "${SECRET_FILE}"

docker network create "${NETWORK}" >/dev/null
for volume in "${VOLUMES[@]}"; do
  docker volume create "${volume}" >/dev/null
done

# Start peers first. The creator starts itself in the background, waits for all
# six nodes, and then executes redis-cli --cluster create.
for i in 1 2 3 4 5; do
  run_node "${i}" no
done
run_node 0 yes

if ! retry 60 2 cluster_is_ok; then
  echo "Redis Cluster did not reach a healthy six-node state" >&2
  for node in "${NODES[@]}"; do
    echo "===== ${node} logs =====" >&2
    docker logs "${node}" >&2 || true
  done
  exit 1
fi

cluster_nodes="$(redis_exec "${NODES[0]}" cluster nodes)"
master_count="$(awk 'index($3,"master") {n++} END {print n+0}' <<<"${cluster_nodes}")"
replica_count="$(awk 'index($3,"slave") || index($3,"replica") {n++} END {print n+0}' <<<"${cluster_nodes}")"
[[ "${master_count}" == "3" ]] || {
  echo "expected 3 masters, got ${master_count}" >&2
  exit 1
}
[[ "${replica_count}" == "3" ]] || {
  echo "expected 3 replicas, got ${replica_count}" >&2
  exit 1
}

# Password-file contract and special-character escaping are exercised by every
# node. Validate persistence configuration and a real cluster-routed write/read.
redis_exec "${NODES[0]}" config get appendonly --raw | grep -qx 'yes'
redis_exec "${NODES[0]}" -c set archinfra:runtime-e2e ok >/dev/null
[[ "$(redis_exec "${NODES[0]}" -c get archinfra:runtime-e2e)" == "ok" ]]

# Dynamic-IP recovery: keep the old address occupied, restart one replica with
# the same persistent data, and require the runtime to repair nodes.conf and
# return the cluster to cluster_state:ok.
OLD_IP="$(docker inspect -f '{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}' "${NODES[5]}")"
docker rm -f "${NODES[5]}" >/dev/null

docker run -d \
  --name "${PREFIX}-ip-holder" \
  --network "${NETWORK}" \
  --entrypoint /bin/sleep \
  "${IMAGE}" 300 >/dev/null

run_node 5 no
NEW_IP="$(docker inspect -f '{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}' "${NODES[5]}")"
[[ -n "${NEW_IP}" && "${NEW_IP}" != "${OLD_IP}" ]] || {
  echo "dynamic-IP test could not force an address change (${OLD_IP} -> ${NEW_IP})" >&2
  exit 1
}

nodes_conf_repaired() {
  docker exec "${NODES[5]}" grep -Fq "${NEW_IP}:6379" /bitnami/redis/data/nodes.conf
}
retry 30 1 nodes_conf_repaired || {
  echo "nodes.conf was not repaired to the new Pod/container IP" >&2
  docker exec "${NODES[5]}" cat /bitnami/redis/data/nodes.conf >&2 || true
  exit 1
}

docker rm -f "${PREFIX}-ip-holder" >/dev/null
retry 60 2 cluster_is_ok || {
  echo "cluster did not recover after dynamic-IP restart" >&2
  exit 1
}

[[ "$(redis_exec "${NODES[0]}" -c get archinfra:runtime-e2e)" == "ok" ]]

echo "redis runtime cluster E2E: OK"
