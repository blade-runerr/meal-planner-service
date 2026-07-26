resource "kubernetes_service" "postgres" {
  metadata {
    name      = "meal-planner-postgres"
    namespace = kubernetes_namespace.meal_planner.metadata[0].name
  }

  spec {
    cluster_ip = "None"

    selector = {
      app = "meal-planner-postgres"
    }

    port {
      port        = 5432
      target_port = 5432
    }
  }
}

resource "kubernetes_stateful_set" "postgres" {
  metadata {
    name      = "meal-planner-postgres"
    namespace = kubernetes_namespace.meal_planner.metadata[0].name
    labels = {
      app = "meal-planner-postgres"
    }
  }

  spec {
    service_name = kubernetes_service.postgres.metadata[0].name
    replicas     = 1

    selector {
      match_labels = {
        app = "meal-planner-postgres"
      }
    }

    template {
      metadata {
        labels = {
          app = "meal-planner-postgres"
        }
      }

      spec {
        container {
          name  = "postgres"
          image = "postgres:16-alpine"

          port {
            container_port = 5432
          }

          env {
            name = "POSTGRES_DB"
            value_from {
              config_map_key_ref {
                name = kubernetes_config_map.app_config.metadata[0].name
                key  = "DB_NAME"
              }
            }
          }

          env {
            name = "POSTGRES_USER"
            value_from {
              config_map_key_ref {
                name = kubernetes_config_map.app_config.metadata[0].name
                key  = "DB_USER"
              }
            }
          }

          env {
            name = "POSTGRES_PASSWORD"
            value_from {
              secret_key_ref {
                name = kubernetes_secret.app_secrets.metadata[0].name
                key  = "DB_PASSWORD"
              }
            }
          }

          resources {
            requests = {
              cpu    = "50m"
              memory = "64Mi"
            }
            limits = {
              cpu    = "200m"
              memory = "128Mi"
            }
          }

          volume_mount {
            name       = "pgdata"
            mount_path = "/var/lib/postgresql/data"
            sub_path   = "pgdata"
          }
        }
      }
    }

    volume_claim_template {
      metadata {
        name = "pgdata"
      }
      spec {
        access_modes       = ["ReadWriteOnce"]
        storage_class_name = "standard"
        resources {
          requests = {
            storage = var.postgres_storage_size
          }
        }
      }
    }
  }
}
