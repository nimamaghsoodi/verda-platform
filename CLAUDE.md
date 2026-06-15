# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Context

This is a senior platform engineering assignment for Verda Cloud. The goal is to provision CPU VMs with public IPs on Verda Cloud and build a Kubernetes platform demonstrating DevOps/platform engineering skills. The assignment PDF is at `senior-assignment-platform-engineer.pdf`.

## Assignment Deliverables

1. Access instructions or screenshots
2. Git repository with manifests/scripts/docs (this repo)
3. A short summary report covering: what was built, architecture, what worked/didn't, security considerations, and what would be improved with more time

## Target Architecture

The platform stack to be built on Verda Cloud VMs:

- **Kubernetes** — provisioned on CPU VMs (likely RKE2 or k3s on bare VMs)
- **Rancher Manager** — cluster management UI, import/register the Kubernetes cluster, SSO if possible
- **Argo CD** — GitOps continuous delivery, SSO if possible, at least one app deployed through it
- **Harbor** — container registry, image push/build flow connected to Argo CD
- **kube-prometheus-stack** — monitoring (Prometheus + Grafana + Alertmanager), cluster health dashboards

Optional/advanced: Cilium (CNI + network policy), KWOK (node simulation), Kueue (job queues), GPU workloads, backup strategy, security hardening.

A sample app must also be created which will be used to demo the requirements in the assignment document. The observability for the app must be implemeted with otel with templars and also the sample app must have a ui from which the user can simulate errors, or span slowness or a couple of successfull scenarios so that the observability stack can capture them and show them all during the demo

also use
Terraform = infrastructure provisioning
Ansible/scripts = cluster bootstrap
Argo CD = ongoing GitOps deployment

## Repo Structure

```
infra/                          # Terraform (OpenStack/Verda Cloud provider)
  main.tf                       # VMs, network, floating IPs, security groups
  variables.tf / outputs.tf
  terraform.tfvars.example      # copy → terraform.tfvars, fill credentials

bootstrap/                      # Ansible — run site.yml after terraform apply
  site.yml                      # master playbook (runs all sub-playbooks in order)
  playbooks/
    01-prepare-nodes.yml        # swap off, sysctl, kernel modules
    02-install-rke2-server.yml  # RKE2 server on control-plane
    03-install-rke2-agents.yml  # RKE2 agents on workers
    04-install-helm.yml         # Helm + repo adds
    05-bootstrap-argocd.yml     # installs Argo CD, applies app-of-apps root

k8s/
  argocd/
    install/argocd-values.yaml  # Helm values incl. GitHub OAuth via Dex
    apps/                       # One Application YAML per platform component
      app-of-apps.yaml          # Root Application — manages all others
    projects/                   # AppProject definitions (platform, apps)
  platform/
    cert-manager/               # ClusterIssuer (Let's Encrypt prod + staging)
    ingress-nginx/values.yaml
    harbor/values.yaml
    monitoring/kube-prometheus-stack-values.yaml  # incl. Grafana GitHub OAuth
    observability/              # OTEL Collector, Tempo, Loki, Promtail Applications
    rancher/values.yaml
  apps/
    demo-app/                   # Namespace, Deployment, Service, Ingress, ServiceMonitor

apps/demo-app/
  backend/                      # FastAPI + OpenTelemetry
    main.py                     # /api/simulate/{success,error,slow} endpoints
    requirements.txt / Dockerfile
  frontend/                     # React SPA
    src/App.jsx                 # UI with scenario buttons + history + Grafana links
    Dockerfile / nginx.conf
  build-and-push.sh             # CLUSTER_IP=x.x.x.x ./build-and-push.sh [tag]

docs/
  architecture.md               # Diagram + flow explanation
  summary-report.md             # Assignment report (what/why/tradeoffs)
```

## Placeholders to Replace

Every file containing `<CLUSTER_IP>` must have it replaced with the actual worker-1 public IP once provisioned. Search with:
```bash
grep -r '<CLUSTER_IP>' k8s/ apps/
```
Also replace `YOUR_ORG`, `YOUR_GITHUB_ORG`, `YOUR_GITHUB_USERNAME`, `GITHUB_CLIENT_ID`, `GITHUB_CLIENT_SECRET` throughout.

## Workflow: End-to-End Setup

```bash
# 1. Provision VMs
cd infra
cp terraform.tfvars.example terraform.tfvars   # fill credentials
terraform init && terraform apply
terraform output ansible_inventory > ../bootstrap/inventory.ini

# 2. Bootstrap cluster
cd ../bootstrap
ansible-playbook site.yml -i inventory.ini
# KUBECONFIG is fetched to ./kubeconfig-raw.yaml; fix the IP:
sed 's/127.0.0.1/<CP_PUBLIC_IP>/' kubeconfig-raw.yaml > ~/.kube/config-verda
export KUBECONFIG=~/.kube/config-verda

# 3. Verify cluster
kubectl get nodes -o wide

# 4. After Argo CD bootstraps, update app-of-apps repoURL, then:
kubectl apply -f k8s/argocd/apps/app-of-apps.yaml
argocd app list   # watch all apps sync

# 5. Build and push demo app (after Harbor is ready)
cd apps/demo-app
CLUSTER_IP=<WORKER1_IP> ./build-and-push.sh latest
```

## Common Commands

```bash
# Cluster state
kubectl get nodes -o wide
kubectl get pods -A

# Argo CD
argocd login argocd.<CLUSTER_IP>.nip.io --grpc-web
argocd app list
argocd app sync <app-name>
argocd app diff <app-name>

# Helm (manual installs / debugging)
helm upgrade --install <release> <chart> -n <ns> --create-namespace -f values.yaml
helm history <release> -n <ns>

# Demo app — local development
cd apps/demo-app/backend && pip install -r requirements.txt
OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4317 uvicorn main:app --reload

cd apps/demo-app/frontend && npm install && npm start

# Monitoring port-forwards (if not via ingress)
kubectl port-forward -n monitoring svc/kube-prometheus-stack-grafana 3000:80
kubectl port-forward -n observability svc/tempo 3100:3100
```

## Key Helm Charts

| Component | Helm Repo | Chart |
|-----------|-----------|-------|
| Rancher | `https://releases.rancher.com/server-charts/stable` | `rancher-stable/rancher` |
| Argo CD | `https://argoproj.github.io/argo-helm` | `argo/argo-cd` |
| Harbor | `https://helm.goharbor.io` | `harbor/harbor` |
| kube-prometheus-stack | `https://prometheus-community.github.io/helm-charts` | `prometheus-community/kube-prometheus-stack` |
| cert-manager | `https://charts.jetstack.io` | `jetstack/cert-manager` |

## GitOps Promotion Pattern

Argo CD apps follow the app-of-apps or directory-based pattern. Promotion across environments (dev → staging → prod) is done by updating image tags or Helm values in git — Argo CD auto-syncs or requires manual sync depending on the policy configured per Application.
