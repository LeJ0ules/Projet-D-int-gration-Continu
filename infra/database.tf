# PostgreSQL managé : sauvegardes et mises à jour gérées par Scaleway.
resource "scaleway_rdb_instance" "main" {
  name          = "${var.name_prefix}-postgres"
  node_type     = var.db_node_type
  engine        = "PostgreSQL-16"
  is_ha_cluster = false
  user_name     = "pipeline_admin"
  password      = var.db_password

  private_network {
    pn_id       = scaleway_vpc_private_network.main.id
    enable_ipam = true
  }
}

resource "scaleway_rdb_database" "pipeline" {
  instance_id = scaleway_rdb_instance.main.id
  name        = "pipeline"
}
