output "vpc_id" {
  value = aws_vpc.shared.id
}

output "subnet_arns" {
  description = "List of subnet ARNs in the shared VPC"
  value       = [aws_subnet.public.arn]
}

output "route_table_id" {
  value = aws_vpc.shared.default_route_table_id != null ? aws_vpc.shared.default_route_table_id : aws_default_route_table.this.id
}

output "aws_vpc_cidr" {
  value = aws_vpc.shared.cidr_block
}
output "vpc_cidr" {
  value = var.vpc_cidr
}

output "gm_private_ip" {
  value = aws_network_interface.gm_lan1.private_ip
}

output "gm_bgp_ip" {
  value = "169.254.100.2"
}

output "public_subnet_arn" {
  description = "ARN of the shared VPC public subnet"
  value       = aws_subnet.public.arn
}
