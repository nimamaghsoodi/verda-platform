#!/usr/bin/env bash
# Build and push demo app images to Harbor
# Usage: CLUSTER_IP=1.2.3.4 ./build-and-push.sh [tag]
set -euo pipefail

CLUSTER_IP="${CLUSTER_IP:?Set CLUSTER_IP to your worker-1 public IP}"
TAG="${1:-latest}"
REGISTRY="harbor.${CLUSTER_IP}.nip.io"
PROJECT="demo"

echo "→ Logging into Harbor at ${REGISTRY}"
docker login "${REGISTRY}"

echo "→ Building backend"
docker build -t "${REGISTRY}/${PROJECT}/demo-app-backend:${TAG}" ./backend

echo "→ Building frontend"
docker build -t "${REGISTRY}/${PROJECT}/demo-app-frontend:${TAG}" ./frontend

echo "→ Pushing images"
docker push "${REGISTRY}/${PROJECT}/demo-app-backend:${TAG}"
docker push "${REGISTRY}/${PROJECT}/demo-app-frontend:${TAG}"

echo "✓ Done. Images pushed to ${REGISTRY}/${PROJECT}"
echo "  Update k8s/apps/demo-app/deployment.yaml image tags if using a versioned tag."
