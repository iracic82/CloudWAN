variable "ddi_api_key" {
  description = "API key for Infoblox CSP"
  type        = string
  sensitive   = true
}

variable "app1_ip" {
  description = "IP address for app1.infolab.com"
  type        = string
  default     = "10.9.8.7"
}

variable "app2_ip" {
  description = "IP address for app2.infolab.com"
  type        = string
  default     = "10.3.4.5"
}

variable "zone_fqdn" {
  description = "DNS zone FQDN"
  type        = string
  default     = "infolab.com."
}
