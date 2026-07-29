from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import Company, User, Case, ProjectProgress, CommonStatus
from .serializers import (
    CompanySerializer,
    UserSerializer,
    CaseSerializer,
    ProjectProgressSerializer,
)
from .permissions import IsCompanyUser, IsSameCompany


class CompanyFilteredViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated, IsCompanyUser, IsSameCompany]

    def get_queryset(self):
        qs = super().get_queryset()
        if self.request.user.is_superuser:
            return qs
        return qs.filter(company=self.request.user.company)

    def perform_create(self, serializer):
        extra = {}
        if not self.request.user.is_superuser:
            extra['company'] = self.request.user.company
        serializer.save(**extra)


class CurrentUserViewSet(viewsets.GenericViewSet):
    permission_classes = [permissions.IsAuthenticated]

    @action(detail=False, methods=['get'])
    def me(self, request):
        serializer = UserSerializer(request.user, context={'request': request})
        return Response(serializer.data)


class UserViewSet(viewsets.ModelViewSet):
    """用户管理 API"""
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        if self.request.user.is_superuser:
            return User.objects.all()
        return User.objects.filter(company=self.request.user.company)

    def perform_create(self, serializer):
        if not self.request.user.is_superuser:
            serializer.save(company=self.request.user.company)
        else:
            serializer.save()

    def update(self, request, *args, **kwargs):
        """公司管理员只能修改自己的信息"""
        if not request.user.is_superuser:
            obj = self.get_object()
            if obj != request.user:
                return Response({'detail': '无权修改其他用户的信息。'},
                                status=status.HTTP_403_FORBIDDEN)
            # 公司管理员只能修改密码和个人基本信息
            allowed = {'username', 'email', 'password', 'first_name', 'last_name', 'phone'}
            data = {k: v for k, v in request.data.items() if k in allowed}
            serializer = self.get_serializer(obj, data=data, partial=True)
            serializer.is_valid(raise_exception=True)
            self.perform_update(serializer)
            return Response(serializer.data)
        return super().update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        """公司管理员不能删除自己"""
        if not request.user.is_superuser:
            obj = self.get_object()
            if obj == request.user:
                return Response({'detail': '不能删除自己的账号。'},
                                status=status.HTTP_403_FORBIDDEN)
        return super().destroy(request, *args, **kwargs)


class CaseViewSet(CompanyFilteredViewSet):
    queryset = Case.objects.select_related('company').all()
    serializer_class = CaseSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        if not self.request.user.is_superuser:
            # 公司管理员只看到 active 的记录
            qs = qs.filter(status=CommonStatus.ACTIVE)
        style = self.request.query_params.get('style')
        if style:
            qs = qs.filter(style=style)
        return qs

    def destroy(self, request, *args, **kwargs):
        """删除：公司管理员=软删除，系统管理员=硬删除"""
        obj = self.get_object()
        if request.user.is_superuser:
            obj.hard_delete()
        else:
            obj.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class ProjectProgressViewSet(CompanyFilteredViewSet):
    queryset = ProjectProgress.objects.select_related('company').all()
    serializer_class = ProjectProgressSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        if not self.request.user.is_superuser:
            qs = qs.filter(status=CommonStatus.ACTIVE)
        return qs

    def destroy(self, request, *args, **kwargs):
        """删除：公司管理员=软删除，系统管理员=硬删除"""
        obj = self.get_object()
        if request.user.is_superuser:
            obj.hard_delete()
        else:
            obj.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class CompanyViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = CompanySerializer
    permission_classes = [permissions.IsAuthenticated, IsCompanyUser]

    def get_queryset(self):
        if self.request.user.is_superuser:
            return Company.objects.all()
        return Company.objects.filter(id=self.request.user.company_id)
