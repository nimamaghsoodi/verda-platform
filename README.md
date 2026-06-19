# Verda Cloud Platform Engineering Assignment

A production-grade Kubernetes platform built on Verda Cloud CPU VMs, demonstrating GitOps delivery,
multi-tenant observability, container registry integration, cluster management, and security hardening.

---

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Assessment Requirements vs. Delivered Solution](#assessment-requirements-vs-delivered-solution)
3. [Live Endpoints](#live-endpoints)
4. [Step 1 — Provision VMs with Terraform](#step-1--provision-vms-with-terraform)
5. [Step 2 — Bootstrap the Cluster with Ansible](#step-2--bootstrap-the-cluster-with-ansible)
6. [Step 3 — Verify Cluster and Kubeconfig](#step-3--verify-cluster-and-kubeconfig)
7. [Step 4 — Bootstrap Argo CD (app-of-apps)](#step-4--bootstrap-argo-cd-app-of-apps)
8. [Step 5 — Rancher UI — Import Cluster](#step-5--rancher-ui--import-cluster)
9. [Step 6 — Harbor — Push the Demo App Image](#step-6--harbor--push-the-demo-app-image)
10. [Step 7 — Argo CD UI — Manage Applications](#step-7--argo-cd-ui--manage-applications)
11. [Step 8 — Demo App UI — Fire Observability Scenarios](#step-8--demo-app-ui--fire-observability-scenarios)
12. [Step 9 — Grafana — View Logs, Traces, and Metrics](#step-9--grafana--view-logs-traces-and-metrics)
13. [Optional Components](#optional-components)
14. [Security Hardening](#security-hardening)
15. [Backup Strategy](#backup-strategy)
16. [Troubleshooting](#troubleshooting)
17. [What Would Be Improved With More Time](#what-would-be-improved-with-more-time)

---

## Architecture Overview

```
Verda Cloud (OpenStack-compatible)
│
├── verda-k8s-cp         (CPU.4V.16G, floating IP: 86.38.238.225)
│   ├── RKE2 control-plane (API server, etcd, scheduler, controller-manager)
│   └── Rancher Manager   (cattle-system namespace)
│
├── verda-k8s-worker-1   (CPU.4V.16G, floating IP: 86.38.238.224) ← ingress IP
│   └── RKE2 agent + ingress-nginx
│
└── verda-k8s-worker-2   (CPU.4V.16G, floating IP: 86.38.238.226)
    └── RKE2 agent
```

**Platform stack (all managed by Argo CD via GitOps):**

```
Argo CD (argocd)
└── app-of-apps
    ├── Wave 0 — cilium                (kube-system)  Cilium CNI + Hubble
    ├── Wave 1 — cert-manager          (cert-manager) Let's Encrypt TLS
    │            cert-manager-issuers                 ClusterIssuers
    ├── Wave 2 — ingress-nginx         (ingress-nginx) L7 ingress
    │            coredns-patch         (kube-system)   hairpin-NAT fix
    ├── Wave 3 — kwok                  (kube-system)  10 virtual nodes
    │            rancher               (cattle-system) Cluster management UI
    │            harbor                (harbor)        Container registry
    ├── Wave 4 — monitoring            (monitoring)   Prometheus + Grafana + Alertmanager
    │            observability         (observability) OTEL Collector + Tempo + Loki + Promtail
    │            velero                (velero)        Backup operator
    │            rancher-backup        (cattle-resources-system) Rancher state backup
    └── Wave 5 — demo-app             (demo-app)      Sample FastAPI + React app
```

**Observability data flow:**

```
demo-app-backend
  ├─ OTLP gRPC :4317 → otel-collector → Tempo      (traces)
  ├─ OTLP gRPC :4317 → otel-collector → Prometheus  (metrics)
  └─ stdout JSON      → Promtail → Loki              (structured logs with trace_id)

Kubernetes / nodes
  └─ node-exporter + kube-state-metrics → Prometheus

Everything surfaced in Grafana with Loki→Tempo trace-log correlation
```

---

## Assessment Requirements vs. Delivered Solution

| Requirement | Status | Notes |
|---|---|---|
| **Provision CPU VMs with public IPs on Verda Cloud** | ✅ Done | 3× CPU.4V.16G VMs via Terraform + Verda provider |
| **Git repository with manifests/scripts/docs** | ✅ Done | This repo — Terraform, Ansible, k8s manifests, app source |
| **Summary report** | ✅ Done | `docs/summary-report.md` |
| **Architecture diagram** | ✅ Done | `docs/architecture.md` |
| **Rancher Manager** | ✅ Done | Running at `https://rancher.86.38.238.224.nip.io` |
| **Rancher SSO** | ⚠️ Partial | GitHub OAuth configured in values; manual UI step required post-install |
| **Register/import Kubernetes cluster in Rancher** | ✅ Done | Cluster imported and visible in Rancher |
| **Argo CD** | ✅ Done | Running at `https://argocd.86.38.238.224.nip.io` |
| **Argo CD SSO** | ⚠️ Partial | Dex stub in values; GitHub OAuth requires `clientId`/`clientSecret` substitution |
| **At least one app deployed through Argo CD** | ✅ Done | All platform components + demo-app deployed via GitOps |
| **GitOps structure and promotion thinking** | ✅ Done | app-of-apps pattern, sync waves, project separation |
| **Harbor container registry** | ✅ Done | Running at `https://harbor.86.38.238.224.nip.io` |
| **Push/build image via Harbor** | ✅ Done | `build-and-push.sh` script; demo-app images in Harbor `demo/` project |
| **Connect Harbor to Argo CD deployment** | ✅ Done | Deployment pulls from Harbor; Argo CD manages the Deployment |
| **kube-prometheus-stack** | ✅ Done | Prometheus + Grafana + Alertmanager in `monitoring` namespace |
| **Grafana cluster health dashboards** | ✅ Done | 4 pre-loaded dashboards (k8s cluster, pods, node-exporter, nginx) |
| **Alert configuration** | ✅ Done | Full `defaultRules` enabled; alert list documented in values |
| **Cilium CNI + network policy** | ✅ Done | Cilium v1.17.4 with Hubble UI + eBPF NetworkPolicy enforcement |
| **KWOK virtual nodes** | ✅ Done | 10 KWOK fake nodes registered (reduced from 100 for Rancher compatibility) |
| **Backup strategy** | ✅ Done | Velero (node-agent/restic) + Rancher Backup Operator |
| **Security hardening** | ✅ Done | NetworkPolicy, RBAC, PodSecurity, resource quotas, audit policy |
| **Demo app with OTEL observability** | ✅ Done | FastAPI + React; traces → Tempo, logs → Loki, metrics → Prometheus |
| **Demo app UI for scenario simulation** | ✅ Done | Success / Error / Slow scenarios with trace-id deep links to Grafana |

---

## Live Endpoints

| Service | URL | Credentials |
|---------|-----|-------------|
| Demo App | https://demo.86.38.238.224.nip.io | public |
| Argo CD | https://argocd.86.38.238.224.nip.io | admin / see bootstrap output |
| Grafana | https://grafana.86.38.238.224.nip.io | admin / `grafana-admin-change-me` |
| Rancher | https://rancher.86.38.238.224.nip.io | admin / set on first login |
| Harbor | https://harbor.86.38.238.224.nip.io | admin / `Harbor12345!` |

All services use Let's Encrypt TLS certificates via cert-manager (HTTP-01 challenge).

---

## Step 1 — Provision VMs with Terraform

### Prerequisites

- Terraform ≥ 1.6
- Verda Cloud account with API credentials (OAuth2 client ID + secret)
- SSH key pair at `~/.ssh/id_rsa` / `~/.ssh/id_rsa.pub`

### Configure credentials

```bash
cd infra
cp terraform.tfvars.example terraform.tfvars
```

Edit `terraform.tfvars`:

```hcl
client_id     = "your-verda-client-id"
client_secret = "your-verda-client-secret"
location      = "FIN-01"                  # or your preferred datacenter
worker_count  = 2
```

**Where to get credentials:** Verda Cloud console → top-right menu → **Keys** → **Cloud API Credentials** → generate a new OAuth2 client.

### Run Terraform

```bash
terraform init
terraform plan   # review changes
terraform apply  # creates 3 VMs + SSH key + startup script
```

This provisions:
- `verda-k8s-cp` — control-plane (CPU.4V.16G, 100 GB NVMe)
- `verda-k8s-worker-1` — first worker (CPU.4V.16G, 100 GB NVMe)
- `verda-k8s-worker-2` — second worker (CPU.4V.16G, 100 GB NVMe)

The startup script disables swap, loads kernel modules, and installs base packages. Ansible handles everything else.

### Capture outputs

```bash
terraform output                    # shows all IPs and inventory
terraform output ansible_inventory  # paste into bootstrap/inventory.ini
```

Expected output:

```
control_plane_ip = "86.38.238.225"
worker_ips = ["86.38.238.224", "86.38.238.226"]
nip_io_domain = "86.38.238.224.nip.io"
```

---

## Step 2 — Bootstrap the Cluster with Ansible

### Prerequisites

```bash
pip install ansible
```

### Update inventory

Paste the `ansible_inventory` Terraform output into `bootstrap/inventory.ini`:

```ini
[control_plane]
verda-k8s-cp ansible_host=86.38.238.225 ansible_user=root ansible_ssh_private_key_file=~/.ssh/id_rsa

[workers]
verda-k8s-worker-1 ansible_host=86.38.238.224 ansible_user=root ansible_ssh_private_key_file=~/.ssh/id_rsa
verda-k8s-worker-2 ansible_host=86.38.238.226 ansible_user=root ansible_ssh_private_key_file=~/.ssh/id_rsa

[k8s_cluster:children]
control_plane
workers
```

### Run the master playbook

```bash
cd bootstrap
ansible-playbook site.yml -i inventory.ini
```

This runs five playbooks in sequence:

| Playbook | What it does |
|----------|-------------|
| `01-prepare-nodes.yml` | swap off, sysctl, kernel modules on all nodes |
| `02-install-rke2-server.yml` | installs RKE2 on control-plane, fetches kubeconfig |
| `03-install-rke2-agents.yml` | joins workers to the cluster using the node token |
| `04-install-helm.yml` | installs Helm + adds `argo`, `rancher-stable`, `harbor`, `prometheus-community` repos |
| `05-bootstrap-argocd.yml` | installs Argo CD via Helm, prints initial admin password |

The full run takes approximately 10–15 minutes. At the end you will see:

```
TASK [Show Argo CD credentials] *****
ok: [verda-k8s-cp] => {
  "msg": [
    "Argo CD URL: https://argocd.86.38.238.224.nip.io",
    "Username: admin",
    "Password: <generated-password>"
  ]
}
```

Save this password.

---

## Step 3 — Verify Cluster and Kubeconfig

The Ansible run fetches the kubeconfig to `./kubeconfig.yaml` (repo root). Make it active:

```bash
export KUBECONFIG=~/Desktop/Tasks/verda-task/kubeconfig.yaml
# or copy to the standard location:
cp ~/Desktop/Tasks/verda-task/kubeconfig.yaml ~/.kube/config-verda
export KUBECONFIG=~/.kube/config-verda
```

Verify:

```bash
kubectl get nodes -o wide
```

Expected (3 real nodes + 10 KWOK virtual nodes after Argo CD syncs):

```
NAME                STATUS   ROLES                       AGE   VERSION
verda-k8s-cp        Ready    control-plane,etcd,master   10m   v1.35.5+rke2r2
verda-k8s-worker-1  Ready    worker                      8m    v1.35.5+rke2r2
verda-k8s-worker-2  Ready    worker                      8m    v1.35.5+rke2r2
kwok-node-001       Ready    worker                      5m    v1.35.5
...
kwok-node-010       Ready    worker                      5m    v1.35.5
```

```bash
kubectl get pods -A   # all platform pods across all namespaces
```

---

## Step 4 — Bootstrap Argo CD (app-of-apps)

Before Argo CD can manage the platform, apply the root Application that points to this repo:

```bash
kubectl apply -f k8s/argocd/apps/app-of-apps.yaml
```

This single manifest tells Argo CD to watch `k8s/argocd/apps/` in this repo and reconcile all Application YAMLs it finds there. Every platform component — cert-manager, ingress-nginx, Rancher, Harbor, monitoring, observability, demo-app — is an Application YAML in that directory.

### Watch the rollout

```bash
# in a terminal: watch all apps come up
kubectl get applications -n argocd -w

# or use the CLI
argocd login argocd.86.38.238.224.nip.io --grpc-web --username admin --password <password>
argocd app list
```

Apps progress through sync waves 0 → 5. Full convergence takes 5–10 minutes.

### Check a specific app

```bash
argocd app get demo-app
argocd app diff demo-app          # show diff between git and cluster
argocd app sync demo-app          # force a manual sync
argocd app history demo-app       # show rollout history
```

### Force sync all apps

```bash
argocd app sync app-of-apps --cascade
```

---

## Step 5 — Rancher UI — Import Cluster

### First login

1. Navigate to **https://rancher.86.38.238.224.nip.io**
2. On the first visit, Rancher prompts you to set the admin password.
3. Accept the terms and click **Continue**.

### Import the RKE2 cluster

Rancher does not auto-discover the cluster it runs inside. You must import it:

1. Click **≡ (hamburger menu)** → **Cluster Management**
2. Click **Import Existing** → choose **Generic**
3. Name the cluster (e.g., `verda-k8s`) and click **Create**
4. Copy the `kubectl apply` command Rancher shows (it includes a registration token)
5. On the control-plane node or from your local kubectl:

```bash
kubectl apply -f <rancher-registration-url>
```

6. Wait 1–2 minutes. The cluster appears as **Active** in Rancher.

### Explore the cluster in Rancher

- **Cluster Dashboard** — CPU, memory, pod counts, events
- **Workloads → Pods** — filter by namespace, view logs inline
- **Storage** — PersistentVolumes and claims
- **Service Discovery** — services and endpoints
- **Apps** — Helm releases (useful for checking chart versions)
- **Cluster Tools** — upgrade RKE2, manage add-ons

### Configure GitHub SSO (optional)

1. Rancher UI → **☰ → Users & Authentication → Auth Providers**
2. Select **GitHub**
3. Register a GitHub OAuth App at https://github.com/settings/developers:
   - Homepage URL: `https://rancher.86.38.238.224.nip.io`
   - Callback URL: `https://rancher.86.38.238.224.nip.io/verify-auth`
4. Paste `Client ID` and `Client Secret` into Rancher
5. Configure allowed orgs/teams and click **Enable**

---

## Step 6 — Harbor — Push the Demo App Image

### First login

1. Navigate to **https://harbor.86.38.238.224.nip.io**
2. Username: `admin`, Password: `Harbor12345!`
3. Change the password immediately via **User Profile → Change Password**

### Create a project

1. Click **Projects → New Project**
2. Name: `demo`, Access level: **Private**
3. Click **OK**

### Build and push from your local machine

```bash
cd apps/demo-app
CLUSTER_IP=86.38.238.224 ./build-and-push.sh latest
```

This script:
1. Runs `docker login harbor.86.38.238.224.nip.io` (prompts for credentials)
2. Builds `./backend` → `harbor.86.38.238.224.nip.io/demo/demo-app-backend:latest`
3. Builds `./frontend` → `harbor.86.38.238.224.nip.io/demo/demo-app-frontend:latest`
4. Pushes both images to Harbor

### Create the image pull secret in Kubernetes

```bash
kubectl create secret docker-registry harbor-registry-secret \
  --docker-server=harbor.86.38.238.224.nip.io \
  --docker-username=admin \
  --docker-password=Harbor12345! \
  -n demo-app
```

This secret is referenced in `k8s/apps/demo-app/deployment.yaml` under `imagePullSecrets`.

### Verify image is in Harbor

Harbor UI → **Projects → demo → Repositories** — you should see:
- `demo/demo-app-backend` with tag `latest`
- `demo/demo-app-frontend` with tag `latest`

Harbor also runs **Trivy vulnerability scans** on every pushed image automatically. Click an image tag → **Scan** to trigger a manual scan and view CVEs.

### GitOps image promotion

To deploy a new version:

```bash
CLUSTER_IP=86.38.238.224 ./build-and-push.sh v1.1.0   # push versioned tag
# then update the image tag in k8s/apps/demo-app/deployment.yaml
# and git commit + push — Argo CD will apply the change automatically
```

---

## Step 7 — Argo CD UI — Manage Applications

### Login

1. Navigate to **https://argocd.86.38.238.224.nip.io**
2. Username: `admin`, Password: retrieved in Step 2

Alternatively via CLI:

```bash
argocd login argocd.86.38.238.224.nip.io --grpc-web --username admin --password <password>
```

### Application tiles

The main screen shows all Applications as tiles. Each tile shows:
- **Sync Status**: `Synced` (green) or `OutOfSync` (yellow)
- **Health**: `Healthy` (green), `Degraded` (red), `Progressing` (yellow)
- **Last sync time** and the git commit it's at

### Viewing an application

Click any app tile (e.g., `demo-app`) to see:
- **Resource tree** — every Kubernetes resource the app owns (Namespace, Deployment, Service, Ingress, ConfigMap, etc.)
- **Events** — Kubernetes events for each resource
- **Logs** — stream container logs directly from the UI (click a Pod → Logs)
- **Diff** — what's different between git and the running cluster

### Manual sync

From the app detail page:
- **Sync** button → choose resources to sync → **Synchronize**
- Check **Prune** to delete resources removed from git
- Check **Force** to replace (not patch) resources

### App-of-apps hierarchy

```
app-of-apps  (manages k8s/argocd/apps/)
├── cert-manager
├── cert-manager-issuers
├── ingress-nginx
├── cilium
├── kwok
├── rancher
├── harbor
├── monitoring
├── tempo
├── loki
├── promtail
├── otel-collector
├── velero
├── rancher-backup
└── demo-app
```

### Projects

Argo CD organizes apps into Projects. This platform uses two:
- **platform** — all infrastructure components (cluster-admin permissions)
- **apps** — tenant applications (namespace-scoped permissions only)

View projects: **Settings → Projects** in the UI.

### Rolling back a deployment

1. App detail page → **History and Rollback** tab
2. Select a previous revision and click **Rollback**
3. Argo CD deploys the git state from that revision and pauses auto-sync

---

## Step 8 — Demo App UI — Fire Observability Scenarios

### Access

Navigate to **https://demo.86.38.238.224.nip.io**

### Available scenarios

| Scenario | Button | What it does | What to look for |
|----------|--------|-------------|-----------------|
| **Success** | ✅ Fire | Runs a normal request with a parent span + `process-business-logic` child span | HTTP 200, green trace in Tempo, INFO log in Loki |
| **Error** | 💥 Fire | Raises a `ValueError` inside a span, records exception, returns HTTP 500 | Red/error span in Tempo with exception event, ERROR log in Loki |
| **Slow Request** | 🐢 Fire | Sleeps inside a `slow-database-query` child span for 0.5–10 s (slider) | Long duration in Tempo waterfall, WARNING log in Loki, p99 spike in Grafana |

### Request history panel

Every fired scenario appears in the history panel below with:
- **trace_id** — the full 32-character hex trace ID
- **duration** — wall-clock milliseconds
- **View in Grafana →** — deep link that opens Grafana Explore with the exact trace preloaded in Tempo

### API docs

Click **API Docs (Swagger)** or visit `https://demo.86.38.238.224.nip.io/docs` to see the interactive FastAPI Swagger UI and try endpoints directly.

### Direct API calls

```bash
# Success
curl -X POST https://demo.86.38.238.224.nip.io/api/simulate/success \
  -H "Content-Type: application/json" -d '{"delay_ms": 0}'

# Error
curl -X POST https://demo.86.38.238.224.nip.io/api/simulate/error \
  -H "Content-Type: application/json" -d '{}'

# Slow (3 second delay)
curl -X POST https://demo.86.38.238.224.nip.io/api/simulate/slow \
  -H "Content-Type: application/json" -d '{"delay_ms": 3000}'
```

Each response includes:
```json
{
  "scenario": "success",
  "status": "ok",
  "trace_id": "ef818bddd3dca428e273ad228432a46d",
  "span_id": "f866305964b2bc8c",
  "duration_ms": 10.26,
  "message": "Request completed successfully."
}
```

---

## Step 9 — Grafana — View Logs, Traces, and Metrics

### Login

Navigate to **https://grafana.86.38.238.224.nip.io**  
Username: `admin`, Password: `grafana-admin-change-me`

### Pre-loaded dashboards

Go to **Dashboards** (grid icon in sidebar):

| Dashboard | Grafana ID | What it shows |
|-----------|-----------|--------------|
| Kubernetes Cluster | 7249 | Namespace-level CPU, memory, pod counts |
| Kubernetes Pods | 6781 | Per-pod resource usage with drill-down |
| Node Exporter Full | 1860 | Host-level CPU, memory, disk, network |
| NGINX Ingress | 9614 | Request rates, error rates, latency by ingress |

### View traces in Tempo

1. Click **Explore** (compass icon in sidebar)
2. Select datasource **Tempo** from the dropdown
3. Query type: **Search**
4. Set **Service Name**: `demo-app`
5. Click **Run query** — recent traces appear as a list
6. Click any trace to open the waterfall view showing all spans

To look up a specific trace by ID:
1. Explore → Tempo
2. Query type: **TraceQL** or **Trace ID**
3. Paste the trace ID from the demo app UI or API response
4. Click **Run query**

The waterfall view shows:
- `POST /api/simulate/success` (root span, FastAPI HTTP)
- `simulate-success` (application span)
  - `process-business-logic` (child span)
- HTTP middleware spans (request receive, response send)

### View logs in Loki

1. Explore → select **Loki**
2. Use LogQL to query:

```logql
# All demo-app logs
{namespace="demo-app"}

# Only error logs
{namespace="demo-app"} | json | level="ERROR"

# Logs for a specific trace
{namespace="demo-app"} | json | trace_id="ef818bddd3dca428e273ad228432a46d"

# Slow scenario logs
{namespace="demo-app"} |= "Slow scenario"
```

3. Each log line has a **View in Tempo** button next to the `trace_id` field — click it to jump directly to the corresponding trace in Tempo. This is the trace-log correlation feature.

### Trace → Log correlation (from Tempo side)

When viewing a trace in Tempo:
1. Click the **Logs** tab at the bottom of the trace view
2. Grafana queries Loki for logs with matching `trace_id` during the trace time window
3. The correlated logs appear inline without any additional configuration

### Metrics from the demo app

The backend exposes custom Prometheus metrics:
- `otel_demo_scenario_total` — counter by scenario type and status
- `otel_demo_scenario_duration_seconds` — histogram of request durations

Query in Grafana Explore (Prometheus datasource):

```promql
# Request rate by scenario
rate(otel_demo_scenario_total[5m])

# P99 latency
histogram_quantile(0.99, rate(otel_demo_scenario_duration_seconds_bucket[5m]))

# Error rate
rate(otel_demo_scenario_total{status="error"}[5m])
```

### Hubble network observability (Cilium)

Port-forward Hubble UI:

```bash
kubectl port-forward -n kube-system svc/hubble-ui 12000:80
```

Open http://localhost:12000 to see live L3/L4/L7 network flows between pods, with filter by namespace, pod, or protocol.

---

## Optional Components

### Cilium CNI + Hubble

Cilium replaces Canal as the CNI, providing:
- **eBPF-based NetworkPolicy enforcement** — kernel-level, lower overhead than iptables
- **Hubble** — L7 flow observability (HTTP method, status code, DNS queries)
- **kube-proxy replacement disabled** — standard iptables handles NodePort/LoadBalancer since this is bare-VM without native LB support

NetworkPolicies applied in `k8s/platform/cilium/network-policies.yaml`:
- `default-deny-ingress` on `demo-app` namespace — all ingress blocked by default
- Explicit allow rules for ingress-nginx → backend, ingress-nginx → frontend, Prometheus → backend
- `allow-otlp-from-demo-app` on `observability` namespace — restricts OTEL collector to only receive from demo-app pods

### KWOK Virtual Nodes

KWOK (Kubernetes Without Kubelet) registers 10 fake nodes that appear `Ready` in the API server, allowing you to:
- Test cluster-wide scheduling behavior at scale
- Validate resource quota and LimitRange configs without real hardware
- Demonstrate autoscaler behavior

The nodes carry a `kwok.x-k8s.io/node=fake:NoSchedule` taint, so no real workloads accidentally schedule there. Cilium is explicitly configured to skip KWOK nodes via node affinity.

View the fake nodes:

```bash
kubectl get nodes -l type=kwok
kubectl describe node kwok-node-001
```

### Velero Backup

Velero with restic node-agent backs up PersistentVolume data. In this demo it uses local filesystem storage (`/tmp/velero-backups`). For production, configure an S3-compatible bucket.

```bash
# Manual backup
velero backup create manual-backup --include-namespaces demo-app,monitoring

# Restore
velero restore create --from-backup manual-backup

# List backups
velero backup get
```

### Rancher Backup Operator

Backs up Rancher state (cluster registrations, users, roles, settings) as Kubernetes resource snapshots. Scheduled daily via `k8s/platform/backup/backup-schedules.yaml`.

---

## Security Hardening

### NetworkPolicy (Cilium)

Zero-trust network model for the demo-app namespace: default-deny-all-ingress, with explicit allow rules only for required traffic paths. This prevents lateral movement between namespaces.

### RBAC

- `automountServiceAccountToken: false` on demo-app service account — no token injected unless explicitly needed
- Scoped viewer Role for the demo-app namespace — read-only access to pods, logs, services
- Argo CD project `apps` restricts tenant applications to namespace-scoped resources only

### PodSecurity

`k8s/platform/security/pod-security.yaml` enforces baseline Pod Security Standards on workload namespaces via namespace labels, preventing privileged containers, hostPath mounts, and host networking.

### Resource Quotas

`k8s/platform/security/resource-quotas.yaml` sets per-namespace CPU/memory quotas to prevent one noisy neighbor from starving others.

### Audit Policy

`k8s/platform/security/audit-policy.yaml` documents the intended Kubernetes API audit log policy:
- `Metadata` level for secret/configmap access
- `RequestResponse` for pod exec/attach/portforward
- `Request` level for RBAC mutations

Apply to RKE2 by placing the file on the control-plane and adding `--audit-policy-file` to the kube-apiserver config.

### TLS

All public endpoints use Let's Encrypt production certificates managed by cert-manager (HTTP-01 challenge). Ingress terminates TLS; backends communicate over cluster-internal plaintext.

---

## Backup Strategy

| Component | Tool | Target | Schedule |
|-----------|------|--------|----------|
| PersistentVolumes (all namespaces) | Velero + restic | Local filesystem (upgrade to S3 for production) | on-demand |
| Rancher state (registrations, users, settings) | Rancher Backup Operator | Kubernetes resource snapshots in cluster | daily |
| etcd | RKE2 built-in | `rke2 etcd-snapshot save` on CP node | on-demand |

Production recommendation: point Velero at an S3-compatible bucket (MinIO or object storage on another Verda region), and enable Rancher Backup with an S3 target for cross-region durability.

---

## Troubleshooting

### Check all app statuses

```bash
kubectl get applications -n argocd
```

### Restart a stale pod (cross-CNI issues after Cilium install)

If pods created before Cilium was installed can no longer communicate with newer pods (Canal vs. Cilium network interfaces), restart the affected deployments:

```bash
kubectl rollout restart deployment/<name> -n <namespace>
```

### CoreDNS hairpin NAT

cert-manager's ACME HTTP-01 self-check resolves nip.io domains to the external floating IP. From inside the cluster, OpenStack hairpin NAT blocks the return path. The CoreDNS ConfigMap in `k8s/platform/coredns/coredns-patch.yaml` overrides those domains to resolve to the ingress-nginx ClusterIP instead.

If cert-manager challenges fail, verify the CoreDNS override is active:

```bash
kubectl exec -n kube-system deploy/rke2-coredns-rke2-coredns -- \
  cat /etc/coredns/Corefile | grep -A10 "hosts"
```

### OTEL trace pipeline

If traces are not appearing in Tempo:

```bash
# Check OTEL collector logs for span receipt
kubectl logs -n observability deployment/otel-collector | grep -i "TracesExporter\|error"

# Query Tempo directly for recent traces
kubectl run q --rm -i --restart=Never --image=curlimages/curl -n observability \
  -- curl -s http://tempo.observability.svc.cluster.local:3100/api/search?limit=5

# Verify the backend is sending spans
kubectl exec -n demo-app deployment/demo-app-backend -- env | grep OTEL
```

Common pitfalls:
- The Tempo exporter endpoint in the OTEL collector must be bare `host:port` (no `http://` prefix) — the `http://` prefix switches the exporter to HTTP protocol, which does not work on Tempo's gRPC port
- The debug exporter is wired into the traces pipeline for visibility; remove it in production

### Get the initial Argo CD admin password

```bash
kubectl -n argocd get secret argocd-initial-admin-secret \
  -o jsonpath='{.data.password}' | base64 -d; echo
```

### Check Let's Encrypt certificate status

```bash
kubectl get certificate -A
kubectl describe certificaterequest -A | grep -A5 "Message:"
```

### Check which pods are on Cilium vs. Canal interfaces

```bash
# Pod created before Cilium install → Canal-managed → may not communicate with Cilium pods
# Solution: restart old pods
kubectl get pods -A -o wide | sort -k8
```

---

## What Would Be Improved With More Time

1. **SSO fully automated** — GitHub OAuth clientId/clientSecret substituted via Sealed Secrets or Vault Agent, so no manual post-install UI step is needed for Argo CD, Grafana, and Rancher.

2. **Harbor webhook → Argo CD** — configure a Harbor webhook to trigger an Argo CD sync on new image push, completing the full CI→CD loop without a separate CI system.

3. **Argo CD Image Updater** — scan Harbor for new tags and automatically update Deployment manifests in git, enabling fully automated continuous delivery.

4. **Multi-environment GitOps** — separate `dev/` and `prod/` overlay directories (Kustomize or Helm values), with Argo CD ApplicationSets generating per-environment Applications. Promotion = merging a PR from dev branch to prod branch.

5. **Velero with S3** — replace the local-filesystem Velero backend with a proper S3-compatible object store for durable, cross-node backup.

6. **Alertmanager receivers** — wire Alertmanager to Slack/PagerDuty with specific routes for the priority alerts listed in the Prometheus values (KubeNodeNotReady, PodCrashLooping, PVCFillingUp, CPUThrottlingHigh).

7. **Kueue job queues** — add high-priority and low-priority job queues for batch workload scheduling, completing the advanced task from the assignment.

8. **etcd scheduled backups** — cron job calling `rke2 etcd-snapshot save` and uploading snapshots to object storage.

9. **KWOK at 100 nodes** — currently limited to 10 because Rancher's node registration UI becomes slow at scale. With Rancher excluded or with a higher-resource setup, 100 fake nodes would demonstrate scheduler behavior at realistic scale.

10. **Grafana alerts** — create Grafana-managed alert rules for `error_rate > 1%`, `p99_latency > 5s`, and `pod_restart_count > 3` targeting the demo app, with notifications sent to a demo Slack webhook.
