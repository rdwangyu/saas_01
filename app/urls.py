from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)

from .views import (
    CurrentUserViewSet,
    UserViewSet,
    CompanyViewSet,
    CaseViewSet,
    ProjectProgressViewSet,
)

router = DefaultRouter()
router.register(r'cases', CaseViewSet, basename='case')
router.register(r'projects', ProjectProgressViewSet, basename='project')
router.register(r'companies', CompanyViewSet, basename='company')
router.register(r'users', UserViewSet, basename='user')

urlpatterns = [
    path('auth/login/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('auth/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('me/', CurrentUserViewSet.as_view({'get': 'me'}), name='current_user'),
    path('', include(router.urls)),
]
