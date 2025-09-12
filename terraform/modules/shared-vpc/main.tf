locals {
  infoblox_ami_id = "ami-08659b5070b66249d"
  join_token       = var.infoblox_join_token
}

data "aws_availability_zones" "available" {}

# Shared Services VPC
resource "aws_vpc" "shared" {
  cidr_block           = "10.30.0.0/16"
  enable_dns_support   = true
  enable_dns_hostnames = true
  tags                 = merge(var.tags, { Name = "shared-vpc" })
}

# Subnet for management & LAN
resource "aws_subnet" "public" {
  vpc_id                  = aws_vpc.shared.id
  cidr_block              = "10.30.1.0/24"
  availability_zone       = data.aws_availability_zones.available.names[0]
  map_public_ip_on_launch = true
  tags                    = merge(var.tags, { Name = "shared-subnet" })
}


resource "aws_default_route_table" "this" {
  default_route_table_id = aws_vpc.shared.default_route_table_id

  tags = merge(var.tags, {
    Name = "shared-default-rt"
  })
}

# Internet Gateway
resource "aws_internet_gateway" "gw" {
  vpc_id = aws_vpc.shared.id
  tags   = merge(var.tags, { Name = "shared-igw" })
}

# punch 0.0.0.0/0 out to the IGW on the VPC’s default RT
resource "aws_route" "default_outbound" {
  route_table_id         = aws_default_route_table.this.id
  destination_cidr_block = "0.0.0.0/0"
  gateway_id             = aws_internet_gateway.gw.id
}

# Allow HTTPS in & all out
resource "aws_security_group" "rdp_sg" {
  name   = "shared-sg"
  vpc_id = aws_vpc.shared.id

  ingress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }
  ingress {
    from_port   = 53
    to_port     = 53
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }
  ingress {
    from_port   = 53
    to_port     = 53
    protocol    = "udp"
    cidr_blocks = ["0.0.0.0/0"]
  }
  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(var.tags, { Name = "shared-sg" })
}

# Network Interface for Grid Master
resource "aws_network_interface" "gm_lan1" {
  subnet_id       = aws_subnet.public.id
  private_ips     = ["10.30.1.5"]
  security_groups = [aws_security_group.rdp_sg.id]
  tags            = merge(var.tags, { Name = "gm-lan1-nic" })
}

# Create a SSH private key
resource "tls_private_key" "gm_key" {
  algorithm = "RSA"
  rsa_bits  = 4096
}

# Create the AWS Key Pair from the public key
resource "aws_key_pair" "gm_key_pair" {
  key_name   = var.key_name
  public_key = tls_private_key.gm_key.public_key_openssh
  tags       = var.tags
}


# Write the private key to a local file for SSH
resource "local_sensitive_file" "gm_private_key_pem" {
  content         = tls_private_key.gm_key.private_key_pem
  filename        = "./${var.key_name}.pem"
  file_permission = "0400"
}

# Grid Master EC2 (NIOS-X)
resource "aws_instance" "gm" {
  ami                    =  local.infoblox_ami_id
  instance_type          = "c5a.2xlarge"
  key_name               = aws_key_pair.gm_key_pair.key_name

  network_interface {
    network_interface_id = aws_network_interface.gm_lan1.id
    device_index         = 0
  }

  user_data = <<-EOF
    #cloud-config
    host_setup:
      jointoken: "${local.join_token}"
  EOF

  metadata_options {
    http_tokens                 = "optional"
    http_put_response_hop_limit = 1
    http_endpoint               = "enabled"
    instance_metadata_tags      = "enabled"
  }

  tags      = merge(var.tags, { Name = "Infoblox-NIOSX" })
  depends_on = [aws_internet_gateway.gw]
}
