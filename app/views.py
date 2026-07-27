from rest_framework import viewsets, permissions
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


class CaseViewSet(CompanyFilteredViewSet):
    queryset = Case.objects.select_related('company').all()
    serializer_class = CaseSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        style = self.request.query_params.get('style')
        if style:
            qs = qs.filter(style=style)
        return qs


class ProjectProgressViewSet(CompanyFilteredViewSet):
    queryset = ProjectProgress.objects.select_related('company').all()
    serializer_class = ProjectProgressSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        stage = self.request.query_params.get('stage')
        if stage is not None:
            qs = qs.filter(current_stage=int(stage))
        return qs


class CompanyViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = CompanySerializer
    permission_classes = [permissions.IsAuthenticated, IsCompanyUser]

    def get_queryset(self):
        if self.request.user.is_superuser:
            return Company.objects.all()
        return Company.objects.filter(id=self.request.user.company_id)
