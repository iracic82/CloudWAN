terraform {
  required_providers {
    bloxone = {
      source  = "infobloxopen/bloxone"
      version = ">= 1.5.0"
    }
  }
}

provider "bloxone" {
  csp_url = "https://csp.infoblox.com"
  api_key = var.ddi_api_key

  default_tags = {
    managed_by = "terraform"
    project    = "infoblox-cloudwan-lab"
  }
}
