resource "kubernetes_config_map" "app_config" {
  metadata {
    name      = "meal-planner-config"
    namespace = kubernetes_namespace.meal_planner.metadata[0].name
  }

  data = {
    DEBUG                    = "False"
    ALLOWED_HOSTS             = "*"
    DB_HOST                   = "meal-planner-postgres"
    DB_NAME                   = "planner_db"
    DB_USER                   = "planner_user"
    DB_PORT                   = "5432"
    REDIS_URL                 = "redis://meal-planner-redis:6379/0"
    AI_SUGGESTIONS_CACHE_TTL  = "3600"
    MOCK_RECIPES              = "1"
    EXTERNAL_SERVICE_TIMEOUT  = "10"
    MISTRAL_API_BASE          = "https://api.mistral.ai/v1"
    MISTRAL_MODEL             = "mistral-small-latest"
    MISTRAL_REQUEST_TIMEOUT   = "180"
  }
}
