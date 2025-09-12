provider "aws" {
  profile = "okta-sso"
  region = "eu-central-1"
}

provider "aws" {
  profile = "okta-sso"
  alias  = "us-east-1"
  region = "us-east-1"
}
