terraform {
  required_version = ">= 1.5"

  required_providers {
    verda = {
      source  = "verda-cloud/verda"
      version = "~> 1.1"
    }
  }
}

provider "verda" {
  client_id     = var.client_id
  client_secret = var.client_secret
  # API base: https://api.verda.com/v1 (OAuth2 client_credentials flow)
}
