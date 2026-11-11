# Ces sorties correspondent aux variables d'environnement lues par la pipeline.

output "s3_endpoint_url" {
  description = "Valeur de S3_ENDPOINT_URL."
  value       = "https://s3.${var.region}.scw.cloud"
}

output "s3_bucket" {
  description = "Valeur de S3_BUCKET."
  value       = scaleway_object_bucket.transactions.name
}

output "s3_access_key" {
  description = "Valeur de S3_ACCESS_KEY."
  value       = scaleway_iam_api_key.pipeline.access_key
}

output "s3_secret_key" {
  description = "Valeur de S3_SECRET_KEY."
  value       = scaleway_iam_api_key.pipeline.secret_key
  sensitive   = true
}

output "database_url" {
  description = "Valeur de DATABASE_URL (adresse privée, accessible depuis le cluster)."
  value = format(
    "postgresql://%s:%s@%s:%d/%s",
    scaleway_rdb_instance.main.user_name,
    urlencode(var.db_password),
    scaleway_rdb_instance.main.private_network[0].ip,
    scaleway_rdb_instance.main.private_network[0].port,
    scaleway_rdb_database.pipeline.name,
  )
  sensitive = true
}

output "kubeconfig" {
  description = "Fichier kubeconfig pour se connecter au cluster."
  value       = scaleway_k8s_cluster.main.kubeconfig[0].config_file
  sensitive   = true
}
