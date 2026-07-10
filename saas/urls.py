"""
URL configuration for saas project.

- admin/  — Django Admin 管理后台
- api/    — DRF REST API
- media/  — 媒体文件（开发环境）
"""

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    # Django Admin 管理后台
    path('admin/', admin.site.urls),

    # DRF REST API
    path('api/', include('app.urls')),
]

# 开发环境提供媒体文件访问
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
