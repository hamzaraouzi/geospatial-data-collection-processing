resource "google_storage_bucket" "storage" {
  name          = "storage-${var.project_id}"
  location      = var.region
  force_destroy = true
  project = "${var.project_id}"

  public_access_prevention = "enforced"
}