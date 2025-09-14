##############################################################################
# Shared VPC
##############################################################################
module "shared_vpc" {
  providers = { aws = aws }
  source    = "./modules/shared-vpc"

  vpc_name            = var.shared_vpc["name"]
  vpc_cidr            = var.shared_vpc["cidr"]
  subnet_cidr         = var.shared_vpc["subnet"]
  az                  = var.shared_vpc["az"]
  gm_ip               = var.shared_vpc["gm_ip"]
  nios_ip             = var.shared_vpc["nios_ip"]

  infoblox_join_token = var.infoblox_join_token
  key_name       = var.shared_vpc["key_name"]
  tags                = var.tags
}

##############################################################################
# Spoke VPCs (map-driven)
##############################################################################
module "spoke_vpc_eu" {
  providers = { aws = aws }
  source         = "./modules/spoke-vpc"
  vpc_name       = var.spokes["eu_central_1"].name
  vpc_cidr       = var.spokes["eu_central_1"].cidr
  subnet_cidr    = var.spokes["eu_central_1"].subnet
  az             = var.spokes["eu_central_1"].az
  private_ip     = var.spokes["eu_central_1"].private_ip
  instance_name  = var.spokes["eu_central_1"].instance
  key_name       = var.spokes["eu_central_1"].key_name
  tags           = var.tags
}

module "spoke_vpc_us" {
  providers = { aws = aws.us-east-1 }
  source         = "./modules/spoke-vpc"
  vpc_name       = var.spokes["us_east_1"].name
  vpc_cidr       = var.spokes["us_east_1"].cidr
  subnet_cidr    = var.spokes["us_east_1"].subnet
  az             = var.spokes["us_east_1"].az
  private_ip     = var.spokes["us_east_1"].private_ip
  instance_name  = var.spokes["us_east_1"].instance
  key_name       = var.spokes["eu_central_1"].key_name
  tags           = var.tags
}

##############################################################################
# CloudWAN Core Network
##############################################################################
module "cloudwan" {
  providers = {
    aws           = aws
    aws.us-east-1 = aws.us-east-1
  }

  source = "./modules/cloudwan"

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

##############################################################################
# Wait for CloudWAN to settle
##############################################################################
resource "time_sleep" "wait_for_core_network" {
  depends_on      = [module.cloudwan]
  create_duration = "120s"
}

##############################################################################
# Optimized EU-side Routes
##############################################################################
resource "aws_route" "eu_routes" {
  for_each = {
    eu_to_us            = { rt = module.spoke_vpc_eu.route_table_id, dest = module.spoke_vpc_us.vpc_cidr }
    eu_to_shared        = { rt = module.spoke_vpc_eu.route_table_id, dest = module.shared_vpc.vpc_cidr }
    shared_to_spoke_eu  = { rt = module.shared_vpc.route_table_id,   dest = module.spoke_vpc_eu.vpc_cidr }
    shared_to_spoke_us  = { rt = module.shared_vpc.route_table_id,   dest = module.spoke_vpc_us.vpc_cidr }
    shared_to_connect   = { rt = module.shared_vpc.route_table_id,   dest = "10.60.0.0/16" }
  }

  depends_on             = [time_sleep.wait_for_core_network]
  route_table_id         = each.value.rt
  destination_cidr_block = each.value.dest
  core_network_arn       = module.cloudwan.core_network_arn
}

##############################################################################
# Optimized US-side Routes
##############################################################################
resource "aws_route" "us_routes" {
  provider = aws.us-east-1

  for_each = {
    us_to_eu      = { rt = module.spoke_vpc_us.route_table_id, dest = module.spoke_vpc_eu.vpc_cidr }
    us_to_shared  = { rt = module.spoke_vpc_us.route_table_id, dest = module.shared_vpc.vpc_cidr }
  }

  depends_on             = [time_sleep.wait_for_core_network]
  route_table_id         = each.value.rt
  destination_cidr_block = each.value.dest
  core_network_arn       = module.cloudwan.core_network_arn
}
