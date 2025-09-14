data "aws_availability_zones" "available" {}

# VPC
resource "aws_vpc" "shared" {
  cidr_block           = var.vpc_cidr
  enable_dns_support   = true
  enable_dns_hostnames = true
  tags                 = merge(var.tags, { Name = var.vpc_name })
}

# Subnet
resource "aws_subnet" "public" {
  vpc_id                  = aws_vpc.shared.id
  cidr_block              = var.subnet_cidr
  availability_zone       = var.az
  map_public_ip_on_launch = true
  tags                    = merge(var.tags, { Name = "${var.vpc_name}-subnet" })
}

# Default RT (keep as main so Cloud WAN can target it)
resource "aws_default_route_table" "this" {
  default_route_table_id = aws_vpc.shared.default_route_table_id
  tags = merge(var.tags, { Name = "${var.vpc_name}-default-rt" })
}

# IGW + default 0/0
resource "aws_internet_gateway" "igw" {
  vpc_id = aws_vpc.shared.id
  tags   = merge(var.tags, { Name = "${var.vpc_name}-igw" })
}

resource "aws_route" "default_outbound" {
  route_table_id         = aws_default_route_table.this.id
  destination_cidr_block = "0.0.0.0/0"
  gateway_id             = aws_internet_gateway.igw.id
}

# Security group (HTTPS, DNS tcp/udp, SSH, ICMP from 10/8)
resource "aws_security_group" "srv" {
  name   = "${var.vpc_name}-sg"
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
    from_port   = -1
    to_port     = -1
    protocol    = "icmp"
    cidr_blocks = ["10.0.0.0/8"]
  }

  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    from_port   = 179
    to_port     = 179
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(var.tags, { Name = "${var.vpc_name}-sg" })
}

##############################################################################
# Key Pair (generate inside TF, write PEM to disk)
##############################################################################
resource "tls_private_key" "gm_key" {
  algorithm = "RSA"
  rsa_bits  = 4096
}

resource "aws_key_pair" "gm_key_pair" {
  key_name   = var.key_name
  public_key = tls_private_key.gm_key.public_key_openssh
  tags       = var.tags
}

resource "local_sensitive_file" "gm_private_key_pem" {
  content         = tls_private_key.gm_key.private_key_pem
  filename        = "./${var.key_name}.pem"
  file_permission = "0400"
}


##############################################################################
# ENIs
##############################################################################
resource "aws_network_interface" "gm_lan1" {
  subnet_id       = aws_subnet.public.id
  private_ips     = [var.gm_ip]
  security_groups = [aws_security_group.srv.id]
  tags            = merge(var.tags, { Name = "gm-lan1-nic" })
}

resource "aws_network_interface" "niosx2_lan1" {
  subnet_id       = aws_subnet.public.id
  private_ips     = [var.nios_ip]
  security_groups = [aws_security_group.srv.id]
  tags            = merge(var.tags, { Name = "niosx2-lan1-nic" })
}

##############################################################################
# NIOS-X instances (two nodes)
##############################################################################
resource "aws_instance" "gm" {
  ami           = var.infoblox_ami_id
  instance_type = "c5a.2xlarge"
  key_name      = aws_key_pair.gm_key_pair.key_name  # ✅ use generated key

  primary_network_interface {
    network_interface_id = aws_network_interface.gm_lan1.id
  }

  user_data = <<-EOF
    #cloud-config
    host_setup:
      jointoken: "${var.infoblox_join_token}"
  EOF

  metadata_options {
    http_tokens                 = "optional"
    http_put_response_hop_limit = 1
    http_endpoint               = "enabled"
    instance_metadata_tags      = "enabled"
  }

  tags       = merge(var.tags, { Name = "Infoblox-NIOSX-1" })
  depends_on = [aws_internet_gateway.igw]
}

resource "aws_instance" "niosx2" {
  ami           = var.infoblox_ami_id
  instance_type = "c5a.2xlarge"
  key_name      = aws_key_pair.gm_key_pair.key_name  # ✅ use generated key

  primary_network_interface {
    network_interface_id = aws_network_interface.niosx2_lan1.id
  }

  user_data = <<-EOF
    #cloud-config
    host_setup:
      jointoken: "${var.infoblox_join_token}"
  EOF

  metadata_options {
    http_tokens                 = "optional"
    http_put_response_hop_limit = 1
    http_endpoint               = "enabled"
    instance_metadata_tags      = "enabled"
  }

  tags       = merge(var.tags, { Name = "Infoblox-NIOSX-2" })
  depends_on = [aws_internet_gateway.igw]
}

##############################################################################
# EIPs (optional—remove if you don't need public reachability)
##############################################################################
resource "aws_eip" "gm_eip" {
  domain = "vpc"
  tags   = merge(var.tags, { Name = "gm-eip" })
}

resource "aws_eip" "nios2_eip" {
  domain = "vpc"
  tags   = merge(var.tags, { Name = "niosx2-eip" })
}

resource "aws_eip_association" "gm_assoc" {
  network_interface_id = aws_network_interface.gm_lan1.id
  allocation_id        = aws_eip.gm_eip.id
  private_ip_address   = var.gm_ip
}

resource "aws_eip_association" "nios2_assoc" {
  network_interface_id = aws_network_interface.niosx2_lan1.id
  allocation_id        = aws_eip.nios2_eip.id
  private_ip_address   = var.nios_ip
}

