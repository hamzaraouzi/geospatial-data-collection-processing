terraform {
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "5.36.0"
    }

    kubernetes = {
      source  = "hashicorp/kubernetes"
      version = ">= 2.18.1"
    }

    helm = {
      source  = "hashicorp/helm"
      version = ">= 2.11.0"
    }
  }
    required_version = "~>1.5"
  }
