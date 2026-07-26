# Деплой meal-planner-service в Kubernetes

Terraform-конфигурация, разворачивающая сервис в minikube-кластере.

## Текущий статус

- ✅ **Namespace `meal-planner`**: web (Django/gunicorn), Celery worker, PostgreSQL
  (StatefulSet + PVC), Redis (кэш + брокер Celery) — задеплоено и проверено.
- ⏸️ **Мониторинг (Prometheus + Grafana)**: конфигурация готова (`monitoring.tf.disabled`),
  но временно отключена. Целевая VM (2 CPU / ~1.9GB RAM без swap) не потянула
  полный `kube-prometheus-stack` одновременно с приложением — load average
  улетал за 19 на 2 ядрах, API-сервер кластера периодически переставал отвечать.
  Приложение само по себе (`django-prometheus`) уже отдаёт метрики на `/metrics`,
  их можно собрать mониторингом позже — на увеличенной VM или отдельным лёгким
  Prometheus без полного стека операторов/сайдкаров. Чтобы включить: переименовать
  `monitoring.tf.disabled` обратно в `monitoring.tf` и прогнать двухфазный apply
  (см. ниже).

## Архитектура

- Метрики самого приложения (`django-prometheus`) уже собираются и доступны на
  `/metrics` — готовы к скрейпу любым Prometheus, когда мониторинг будет включён.
- Образ приложения собирается локально в Docker-демоне minikube
  (`eval $(minikube docker-env) && docker build ...`), без внешнего registry.
- Провайдеры Terraform (`kubernetes`, `helm`) ставятся через локальный
  filesystem mirror (`~/.terraform-mirror`), а не напрямую из
  `registry.terraform.io` — HashiCorp геоблокирует запросы из РФ
  (`x-amzn-waf-reason: geo`), поэтому бинарники провайдеров скачаны на другой
  машине и перенесены на сервер вручную.

## Запуск

Terraform выполняется **прямо на сервере с minikube** (не с локальной машины) —
провайдерам `kubernetes`/`helm` нужен прямой доступ к API кластера, который
изнутри VM работает без туннелей.

```bash
cd deploy
terraform init
cp terraform.tfvars.example terraform.tfvars   # заполнить реальные секреты
terraform apply
```

Если включаете мониторинг (`monitoring.tf.disabled` → `monitoring.tf`), нужен
двухфазный apply — `ServiceMonitor` это CRD, которую устанавливает сам
`helm_release`, применять всё одним прогоном нельзя:

```bash
terraform apply -target=kubernetes_namespace.meal_planner -target=helm_release.kube_prometheus_stack
terraform apply
```

## Доступ (с Windows через SSH-туннель)

```bash
ssh -i <key> -L 8080:$(minikube ip):30080 roma@89.169.188.41   # приложение
```

Приложение: `http://localhost:8080/api/docs/`

## Известные компромиссы (сделаны осознанно для демо, не для прода)

- `ALLOWED_HOSTS=*` — kubelet шлёт IP пода как Host-заголовок в пробах.
- `MOCK_RECIPES=1` — сосед-сервис `recipes-service` не задеплоен, используется
  встроенный мок.
- Ресурсы всех компонентов урезаны под реальные ограничения VM
  (2 CPU / ~1.9GB RAM без swap) — `gunicorn` работает в 1 воркер + 4 треда.
