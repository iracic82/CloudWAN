variable "vpc_name" {
  description = "Name for the spoke VPC"
  type        = string
}

variable "vpc_cidr" {
  description = "CIDR for the spoke VPC"
  type        = string
}

variable "subnet_cidr" {
  description = "CIDR for the public subnet"
  type        = string
}

variable "az" {
  description = "Availability Zone"
  type        = string
}

variable "private_ip" {
  description = "Static private IP for the EC2 instance"
  type        = string
}

variable "instance_name" {
  description = "Name for the EC2 instance"
  type        = string
}

variable "key_name" {
  description = "EC2 key pair name"
  type        = string
}
variable "tags" {
  type = map(string)
  default = {
    ResourceOwner = "iracic@infoblox.com"
  }
}
