terraform {
  required_version = ">= 1.9.0"

  required_providers {
    opnsense = {
      source  = "browningluke/opnsense"
      version = "0.26.0"
    }
  }
}

provider "opnsense" {
  uri            = var.opnsense_uri
  allow_insecure = false
}
