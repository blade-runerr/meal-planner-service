# MEAL-PLANNER-SERVICE (этап 3)

Микросервис генерации персональных рационов с **Mistral API**, **Celery**, **Redis-кешем** и метрикой разнообразия. Часть проекта **Foodgram Microservices + AI Meal Planner** (роль: Кондрашов Роман). В ТЗ указан Perplexity — в реализации используется **Mistral** (Chat Completions, OpenAI-совместимый эндпоинт).

## Возможности этапа 3

- Клиент **Mistral** — `POST {MISTRAL_API_BASE}/chat/completions`, по умолчанию `https://api.mistral.ai/v1`, модель по умолчанию **`mistral-small-latest`** (переопределение: `MISTRAL_MODEL`).
- **Celery**-задача `generate_plan_suggestions`: асинхронная генерация AI-рекомендаций по уже сохранённому плану.
- **GET** `/plans/{id}/suggestions/` — ответ из **Redis** (ключ `meal_plan:<user_id>:<plan_id>`, TTL по умолчанию **1 час**).
- Поле **`diversity_score`** в **GET** `/plans/{id}/` и в ответе suggestions.
- **Postman**: `postman/MealPlanner_AI.postman_collection.json`.
- **33** unit/integration-теста (`pytest`).

## Алгоритмы (кратко)

### Сходство рецептов (`calculate_similarity`)

Коэффициент **Жаккара** по тегам и ингредиентам — используется при сборке недели в `plan_generator`.

### Разнообразие плана (`diversity_score`)

`0.5 * unique_ratio + 0.5 * edge_ratio` по `recipe_id` в сохранённом плане.

### AI-промпт

`plans/services/ai_prompts.py` — просьба вернуть один JSON: `summary`, `tips`, `possible_improvements`, `warnings`.

## Эндпоинты

| Метод | URL | Описание |
|-------|-----|----------|
| `POST` | `/profiles/` | Профиль |
| `GET` | `/profiles/me/` | Текущий профиль |
| `POST` | `/plans/generate/` | Неделя |
| `GET` | `/plans/{id}/` | План + `diversity_score` |
| `GET` | `/plans/{id}/suggestions/` | AI из кеша / Celery |
| `GET` | `/api/docs/` | Swagger |

Заголовок **`X-User-Id`** обязателен.

## Переменные окружения

Ключ: **https://console.mistral.ai**

| Переменная | По умолчанию | Описание |
|------------|--------------|----------|
| `MISTRAL_API_KEY` | — | API-ключ Mistral |
| `MISTRAL_API_BASE` | `https://api.mistral.ai/v1` | База API |
| `MISTRAL_MODEL` | `mistral-small-latest` | Модель (см. доку Mistral) |
| `REDIS_URL` | `redis://localhost:6379/0` | Celery + кеш |
| `AI_SUGGESTIONS_CACHE_TTL` | `3600` | TTL подсказок (сек) |
| `MOCK_RECIPES` | `0` | `1` — мок-рецепты |
| `RECIPES_SERVICE_URL` | — | URL recipes-service |

Ошибки в кеше: `mistral_not_configured`, `mistral_failed`. Старые ключи `grok_*`, `deepseek_*` в Redis по-прежнему обрабатываются в ответах.

## Запуск

```bash
export REDIS_URL=redis://localhost:6379/0
export MISTRAL_API_KEY=ваш_ключ
pip install -r requirements.txt
python manage.py migrate
celery -A meal_planner_service worker -l info
python manage.py runserver 0.0.0.0:8000
```

Docker: в `.env` укажите `MISTRAL_API_KEY`, затем `docker compose up --build`.

## Тесты

```bash
pytest -q
```

Вызовы Mistral в тестах **мокируются**.

## Структура

- `plans/clients/mistral.py` — HTTP-клиент Mistral
- `plans/tasks.py` — Celery + Redis
- `plans/services/ai_prompts.py` — промпты

## Ключи

Не коммитьте секреты. После смены провайдера сбросьте Redis или дождитесь протухания кеша ошибок (~10 мин).
