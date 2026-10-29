#!/bin/sh
# ============================
# Simple host-based Swarm autoscaler
# ============================

# ---- CONFIG ----
SERVICE="${SERVICE:-back}"
STACK_NAME="${STACK_NAME:-demo}"
MIN_REPLICAS=1
MAX_REPLICAS=5
CPU_SCALE_UP=80           # percent
CPU_SCALE_DOWN=10         # percent
SLEEP=10                  # seconds between checks

echo "Starting autoscaler for ${STACK_NAME}_${SERVICE}"

while true; do
  # Get all tasks for this service that are running
  REPLICAS=$(docker service ps "${STACK_NAME}_${SERVICE}" \
    --filter desired-state=running -q 2>/dev/null | wc -l | tr -d ' ')
  REPLICAS="${REPLICAS:-0}"

  # Get total CPU usage across all containers of this service
  TOTAL_CPU=$(docker stats --no-stream --format "{{.Name}} {{.CPUPerc}}" 2>/dev/null \
    | grep "${STACK_NAME}_${SERVICE}" \
    | awk '{gsub(/%/,"",$2); sum+=$2} END {print int(sum)}')
  TOTAL_CPU="${TOTAL_CPU:-0}"

  echo "$(date) - CPU=${TOTAL_CPU}% | replicas=${REPLICAS}"

  # Scale up if CPU > threshold
  if [ "$TOTAL_CPU" -gt "$CPU_SCALE_UP" ] && [ "$REPLICAS" -lt "$MAX_REPLICAS" ]; then
    NEW=$((REPLICAS + 1))
    echo "Scaling UP -> $NEW replicas"
    docker service scale "${STACK_NAME}_${SERVICE}=$NEW"
  fi

  # Scale down if CPU < threshold
  if [ "$TOTAL_CPU" -lt "$CPU_SCALE_DOWN" ] && [ "$REPLICAS" -gt "$MIN_REPLICAS" ]; then
    NEW=$((REPLICAS - 1))
    echo "Scaling DOWN -> $NEW replicas"
    docker service scale "${STACK_NAME}_${SERVICE}=$NEW"
  fi

  sleep "$SLEEP"
done
