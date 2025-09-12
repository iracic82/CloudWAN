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

