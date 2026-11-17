#!/usr/bin/env bash
# Ejecuta el plan de JMeter (modo no-GUI) para varios niveles de carga.
#
# Uso:    ./scripts/run_jmeter.sh <escenario> <host> <puerto> <replicas> [usuarios ...]
# Ej.:    ./scripts/run_jmeter.sh compose 192.168.1.20 8000 1
#         ./scripts/run_jmeter.sh k8s-2nodos 192.168.1.21 30080 3 10 50 100 200
#
# Escenarios reconocidos por el notebook: compose | k8s-1nodo | k8s-2nodos | k8s-3nodos
# Variables opcionales: DURATION (150 s totales), RAMP (30 s), THINK_MS (100), PAUSE (30 s entre pruebas),
#                       CONNECTION (keep-alive|close), RUN_ID (sufijo para repeticiones), REPORT=1 (informe HTML),
#                       JMETER_BIN (por defecto "jmeter").
# Importante: ejecútalo desde una máquina DISTINTA a la que aloja la aplicación.
set -euo pipefail

if [ "$#" -lt 4 ]; then
  sed -n '2,13p' "$0"; exit 1
fi
SCENARIO=$1; HOST=$2; PORT=$3; REPLICAS=$4; shift 4
if [ "$#" -gt 0 ]; then USERS=("$@"); else USERS=(10 50 100 200); fi

DURATION=${DURATION:-150}
RAMP=${RAMP:-30}
THINK_MS=${THINK_MS:-100}
PAUSE=${PAUSE:-30}
CONNECTION=${CONNECTION:-keep-alive}
JMETER_BIN=${JMETER_BIN:-jmeter}
ROOT=$(cd "$(dirname "$0")/.." && pwd)
mkdir -p "$ROOT/results"

# Comprobación previa: la API debe responder y tener datos.
echo ">> Verificando http://$HOST:$PORT/reports/counts"
curl -fsS "http://$HOST:$PORT/reports/counts" && echo

for u in "${USERS[@]}"; do
  NAME="${SCENARIO}__r${REPLICAS}__u${u}"
  [ -n "${RUN_ID:-}" ] && NAME="${NAME}__run${RUN_ID}"
  OUT="$ROOT/results/$NAME"
  rm -f "$OUT.jtl"
  echo ">> $NAME  (usuarios=$u, duración=${DURATION}s, ramp-up=${RAMP}s)"
  ARGS=(-n -t "$ROOT/jmeter/plan_tienda.jmx"
        -Jhost="$HOST" -Jport="$PORT" -Jthreads="$u" -Jrampup="$RAMP"
        -Jduration="$DURATION" -Jthink_ms="$THINK_MS" -Jconnection="$CONNECTION"
        -l "$OUT.jtl" -j "$OUT.log")
  if [ "${REPORT:-0}" = "1" ]; then
    rm -rf "$ROOT/reports/$NAME"; mkdir -p "$ROOT/reports"
    ARGS+=(-e -o "$ROOT/reports/$NAME")
  fi
  "$JMETER_BIN" "${ARGS[@]}"
  echo ">> Pausa de ${PAUSE}s para que se estabilice el sistema"
  sleep "$PAUSE"
done
echo ">> Resultados en $ROOT/results/"
