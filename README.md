# 🌐 CloudWAN Terraform Lab

This repository contains Infrastructure-as-Code (IaC) to **deploy a complete AWS Cloud WAN lab environment**.  
It is designed to demonstrate how to interconnect multiple VPCs (shared services and spoke VPCs) across AWS regions using **AWS Cloud WAN**, with route control, BGP peering, and Infoblox NIOS-X integration in the Shared VPC acting as DNS.  
This is a scalable lab framework, and the Terraform module structure can be applied to your own CI/CD pipeline.

---

## 🚀 What This Code Does

- **Global & Core Network**
  - Creates a `Global Network` and a `Core Network` in AWS Network Manager
  - Seeds a **base policy** across `eu-central-1` and `us-east-1`
  - Attaches a **full policy** with segments (`dnsShared`, `vpcComm`) and segment-sharing rules

- **VPCs**
  - Deploys:
    - A **Shared Services VPC** (10.30.0.0/16)  
      → Hosts Infoblox **NIOS-X Grid Master** with EIP for management, working as DNS  
    - A **Spoke VPC in EU** (CIDR configurable)  
    - A **Spoke VPC in US** (CIDR configurable)
  - Configures **subnets, IGWs, and security groups**

- **Attachments**
  - Creates Cloud WAN **VPC attachments** for Shared + Spokes
  - Creates a **Connect Attachment + Connect Peers** in Shared VPC
  - Peers EC2/Infoblox GM over **BGP (NO_ENCAP)**

- **Routing**
  - Demonstrates **manual propagation of Cloud WAN routes** into VPC route tables  
    (via `aws_route` resources, pointing to `core_network_arn`)

- **EC2 Instances**
  - Deploys EC2 in each spoke for connectivity testing (Linux with SSH)
  - Deploys Infoblox **NIOS-X GM** in Shared VPC (with join token + cloud-init)

---

## 🗂 Repository Structure

```
.
├── terraform/           # Core Terraform configs
│   ├── main.tf          # Root Terraform entrypoint
│   ├── providers.tf     # AWS provider definitions & aliases
│   ├── variables.tf     # Input variables
│   ├── outputs.tf       # Exported values (VPC IDs, SSH commands, etc.)
│   ├── terraform.tfvars # Input varibale values
├── modules/             # Terraform modules
│   ├── shared-vpc/      # Shared services VPC + Infoblox NIOS-X GM
│   ├── spoke-vpc/       # EU & US spoke VPCs
│   └── cloudwan/        # Cloud WAN core + policy + attachments
│
└── scripts/            # Helper scripts (e.g., Infoblox automation)
```

---

## 🔑 Usage

### 1. Clone the repo
```bash
git clone https://github.com/iracic82/CloudWAN.git
cd CloudWAN/terraform
```

### 2. Initialize Terraform
```bash
terraform init
```

### 3. Apply the configuration
```bash
terraform apply
```

This will provision:
- Cloud WAN core & policy
- Shared/Spoke VPCs with subnets + IGWs
- EC2 instances + Infoblox NIOS-X GM
- Cloud WAN VPC + Connect attachments
- BGP Connect Peers

---

## 🧪 Testing

- Use outputs for SSH access:
  ```bash
  ssh -i demo-key-XXXX.pem ec2-user@<public-ip>
  ```
- Ping between VPC EC2 instances across regions.
- Verify Cloud WAN segment routing via `aws ec2 describe-route-tables`.

---

## 📝 Notes

- Cloud WAN **does not automatically inject routes** into VPC route tables.  
  Routes are explicitly added using `aws_route` with `core_network_arn`.
- Infoblox NIOS-X GM requires a valid **join token** (set in `variables.tf`).
- Use `.gitignore` to avoid committing IDE files (`.idea/`) and Terraform state.

---

## 🧭 Roadmap

- In progress 

---


## 🔧 Optional: Route Monitor Lambda

By default, AWS Cloud WAN **does not automatically propagate routes into VPC route tables**.  
You can add a Lambda function to handle this dynamically based on **BGP peer state**.

### How it Works
- Subscribes to **CloudWAN Connect events** (`CONNECT_PEER_BGP_UP` / `DOWN`).
- Stores peer health in a **DynamoDB table** (`CloudWANPeerState`).
- If **any peer is UP** → ensures the route exists in the target VPC RT.
- If **all peers are DOWN** → removes the route.
- Publishes notifications via **SNS** (e.g. `route-monitor-alerts`).

### Example Architecture

CloudWAN (ConnectPeer) → EventBridge → Lambda → DynamoDB + EC2 RouteTable + SNS

### Example Use Case
In this lab:
- VPC RT = `rtb-xxxxxxxx`  
- Route managed = `192.168.0.0/16`  
- Core network = `core-network-xxxxxxxx`  
- SNS = `route-monitor-alerts`

When a Connect Peer goes **UP**, the Lambda adds the route.  
When all peers are **DOWN**, the Lambda deletes it and sends an alert.

### Lambda Source Code
The Python Lambda (with boto3) is in `/scripts/route_monitor_lambda.py`.  
You can deploy it with:
- IAM role (EC2 + DynamoDB + SNS permissions),
- EventBridge rule for `NetworkManager ConnectPeer` events,
- DynamoDB table `CloudWANPeerState`.

---

## 👨‍💻 Author

**Igor Racic**  
Technology Evangelist – AI-Driven Cloud Networking & Security 
