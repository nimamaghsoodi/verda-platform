# Architecture

## Infrastructure

```
Verda Cloud (OpenStack)
│
├── Network: verda-k8s-net (10.10.0.0/24)
│   └── Router → External/Public network
│
├── verda-k8s-cp          (control-plane, floating IP: CP_IP)
│   ├── RKE2 Server (API server, etcd, scheduler, controller-manager)
│   └── Rancher Manager  (cattle-system namespace)
│
├── verda-k8s-worker-1    (floating IP: WORKER1_IP — ingress IP)
│   ├── RKE2 Agent
│   └── ingress-nginx DaemonSet
│
└── verda-k8s-worker-2    (floating IP: WORKER2_IP)
    └── RKE2 Agent
```

## Platform Stack (deployed via Argo CD)

```
Argo CD (argocd ns)
└── app-of-apps
    ├── cert-manager          (cert-manager ns)     — TLS via Let's Encrypt HTTP01
    ├── ingress-nginx         (ingress-nginx ns)     — L7 ingress, externalIP = WORKER1_IP
    ├── rancher               (cattle-system ns)     — Cluster management UI
    ├── harbor                (harbor ns)            — Container registry
    ├── monitoring            (monitoring ns)        — kube-prometheus-stack
    │   ├── Prometheus                               — metrics scraping + alerting
    │   ├── Grafana                                  — dashboards + datasources
    │   └── Alertmanager                             — alert routing
    ├── observability         (observability ns)
    │   ├── OTEL Collector                           — receives OTLP, routes to backends
    │   ├── Tempo                                    — distributed tracing backend
    │   ├── Loki                                     — log aggregation
    │   └── Promtail (DaemonSet)                     — log shipping from pods
    └── demo-app              (demo-app ns)
        ├── Backend (FastAPI)                        — emits traces, metrics, logs via OTEL
        └── Frontend (React/nginx)                   — UI to trigger scenarios
```

## DNS (nip.io wildcard)

| Service    | URL                                      |
|------------|------------------------------------------|
| Argo CD    | https://argocd.WORKER1_IP.nip.io        |
| Rancher    | https://rancher.CP_IP.nip.io            |
| Harbor     | https://harbor.WORKER1_IP.nip.io        |
| Grafana    | https://grafana.WORKER1_IP.nip.io       |
| Demo App   | https://demo.WORKER1_IP.nip.io          |

## Observability Flow

```
demo-app-backend
  │── OTLP gRPC (traces, metrics, logs)
  └──► otel-collector
          ├──► Tempo        ← Grafana datasource (traces)
          ├──► Prometheus   ← via remote_write (OTEL metrics)
          └──► Loki         ← via loki exporter (structured logs)

Node/pod logs
  └── Promtail (DaemonSet)
        └──► Loki

Kubernetes metrics
  └── kube-state-metrics + node-exporter
        └──► Prometheus

All visualised in Grafana (unified dashboards with trace-log correlation via trace_id)
```

## GitOps Promotion

```
git push → GitHub
    └── Argo CD watches repo (HEAD)
            └── Syncs Application manifests
                    └── Helm/kubectl apply → cluster

Environment promotion:
  dev   → k8s/apps/demo-app/  (auto-sync, no approval)
  prod  → separate Application with syncPolicy.automated disabled
          (requires manual argocd app sync demo-app-prod or PR merge to prod branch)
```

## SSO

- **Argo CD**: GitHub OAuth via Dex (configured in `argocd-values.yaml`)
- **Grafana**: GitHub OAuth (`auth.github` in kube-prometheus-stack values)
- **Rancher**: GitHub OAuth configured post-install via UI (Settings → Auth Provider)
- **Harbor**: Local admin only (LDAP/OIDC can be added post-demo)
