# Shared VPC config
shared_vpc = {
  name    = "shared-vpc"
  cidr    = "10.30.0.0/16"
  subnet  = "10.30.1.0/24"
  az      = "eu-central-1a"
  gm_ip   = "10.30.1.5"
  nios_ip = "10.30.1.6"
  key_name = "shared"
}

# Spoke VPCs
spokes = {
  eu_central_1 = {
    name       = "spoke-vpc-eu"
    region     = "eu-central-1"
    cidr       = "10.10.0.0/16"
    subnet     = "10.10.1.0/24"
    az         = "eu-central-1a"
    private_ip = "10.10.1.10"
    instance   = "spoke-ec2-eu"
    key_name = "spoke-eu"
  }
  us_east_1 = {
    name       = "spoke-vpc-us"
    region     = "us-east-1"
    cidr       = "10.20.0.0/16"
    subnet     = "10.20.1.0/24"
    az         = "us-east-1a"
    private_ip = "10.20.1.10"
    instance   = "spoke-ec2-us"
    key_name = "spoke-us"
  }
}

