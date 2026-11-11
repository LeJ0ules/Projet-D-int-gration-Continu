# Dernière version de Kubernetes proposée par Scaleway.
data "scaleway_k8s_version" "latest" {
  name = "latest"
}

# Cluster Kubernetes managé (Kapsule).
resource "scaleway_k8s_cluster" "main" {
  name                        = "${var.name_prefix}-k8s"
  type                        = "kapsule"
  version                     = data.scaleway_k8s_version.latest.name
  cni                         = "cilium"
  private_network_id          = scaleway_vpc_private_network.main.id
  delete_additional_resources = true # supprime aussi volumes et load balancers au destroy
}

# Pool de noeuds (les machines qui font tourner nos pods).
resource "scaleway_k8s_pool" "default" {
  cluster_id = scaleway_k8s_cluster.main.id
  name       = "default"
  node_type  = var.k8s_node_type
  size       = var.k8s_node_count
}
