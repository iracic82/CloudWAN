variable "infoblox_join_token" {
  description = "Join token for Infoblox NIOS-X"
  type        = string
}

variable "key_name" {
  description = "EC2 key pair name for the Grid Master"
  type        = string
}

variable "vpc_name" {
  description = "EC2 key pair name for the Grid Master"
  type        = string
}
variable "vpc_cidr" {
  description = "EC2 key pair name for the Grid Master"
  type        = string
}
variable "subnet_cidr" {
  description = "EC2 key pair name for the Grid Master"
  type        = string
}
variable "az" {
  description = "EC2 key pair name for the Grid Master"
  type        = string
}
variable "gm_ip"  {
  description = "EC2 key pair name for the Grid Master"
  type        = string
}
variable "nios_ip"  {
  description = "EC2 key pair name for the Grid Master"
  type        = string
}



variable "tags" {
  type = map(string)
  default = {
    ResourceOwner = "iracic@infoblox.com"
  }
}

# Allow override if needed
variable "infoblox_ami_id" {
  type    = string
  default = "ami-08659b5070b66249d"
}
