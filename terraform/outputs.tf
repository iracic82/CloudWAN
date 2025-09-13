output "shared_vpc_id" {
  value = module.shared_vpc.vpc_id
}

output "spoke_eu_vpc_id" {
  value = module.spoke_vpc_eu.vpc_id
}

output "spoke_us_vpc_id" {
  value = module.spoke_vpc_us.vpc_id
}

output "ssh_access_eu" {
  description = "SSH command for EU spoke"
  value       = module.spoke_vpc_eu.ssh_access
}

output "ssh_access_us" {
  description = "SSH command for US spoke"
  value       = module.spoke_vpc_us.ssh_access
}

output "bgp_peering_details" {
  description = "All BGP peering details for NIOS-X to AWS"
  value       = module.cloudwan.connect_peer_bgp
}
