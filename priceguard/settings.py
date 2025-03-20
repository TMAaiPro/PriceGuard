"""
Django settings for priceguard project.
"""

import os
from pathlib import Path
import environ
from datetime import timedelta

# Initialiser environ
env = environ.Env(
    # set casting, default value
    DEBUG=(bool, False),
    ALLOWED_HOSTS=(list, []),
)

# Build paths inside the project like this: BASE_DIR / 'subdir'
BASE_DIR = Path(__file__).resolve().parent.parent

# Take environment variables from .env file
environ.Env.read_env(os.path.join(BASE_DIR, '.env'))

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = env('SECRET_KEY', default='django-insecure-change-this-in-production')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = env('DEBUG')

ALLOWED_HOSTS = env('ALLOWED_HOSTS')

# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    
    # Third party apps
    'rest_framework',
    'corsheaders',
    'django_filters',
    'drf_spectacular',
    'django_celery_beat',
    'django_celery_results',
    
    # Local apps
    'core',
    'users',
    'products',
    'alerts',
    'analytics',
    'monitoring',
    'notifications',
    'scraper',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'priceguard.urls'

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

WSGI_APPLICATION = 'priceguard.wsgi.application'

# Database
DATABASES = {
    'default': env.db('DATABASE_URL', default='postgres://postgres:postgres@localhost:5432/priceguard')
}

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# Custom user model
AUTH_USER_MODEL = 'users.User'

# Internationalization
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)
STATIC_URL = 'static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')

MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# REST Framework settings
REST_FRAMEWORK = {
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
        'rest_framework.authentication.SessionAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticated',
    ),
    'DEFAULT_FILTER_BACKENDS': (
        'django_filters.rest_framework.DjangoFilterBackend',
        'rest_framework.filters.SearchFilter',
        'rest_framework.filters.OrderingFilter',
    ),
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20
}

# CORS settings
CORS_ALLOWED_ORIGINS = env.list('CORS_ALLOWED_ORIGINS', default=[
    'http://localhost:3000',
    'http://127.0.0.1:3000',
])

# Redis cache
CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": env('REDIS_URL', default='redis://localhost:6379/1'),
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
        }
    }
}

# Celery Configuration
CELERY_BROKER_URL = env('REDIS_URL', default='redis://localhost:6379/0')
CELERY_RESULT_BACKEND = env('REDIS_URL', default='redis://localhost:6379/0')
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = TIME_ZONE
CELERY_TASK_ACKS_LATE = True
CELERY_WORKER_PREFETCH_MULTIPLIER = 1
CELERY_TASK_TIME_LIMIT = 600  # 10 minutes
CELERY_TASK_SOFT_TIME_LIMIT = 300  # 5 minutes

# Configuration spécifique
CELERY_TASK_ROUTES = {
    'monitoring.tasks.high_priority_monitoring': {'queue': 'high_priority'},
    'monitoring.tasks.normal_priority_monitoring': {'queue': 'default'},
    'monitoring.tasks.low_priority_monitoring': {'queue': 'low_priority'},
    'monitoring.tasks.update_product_priorities': {'queue': 'maintenance'},
    'monitoring.tasks.cleanup_old_monitoring_data': {'queue': 'maintenance'},
}

# Configuration redis avec protections contre time-out
BROKER_TRANSPORT_OPTIONS = {
    'visibility_timeout': 3600,  # 1 heure
    'max_retries': 5,
    'interval_start': 0,
    'interval_step': 0.2,
    'interval_max': 0.5,
}

# Configuration des tâches périodiques
CELERY_BEAT_SCHEDULE = {
    'schedule-monitoring-tasks': {
        'task': 'monitoring.tasks.schedule_monitoring_tasks',
        'schedule': timedelta(minutes=5),
        'kwargs': {'batch_size': 1000},
    },
    'process-monitoring-queue': {
        'task': 'monitoring.tasks.process_monitoring_queue',
        'schedule': timedelta(minutes=2),
        'kwargs': {'max_tasks': 200},
    },
    'update-product-priorities': {
        'task': 'monitoring.tasks.update_product_priorities',
        'schedule': timedelta(hours=6),
        'kwargs': {'batch_size': 5000},
    },
    'cleanup-old-monitoring-data': {
        'task': 'monitoring.tasks.cleanup_old_monitoring_data',
        'schedule': timedelta(days=1),
        'kwargs': {'days_to_keep': 30},
    },
    'update-monitoring-stats': {
        'task': 'monitoring.tasks.update_monitoring_stats',
        'schedule': timedelta(hours=1),
    },
}

# Configuration Celery Results
CELERY_RESULT_EXTENDED = True
CELERY_RESULT_BACKEND_ALWAYS_RETRY = True
CELERY_RESULT_BACKEND_MAX_RETRIES = 10

# API documentation
SPECTACULAR_SETTINGS = {
    'TITLE': 'PriceGuard API',
    'DESCRIPTION': 'API for tracking product prices and alerting on price changes',
    'VERSION': '1.0.0',
}

# Monitoring settings
MONITORING = {
    'DEFAULT_FREQUENCY': 'normal',  # Fréquence de monitoring par défaut (high, normal, low)
    'HIGH_FREQUENCY_HOURS': 4,      # Intervalle pour fréquence haute (en heures)
    'NORMAL_FREQUENCY_HOURS': 12,   # Intervalle pour fréquence normale (en heures)
    'LOW_FREQUENCY_HOURS': 24,      # Intervalle pour fréquence basse (en heures)
    'SCREENSHOT_ENABLED': True,     # Activer les captures d'écran par défaut
    'DEFAULT_PRIORITY': 5,          # Priorité par défaut (1-10)
    'MAX_RETRIES': 3,               # Nombre maximum de tentatives pour une tâche
    'RETRY_DELAY': 60               # Délai entre les tentatives (en secondes)
}

# Logging configuration
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'level': 'INFO',
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
        'file': {
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': os.path.join(BASE_DIR, 'logs/priceguard.log'),
            'maxBytes': 1024 * 1024 * 10,  # 10 MB
            'backupCount': 10,
            'formatter': 'verbose',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
            'propagate': True,
        },
        'monitoring': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
            'propagate': False,
        },
        'celery': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}

# Créer le répertoire de logs si nécessaire
os.makedirs(os.path.join(BASE_DIR, 'logs'), exist_ok=True)
