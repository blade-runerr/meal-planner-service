variable "namespace" {
  description = "Kubernetes namespace for the app"
  type        = string
  default     = "meal-planner"
}

variable "web_node_port" {
  description = "Fixed NodePort for the web app"
  type        = number
  default     = 30080
}

variable "grafana_node_port" {
  description = "Fixed NodePort for Grafana"
  type        = number
  default     = 30300
}

variable "postgres_storage_size" {
  description = "Size of the PostgreSQL PVC"
  type        = string
  default     = "2Gi"
}

variable "kube_prometheus_stack_version" {
  description = "Pinned kube-prometheus-stack chart version"
  type        = string
  default     = "87.19.1"
}

variable "secret_key" {
  description = "Django SECRET_KEY"
  type        = string
  sensitive   = true
}

variable "db_password" {
  description = "PostgreSQL password (shared by the app and the postgres StatefulSet)"
  type        = string
  sensitive   = true
}

variable "mistral_api_key" {
  description = "Real Mistral AI API key (from console.mistral.ai)"
  type        = string
  sensitive   = true
  default     = ""
}

variable "grafana_admin_password" {
  description = "Grafana admin password (demo-only shortcut, not a prod practice)"
  type        = string
  sensitive   = true
}
