# Monitorización (opcional)

## Docker Compose
```bash
docker compose -f docker-compose.yml -f docker-compose.monitoring.yml up -d --build
```
- Prometheus: http://localhost:9090  (targets en *Status > Targets*)
- Grafana: http://localhost:3000 (usuario `admin`, clave `admin`); la fuente de datos Prometheus ya viene aprovisionada.

## Kubernetes
```bash
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo update
helm install monitoring prometheus-community/kube-prometheus-stack \
  -n monitoring --create-namespace -f monitoring/k8s/values-kube-prometheus-stack.yaml
kubectl apply -f k8s/optional/servicemonitor.yaml
```
Grafana queda en `http://<ip-de-un-nodo>:30300` (admin / admin). El chart ya incluye
paneles de uso de CPU/memoria por pod y por nodo.

## Consultas PromQL útiles
| Qué mide | Consulta |
|---|---|
| CPU por pod de la API (núcleos) | `sum(rate(container_cpu_usage_seconds_total{namespace="tienda",container="api"}[1m])) by (pod)` |
| Memoria por pod (bytes) | `sum(container_memory_working_set_bytes{namespace="tienda",container="api"}) by (pod)` |
| Peticiones/s de la app | `sum(rate(http_requests_total{path!="/metrics"}[1m]))` |
| Latencia p95 de la app | `histogram_quantile(0.95, sum(rate(http_request_duration_seconds_bucket[1m])) by (le))` |
| CPU por nodo (%) | `100 * (1 - avg by (instance) (rate(node_cpu_seconds_total{mode="idle"}[1m])))` |
| CPU contenedores en Compose | `rate(container_cpu_usage_seconds_total{name=~"tienda.*"}[1m])` |

Sin Prometheus también puedes registrar recursos con `docker stats` (Compose) o
`kubectl top pods -n tienda` / `kubectl top nodes` (K8s; K3s trae metrics-server).
