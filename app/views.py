"""
装修公司 SaaS 系统 — DRF API 视图

- 所有业务视图自动按公司过滤数据
- 创建数据时自动绑定当前用户公司
- 超级管理员可查看/操作全部数据
"""

from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import Company, Case, ProjectProgress
from .serializers import (
    CompanySerializer,
    UserSerializer,
    CaseSerializer,
    ProjectProgressSerializer,
)
from .permissions import IsCompanyUser, IsSameCompany


# ============================================================
# 业务视图基类 — 公司数据隔离
# ============================================================
class CompanyFilteredViewSet(viewsets.ModelViewSet):
    """
    所有业务 ViewSet 的基类。
    - 过滤 queryset 使普通用户只能看到自己公司的数据
    - 创建时自动绑定 company
    - 超级管理员不受限制
    """

    permission_classes = [permissions.IsAuthenticated, IsCompanyUser, IsSameCompany]

    def get_queryset(self):
        """非超级管理员只返回自己公司的数据。"""
        qs = super().get_queryset()
        if self.request.user.is_superuser:
            return qs
        return qs.filter(company=self.request.user.company)

    def perform_create(self, serializer):
        """创建时自动绑定 company（序列化器中也会处理，这里是双保险）。"""
        extra = {}
        if not self.request.user.is_superuser:
            extra['company'] = self.request.user.company
        serializer.save(**extra)


# ============================================================
# 用户相关端点
# ============================================================
class CurrentUserViewSet(viewsets.GenericViewSet):
    """
    当前登录用户信息。
    """

    permission_classes = [permissions.IsAuthenticated]

    @action(detail=False, methods=['get'])
    def me(self, request):
        """GET /api/me/ — 返回当前用户信息。"""
        serializer = UserSerializer(request.user, context={'request': request})
        return Response(serializer.data)


# ============================================================
# Case — 装修案例 CRUD
# ============================================================
class CaseViewSet(CompanyFilteredViewSet):
    """
    装修案例 API。

    - GET    /api/cases/      — 列表（按公司过滤）
    - POST   /api/cases/      — 新增
    - GET    /api/cases/{id}/ — 详情
    - PUT    /api/cases/{id}/ — 更新
    - DELETE /api/cases/{id}/ — 删除
    """

    queryset = Case.objects.select_related('company').all()
    serializer_class = CaseSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        # 支持按风格筛选
        style = self.request.query_params.get('style')
        if style:
            qs = qs.filter(style=style)
        return qs


# ============================================================
# ProjectProgress — 项目进度 CRUD
# ============================================================
class ProjectProgressViewSet(CompanyFilteredViewSet):
    """
    项目进度 API。

    - GET    /api/projects/      — 列表（按公司过滤）
    - POST   /api/projects/      — 新增
    - GET    /api/projects/{id}/ — 详情
    - PUT    /api/projects/{id}/ — 更新
    - DELETE /api/projects/{id}/ — 删除
    """

    queryset = ProjectProgress.objects.select_related('company').all()
    serializer_class = ProjectProgressSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        # 支持按阶段筛选
        stage = self.request.query_params.get('stage')
        if stage is not None:
            qs = qs.filter(current_stage=int(stage))
        return qs


# ============================================================
# Company — 公司信息（只读）
# ============================================================
class CompanyViewSet(viewsets.ReadOnlyModelViewSet):
    """
    公司信息 API（只读）。
    普通用户只能看到自己的公司信息。
    """

    serializer_class = CompanySerializer
    permission_classes = [permissions.IsAuthenticated, IsCompanyUser]

    def get_queryset(self):
        if self.request.user.is_superuser:
            return Company.objects.all()
        return Company.objects.filter(id=self.request.user.company_id)
