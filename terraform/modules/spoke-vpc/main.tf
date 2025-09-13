##############################################################################
# Key Pair (generate inside TF, write PEM to disk)
##############################################################################
resource "tls_private_key" "spoke_key" {
  algorithm = "RSA"
  rsa_bits  = 4096
}

resource "aws_key_pair" "spoke_key_pair" {
  key_name   = var.key_name
  public_key = tls_private_key.spoke_key.public_key_openssh
  tags       = var.tags
}

resource "local_sensitive_file" "spoke_private_key_pem" {
  content         = tls_private_key.spoke_key.private_key_pem
  filename        = "./${var.key_name}.pem"
  file_permission = "0400"
}

##############################################################################
# VPC + Subnet
##############################################################################
resource "aws_vpc" "spoke" {
  cidr_block           = var.vpc_cidr
  enable_dns_support   = true
  enable_dns_hostnames = true
  tags                 = merge(var.tags, { Name = var.vpc_name })
}

resource "aws_subnet" "subnet" {
  vpc_id                  = aws_vpc.spoke.id
  cidr_block              = var.subnet_cidr
  availability_zone       = var.az
  map_public_ip_on_launch = true
  tags                    = merge(var.tags, { Name = "${var.vpc_name}-subnet" })
}

##############################################################################
# IGW + Default Route
##############################################################################
resource "aws_internet_gateway" "igw" {
  vpc_id = aws_vpc.spoke.id
  tags   = merge(var.tags, { Name = "${var.vpc_name}-igw" })
}

resource "aws_default_route_table" "this" {
  default_route_table_id = aws_vpc.spoke.default_route_table_id
  tags                   = merge(var.tags, { Name = "${var.vpc_name}-default-rt" })
}

resource "aws_route" "default_outbound" {
  route_table_id         = aws_default_route_table.this.id
  destination_cidr_block = "0.0.0.0/0"
  gateway_id             = aws_internet_gateway.igw.id
}

##############################################################################
# Security Group
##############################################################################
resource "aws_security_group" "sg" {
  name   = "${var.vpc_name}-sg"
  vpc_id = aws_vpc.spoke.id

  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    from_port   = -1
    to_port     = -1
    protocol    = "icmp"
    cidr_blocks = ["10.0.0.0/8"]
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
# ENI + EC2
##############################################################################
resource "aws_network_interface" "eni" {
  subnet_id       = aws_subnet.subnet.id
  private_ips     = [var.private_ip]
  security_groups = [aws_security_group.sg.id]
  tags            = merge(var.tags, { Name = "${var.vpc_name}-eni" })
}

resource "aws_instance" "ec2" {
  ami           = data.aws_ami.linux.id
  instance_type = "t3.micro"
  key_name      = aws_key_pair.spoke_key_pair.key_name  # ✅ use generated key
  tags          = merge(var.tags, { Name = var.instance_name })

  primary_network_interface {
    network_interface_id = aws_network_interface.eni.id
  }

  depends_on = [aws_internet_gateway.igw]
}

##############################################################################
# Public AMI
##############################################################################
data "aws_ami" "linux" {
  most_recent = true
  owners      = ["amazon"]
  filter {
    name   = "name"
    values = ["amzn2-ami-hvm-*-x86_64-gp2"]
  }
}

##############################################################################
# Optional EIP for quick SSH
##############################################################################
resource "aws_eip" "eip" {
  domain = "vpc"
  tags   = var.tags
}

resource "aws_eip_association" "assoc" {
  allocation_id        = aws_eip.eip.id
  network_interface_id = aws_network_interface.eni.id
  private_ip_address   = var.private_ip
}


