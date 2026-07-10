"""
装修公司 SaaS 系统 — API 路由
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)

from .views import (
    CurrentUserViewSet,
    CompanyViewSet,
    CaseViewSet,
    ProjectProgressViewSet,
)

# DRF Router 自动生成 CRUD 路由
router = DefaultRouter()
router.register(r'cases', CaseViewSet, basename='case')
router.register(r'projects', ProjectProgressViewSet, basename='project')
router.register(r'companies', CompanyViewSet, basename='company')

urlpatterns = [
    # ============================================================
    # JWT 认证
    # ============================================================
    path('auth/login/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('auth/refresh/', TokenRefreshView.as_view(), name='token_refresh'),

    # ============================================================
    # 当前用户
    # ============================================================
    path('me/', CurrentUserViewSet.as_view({'get': 'me'}), name='current_user'),

    # ============================================================
    # 业务 API（由 Router 自动注册）
    # ============================================================
    path('', include(router.urls)),
]
