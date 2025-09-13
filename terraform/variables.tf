variable "shared_vpc" {
  description = "Shared VPC config (NIOS-X + GM)"
  type = object({
    name    = string
    cidr    = string
    subnet  = string
    az      = string
    gm_ip   = string
    key_name = string
    nios_ip = string
  })
}

variable "spokes" {
  description = "Map of spoke VPCs"
  type = map(object({
    name       = string
    region     = string
    cidr       = string
    subnet     = string
    az         = string
    private_ip = string
    instance   = string
    key_name = string
  }))
}

variable "infoblox_join_token" {
  description = "Join token for Infoblox NIOS-X"
  type        = string
}

variable "demo_key_name" {
  description = "Key pair name for EC2 instances"
  type        = string
  default     = "demo-key"
}

variable "tags" {
  description = "Common tags for all resources"
  type        = map(string)
  default = {
    ResourceOwner = "iracic@infoblox.com"
  }
}
