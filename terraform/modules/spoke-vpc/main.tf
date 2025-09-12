data "aws_availability_zones" "available" {}


# Get latest Amazon Linux 2 AMI
data "aws_ami" "linux" {
  most_recent = true
  owners      = ["amazon"]
  filter {
    name   = "name"
    values = ["amzn2-ami-hvm-*-x86_64-gp2"]
  }
}


# Create the spoke VPC
resource "aws_vpc" "spoke" {
  cidr_block           = var.aws_vpc_cidr
  enable_dns_support   = true
  enable_dns_hostnames = true
  tags                 = merge(var.tags, { Name = var.vpc_name })
}

# Public subnet for the spoke
resource "aws_subnet" "subnet" {
  vpc_id                  = aws_vpc.spoke.id
  cidr_block              = var.aws_subnet_cidr
  availability_zone       = data.aws_availability_zones.available.names[0]
  map_public_ip_on_launch = true
  tags                    = merge(var.tags, { Name = "${var.vpc_name}-subnet" })
}

# Internet Gateway & Route Table
resource "aws_internet_gateway" "igw" {
  vpc_id = aws_vpc.spoke.id
  tags   = merge(var.tags, { Name = "${var.vpc_name}-igw" })
}

# Use the VPC’s default route table so Cloud WAN propagation works
resource "aws_default_route_table" "this" {
  default_route_table_id = aws_vpc.spoke.default_route_table_id

  tags = merge(var.tags, {
    Name = "${var.vpc_name}-default-rt"
  })
}

# Add outbound IGW route to the default RT
resource "aws_route" "default_outbound" {
  route_table_id         = aws_default_route_table.this.id
  destination_cidr_block = "0.0.0.0/0"
  gateway_id             = aws_internet_gateway.igw.id
}

# Security Group: SSH + ICMP
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

# Create Network Interface
resource "aws_network_interface" "eth1" {
  subnet_id       = aws_subnet.subnet.id
  private_ips     = [var.private_ip]
  security_groups = [aws_security_group.sg.id]
  tags            = merge(var.tags, { Name = "${var.vpc_name}-eni" })
}

# Create a SSH private key
resource "tls_private_key" "demo_key" {
  algorithm = "RSA"
  rsa_bits  = 4096
}

resource "random_pet" "suffix" {}
resource "aws_key_pair" "demo_key_pair" {
  key_name   = "${var.key_name}-${random_pet.suffix.id}"
  public_key = tls_private_key.demo_key.public_key_openssh
  tags       = var.tags
}

resource "local_sensitive_file" "private_key_pem" {
  content         = tls_private_key.demo_key.private_key_pem
  filename        = "${path.root}/${aws_key_pair.demo_key_pair.key_name}.pem"
  file_permission = "0400"
}

# EC2: attach the prebuilt ENI as primary; do NOT set subnet_id/private_ip/SG here
resource "aws_instance" "ec2" {
  ami           = data.aws_ami.linux.id
  instance_type = "t3.micro"
  key_name      = aws_key_pair.demo_key_pair.key_name
  tags          = merge(var.tags, { Name = var.instance_name })

  network_interface {
    network_interface_id = aws_network_interface.eth1.id
    device_index         = 0
  }

  depends_on = [aws_internet_gateway.igw]
}

# Allocate and associate an Elastic IP to the EC2 instance
# Allocate a new Elastic IP
resource "aws_eip" "eip" {
  # no "vpc" argument needed
  tags = var.tags
}

# Associate that EIP to the spoke ENI
resource "aws_eip_association" "eip_assoc" {
  allocation_id        = aws_eip.eip.id
  network_interface_id = aws_network_interface.eth1.id
  private_ip_address   = var.private_ip
}

