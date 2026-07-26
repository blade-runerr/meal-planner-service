resource "kubernetes_deployment" "redis" {
  metadata {
    name      = "meal-planner-redis"
    namespace = kubernetes_namespace.meal_planner.metadata[0].name
    labels = {
      app = "meal-planner-redis"
    }
  }

  spec {
    replicas = 1

    selector {
      match_labels = {
        app = "meal-planner-redis"
      }
    }

    template {
      metadata {
        labels = {
          app = "meal-planner-redis"
        }
      }

      spec {
        container {
          name  = "redis"
          image = "redis:7-alpine"

          port {
            container_port = 6379
          }

          resources {
            requests = {
              cpu    = "20m"
              memory = "24Mi"
            }
            limits = {
              cpu    = "100m"
              memory = "48Mi"
            }
          }
        }
      }
    }
  }
}

resource "kubernetes_service" "redis" {
  metadata {
    name      = "meal-planner-redis"
    namespace = kubernetes_namespace.meal_planner.metadata[0].name
  }

  spec {
    selector = {
      app = "meal-planner-redis"
    }

    port {
      port        = 6379
      target_port = 6379
    }
  }
}
