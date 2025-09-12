terraform {
  required_providers {
    aws = {
      source = "hashicorp/aws"
      version = ">= 5.0"

      # Declare which aliases this module expects
      configuration_aliases = [
        aws.us-east-1,
      ]
    }
  }
}
