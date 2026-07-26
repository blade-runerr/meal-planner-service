output "web_url_hint" {
  value       = "http://<minikube-ip>:${var.web_node_port}  (run `minikube ip` on the VM to get <minikube-ip>)"
  description = "How to reach the app from inside the VM"
}

output "namespace" {
  value = kubernetes_namespace.meal_planner.metadata[0].name
}
