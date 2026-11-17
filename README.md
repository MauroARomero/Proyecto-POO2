# Proyecto Final: comportamiento de una aplicación bajo distintos escenarios de despliegue

Curso: *Principios y prácticas de Desarrollo de Software Orientado a Objetos*.

Se despliega una misma API REST ("Tienda API", FastAPI + PostgreSQL con más de 150.000 registros) en
**Docker Compose** y en **Kubernetes de 1, 2 y 3 nodos** variando las réplicas (1, 2, 3). Se genera carga con
**JMeter** y se analizan **tiempo medio de respuesta** y **throughput** en un **Notebook de Jupyter**.

```
.
├── app/                    API (routers, servicios, puertos, repositorios, dominio, métricas, seed)
├── db/                     schema.sql y seed.sql (20 categorías, 20K productos, 10K clientes, 30K pedidos, ~90K líneas)
├── tests/                  pruebas unitarias (repositorios en memoria)
├── Dockerfile              imagen de la API
├── docker-compose.yml      Fase 1: despliegue en una sola máquina
├── docker-compose.monitoring.yml   (opcional) Prometheus + cAdvisor + Grafana
├── k8s/                    Fases 2-4: manifiestos (kustomize) + optional/servicemonitor.yaml
├── jmeter/plan_tienda.jmx  plan de carga parametrizable
├── scripts/                build_push, run_jmeter, run_k8s_matrix, collect_resources, generate_demo_results
├── monitoring/             configuración de Prometheus/Grafana y consultas PromQL
├── docs/guia_digitalocean.md    despliegue paso a paso en DigitalOcean (doctl + DOKS)
├── docs/guia_k3s_multinodo.md   cómo montar 1, 2 y 3 nodos con K3s (clúster propio)
├── results/                aquí quedan los .jtl de JMeter (entrada del notebook)
├── notebooks/Analisis_Despliegue.ipynb   análisis, gráficos, conclusiones
└── reporte/Reporte_Instrucciones.pdf     instrucciones de ejecución y enlaces
```

## Requisitos
Docker y Docker Compose v2 · `kubectl` · K3s (u otro Kubernetes) · Apache JMeter 5.6+ (máquina distinta a la de la app) ·
Python 3.10+ con `pandas`, `matplotlib`, `seaborn` y Jupyter (o Google Colab) · cuenta de Docker Hub (para K8s multinodo).

## Fase 1: Docker Compose
```bash
docker compose up -d --build              # db + seed (carga datos) + api
curl http://localhost:8000/reports/counts # comprueba el total de registros (> 10.000)
curl http://localhost:8000/docs           # documentación OpenAPI interactiva
./scripts/run_jmeter.sh compose <ip-servidor> 8000 1     # desde OTRA máquina
```

## Fases 2-4: Kubernetes (1, 2 y 3 nodos)
Si usas **DigitalOcean** (con el crédito de bienvenida), sigue [`docs/guia_digitalocean.md`](docs/guia_digitalocean.md).
Si montas el clúster tú mismo en VMs (Hetzner, Civo, etc.), sigue [`docs/guia_k3s_multinodo.md`](docs/guia_k3s_multinodo.md). Resumen:
```bash
./scripts/build_push.sh <usuario-dockerhub>      # y edita images.newName en k8s/kustomization.yaml
kubectl label node <nodo1> role=database
kubectl apply -k k8s/
kubectl -n tienda wait --for=condition=complete job/tienda-seed --timeout=300s
./scripts/run_k8s_matrix.sh k8s-1nodo <ip-nodo> 30080     # réplicas 1,2,3; luego repite con 2 y 3 nodos
```
Réplicas a mano: `kubectl -n tienda scale deployment/api --replicas=2`.

## Generación de carga (JMeter)
`scripts/run_jmeter.sh <escenario> <host> <puerto> <réplicas> [usuarios...]` ejecuta el plan en modo no-GUI para
10, 50, 100 y 200 usuarios (150 s por prueba: 30 s de ramp-up + 120 s estables) y guarda
`results/<escenario>__r<réplicas>__u<usuarios>.jtl`. Escenarios: `compose`, `k8s-1nodo`, `k8s-2nodos`, `k8s-3nodos`.
Variables útiles: `DURATION`, `RAMP`, `THINK_MS`, `PAUSE`, `RUN_ID` (repeticiones), `REPORT=1` (informe HTML).
El plan también se puede abrir en la GUI de JMeter para inspeccionarlo (no lo uses para medir).

## Análisis
```bash
pip install pandas matplotlib seaborn jupyter
jupyter notebook notebooks/Analisis_Despliegue.ipynb
```
- Edita la primera celda (`REPO_URL`) y completa las secciones marcadas con `[COMPLETAR]`.
- En **Colab**: sube el notebook, ejecuta la primera celda (clona el repositorio) y sube tus `.jtl` a `results/`
  (o súbelos al repositorio).
- Para **probar el notebook antes de medir**, pon `USE_DEMO_DATA = True`: genera datos sintéticos claramente
  etiquetados. **No los uses en el informe final.**

## Monitorización (opcional)
Ver [`monitoring/README.md`](monitoring/README.md). Alternativa ligera: `scripts/collect_resources.sh`
(`docker stats` o `kubectl top`).

## Pruebas de la aplicación
```bash
python -m unittest tests.test_services              # lógica de negocio, sin dependencias
pip install -r requirements-dev.txt && python -m unittest   # incluye pruebas HTTP (FastAPI TestClient)
```

## Decisiones de diseño que afectan a los resultados
- Límites idénticos por réplica en Compose y Kubernetes (0,5 vCPU / 512 MiB); 1 worker de uvicorn por contenedor.
- Réplicas repartidas entre nodos (`topologySpreadConstraints`); PostgreSQL único, preferentemente en el nodo `role=database`.
- Mezcla de carga: 40 % lecturas por id, 20 % listados, 10 % por categoría, 15 % búsqueda sin índice, 10 % escrituras, 5 % reportes pesados.
- `kube-proxy` balancea por conexión: con pocos usuarios y *keep-alive* el reparto puede ser desigual (ver limitaciones en el notebook).

## Checklist de entrega
- [ ] Repositorio público/accesible con Dockerfile, docker-compose.yml y YAML de Kubernetes
- [ ] `.jtl` reales en `results/` (o enlace a ellos) y notebook ejecutado con salidas visibles
- [ ] Secciones `[COMPLETAR]` del notebook rellenas (entorno, análisis, conclusiones, recomendaciones)
- [ ] PDF `reporte/Reporte_Instrucciones.pdf` con tus enlaces reales (repositorio y Colab)
