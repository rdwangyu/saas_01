"""URL 配置：后台 dashboard 与前台 api 两组路由，供根 URLconf 分别挂载。"""

from django.urls import path

from . import views

# /dashboard/ 后台（员工验证码登录的租户后台）
dashboard_patterns = [
    path("login/", views.DashboardLoginView.as_view(), name="login"),
    path("send-code/", views.DashboardSendCodeView.as_view(), name="send_code"),
    path("logout/", views.DashboardLogoutView.as_view(), name="logout"),
    path("", views.DashboardIndexView.as_view(), name="index"),
    path("company/", views.CompanyUpdateView.as_view(), name="company"),
    path("cases/", views.CaseListView.as_view(), name="case_list"),
    path("cases/new/", views.CaseCreateView.as_view(), name="case_create"),
    path("cases/<int:pk>/", views.CaseUpdateView.as_view(), name="case_update"),
    path("cases/<int:pk>/delete/", views.CaseDeleteView.as_view(), name="case_delete"),
    path("projects/", views.ProjectListView.as_view(), name="project_list"),
    path("projects/new/", views.ProjectCreateView.as_view(), name="project_create"),
    path("projects/<int:pk>/", views.ProjectUpdateView.as_view(), name="project_update"),
    path("projects/<int:pk>/delete/", views.ProjectDeleteView.as_view(), name="project_delete"),
    path("customers/", views.CustomerListView.as_view(), name="customer_list"),
    path("customers/<int:pk>/", views.CustomerDetailView.as_view(), name="customer_detail"),
    path("staff/", views.StaffListView.as_view(), name="staff_list"),
    path("staff/new/", views.StaffCreateView.as_view(), name="staff_create"),
    path("staff/<int:pk>/", views.StaffUpdateView.as_view(), name="staff_update"),
]

# /api/ 前台（客户 + 公开 API）
api_patterns = [
    path(
        "public/companies/<int:pk>/",
        views.PublicCompanyDetail.as_view(),
        name="public-company-detail",
    ),
    path("public/cases/", views.PublicCaseList.as_view(), name="public-case-list"),
    path(
        "public/cases/<int:pk>/",
        views.PublicCaseDetail.as_view(),
        name="public-case-detail",
    ),
    path("customer/send-code/", views.SendCodeView.as_view(), name="customer-send-code"),
    path("customer/login/", views.CustomerLoginView.as_view(), name="customer-login"),
    path("customer/me/", views.CustomerMeView.as_view(), name="customer-me"),
    path(
        "customer/projects/",
        views.CustomerProjectListView.as_view(),
        name="customer-project-list",
    ),
    path(
        "customer/projects/<int:pk>/",
        views.CustomerProjectDetailView.as_view(),
        name="customer-project-detail",
    ),
]
