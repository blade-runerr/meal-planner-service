# MEAL-PLANNER-SERVICE — Этап 1

Микросервис генерации персональных рационов питания. Часть проекта **Foodgram Microservices + AI Meal Planner**.

## Стек

- Python 3.11 / Django 4.2 / Django REST Framework
- PostgreSQL 16
- Redis 7
- Celery 5 (подготовлен, используется в этапе 2–3)
- Docker / docker-compose

## Архитектура этапа 1

Сервис принимает пользовательские настройки профиля (калорийность рациона). Идентификация пользователя осуществляется через заголовок `X-User-Id`, который выставляет auth-service или API Gateway.

## Эндпоинты

| Метод | URL | Описание |
|-------|-----|----------|
| `POST` | `/profiles/` | Создать / обновить профиль пользователя |
| `GET`  | `/profiles/me/` | Получить профиль текущего пользователя |

### Заголовки

| Заголовок | Обязателен | Описание |
|-----------|------------|----------|
| `X-User-Id` | да | ID пользователя из auth-service |

### Примеры запросов

**Создать профиль**
```bash
curl -X POST http://localhost:8002/profiles/ \
  -H "Content-Type: application/json" \
  -H "X-User-Id: 42" \
  -d '{"daily_calories": 2500}'
```

**Получить профиль**
```bash
curl http://localhost:8002/profiles/me/ \
  -H "X-User-Id: 42"
```

## Запуск через Docker

```bash
docker-compose up --build
```

Сервис будет доступен на `http://localhost:8002`.

Применение миграций происходит автоматически при старте контейнера.

## Запуск тестов

```bash
# Установить зависимости
pip install -r requirements.txt

# Запустить тесты (используется SQLite in-memory)
pytest profiles/tests.py -v
```

## Структура проекта

```
.
├── manage.py
├── meal_planner_service/
│   ├── settings.py
│   ├── urls.py
│   ├── wsgi.py
│   └── asgi.py
├── profiles/
│   ├── models.py        # UserProfile
│   ├── serializers.py
│   ├── views.py         # POST /profiles, GET /profiles/me
│   ├── urls.py
│   └── tests.py         # 4 unit-теста
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
└── pytest.ini
```

## Переменные окружения

| Переменная | По умолчанию | Описание |
|------------|--------------|----------|
| `SECRET_KEY` | `django-insecure-...` | Django secret key |
| `DEBUG` | `True` | Debug режим |
| `DB_NAME` | `planner_db` | Имя БД |
| `DB_USER` | `planner_user` | Пользователь БД |
| `DB_PASSWORD` | `planner_pass` | Пароль БД |
| `DB_HOST` | `localhost` | Хост БД |
| `DB_PORT` | `5432` | Порт БД |
| `REDIS_URL` | `redis://localhost:6379/0` | URL Redis |
