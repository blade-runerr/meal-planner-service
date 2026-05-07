# Foodgram — Meal Planner Service

Микросервис **персональных рационов** в составе учебного проекта **Foodgram Microservices + AI Meal Planner** (команда из ТЗ: auth-service, recipes-service, meal-planner-service). Этот репозиторий — **только meal-planner**: Django + DRF, свой PostgreSQL, Redis, Celery, интеграция с **recipes-service** / моками и внешним **LLM (Mistral)** для текстовых рекомендаций.

Пользователь идентифицируется заголовком **`X-User-Id`** (его выставляет auth-service или API Gateway).

---

## Возможности (логика по этапам ТЗ)

### Профиль (этап 1)

- Сохранение целевой калорийности и строки исключённых ингредиентов.
- **POST** `/profiles/` — создать/обновить профиль.
- **GET** `/profiles/me/` — прочитать профиль.

### План на неделю (этап 2)

- **POST** `/plans/generate/` — построить **7 дней × 3 приёма пищи** из пула рецептов:
  - источник: **recipes-service** (`RECIPES_SERVICE_URL`) или **мок-список** (`MOCK_RECIPES=1`);
  - фильтр по исключениям из профиля;
  - учёт калорий: сумма за день в коридоре от цели (см. `plan_generator`);
  - **разнообразие**: коэффициент Жаккара по тегам и ингредиентам (`calculate_similarity`);
  - при «застревании» жадного выбора — перебор троек блюд для малого пула (`plan_generator`).
- Опционально: проверка пользователя в **auth-service** (`AUTH_SERVICE_URL`).
- План сохраняется в БД как **`MealPlan`** (JSON `payload`).

- **GET** `/plans/{id}/` — получить план владельца; в ответе также **`diversity_score`**.

### AI-подсказки и инфраструктура (этап 3)

- **GET** `/plans/{id}/suggestions/` — рекомендации по **уже сохранённому** плану:
  - при наличии записи в **Redis** (Django cache) — ответ из кеша;
  - иначе постановка Celery-задачи **`generate_plan_suggestions`** и ответ **202** до готовности (повторный GET).
- Внешний API: **Mistral** (`chat/completions`, см. `plans/clients/mistral.py`).
- **Swagger**: **GET** `/api/docs/`, схема `/api/schema/`.
- Коллекция **Postman**: `postman/MealPlanner_AI.postman_collection.json`.

**Важно:** нейросеть **не** генерирует сам недельный график блюд — только **комментирует** готовый план.

---

## Алгоритмы (кратко)

| Что | Где | Суть |
|-----|-----|------|
| **Сходство рецептов** | `plans/similarity.py` | Жаккар по множествам тегов и ингредиентов; нужен при подборе блюд в день. |
| **Генератор недели** | `plans/services/plan_generator.py` | Нормализация рецептов, фильтр исключений, жадный подбор + при необходимости полный перебор троек, проверка ккал/день. |
| **Разнообразие плана** | `plans/diversity.py` | Оценка 0..1 по уникальности `recipe_id` и смене блюд между соседними приёмами; в API и в промпте для LLM. |
| **Промпт для LLM** | `plans/services/ai_prompts.py` | Компактный JSON плана + цель ккал, `diversity_score`, исключения; ответ ожидается одним JSON с полями `summary`, `tips`, и т.д. |

---

## API

| Метод | URL | Описание |
|-------|-----|----------|
| `POST` | `/profiles/` | Создать/обновить профиль |
| `GET` | `/profiles/me/` | Текущий профиль |
| `POST` | `/plans/generate/` | Сгенерировать и сохранить недельный план |
| `GET` | `/plans/{id}/` | План + `diversity_score` |
| `GET` | `/plans/{id}/suggestions/` | AI-подсказки (кеш / Celery) |
| `GET` | `/api/docs/` | Swagger UI |
| `GET` | `/api/schema/` | OpenAPI-схема |

Во всех сценариях с «текущим пользователем» нужен заголовок **`X-User-Id`**.

---

## Стек

- Python 3.11+, Django 4.2, DRF, **drf-spectacular**
- PostgreSQL (в Docker), SQLite для простого локального запуска без `DB_HOST`
- **Redis** — брокер Celery и кеш ответов LLM
- **Celery 5**
- **httpx** — HTTP-клиент к Mistral
- **pytest**, **pytest-django**

---

## Переменные окружения

См. **`.env.example`**. Основное:

| Переменная | По умолчанию / примечание |
|------------|---------------------------|
| `SECRET_KEY`, `DEBUG`, `ALLOWED_HOSTS` | Как в Django |
| `DB_*` | PostgreSQL; без `DB_HOST` — SQLite в каталоге проекта |
| `REDIS_URL` | Celery и `CACHES` (если задан — Redis, иначе locmem) |
| `MOCK_RECIPES` | `1` — встроенные рецепты без recipes-service |
| `RECIPES_SERVICE_URL` | Базовый URL recipes-service |
| `AUTH_SERVICE_URL` | Опционально: проверка пользователя перед генерацией |
| `EXTERNAL_SERVICE_TIMEOUT` | Таймаут HTTP к auth/recipes (сек) |
| `MISTRAL_API_KEY` | Ключ [console.mistral.ai](https://console.mistral.ai) |
| `MISTRAL_API_BASE`, `MISTRAL_MODEL` | Обычно не меняют |
| `MISTRAL_REQUEST_TIMEOUT` | Таймаут чтения ответа LLM (сек), по умолчанию `180` |
| `MISTRAL_HTTPS_PROXY` / `HTTPS_PROXY` | Прокси до Mistral (часто из Docker) |
| `AI_SUGGESTIONS_CACHE_TTL` | TTL кеша подсказок (сек), по умолчанию `3600` |

---

## Запуск

### Docker Compose

```bash
cp .env.example .env
# В .env: MISTRAL_API_KEY=... при необходимости MISTRAL_HTTPS_PROXY=...

docker compose up --build
```

Поднимаются: **planner-db** (Postgres), **planner-redis**, **planner-service** (Django на `:8000`), **planner-worker** (Celery). Миграции выполняются при старте web-контейнера.

### Локально (без Docker)

```bash
pip install -r requirements.txt
export REDIS_URL=redis://127.0.0.1:6379/0
# опционально: export MISTRAL_API_KEY=...
python manage.py migrate
# отдельный терминал:
celery -A meal_planner_service worker -l info
python manage.py runserver 0.0.0.0:8000
```

---

## Тесты

```bash
pytest -q
```

Используется `meal_planner_service.settings_test`: SQLite in-memory, cache locmem, Celery в **eager**-режиме; вызовы Mistral **мокируются**.

---

## Структура проекта

```
meal_planner_service/   # Django-проект: settings, urls, celery.py
profiles/               # Модель UserProfile, POST/GET профиля
plans/                  # MealPlan, генерация плана, suggestions
  clients/              # recipes, auth, mistral HTTP-клиенты
  services/             # plan_generator, ai_prompts, suggestions_cache
  tasks.py              # Celery: generate_plan_suggestions
  views.py              # generate, detail plan, suggestions
postman/                # Postman-коллекция
```

---

## Безопасность и типичные проблемы

- Не коммитьте **`.env`** и реальные API-ключи.
- Ошибки LLM кешируются ненадолго; при смене кода полезен **сброс Redis** или новый ключ кеша в `suggestions_cache.py`.
- **`mistral_failed` / `RemoteDisconnected` из Docker:** запросы к Mistral идут из **planner-worker**; при обрывах попробуйте **`MISTRAL_HTTPS_PROXY`** (см. `.env.example`) или запуск воркера на хосте, затем `docker compose build --no-cache`.
