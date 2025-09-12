output "vpc_id" {
  value = aws_vpc.spoke.id
}

output "subnet_arns" {
  value = [aws_subnet.subnet.arn]
}
output "route_table_id" {
  value = aws_route_table.rt.id
}
output "aws_vpc_cidr" {
  value = var.aws_vpc_cidr
}


output "public_ip" {
  description = "Public EIP of the spoke EC2 instance"
  value       = aws_eip.eip.public_ip
}

output "ssh_access" {
  description = "SSH command for this spoke EC2"
  value       = "ssh -i ${aws_key_pair.demo_key_pair.key_name}.pem ec2-user@${aws_eip.eip.public_ip}"
}