# Guía: desplegar el proyecto en DigitalOcean (con crédito de bienvenida)

DigitalOcean ofrece a las cuentas nuevas un crédito de $200 válido por 60 días (condiciones promocionales; solo cuentas nuevas).
Con la estrategia de esta guía el experimento completo cuesta del orden de **unos pocos dólares**, siempre que **borres todo al terminar**.

## Plan de máquinas (una región para todo)

| Cuándo | Qué | Tamaño |
|---|---|---|
| Fase 1 | Droplet `tienda-compose` (Docker Compose) | `s-2vcpu-4gb` |
| Fases 1 a 4 | Droplet `tienda-jmeter` (generador de carga) | `s-2vcpu-4gb` |
| Fases 2 a 4 | Clúster DOKS `tienda`: 1 nodo, luego 2, luego 3 | `s-2vcpu-4gb` por nodo |

Usa **el mismo tamaño** en la VM de Compose y en los nodos del clúster para que la comparación sea justa.
El droplet de Compose se borra al terminar la Fase 1, así que nunca hay más de 4 máquinas encendidas.

> **Límite de droplets:** los nodos de DOKS cuentan como droplets. Si al crear el tercer nodo falla por límite de cuenta,
> pide un aumento en el panel de soporte de DigitalOcean (las cuentas nuevas suelen tener un límite bajo; consulta el tuyo en el panel).

---
## 0) Preparación (una sola vez, en tu computador)

1. Sube el proyecto a un repositorio público de GitHub/GitLab (los droplets lo clonarán).
   Crea la cuenta en DigitalOcean, activa el crédito y **configura una alerta de facturación** en el panel.
2. Crea una cuenta en Docker Hub (gratis) para publicar la imagen.
3. Instala `doctl` (CLI de DigitalOcean), crea un *Personal Access Token* con permisos de lectura y escritura en el panel y ejecuta:
   ```bash
   doctl auth init                      # pega el token
   doctl compute ssh-key list           # si no hay llaves, súbela:  doctl compute ssh-key import mi-llave --public-key-file ~/.ssh/id_ed25519.pub
   doctl kubernetes options regions     # elige una región que sea válida también para droplets
   ```
4. Define las variables que usarás en los comandos siguientes:
   ```bash
   export REGION=nyc3                   # ejemplo: usa una región de la lista anterior
   export SSHKEY=<ID-de-tu-llave>
   ```

---
## 1) Fase 1: Docker Compose + JMeter en dos droplets

```bash
doctl compute droplet create tienda-compose tienda-jmeter \
  --region $REGION --size s-2vcpu-4gb --image ubuntu-24-04-x64 --ssh-keys $SSHKEY --wait
doctl compute droplet list --format Name,PublicIPv4,PrivateIPv4
```

### 1.1 Droplet `tienda-compose` (aplicación)
```bash
ssh root@<IP-publica-compose>
curl -fsSL https://get.docker.com | sh
git clone <URL-de-tu-repositorio> && cd proyecto-final-despliegue
docker compose up -d --build
docker compose ps                              # api 'healthy'
curl localhost:8000/reports/counts             # total de registros > 10.000
```

### 1.2 Droplet `tienda-jmeter` (carga)
```bash
ssh root@<IP-publica-jmeter>
apt-get update && apt-get install -y openjdk-17-jre-headless git
wget https://archive.apache.org/dist/jmeter/binaries/apache-jmeter-5.6.3.tgz
tar xzf apache-jmeter-5.6.3.tgz && export PATH=$PWD/apache-jmeter-5.6.3/bin:$PATH
git clone <URL-de-tu-repositorio> && cd proyecto-final-despliegue
curl http://<IP-privada-compose>:8000/reports/counts      # comprueba conectividad
./scripts/run_jmeter.sh compose <IP-privada-compose> 8000 1
```
- Las IP privadas funcionan porque ambos droplets están en la VPC por defecto de la misma región. Si no responde, usa la IP pública.
- Vigila la CPU del droplet de JMeter con `top` durante una prueba: si pasa del ~70 % el generador de carga se vuelve el cuello de botella.

### 1.3 Publicar la imagen (desde el droplet de Compose) y limpiar
```bash
# en tienda-compose, dentro del repositorio
docker login -u <usuario-dockerhub>
./scripts/build_push.sh <usuario-dockerhub>      # publica docker.io/<usuario>/tienda-api:1.0.0
```
En Docker Hub deja el repositorio **público** (los nodos del clúster descargarán la imagen sin credenciales).
**En tu computador**, edita `images.newName` en `k8s/kustomization.yaml` (`docker.io/<usuario-dockerhub>/tienda-api`), haz *commit* y *push*.
Trae los `.jtl` a tu computador y borra el droplet de Compose:
```bash
scp -r root@<IP-publica-jmeter>:~/proyecto-final-despliegue/results ./results_fase1   # (o al final, todos juntos)
doctl compute droplet delete tienda-compose
```
> Si construyes la imagen en un Mac con chip ARM, `build_push.sh` ya fuerza `linux/amd64`; sin eso los pods fallan con `exec format error`.

---
## 2) Fases 2 a 4: clúster DOKS de 1, 2 y 3 nodos

### 2.1 Crear el clúster con 1 nodo
```bash
doctl kubernetes cluster create tienda --region $REGION \
  --node-pool "name=pool;size=s-2vcpu-4gb;count=1" --wait
doctl kubernetes cluster kubeconfig show tienda > kubeconfig-tienda.yaml
scp kubeconfig-tienda.yaml root@<IP-publica-jmeter>:~/
```

### 2.2 Preparar `tienda-jmeter` para hablar con el clúster
```bash
ssh root@<IP-publica-jmeter>
snap install kubectl --classic
export KUBECONFIG=~/kubeconfig-tienda.yaml
cd proyecto-final-despliegue && git pull         # trae el kustomization.yaml con tu imagen
kubectl get nodes -o wide                        # anota INTERNAL-IP (o EXTERNAL-IP) del nodo
```

### 2.3 Desplegar la aplicación
```bash
kubectl label node $(kubectl get nodes -o name | head -1 | cut -d/ -f2) role=database
kubectl apply -k k8s/
kubectl -n tienda wait --for=condition=complete job/tienda-seed --timeout=300s
kubectl -n tienda get pods -o wide
curl http://<IP-nodo>:30080/reports/counts       # debe mostrar total > 10000
```
DigitalOcean abre automáticamente en el firewall del clúster los puertos NodePort (30000-32767) de los servicios que creas.
El volumen de PostgreSQL se crea con la clase de almacenamiento por defecto (`kubectl get storageclass`).

### 2.4 Medir con 1 nodo
```bash
./scripts/run_k8s_matrix.sh k8s-1nodo <IP-nodo> 30080      # réplicas 1, 2 y 3
```

### 2.5 Pasar a 2 nodos y medir
Desde tu computador:
```bash
doctl kubernetes cluster node-pool list tienda              # anota el nombre/ID del pool
doctl kubernetes cluster node-pool update tienda pool --count 2
```
En `tienda-jmeter` espera a que `kubectl get nodes` muestre 2 nodos `Ready` y mide **usando la misma IP de entrada**:
```bash
./scripts/run_k8s_matrix.sh k8s-2nodos <IP-nodo> 30080
```

### 2.6 Pasar a 3 nodos y medir
```bash
doctl kubernetes cluster node-pool update tienda pool --count 3
```
```bash
./scripts/run_k8s_matrix.sh k8s-3nodos <IP-nodo> 30080
```
El script baja las réplicas a 0 y las sube de nuevo en cada configuración, así el *scheduler* las reparte entre los nodos disponibles
(comprueba el reparto en `results/*__pods.txt`). PostgreSQL permanece en el primer nodo.

### 2.7 (Opcional) Recursos
Si `kubectl top nodes` no funciona, instala metrics-server:
`kubectl apply -f https://github.com/kubernetes-sigs/metrics-server/releases/latest/download/components.yaml`

---
## 3) Traer los resultados y borrar todo

```bash
# desde tu computador
scp -r root@<IP-publica-jmeter>:~/proyecto-final-despliegue/results/. ./results/

# en tienda-jmeter: elimina primero la app (libera el volumen), luego el clúster y el droplet
kubectl delete -k k8s/
doctl kubernetes cluster delete tienda
doctl compute droplet delete tienda-jmeter
# comprueba que no queda nada que cobre:
doctl compute droplet list; doctl compute volume list; doctl compute load-balancer list; doctl kubernetes cluster list
```
Borra a mano lo que aparezca en esas listas (`doctl compute volume delete <id>`, etc.) y revisa el panel de facturación.

## Problemas frecuentes
| Síntoma | Causa probable | Solución |
|---|---|---|
| `exec format error` en el pod | Imagen construida para ARM | Reconstruye con `./scripts/build_push.sh` (fuerza `linux/amd64`) |
| `ImagePullBackOff` | Repositorio privado o nombre mal escrito | Hazlo público y revisa `images.newName` |
| PVC de PostgreSQL en `Pending` | Sin clase de almacenamiento por defecto | `kubectl get storageclass`; espera 1-2 min a que se aprovisione el volumen |
| `curl` al NodePort no responde | IP equivocada o servicio sin pods listos | Prueba la IP externa; `kubectl -n tienda get pods,svc` |
| El tercer nodo no se crea | Límite de droplets de la cuenta | Pide aumento de límite en soporte |
| Resultados muy variables | Generador de carga saturado, o nodos recreados por mantenimiento | Revisa `top` en la VM de JMeter y repite la prueba (`RUN_ID`) |
