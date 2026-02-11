"""
Django settings for authhentication project.
"""

from pathlib import Path
import socket

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = 'django-insecure-td5cb0=q3)1a$lt(6ev##*qu+avuwn1f!by_e9k++@2=i4b*7b'
DEBUG = True
ALLOWED_HOSTS = ["*"]

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    "rest_framework",
    'rest_framework.authtoken',
    'corsheaders',
    'myground.apps.MygroundConfig',
    'django_apscheduler',
   
]

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

CORS_ALLOWED_ORIGINS = [
    "http://localhost:5173",
    "http://localhost:3000",
]
CORS_ALLOW_ALL_ORIGINS = True

ROOT_URLCONF = 'authhentication.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'authhentication.wsgi.application'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'cloud management',  # FIXED: Remove space or use underscore
        'USER': 'postgres',
        'PASSWORD': 'Uchimevictor',
        'HOST': '127.0.0.1',
        'PORT': '5432'
    }
}

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

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

STATIC_URL = 'static/'
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# ========== EMAIL CONFIGURATION ==========
# Use console backend for development (NO TIMEOUTS!)
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# Remove or comment out all Gmail settings:
'''
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_USE_SSL = False
EMAIL_HOST_USER = 'uchimevictor797@gmail.com'
EMAIL_HOST_PASSWORD = 'nuoukgiykpvupuhn'
EMAIL_TIMEOUT = 30
'''

# REST Framework settings
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.TokenAuthentication',
        'rest_framework.authentication.SessionAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.AllowAny',
    ],
}



# Debugging
try:
    socket.gethostbyname('localhost')
    print("✅ DNS resolution successful")
except socket.gaierror as e:
    print(f"❌ DNS resolution failed: {e}")

PLATFORM_AWS_ACCOUNT_ID = "026395503692"
AWS_ROLE_NAME = "CloudCostReadOnlyRole"

APSCHEDULER_DATETIME_FORMAT = "N j, Y, f:s a"
APSCHEDULER_RUN_NOW_TIMEOUT = 25  # Seconds


# Timezone
TIME_ZONE = 'UTC'
USE_TZ = True



# Add to your settings.py

CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": "redis://127.0.0.1:6379/1",
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
        }
    }
}

# Cache timeout settings
CACHE_TTL = 60 * 15  # 15 minutes cache timeout
RESOURCE_CACHE_TTL = 60 * 30  # 30 minutes for resources
COST_CACHE_TTL = 60 * 60  # 60 minutes for cost data

# For production, use:
# "LOCATION": "redis://:password@127.0.0.1:6379/0"

# settings.py
import os
from django.core.cache import cache

# Set up cache with fallback logic
CACHE_ENABLED = True

def safe_cache_get(key, default=None):
    """Safely get from cache, return default if cache fails"""
    if not CACHE_ENABLED:
        return default
    try:
        return cache.get(key, default)
    except Exception as e:
        print(f"⚠️ Cache get failed: {e}")
        return default

def safe_cache_set(key, value, timeout=None):
    """Safely set cache value"""
    if not CACHE_ENABLED:
        return
    try:
        cache.set(key, value, timeout)
    except Exception as e:
        print(f"⚠️ Cache set failed: {e}")

def safe_cache_delete(key):
    """Safely delete from cache"""
    if not CACHE_ENABLED:
        return
    try:
        cache.delete(key)
    except Exception as e:
        print(f"⚠️ Cache delete failed: {e}")

# Simple cache configuration
try:
    # Try to use Redis if django-redis is installed
    import django_redis
    CACHES = {
        'default': {
            'BACKEND': 'django_redis.cache.RedisCache',
            'LOCATION': 'redis://127.0.0.1:6379/1',
            'OPTIONS': {
                'CLIENT_CLASS': 'django_redis.client.DefaultClient',
                'IGNORE_EXCEPTIONS': True,
            }
        }
    }
    print("✅ Redis cache configured")
except ImportError:
    # Fall back to local memory cache
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
            'LOCATION': 'unique-snowflake',
        }
    }
    print("⚠️ django-redis not installed, using local memory cache")

# Cache TTLs
RESOURCE_CACHE_TTL = 60 * 60 * 6
COST_CACHE_TTL = 60 * 60
SUMMARY_CACHE_TTL = 60 * 60 * 2