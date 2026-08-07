"""
URL configuration for saas project.

- admin/     — Django Admin 管理后台（超管）
- dashboard/ — 后台租户后台（员工验证码登录）
- api/       — 前台 API（客户 + 公开）
- media/     — 媒体文件（开发环境）
"""

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path, include

from app.urls import api_patterns, dashboard_patterns

urlpatterns = [
    # Django Admin 管理后台（超管专用）
    path("admin/", admin.site.urls),
    # 后台租户后台
    path("dashboard/", include((dashboard_patterns, "dashboard"))),
    # 前台 API
    path("api/", include((api_patterns, "api"))),
]

# 开发环境提供媒体文件访问
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
