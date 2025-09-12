variable "aws_region" {}
variable "vpc_name" {}
variable "aws_vpc_cidr" {}
variable "aws_subnet_cidr" {}
variable "az" {}
variable "private_ip" {}
variable "instance_name" {}
variable "key_name" {}
variable "tags" {
  type = map(string)
  default = {
    ResourceOwner = "iracic@infoblox.com"
  }
}
