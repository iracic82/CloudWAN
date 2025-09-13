output "vpc_id" {
  value       = aws_vpc.spoke.id
  description = "Spoke VPC ID"
}

output "subnet_arns" {
  value       = [aws_subnet.subnet.arn]
  description = "Subnet ARN(s)"
}

output "route_table_id" {
  value       = aws_default_route_table.this.id
  description = "Default route table ID"
}

output "aws_vpc_cidr" {
  value       = aws_vpc.spoke.cidr_block
  description = "VPC CIDR"
}
output "vpc_cidr" {
  value = var.vpc_cidr
}

output "public_ip" {
  value       = aws_eip.eip.public_ip
  description = "Public IP of spoke EC2"
}

output "ssh_access" {
  value       = "ssh -i ${var.key_name}.pem ec2-user@${aws_eip.eip.public_ip}"
  description = "SSH command to access the spoke EC2"
}
