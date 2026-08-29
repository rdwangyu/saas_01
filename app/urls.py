from django.urls import path

from . import views

# /dashboard/ 后台（员工手机号+密码登录的租户后台）
dashboard_patterns = [
    path("login/", views.DashboardLoginView.as_view(), name="login"),
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
    path("projects/<int:pk>/detail/", views.ProjectDetailView.as_view(), name="project_detail"),
    path("projects/<int:pk>/stages/new/", views.ProjectStageCreateView.as_view(), name="stage_create"),
    path("stages/<int:pk>/", views.ProjectStageUpdateView.as_view(), name="stage_update"),
    path("customers/", views.CustomerListView.as_view(), name="customer_list"),
    path("customers/new/", views.CustomerCreateView.as_view(), name="customer_create"),
    path("customers/<int:pk>/", views.CustomerUpdateView.as_view(), name="customer_update"),
    path(
        "customers/<int:pk>/delete/",
        views.CustomerDeleteView.as_view(),
        name="customer_delete",
    ),
    path(
        "customers/<int:pk>/detail/",
        views.CustomerDetailView.as_view(),
        name="customer_detail",
    ),
    path("staff/", views.StaffListView.as_view(), name="staff_list"),
    path("staff/password/", views.StaffPasswordChangeView.as_view(), name="staff_password"),
]

# /api/ 前台（公开 + 订单绑定 API）
api_patterns = [
    path("public/companies/", views.PublicCompanyList.as_view(), name="public-company-list"),
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
    path("bind-project/", views.BindProjectView.as_view(), name="bind-project"),
    path("oss/upload-url/", views.OssUploadUrlView.as_view(), name="oss-upload-url"),
]
