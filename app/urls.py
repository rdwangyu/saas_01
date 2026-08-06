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
    PublicCompanyDetail,
    PublicCaseList,
    PublicCaseDetail,
    SendCodeView,
    CustomerLoginView,
    CustomerMeView,
    CustomerProjectListView,
    CustomerProjectDetailView,
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

    # 公开只读接口（前台小程序免登录）
    path('public/companies/<int:pk>/', PublicCompanyDetail.as_view(), name='public-company-detail'),
    path('public/cases/', PublicCaseList.as_view(), name='public-case-list'),
    path('public/cases/<int:pk>/', PublicCaseDetail.as_view(), name='public-case-detail'),

    # 客户登录体系
    path('customer/send-code/', SendCodeView.as_view(), name='customer-send-code'),
    path('customer/login/', CustomerLoginView.as_view(), name='customer-login'),
    path('customer/me/', CustomerMeView.as_view(), name='customer-me'),
    path('customer/projects/', CustomerProjectListView.as_view(), name='customer-project-list'),
    path('customer/projects/<int:pk>/', CustomerProjectDetailView.as_view(), name='customer-project-detail'),
]
