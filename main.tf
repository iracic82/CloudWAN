
module "shared_vpc" {
  providers = { aws = aws }
  source              = "./modules/shared-vpc"
  infoblox_join_token = "0c40ebc559a4436410c8d00964991f5f5f94b69313ba3285d0234c0e4579f7c5"
  key_name       = var.demo_key_name
  tags                = var.tags
}



module "spoke_vpc_eu" {
  providers = { aws = aws }
  source         = "./modules/spoke-vpc"
  aws_region     = "eu-west-1"
  vpc_name       = "spoke-vpc-eu"
  aws_vpc_cidr   = "10.10.0.0/16"
  aws_subnet_cidr= "10.10.1.0/24"
  az             = "eu-west-1a"
  private_ip     = "10.10.1.10"
  instance_name  = "spoke-ec2-eu"
  key_name       = var.demo_key_name
  tags           = var.tags
}

module "spoke_vpc_us" {
  providers = { aws = aws.us-east-1 }
  source         = "./modules/spoke-vpc"
  aws_region     = "us-east-1"
  vpc_name       = "spoke-vpc-us"
  aws_vpc_cidr   = "10.20.0.0/16"
  aws_subnet_cidr= "10.20.1.0/24"
  az             = "us-east-1a"
  private_ip     = "10.20.1.10"
  instance_name  = "spoke-ec2-us"
  key_name       = var.demo_key_name
  tags           = var.tags
}

module "cloudwan" {
  providers = {
    aws             = aws               # EU resources
    aws.us-east-1   = aws.us-east-1     # US resources
  }
  source             = "./modules/cloudwan"
  vpcs = {
  shared       = module.shared_vpc.vpc_id
  eu_central_1 = module.spoke_vpc_eu.vpc_id
  us_east_1    = module.spoke_vpc_us.vpc_id
  }

  subnet_arns_map = {
  shared       = module.shared_vpc.subnet_arns
  eu_central_1 = module.spoke_vpc_eu.subnet_arns
  us_east_1    = module.spoke_vpc_us.subnet_arns
  }
  tags = var.tags
}

resource "aws_route" "eu_to_us" {
  route_table_id         = module.spoke_vpc_eu.route_table_id
  destination_cidr_block = module.spoke_vpc_us.aws_vpc_cidr
  core_network_arn       = module.cloudwan.core_network_arn
}

resource "aws_route" "us_to_eu" {
  provider               = aws.us-east-1
  route_table_id         = module.spoke_vpc_us.route_table_id
  destination_cidr_block = module.spoke_vpc_eu.aws_vpc_cidr
  core_network_arn       = module.cloudwan.core_network_arn
}

resource "aws_route" "eu_spoke_to_shared" {
  route_table_id         = module.spoke_vpc_eu.route_table_id
  destination_cidr_block = module.shared_vpc.aws_vpc_cidr
  core_network_arn       = module.cloudwan.core_network_arn
}

resource "aws_route" "us_spoke_to_shared" {
  provider               = aws.us-east-1
  route_table_id         = module.spoke_vpc_us.route_table_id
  destination_cidr_block = module.shared_vpc.aws_vpc_cidr
  core_network_arn       = module.cloudwan.core_network_arn
}

resource "aws_route" "shared_to_spoke_eu" {
  route_table_id         = module.shared_vpc.route_table_id
  destination_cidr_block = module.spoke_vpc_eu.aws_vpc_cidr
  core_network_arn       = module.cloudwan.core_network_arn
}

resource "aws_route" "shared_to_spoke_us" {
  route_table_id         = module.shared_vpc.route_table_id
  destination_cidr_block = module.spoke_vpc_us.aws_vpc_cidr
  core_network_arn       = module.cloudwan.core_network_arn
}


