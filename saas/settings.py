"""
Django settings for saas project.

装修公司 SaaS 系统配置
"""

from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = "django-insecure-2x)l(1j!#u%q1ul#q5yt)@8#acelczv=$&zy0yyx#v0(z&kmwg"

DEBUG = True

ALLOWED_HOSTS = ["*"]

# ============================================================
# 应用注册
# ============================================================
INSTALLED_APPS = [
    # 业务应用（必须在 django.contrib.admin 之前，才能覆盖 admin 模板）
    "app",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # 第三方
    "rest_framework",
    "rest_framework_simplejwt",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "saas.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "saas.wsgi.application"

# ============================================================
# 数据库 — SQLite
# ============================================================
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

# ============================================================
# 密码校验（admin 认证用户 auth.User 使用）
# ============================================================
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# ============================================================
# 国际化 — 中文
# ============================================================
LANGUAGE_CODE = "zh-hans"
TIME_ZONE = "Asia/Shanghai"
USE_I18N = True
USE_TZ = True

# ============================================================
# 静态文件
# ============================================================
STATIC_URL = "static/"
STATIC_ROOT = "/var/www/saas/staticfiles"

# ============================================================
# 阿里云 OSS — 媒体文件存储
# ============================================================
STORAGES = {
    "default": {
        "BACKEND": "app.oss_storage.OSSStorage",
    },
    "staticfiles": {
        "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
    },
}
MEDIA_URL = "https://byqg-image.oss-cn-beijing.aliyuncs.com/"


ALIYUN_OSS_ACCESS_KEY_ID = ""
ALIYUN_OSS_ACCESS_KEY_SECRET = ""
ALIYUN_OSS_BUCKET_NAME = "byqg-image"
ALIYUN_OSS_ENDPOINT = "oss-cn-beijing.aliyuncs.com"
ALIYUN_OSS_BUCKET_DOMAIN = "byqg-image.oss-cn-beijing.aliyuncs.com"

# ============================================================
# DRF 配置（客户 + 公开 API）
# ============================================================
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.SessionAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 20,
}

# ============================================================
# 微信小程序（生成小程序码：客户扫码直接进入对应公司）
# WECHAT_MINI_PROGRAM_SECRET 需在微信公众平台「开发管理-开发设置」获取后填入
# ============================================================
WECHAT_MINI_PROGRAM_APPID = ""
WECHAT_MINI_PROGRAM_SECRET = ""

# 默认主键类型
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
