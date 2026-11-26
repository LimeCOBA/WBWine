import os
import secrets
from pathlib import Path

ROOT = Path(__file__).resolve().parent
KEY = ROOT / ".local-secret"
if not KEY.exists():
    try:
        with KEY.open("x") as handle:
            handle.write(secrets.token_urlsafe(64))
    except FileExistsError:
        pass
SECRET_KEY = KEY.read_text()
ALLOWED_HOSTS = ["127.0.0.1","localhost","testserver"]
SERVICE = os.environ.get("WB_SERVICE","seller")
ROOT_URLCONF = "common"
INSTALLED_APPS = ["django.contrib.admin","django.contrib.auth","django.contrib.contenttypes",
                  "django.contrib.sessions","django.contrib.messages","django.contrib.staticfiles","ledger",
                  *["services."+name for name in ("atlas","wild","seller","node","fleet","partner","drive")]]
MIDDLEWARE = ["django.middleware.security.SecurityMiddleware","django.contrib.sessions.middleware.SessionMiddleware",
              "django.middleware.common.CommonMiddleware","django.middleware.csrf.CsrfViewMiddleware",
              "django.contrib.auth.middleware.AuthenticationMiddleware","django.contrib.messages.middleware.MessageMiddleware",
              "django.middleware.clickjacking.XFrameOptionsMiddleware"]
DATABASES = {"default":{"ENGINE":"django.db.backends.sqlite3","NAME":ROOT/"wbwine.sqlite3",
                        "OPTIONS":{"transaction_mode":"IMMEDIATE","timeout":15}}}
TEMPLATES = [{"BACKEND":"django.template.backends.django.DjangoTemplates","DIRS":[ROOT/"templates"],"APP_DIRS":True,
              "OPTIONS":{"context_processors":["django.template.context_processors.request","django.contrib.auth.context_processors.auth","django.contrib.messages.context_processors.messages"]}}]
STATIC_URL = "/static/"
LANGUAGE_CODE = "ru"
TIME_ZONE = "Europe/Moscow"
USE_TZ = True
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
LOGIN_REDIRECT_URL = "/"
LOGOUT_REDIRECT_URL = "/login/"
SESSION_COOKIE_HTTPONLY = True
AUTH_PASSWORD_VALIDATORS = [{"NAME":"django.contrib.auth.password_validation."+name} for name in ("MinimumLengthValidator","CommonPasswordValidator","UserAttributeSimilarityValidator","NumericPasswordValidator")]