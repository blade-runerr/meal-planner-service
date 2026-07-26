resource "kubernetes_deployment" "worker" {
  metadata {
    name      = "meal-planner-worker"
    namespace = kubernetes_namespace.meal_planner.metadata[0].name
    labels = {
      app = "meal-planner-worker"
    }
  }

  spec {
    replicas = 1

    selector {
      match_labels = {
        app = "meal-planner-worker"
      }
    }

    template {
      metadata {
        labels = {
          app = "meal-planner-worker"
        }
      }

      spec {
        container {
          name              = "worker"
          image             = "meal-planner-web:dev"
          image_pull_policy = "Never"
          command           = ["celery", "-A", "meal_planner_service", "worker", "-l", "info", "--concurrency=1"]

          env_from {
            config_map_ref {
              name = kubernetes_config_map.app_config.metadata[0].name
            }
          }
          env_from {
            secret_ref {
              name = kubernetes_secret.app_secrets.metadata[0].name
            }
          }

          resources {
            requests = {
              cpu    = "50m"
              memory = "64Mi"
            }
            limits = {
              cpu    = "150m"
              memory = "128Mi"
            }
          }
        }
      }
    }
  }

  depends_on = [kubernetes_deployment.web]
}
