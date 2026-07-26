resource "kubernetes_namespace" "meal_planner" {
  metadata {
    name = var.namespace
  }
}
