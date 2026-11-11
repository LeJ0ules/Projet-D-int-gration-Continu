terraform {
  required_version = ">= 1.6.0"

  required_providers {
    scaleway = {
      source  = "scaleway/scaleway"
      version = "~> 2.91"
    }
  }
}

# Identifiants : variables d'environnement SCW_ACCESS_KEY et SCW_SECRET_KEY
# (jamais écrites dans le code).
provider "scaleway" {
  region     = var.region
  zone       = var.zone
  project_id = var.project_id
}
