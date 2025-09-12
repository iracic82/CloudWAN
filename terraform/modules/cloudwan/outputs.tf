output "core_network_arn" {
  value = aws_networkmanager_core_network.core.arn
}
# No outputs; the module attaches VPCs and propagates routes
output "policy_id" {
  value = aws_networkmanager_core_network_policy_attachment.policy.id
}
