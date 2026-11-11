# Bucket S3 (stockage objet Scaleway, compatible S3) : reçoit les CSV.
resource "scaleway_object_bucket" "transactions" {
  name   = var.bucket_name
  region = var.region

  tags = {
    project = var.name_prefix
  }
}

# Identité dédiée à la pipeline : on évite d'utiliser les clés personnelles du compte.
resource "scaleway_iam_application" "pipeline" {
  name        = "${var.name_prefix}-app"
  description = "Identité utilisée par la pipeline pour accéder au stockage objet."
}

resource "scaleway_iam_policy" "pipeline_storage" {
  name           = "${var.name_prefix}-storage"
  application_id = scaleway_iam_application.pipeline.id

  rule {
    project_ids          = [var.project_id]
    permission_set_names = ["ObjectStorageFullAccess"]
  }
}

resource "scaleway_iam_api_key" "pipeline" {
  application_id     = scaleway_iam_application.pipeline.id
  description        = "Clé d'accès S3 de la pipeline"
  default_project_id = var.project_id
}
