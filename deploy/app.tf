resource "kubernetes_deployment" "web" {
  metadata {
    name      = "meal-planner-web"
    namespace = kubernetes_namespace.meal_planner.metadata[0].name
    labels = {
      app = "meal-planner-web"
    }
  }

  spec {
    replicas = 1

    selector {
      match_labels = {
        app = "meal-planner-web"
      }
    }

    template {
      metadata {
        labels = {
          app = "meal-planner-web"
        }
      }

      spec {
        init_container {
          name              = "migrate"
          image             = "meal-planner-web:dev"
          image_pull_policy = "Never"
          command           = ["python", "manage.py", "migrate", "--noinput"]

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
        }

        container {
          name              = "web"
          image             = "meal-planner-web:dev"
          image_pull_policy = "Never"

          port {
            name           = "http"
            container_port = 8000
          }

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
              memory = "96Mi"
            }
            limits = {
              cpu    = "200m"
              memory = "180Mi"
            }
          }

          liveness_probe {
            http_get {
              path = "/healthz/"
              port = 8000
            }
            initial_delay_seconds = 10
            period_seconds         = 10
            timeout_seconds        = 3
            failure_threshold      = 3
          }

          readiness_probe {
            http_get {
              path = "/healthz/"
              port = 8000
            }
            initial_delay_seconds = 5
            period_seconds         = 5
          }
        }
      }
    }
  }
}

resource "kubernetes_service" "web" {
  metadata {
    name      = "meal-planner-web"
    namespace = kubernetes_namespace.meal_planner.metadata[0].name
    labels = {
      app = "meal-planner-web"
    }
  }

  spec {
    type = "NodePort"

    selector = {
      app = "meal-planner-web"
    }

    port {
      port        = 80
      target_port = "http"
      node_port   = var.web_node_port
    }
  }
}
