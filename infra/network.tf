# Réseau privé partagé : le cluster Kubernetes et la base de données y sont rattachés,
# la base n'a donc pas besoin d'être exposée sur Internet.
resource "scaleway_vpc_private_network" "main" {
  name = "${var.name_prefix}-network"
}
