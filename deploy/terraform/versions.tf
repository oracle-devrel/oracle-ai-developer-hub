terraform {
  required_providers {
    oci = {
      source                = "oracle/oci"
      version               = "~> 6.30"
      configuration_aliases = [oci.home]
    }
    local = {
      source  = "hashicorp/local"
      version = "~> 2"
      # https://registry.terraform.io/providers/hashicorp/local/
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3"
      # https://registry.terraform.io/providers/hashicorp/random/
    }
  }
}
