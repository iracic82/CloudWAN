variable "infoblox_join_token" {
  description = "Join token for Infoblox NIOS-X"
  type        = string
}

variable "key_name" {
  description = "EC2 key pair name for the Grid Master"
  type        = string
}

variable "tags" {
  type = map(string)
  default = {
    ResourceOwner = "iracic@infoblox.com"
  }
}

