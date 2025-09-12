provider "aws" {
  profile = "okta-sso"
  region = "eu-west-1"
}

provider "aws" {
  profile = "okta-sso"
  alias  = "us-east-1"
  region = "us-east-1"
}
