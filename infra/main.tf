locals {
  cluster_name = var.cluster_name
}

# ─── SSH Key ─────────────────────────────────────────────────────────────────

resource "verda_ssh_key" "cluster" {
  name       = "${local.cluster_name}-key"
  public_key = file(var.ssh_public_key_path)
}

# ─── Startup Script ──────────────────────────────────────────────────────────
# Minimal OS prep; Ansible handles RKE2 and platform bootstrap after provisioning.

resource "verda_startup_script" "node_prep" {
  name   = "${local.cluster_name}-node-prep"
  script = <<-BASH
    #!/bin/bash
    set -euo pipefail

    # Disable swap (required by Kubernetes)
    swapoff -a
    sed -i '/\sswap\s/s/^/#/' /etc/fstab

    # Kernel modules for Kubernetes networking
    modprobe overlay
    modprobe br_netfilter
    cat > /etc/modules-load.d/rke2.conf <<EOF
overlay
br_netfilter
EOF

    # Sysctl settings
    cat > /etc/sysctl.d/99-kubernetes.conf <<EOF
net.bridge.bridge-nf-call-iptables  = 1
net.bridge.bridge-nf-call-ip6tables = 1
net.ipv4.ip_forward                 = 1
EOF
    sysctl --system

    # Base packages
    apt-get update -qq
    apt-get install -yq --no-install-recommends curl ca-certificates git vim python3 open-iscsi nfs-common
  BASH
}

# ─── Control-Plane Instance ──────────────────────────────────────────────────

resource "verda_instance" "control_plane" {
  instance_type     = var.instance_type_control_plane
  image             = var.image
  hostname          = "${local.cluster_name}-cp"
  description       = "RKE2 control-plane node"
  location          = var.location
  ssh_key_ids       = [verda_ssh_key.cluster.id]
  startup_script_id = verda_startup_script.node_prep.id

  volumes = [
    {
      name = "${local.cluster_name}-cp-os"
      size = var.os_volume_size_gb
      type = "NVMe"
      on_spot_discontinue = "delete_permanently"
    }
  ]
}

# ─── Worker Instances ─────────────────────────────────────────────────────────

resource "verda_instance" "worker" {
  count             = var.worker_count
  instance_type     = var.instance_type_worker
  image             = var.image
  hostname          = "${local.cluster_name}-worker-${count.index + 1}"
  description       = "RKE2 worker node ${count.index + 1}"
  location          = var.location
  ssh_key_ids       = [verda_ssh_key.cluster.id]
  startup_script_id = verda_startup_script.node_prep.id

  volumes = [
    {
      name = "${local.cluster_name}-worker-${count.index + 1}-os"
      size = var.os_volume_size_gb
      type = "NVMe"
      on_spot_discontinue = "delete_permanently"
    }
  ]
}
