# Guía: clúster K3s de 1, 2 y 3 nodos

K3s es una distribución ligera de Kubernetes (un solo binario) que ya incluye `metrics-server`
(para `kubectl top`) y el provisionador de volúmenes `local-path` que usa PostgreSQL.
Puedes usar también MicroK8s o Kind; los manifiestos de `k8s/` son estándar.

> **Idea para no reconstruir tres veces:** empieza con 1 nodo, mide, une el nodo 2, mide, une el nodo 3 y mide.
> El script `scripts/run_k8s_matrix.sh` baja las réplicas a 0 antes de cada configuración para que el scheduler
> las vuelva a repartir entre los nodos disponibles.

## Requisitos de las máquinas
- 2 vCPU y 4 GB de RAM por nodo como mínimo recomendado (la API usa hasta 0,5 vCPU por réplica y PostgreSQL hasta 2).
- Todas las máquinas en la misma red y con visibilidad mutua (puerto `6443/tcp` hacia el servidor, y `8472/udp` entre nodos para la red de pods).
- Una máquina **distinta** para JMeter, con acceso a los puertos NodePort (`30080/tcp`) de los nodos.

## 1) Nodo 1 (servidor / control-plane)
```bash
curl -sfL https://get.k3s.io | sh -
sudo k3s kubectl get nodes                      # debe aparecer Ready
sudo cat /var/lib/rancher/k3s/server/node-token # guarda el token para unir nodos
```
Copia el kubeconfig a la máquina de carga (o trabaja desde el nodo 1):
```bash
sudo cat /etc/rancher/k3s/k3s.yaml   # reemplaza 127.0.0.1 por la IP del nodo 1 y guárdalo como ~/.kube/config
```

## 2) Etiquetar el nodo de la base de datos
```bash
kubectl label node <nombre-nodo-1> role=database
```

## 3) Publicar la imagen y desplegar
```bash
./scripts/build_push.sh <usuario-dockerhub>      # edita images.newName en k8s/kustomization.yaml
kubectl apply -k k8s/
kubectl -n tienda wait --for=condition=complete job/tienda-seed --timeout=300s
kubectl -n tienda get pods -o wide
curl http://<ip-nodo-1>:30080/reports/counts     # debe mostrar total > 10000
```
Si cambias la imagen y vuelves a aplicar, borra antes el Job: `kubectl -n tienda delete job tienda-seed`.
Recuerda que `kubectl apply -k k8s/` devuelve las réplicas de la API a 1.

## 4) Medir el escenario de 1 nodo
```bash
./scripts/run_k8s_matrix.sh k8s-1nodo <ip-nodo-1> 30080     # réplicas 1, 2 y 3
```

## 5) Unir el nodo 2 y medir
En la máquina del nodo 2:
```bash
curl -sfL https://get.k3s.io | K3S_URL=https://<ip-nodo-1>:6443 K3S_TOKEN=<token> sh -
```
Comprueba con `kubectl get nodes` que hay 2 nodos `Ready` y mide:
```bash
./scripts/run_k8s_matrix.sh k8s-2nodos <ip-nodo-1> 30080
```
(el `NodePort` responde en cualquier nodo; mantén siempre el mismo punto de entrada para que la comparación sea justa).

## 6) Unir el nodo 3 y medir
Repite el comando de unión en el nodo 3 y ejecuta:
```bash
./scripts/run_k8s_matrix.sh k8s-3nodos <ip-nodo-1> 30080
```

## Comprobaciones útiles
```bash
kubectl -n tienda get pods -l app=api -o wide     # ¿las réplicas están repartidas entre nodos?
curl -si http://<ip-nodo-1>:30080/info | grep -i -E 'x-served-by|pod'   # repite varias veces: cambia el pod
kubectl top nodes; kubectl -n tienda top pods     # consumo de CPU/memoria
```

## Problemas frecuentes
| Síntoma | Causa probable | Solución |
|---|---|---|
| Pods `Pending` con 3 réplicas | `topologySpreadConstraints` con `DoNotSchedule` y un nodo sin recursos | Revisa `kubectl describe pod`; añade CPU al nodo o reduce `requests` |
| `ImagePullBackOff` | La imagen no es pública o el nombre es incorrecto | Verifica `images.newName` y que el repositorio de Docker Hub sea público |
| El `Job` de seed falla al inicio | PostgreSQL aún no está listo | El seed reintenta hasta 2 min; revisa `kubectl -n tienda logs job/tienda-seed` |
| Con kubeadm los pods no usan el control-plane | El nodo tiene *taint* | `kubectl taint nodes --all node-role.kubernetes.io/control-plane-` (K3s no lo necesita) |
| JMeter no llega a la API | Firewall/security group | Abre `30080/tcp` en los nodos |
