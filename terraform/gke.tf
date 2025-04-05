variable "gke_username" {
  default     = ""
  description = "gke username"
}

variable "gke_password" {
  default     = ""
  description = "gke password"
}

variable "gke_num_nodes" {
  default     = 1
  description = "number of gke nodes"
}

# GKE cluster
resource "google_container_cluster" "primary" {
  name     = "${var.project_id}-gke"
  location = var.region

  # We can't create a cluster with no node pool defined, but we want to only use
  # separately managed node pools. So we create the smallest possible default
  # node pool and immediately delete it.
  remove_default_node_pool = true
  initial_node_count       = 2

  network    = google_compute_network.vpc.name
  subnetwork = google_compute_subnetwork.subnet.name
  deletion_protection = false
}

# Separately Managed Node Pool
resource "google_container_node_pool" "primary_nodes" {
  name       = "${google_container_cluster.primary.name}-np"
  location   = var.region
  cluster    = google_container_cluster.primary.name
  node_count = var.gke_num_nodes

  node_config {
    oauth_scopes = [
      "https://www.googleapis.com/auth/logging.write",
      "https://www.googleapis.com/auth/monitoring",
    ]
   #disk_size_gb = 10

    labels = {
      env = var.project_id
    }

    # preemptible  = true
    machine_type = "n1-standard-2"
    tags         = ["gke-node", "${var.project_id}-gke"]
    metadata = {
      disable-legacy-endpoints = false
    }
  }
}


resource "null_resource" "configure-local-kubectl" {
  provisioner "local-exec" {
    command = "gcloud container clusters get-credentials ${google_container_cluster.primary.name} --region ${var.region} --project ${var.project_id}"
  }
  depends_on = [ google_container_cluster.primary ,  google_container_node_pool.primary_nodes]
}

resource "null_resource" "test-connetction-cluster" {
  provisioner "local-exec" {
    command = "kubectl get pods"
  }
  depends_on = [null_resource.configure-local-kubectl ]
}

resource "helm_release" "airflow" {

  depends_on = [ null_resource.configure-local-kubectl]
  name       = "airflow"
  repository = "https://airflow-helm.github.io/charts"
  chart      = "airflow"
  version    = "8.5.0"
  namespace  = "default"

  values = [
    "${file("values.yaml")}"
  ]
  
}

# Service Account for the Spark Job
resource "google_service_account" "spark_sa" {
  account_id   = "spark-sa"
  display_name = "Service Account for Spark jobs"
}

# IAM bindings
resource "google_project_iam_member" "spark_sa_permissions" {
  role   = "roles/container.admin"
  member = "serviceAccount:${google_service_account.spark_sa.email}"
  project = "${var.project_id}"
}


resource "null_resource" "helm_spark" {
  depends_on = [null_resource.configure-local-kubectl, google_container_cluster.primary,  google_container_node_pool.primary_nodes]

  provisioner "local-exec" {
    command = <<EOT
    gcloud container clusters get-credentials ${google_container_cluster.primary.name} --region ${var.region}
    helm repo add bitnami https://charts.bitnami.com/bitnami
    helm install spark bitnami/spark --set master.webPort=8080
    EOT
  }
}