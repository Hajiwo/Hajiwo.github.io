import os
from pathlib import Path
from django.core.exceptions import ImproperlyConfigured
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / '.env')
DEBUG = os.getenv('DJANGO_DEBUG', 'false').lower() == 'true'
SECRET_KEY = os.getenv('DJANGO_SECRET_KEY', '')
if not SECRET_KEY:
    raise ImproperlyConfigured('Set DJANGO_SECRET_KEY in backend/.env or the environment.')

def env_list(name, default=''):
    return [value.strip() for value in os.getenv(name, default).split(',') if value.strip()]

ALLOWED_HOSTS = env_list('DJANGO_ALLOWED_HOSTS', 'localhost,127.0.0.1' if DEBUG else '')
if not DEBUG and not ALLOWED_HOSTS:
    raise ImproperlyConfigured('Set DJANGO_ALLOWED_HOSTS for production.')
INSTALLED_APPS = [
    'django.contrib.admin', 'django.contrib.auth', 'django.contrib.contenttypes',
    'django.contrib.sessions', 'django.contrib.messages', 'django.contrib.staticfiles',
    'corsheaders', 'rest_framework', 'blog',
]
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware', 'corsheaders.middleware.CorsMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware', 'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware', 'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware', 'django.middleware.clickjacking.XFrameOptionsMiddleware',
]
ROOT_URLCONF = 'config.urls'
TEMPLATES = [{
    'BACKEND': 'django.template.backends.django.DjangoTemplates', 'DIRS': [BASE_DIR / 'templates'], 'APP_DIRS': True,
    'OPTIONS': {'context_processors': [
        'django.template.context_processors.request', 'django.contrib.auth.context_processors.auth',
        'django.contrib.messages.context_processors.messages',
    ]},
}]
WSGI_APPLICATION = 'config.wsgi.application'
DATABASES = {'default': {'ENGINE': 'django.db.backends.sqlite3', 'NAME': os.getenv('DJANGO_DATABASE_PATH', str(BASE_DIR / 'db.sqlite3')), 'OPTIONS': {'timeout': 20}}}
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]
LANGUAGE_CODE = 'zh-hans'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [BASE_DIR / 'static']
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
CORS_ALLOWED_ORIGINS = env_list('CORS_ALLOWED_ORIGINS', 'https://hajiwo.github.io')
CORS_URLS_REGEX = r'^/api/.*$'
CORS_ALLOW_CREDENTIALS = False
CSRF_TRUSTED_ORIGINS = env_list('CSRF_TRUSTED_ORIGINS')
SESSION_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_SECURE = not DEBUG
SECURE_SSL_REDIRECT = not DEBUG
SECURE_HSTS_SECONDS = 31536000 if not DEBUG else 0
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'
REST_FRAMEWORK = {
    'DEFAULT_PERMISSION_CLASSES': ['rest_framework.permissions.AllowAny'],
    'DEFAULT_AUTHENTICATION_CLASSES': [],
    'DEFAULT_RENDERER_CLASSES': ['rest_framework.renderers.JSONRenderer'],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,
    'DEFAULT_THROTTLE_RATES': {'comments': '30/hour', 'community': '60/hour', 'subscriptions': '5/hour', 'verify': '30/hour'},
    'SEARCH_PARAM': 'q',
}

# Email credentials belong only in the server environment, never in frontend code.
ARTICLES_SITE_URL = os.getenv('ARTICLES_SITE_URL', 'https://hajiwo.github.io/articles').rstrip('/')
SUBSCRIPTIONS_ENABLED = os.getenv('SUBSCRIPTIONS_ENABLED', 'false').lower() == 'true'
EMAIL_BACKEND = os.getenv('EMAIL_BACKEND', 'django.core.mail.backends.smtp.EmailBackend')
EMAIL_HOST = os.getenv('EMAIL_HOST', '')
EMAIL_PORT = int(os.getenv('EMAIL_PORT', '587'))
EMAIL_HOST_USER = os.getenv('EMAIL_HOST_USER', '')
EMAIL_HOST_PASSWORD = os.getenv('EMAIL_HOST_PASSWORD', '')
EMAIL_USE_TLS = os.getenv('EMAIL_USE_TLS', 'true').lower() == 'true'
EMAIL_USE_SSL = os.getenv('EMAIL_USE_SSL', 'false').lower() == 'true'
EMAIL_TIMEOUT = 10
DEFAULT_FROM_EMAIL = os.getenv('DEFAULT_FROM_EMAIL', EMAIL_HOST_USER or 'noreply@localhost')
