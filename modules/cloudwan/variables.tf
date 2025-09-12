# Inputs: map of VPC IDs and map of lists of subnet ARNs
variable "vpcs" {
  type = map(string)
}
variable "subnet_arns_map" {
  type = map(list(string))
}
variable "tags" {
  type    = map(string)
  default = { ResourceOwner = "iracic@infoblox.com" }
}