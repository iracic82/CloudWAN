##############################################################################
# Account ID for ARNs
##############################################################################
data "aws_caller_identity" "me" {}

##############################################################################
# Global Network (parent container for Cloud WAN)
##############################################################################
resource "aws_networkmanager_global_network" "global" {
  description = "Infoblox Cloud WAN Global"
  tags        = var.tags
}

##############################################################################
# Core Network
##############################################################################
resource "aws_networkmanager_core_network" "core" {
  global_network_id   = aws_networkmanager_global_network.global.id
  description         = "Core network with dns-shared & vpc-comm"

  # seeds an initial LIVE policy so attachments won't fail
  create_base_policy  = true
  base_policy_regions = ["eu-central-1", "us-east-1"]

  tags = var.tags
}

##############################################################################
# Core Network Policy
##############################################################################
resource "aws_networkmanager_core_network_policy_attachment" "policy" {
  core_network_id = aws_networkmanager_core_network.core.id

  policy_document = jsonencode({
    version = "2021.12"
    "core-network-configuration" = {
      "vpn-ecmp-support"                   = false
      "dns-support"                        = true
      "security-group-referencing-support" = false

      "inside-cidr-blocks" = [
        "10.30.0.0/16", # Shared VPC
        "10.10.0.0/16", # Spoke EU
        "10.20.0.0/16"  # Spoke US
      ]

      "asn-ranges" = ["64512-65534"]

      "edge-locations" = [
        {
          "location"             = "eu-central-1"
          "asn"                  = 64513
          "inside-cidr-blocks"   = ["10.30.0.0/16", "10.10.0.0/16"]
        },
        {
          "location"             = "us-east-1"
          "asn"                  = 64512
          "inside-cidr-blocks"   = ["10.20.0.0/16"]
        }
      ]
    }

    segments = [
      {
        name        = "dnsShared"
        description = "Shared DNS / NIOS-X"
        "require-attachment-acceptance" = false
      },
      {
        name        = "vpcComm"
        description = "Spoke VPCs"
        "require-attachment-acceptance" = false
      }
    ]

    "segment-actions" = [
      {
        "action"     = "share"
        "mode"       = "attachment-route"
        "segment"    = "vpcComm"
        "share-with" = ["dnsShared"]
      },
      {
        "action"     = "share"
        "mode"       = "attachment-route"
        "segment"    = "dnsShared"
        "share-with" = ["vpcComm"]
      }
    ]

    "attachment-policies" = [
      {
        "rule-number" = 100
        description   = "Map Shared VPC to dnsShared"
        conditions    = [
          { type = "resource-id", operator = "equals", value = var.vpcs["shared"] }
        ]
        action = {
          "association-method" = "constant"
          segment              = "dnsShared"
        }
      },
      {
        "rule-number" = 200
        description   = "Map EU spoke to vpcComm"
        conditions    = [
          { type = "resource-id", operator = "equals", value = var.vpcs["eu_central_1"] }
        ]
        action = {
          "association-method" = "constant"
          segment              = "vpcComm"
        }
      },
      {
        "rule-number" = 300
        description   = "Map US spoke to vpcComm"
        conditions    = [
          { type = "resource-id", operator = "equals", value = var.vpcs["us_east_1"] }
        ]
        action = {
          "association-method" = "constant"
          segment              = "vpcComm"
        }
      },
      {
        "rule-number" = 400
        description   = "Map Connect peers (NIOS-X) to dnsShared"
        conditions    = [
          { type = "attachment-type", operator = "equals", value = "connect" }
        ]
        action = {
          "association-method" = "constant"
          segment              = "dnsShared"
        }
      }
    ]
  })
}

##############################################################################
# VPC Attachments
##############################################################################
resource "aws_networkmanager_vpc_attachment" "shared" {
  depends_on      = [aws_networkmanager_core_network_policy_attachment.policy]
  core_network_id = aws_networkmanager_core_network.core.id
  vpc_arn         = "arn:aws:ec2:eu-central-1:${data.aws_caller_identity.me.account_id}:vpc/${var.vpcs["shared"]}"
  subnet_arns     = var.subnet_arns_map["shared"]
  tags            = var.tags
}

resource "aws_networkmanager_vpc_attachment" "eu" {
  depends_on      = [aws_networkmanager_core_network_policy_attachment.policy]
  core_network_id = aws_networkmanager_core_network.core.id
  vpc_arn         = "arn:aws:ec2:eu-central-1:${data.aws_caller_identity.me.account_id}:vpc/${var.vpcs["eu_central_1"]}"
  subnet_arns     = var.subnet_arns_map["eu_central_1"]
  tags            = var.tags
}

resource "aws_networkmanager_vpc_attachment" "us" {
  provider        = aws.us-east-1
  depends_on      = [aws_networkmanager_core_network_policy_attachment.policy]
  core_network_id = aws_networkmanager_core_network.core.id
  vpc_arn         = "arn:aws:ec2:us-east-1:${data.aws_caller_identity.me.account_id}:vpc/${var.vpcs["us_east_1"]}"
  subnet_arns     = var.subnet_arns_map["us_east_1"]
  tags            = var.tags
}

##############################################################################
# Connect Attachment + Peers
##############################################################################
resource "aws_networkmanager_connect_attachment" "shared_connect" {
  core_network_id         = aws_networkmanager_core_network.core.id
  transport_attachment_id = aws_networkmanager_vpc_attachment.shared.id
  edge_location           = "eu-central-1"

  options {
    protocol = "NO_ENCAP"
  }

  tags = merge(var.tags, { Name = "shared-vpc-connect" })
}

resource "aws_networkmanager_connect_peer" "shared_peer_1" {
  connect_attachment_id = aws_networkmanager_connect_attachment.shared_connect.id

  bgp_options {
    peer_asn = 65001
  }

  peer_address = "10.30.1.5" # First NIOS-X
  subnet_arn   = var.subnet_arns_map["shared"][0]
  tags         = merge(var.tags, { Name = "shared-vpc-peer-1" })
}

resource "aws_networkmanager_connect_peer" "shared_peer_2" {
  connect_attachment_id = aws_networkmanager_connect_attachment.shared_connect.id

  bgp_options {
    peer_asn = 65002
  }

  peer_address = "10.30.1.6" # Second NIOS-X
  subnet_arn   = var.subnet_arns_map["shared"][0]
  tags         = merge(var.tags, { Name = "shared-vpc-peer-2" })
}
