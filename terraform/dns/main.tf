terraform {
  required_providers {
    bloxone = {
      source  = "infobloxopen/bloxone"
      version = ">= 1.5.0"
    }
    aws = {
      source  = "hashicorp/aws"
      version = ">= 5.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
}

provider "bloxone" {
  csp_url = "https://csp.infoblox.com"
  api_key = var.ddi_api_key

  default_tags = {
    managed_by = "terraform"
    site       = "Site A"
  }
}

# -----------------------------
# Variables
# -----------------------------
variable "ddi_api_key" {}
variable "aws_region" {
  default = "eu-west-2"
}
variable "availability_zone" {
  default = "eu-west-2a"
}
variable "project_name" {
  default = "infoblox-aws-integration"
}

# -----------------------------
# Lookup Realm and Federated Block
# -----------------------------
data "bloxone_federation_federated_realms" "acme" {
  filters = {
    name = "ACME Corporation"
  }
}

data "bloxone_federation_federated_blocks" "aws_block" {
  filters = {
    name = "AWS"
  }
}
