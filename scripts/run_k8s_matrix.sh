#!/usr/bin/env bash
# Recorre las réplicas (1, 2, 3 por defecto) de un escenario Kubernetes y lanza JMeter en cada una.
#
# Uso:  ./scripts/run_k8s_matrix.sh <k8s-1nodo|k8s-2nodos|k8s-3nodos> <ip-de-un-nodo> [puerto=30080]
# Requiere: kubectl con acceso al clúster (copia el kubeconfig a la máquina de carga) y JMeter instalado.
# Variables: REPLICAS_LIST="1 2 3"  USERS_LIST="10 50 100 200" (más las de run_jmeter.sh)
set -euo pipefail

if [ "$#" -lt 2 ]; then sed -n '2,7p' "$0"; exit 1; fi
SCENARIO=$1; HOST=$2; PORT=${3:-30080}
REPLICAS_LIST=${REPLICAS_LIST:-"1 2 3"}
USERS_LIST=${USERS_LIST:-"10 50 100 200"}
NS=tienda
ROOT=$(cd "$(dirname "$0")/.." && pwd)
mkdir -p "$ROOT/results"

echo ">> Nodos del clúster:"; kubectl get nodes -o wide

for r in $REPLICAS_LIST; do
  echo "=== $SCENARIO con $r réplica(s) ==="
  # Se reinicia desde 0 para que el scheduler reparta los pods desde cero entre los nodos.
  kubectl -n "$NS" scale deployment/api --replicas=0
  kubectl -n "$NS" wait --for=delete pod -l app=api --timeout=120s || true
  kubectl -n "$NS" scale deployment/api --replicas="$r"
  kubectl -n "$NS" rollout status deployment/api --timeout=240s
  kubectl -n "$NS" get pods -l app=api -o wide | tee "$ROOT/results/${SCENARIO}__r${r}__pods.txt"
  sleep 10   # margen para que kube-proxy actualice los endpoints

  # shellcheck disable=SC2086
  "$ROOT/scripts/run_jmeter.sh" "$SCENARIO" "$HOST" "$PORT" "$r" $USERS_LIST
done
