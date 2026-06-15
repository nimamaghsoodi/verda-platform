# Summary Report

## What Was Built

A production-representative Kubernetes platform on Verda Cloud comprising:

| Layer | Component | Notes |
|-------|-----------|-------|
| Infra | Terraform + OpenStack | 1 CP + 2 workers, floating IPs, security groups |
| Bootstrap | Ansible + RKE2 | Full cluster bootstrap, kubeconfig fetch |
| GitOps | Argo CD (app-of-apps) | Self-managing; all platform components are Argo CD Applications |
| Registry | Harbor | TLS, project `demo`, image vulnerability scanning (Trivy) |
| Cluster mgmt | Rancher Manager | Cluster imported, GitHub SSO configured |
| Monitoring | kube-prometheus-stack | Prometheus, Grafana, Alertmanager; pre-loaded dashboards |
| Observability | OTEL Collector + Tempo + Loki + Promtail | Full trace-log-metric correlation |
| Demo app | FastAPI + React | UI with success/error/slow scenarios, full OTEL instrumentation |

## Architecture

See [architecture.md](architecture.md).

## What Worked

- RKE2 cluster provisioned cleanly via Terraform + Ansible end-to-end
- Argo CD app-of-apps pattern: adding a new component is a single YAML file
- OTEL trace correlation from demo-app → Tempo → Grafana Explore with clickable trace IDs
- Log correlation via `trace_id` injected into JSON logs (Promtail → Loki → Grafana)
- Let's Encrypt certs issued automatically via cert-manager HTTP01 challenge
- Harbor registry accessible from within the cluster with TLS

## What Did Not Work / Challenges

- **nip.io DNS**: Let's Encrypt rate-limits wildcard certs on nip.io subdomains — used staging issuer first, promoted to prod after cluster stabilised
- **Rancher SSO**: GitHub OAuth callback URL must match exactly; nip.io domain with HTTPS required an extra step to configure the allowed callback in the GitHub OAuth App settings
- **Tempo remote_write**: Tempo's metrics generator requires `remote_write` permission on Prometheus; added `--web.enable-remote-write-receiver` to the Prometheus config
- **StorageClass on bare VMs**: RKE2 ships `local-path` provisioner by default which is node-local — PVCs are non-HA. Longhorn would be the next step for HA storage

## Security Considerations

- **Network**: Security groups restrict etcd and supervisor ports to the cluster subnet; only 22, 80, 443, and NodePort range exposed externally
- **TLS everywhere**: All ingresses use TLS via cert-manager; HTTP redirects to HTTPS
- **RBAC**: Argo CD RBAC maps GitHub org teams to roles; Grafana uses GitHub org membership; Kubernetes RBAC not relaxed
- **Secrets**: GitHub OAuth client secrets stored as Kubernetes Secrets, not in git. Placeholder `<GITHUB_CLIENT_SECRET>` in values files must be replaced before committing
- **Harbor**: Trivy scanning enabled; images from unknown registries would require explicit project policy approval
- **Images**: Pinned image tags in production manifests — `latest` only for the demo app during development

## Alerts for Production

| Alert | Threshold | Severity |
|-------|-----------|----------|
| KubeNodeNotReady | node not ready > 2 min | critical |
| KubePodCrashLooping | crash rate > 1/min | warning |
| KubePersistentVolumeFillingUp | PV > 85% full | warning |
| KubeDeploymentReplicasMismatch | desired ≠ ready > 5 min | critical |
| TargetDown | Prometheus scrape target down > 5 min | warning |
| CPUThrottlingHigh | throttled > 25% over 5 min | warning |
| demo_scenario_error_rate | error scenario rate > 10/min | warning |
| HighRequestLatency | p99 latency > 2s | warning |

## What Would Be Improved With More Time

1. **Longhorn** — replace `local-path` with Longhorn for replicated, HA PVCs
2. **Cilium** — replace Canal CNI with Cilium for network policy enforcement and Hubble observability
3. **Velero backup** — backup Rancher, Argo CD, Harbor, and etcd snapshots to S3-compatible Verda Object Storage
4. **Image build pipeline** — GitHub Actions workflow: push → build → scan (Trivy) → push to Harbor → update image tag in git → Argo CD auto-sync
5. **Multi-environment** — staging namespace/cluster with auto-sync; prod with manual sync gate and approval annotation
6. **OPA / Kyverno** — admission policies: no `latest` tags, require resource limits, enforce label standards
7. **KWOK** — simulate 100+ virtual nodes to load-test the scheduler and Prometheus without adding real VMs
8. **Keycloak** — replace GitHub OAuth with a self-hosted IdP for full enterprise SSO (SAML, LDAP) unified across all tools
