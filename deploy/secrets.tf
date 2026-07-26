resource "kubernetes_secret" "app_secrets" {
  metadata {
    name      = "meal-planner-secrets"
    namespace = kubernetes_namespace.meal_planner.metadata[0].name
  }

  data = {
    SECRET_KEY      = var.secret_key
    DB_PASSWORD     = var.db_password
    MISTRAL_API_KEY = var.mistral_api_key
  }

  type = "Opaque"
}
