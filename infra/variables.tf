variable "project_id" {
  description = "ID du projet Scaleway dans lequel créer les ressources."
  type        = string
}

variable "region" {
  description = "Région Scaleway (fr-par = Paris)."
  type        = string
  default     = "fr-par"
}

variable "zone" {
  description = "Zone de disponibilité."
  type        = string
  default     = "fr-par-1"
}

variable "name_prefix" {
  description = "Préfixe des noms de ressources."
  type        = string
  default     = "tp-pipeline"
}

variable "bucket_name" {
  description = "Nom du bucket S3. Doit être unique au monde (ex. tp-pipeline-julio-2026)."
  type        = string
}

variable "db_password" {
  description = "Mot de passe de l'administrateur PostgreSQL (à passer via TF_VAR_db_password)."
  type        = string
  sensitive   = true

  validation {
    condition     = length(var.db_password) >= 12
    error_message = "Le mot de passe doit faire au moins 12 caractères."
  }
}

variable "k8s_node_type" {
  description = "Type de machine des noeuds Kubernetes."
  type        = string
  default     = "DEV1-M"
}

variable "k8s_node_count" {
  description = "Nombre de noeuds Kubernetes."
  type        = number
  default     = 1
}

variable "db_node_type" {
  description = "Type d'instance PostgreSQL managée."
  type        = string
  default     = "DB-DEV-S"
}
