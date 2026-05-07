from pathlib import Path
import os

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.environ.get('SECRET_KEY', 'django-insecure-dev-key-change-in-production')

DEBUG = os.environ.get('DEBUG', 'True') == 'True'

ALLOWED_HOSTS = os.environ.get('ALLOWED_HOSTS', 'localhost 127.0.0.1').split()

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'drf_spectacular',
    'profiles',
    'plans',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'meal_planner_service.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'meal_planner_service.wsgi.application'

if os.environ.get('DB_HOST'):
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': os.environ.get('DB_NAME', 'planner_db'),
            'USER': os.environ.get('DB_USER', 'planner_user'),
            'PASSWORD': os.environ.get('DB_PASSWORD', 'planner_pass'),
            'HOST': os.environ.get('DB_HOST'),
            'PORT': os.environ.get('DB_PORT', '5432'),
        }
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

REST_FRAMEWORK = {
    'DEFAULT_RENDERER_CLASSES': ['rest_framework.renderers.JSONRenderer'],
    'DEFAULT_PARSER_CLASSES': ['rest_framework.parsers.JSONParser'],
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
}

SPECTACULAR_SETTINGS = {
    'TITLE': 'Meal Planner Service API',
    'DESCRIPTION': 'Микросервис генерации персональных рационов питания',
    'VERSION': '1.0.0',
}

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

STATIC_URL = 'static/'
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

CELERY_BROKER_URL = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')
CELERY_RESULT_BACKEND = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = TIME_ZONE

_redis_url = os.environ.get('REDIS_URL', '').strip()
if _redis_url:
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.redis.RedisCache',
            'LOCATION': _redis_url,
            'OPTIONS': {},
            'KEY_PREFIX': 'meal_planner',
        },
    }
else:
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        },
    }

AI_SUGGESTIONS_CACHE_TTL = int(os.environ.get('AI_SUGGESTIONS_CACHE_TTL', '3600'))

# Mistral: ключ из https://console.mistral.ai
MISTRAL_API_KEY = os.environ.get('MISTRAL_API_KEY', '')
MISTRAL_API_BASE = os.environ.get('MISTRAL_API_BASE', 'https://api.mistral.ai/v1')
MISTRAL_MODEL = os.environ.get('MISTRAL_MODEL', 'mistral-small-latest')
MISTRAL_REQUEST_TIMEOUT = float(os.environ.get('MISTRAL_REQUEST_TIMEOUT', '180'))
# Опционально: если из Docker до api.mistral.ai рвётся соединение — прокси (или HTTPS_PROXY).
MISTRAL_HTTPS_PROXY = (
    os.environ.get('MISTRAL_HTTPS_PROXY') or os.environ.get('HTTPS_PROXY') or ''
).strip() or None

RECIPES_SERVICE_URL = os.environ.get('RECIPES_SERVICE_URL', '')
AUTH_SERVICE_URL = os.environ.get('AUTH_SERVICE_URL', '')
EXTERNAL_SERVICE_TIMEOUT = float(os.environ.get('EXTERNAL_SERVICE_TIMEOUT', '10'))
# Режим без recipes-service: MOCK_RECIPES=1 — взять встроенный список рецептов (только для разработки).
MOCK_RECIPES = os.environ.get('MOCK_RECIPES', '').lower() in ('1', 'true', 'yes')
