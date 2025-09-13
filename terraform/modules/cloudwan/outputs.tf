output "core_network_arn" {
  value = aws_networkmanager_core_network.core.arn
}
# No outputs; the module attaches VPCs and propagates routes
output "policy_id" {
  value = aws_networkmanager_core_network_policy_attachment.policy.id
}
output "connect_peer_bgp" {
  description = "BGP configs for Connect peers (mapped to NIOSX1 / NIOSX2)"
  value = {
    niosx1 = {
      aws_ip  = aws_networkmanager_connect_peer.shared_peer_1.configuration[0].bgp_configurations[0].core_network_address
      nios_ip = aws_networkmanager_connect_peer.shared_peer_1.configuration[0].bgp_configurations[0].peer_address
      aws_asn = aws_networkmanager_connect_peer.shared_peer_1.configuration[0].bgp_configurations[0].core_network_asn
      nios_asn= aws_networkmanager_connect_peer.shared_peer_1.configuration[0].bgp_configurations[0].peer_asn
    }
    niosx2 = {
      aws_ip  = aws_networkmanager_connect_peer.shared_peer_2.configuration[0].bgp_configurations[0].core_network_address
      nios_ip = aws_networkmanager_connect_peer.shared_peer_2.configuration[0].bgp_configurations[0].peer_address
      aws_asn = aws_networkmanager_connect_peer.shared_peer_2.configuration[0].bgp_configurations[0].core_network_asn
      nios_asn= aws_networkmanager_connect_peer.shared_peer_2.configuration[0].bgp_configurations[0].peer_asn
    }
  }
}
