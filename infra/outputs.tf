output "control_plane_ip" {
  description = "Public IP of the control-plane node (may be null until instance finishes booting)"
  value       = try(verda_instance.control_plane.ip, null)
}

output "worker_ips" {
  description = "Public IPs of worker nodes (may be null until instances finish booting)"
  value       = [for w in verda_instance.worker : try(w.ip, null)]
}

output "nip_io_domain" {
  description = "nip.io wildcard domain using worker-1 IP"
  value       = try("${verda_instance.worker[0].ip}.nip.io", "IP not yet assigned — re-run: terraform output nip_io_domain")
}

output "instance_ids" {
  description = "Instance IDs for direct API queries"
  value = {
    control_plane = verda_instance.control_plane.id
    worker_1      = verda_instance.worker[0].id
    worker_2      = verda_instance.worker[1].id
  }
}

output "ansible_inventory" {
  description = "Paste into bootstrap/inventory.ini (re-run after IPs are assigned)"
  value = try(<<-INI
    [control_plane]
    ${verda_instance.control_plane.hostname} ansible_host=${verda_instance.control_plane.ip} ansible_user=root ansible_ssh_private_key_file=~/.ssh/id_rsa

    [workers]
    ${join("\n", [
      for w in verda_instance.worker :
      "${w.hostname} ansible_host=${w.ip} ansible_user=root ansible_ssh_private_key_file=~/.ssh/id_rsa"
    ])}

    [k8s_cluster:children]
    control_plane
    workers
  INI
  , "IPs not yet assigned — re-run: terraform output ansible_inventory"
  )
}
