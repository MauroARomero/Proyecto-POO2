#!/usr/bin/env bash
# Construye la imagen y la sube a Docker Hub (necesario para que todos los nodos la descarguen).
# Uso: ./scripts/build_push.sh <usuario-dockerhub> [version=1.0.0]
set -euo pipefail
[ "$#" -ge 1 ] || { sed -n '2,3p' "$0"; exit 1; }
USER_HUB=$1; VERSION=${2:-1.0.0}
IMAGE="docker.io/${USER_HUB}/tienda-api:${VERSION}"
cd "$(dirname "$0")/.."
# Los nodos del proveedor cloud son x86-64: se fuerza esa plataforma aunque construyas en un Mac con chip ARM.
DOCKER_DEFAULT_PLATFORM=linux/amd64 docker build -t "$IMAGE" .
docker push "$IMAGE"
echo "Imagen publicada: $IMAGE"
echo "Actualiza 'images.newName' en k8s/kustomization.yaml con: docker.io/${USER_HUB}/tienda-api"
