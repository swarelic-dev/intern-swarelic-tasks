"""Configuration for the standalone Swarelic queue exercise."""
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "local-development-only-not-for-production")
DEBUG = os.getenv("DJANGO_DEBUG", "false").lower() == "true"
ALLOWED_HOSTS = [s.strip() for s in os.getenv("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1,testserver").split(",") if s.strip()]
INSTALLED_APPS = ["django.contrib.auth", "django.contrib.contenttypes", "rest_framework", "queues"]
MIDDLEWARE = ["django.middleware.security.SecurityMiddleware", "django.middleware.common.CommonMiddleware"]
ROOT_URLCONF = "project.urls"
TEMPLATES = []
WSGI_APPLICATION = "project.wsgi.application"
DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": BASE_DIR / "db.sqlite3"}}
if os.getenv("DATABASE_URL", "").startswith("postgresql://"):
    from urllib.parse import urlsplit, unquote
    p = urlsplit(os.environ["DATABASE_URL"])
    DATABASES["default"] = {
        "ENGINE": "django.db.backends.postgresql", "NAME": p.path.lstrip("/"),
        "USER": unquote(p.username or ""), "PASSWORD": unquote(p.password or ""),
        "HOST": p.hostname, "PORT": p.port or 5432,
    }
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
USE_TZ = True
TIME_ZONE = "UTC"
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": ["rest_framework.authentication.SessionAuthentication", "rest_framework.authentication.BasicAuthentication"],
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.IsAuthenticated"],
}
CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0")
CELERY_TASK_ALWAYS_EAGER = os.getenv("CELERY_TASK_ALWAYS_EAGER", "false").lower() == "true"
QUEUE_ALERT_THRESHOLD = int(os.getenv("QUEUE_ALERT_THRESHOLD", "5"))
SECURE_CONTENT_TYPE_NOSNIFF = True
SESSION_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_SECURE = not DEBUG
