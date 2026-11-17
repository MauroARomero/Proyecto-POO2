#!/usr/bin/env bash
# Registra CPU/memoria cada N segundos en un CSV (alternativa ligera a Prometheus/Grafana).
# Uso:  MODE=docker ./scripts/collect_resources.sh results/recursos_compose.csv [intervalo=5]
#       MODE=k8s    ./scripts/collect_resources.sh results/recursos_k8s-2nodos.csv [intervalo=5]
# Termina con Ctrl+C (lánzalo en otra terminal mientras corre JMeter).
set -euo pipefail
[ "$#" -ge 1 ] || { sed -n '2,5p' "$0"; exit 1; }
OUT=$1; INTERVAL=${2:-5}; MODE=${MODE:-docker}
echo "timestamp,recurso,cpu,memoria" > "$OUT"
while true; do
  TS=$(date +%s)
  if [ "$MODE" = "docker" ]; then
    docker stats --no-stream --format '{{.Name}},{{.CPUPerc}},{{.MemUsage}}' | sed "s/^/${TS},/" >> "$OUT"
  else
    kubectl -n tienda top pods --no-headers | awk -v ts="$TS" '{print ts",pod/"$1","$2","$3}' >> "$OUT"
    kubectl top nodes --no-headers | awk -v ts="$TS" '{print ts",node/"$1","$2","$4}' >> "$OUT"
  fi
  sleep "$INTERVAL"
done
