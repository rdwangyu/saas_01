import random
import secrets
from datetime import timedelta

from django.conf import settings
from django.utils import timezone
from rest_framework import generics, permissions, status, viewsets
from rest_framework.authentication import BaseAuthentication
from rest_framework.decorators import action
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import (
    Company, Customer, CustomerToken, SmsCode, User, Case, ProjectProgress, CommonStatus,
)
from .serializers import (
    CompanySerializer,
    CustomerSerializer,
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


# ============================================================
# 公开只读接口（前台小程序免登录访问）
# ============================================================

class PublicCompanyDetail(generics.RetrieveAPIView):
    """公司详情（按 id 查询，供索引页/公司简介页免登录展示）"""
    authentication_classes = []  # 客户 token 附加到公开请求时也不参与认证
    permission_classes = [permissions.AllowAny]
    queryset = Company.objects.all()
    serializer_class = CompanySerializer
    pagination_class = None


class PublicCaseList(generics.ListAPIView):
    """案例列表（按 ?company=<id> 过滤，免登录只读）"""
    authentication_classes = []
    permission_classes = [permissions.AllowAny]
    serializer_class = CaseSerializer

    def get_queryset(self):
        qs = Case.objects.select_related('company').filter(status=CommonStatus.ACTIVE)
        company_id = self.request.query_params.get('company')
        if company_id:
            qs = qs.filter(company_id=company_id)
        return qs


class PublicCaseDetail(generics.RetrieveAPIView):
    """案例详情（免登录只读）"""
    authentication_classes = []
    permission_classes = [permissions.AllowAny]
    serializer_class = CaseSerializer
    queryset = Case.objects.filter(status=CommonStatus.ACTIVE)


# ============================================================
# 客户登录体系（客户不是 Django 用户，独立 token）
# ============================================================

class CustomerAuthentication(BaseAuthentication):
    """用 CustomerToken 认证客户。"""
    keyword = 'Bearer'

    def authenticate(self, request):
        auth = request.META.get('HTTP_AUTHORIZATION', '')
        if not auth:
            return None
        try:
            parts = auth.split()
            if len(parts) != 2 or parts[0].lower() != 'bearer':
                return None
            key = parts[1]
        except Exception:
            return None
        try:
            token = CustomerToken.objects.select_related('customer').get(
                key=key,
                expires_at__gt=timezone.now(),
            )
        except CustomerToken.DoesNotExist:
            raise AuthenticationFailed('登录已失效，请重新登录')
        return (token.customer, token)


class IsCustomer(permissions.BasePermission):
    """仅已认证客户可访问。"""
    def has_permission(self, request, view):
        return isinstance(request.user, Customer)


class SendCodeView(APIView):
    """发送短信验证码（测试模式：验证码打印日志并随响应返回）。"""
    authentication_classes = []
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        phone = (request.data.get('phone') or '').strip()
        if not phone:
            return Response({'detail': '请输入手机号'}, status=status.HTTP_400_BAD_REQUEST)
        if not Customer.objects.filter(phone=phone).exists():
            return Response({'detail': '该手机号未登记，请联系公司工作人员'},
                            status=status.HTTP_400_BAD_REQUEST)
        last = SmsCode.objects.filter(phone=phone).order_by('-created_at').first()
        if last and (timezone.now() - last.created_at).total_seconds() < 60:
            return Response({'detail': '发送过于频繁，请稍后再试'},
                            status=status.HTTP_429_TOO_MANY_REQUESTS)
        code = f'{random.randint(0, 999999):06d}'
        SmsCode.objects.create(phone=phone, code=code)
        if getattr(settings, 'SMS_TEST_MODE', True):
            # 测试模式：不真正发短信，验证码打印到日志并返回，方便联调
            print(f'[SMS] 验证码: {code} -> {phone}')
            return Response({'detail': '验证码已发送（测试模式）', 'debug_code': code})
        # TODO: 接入阿里云短信后在此处调用发送
        return Response({'detail': '验证码已发送'})


class CustomerLoginView(APIView):
    """手机号 + 验证码 登录，签发客户 token。"""
    authentication_classes = []
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        phone = (request.data.get('phone') or '').strip()
        code = (request.data.get('code') or '').strip()
        if not phone or not code:
            return Response({'detail': '请输入手机号和验证码'}, status=status.HTTP_400_BAD_REQUEST)
        sms = SmsCode.objects.filter(phone=phone, code=code, used=False) \
            .order_by('-created_at').first()
        if not sms:
            return Response({'detail': '验证码错误或已过期'}, status=status.HTTP_400_BAD_REQUEST)
        if (timezone.now() - sms.created_at).total_seconds() > 300:
            return Response({'detail': '验证码已过期，请重新获取'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            customer = Customer.objects.get(phone=phone)
        except Customer.DoesNotExist:
            return Response({'detail': '该手机号未登记，请联系公司工作人员'},
                            status=status.HTTP_400_BAD_REQUEST)
        sms.used = True
        sms.save(update_fields=['used'])
        token = CustomerToken.objects.create(
            key=secrets.token_urlsafe(32),
            customer=customer,
            expires_at=timezone.now() + timedelta(days=30),
        )
        return Response({
            'token': token.key,
            'customer': CustomerSerializer(customer).data,
        })


# ============================================================
# 客户业务接口
# ============================================================

class CustomerMeView(APIView):
    """当前登录客户的信息。"""
    authentication_classes = [CustomerAuthentication]
    permission_classes = [IsCustomer]

    def get(self, request):
        return Response(CustomerSerializer(request.user).data)


class CustomerProjectListView(generics.ListAPIView):
    """当前客户的项目列表（可按 ?company=<id> 过滤）。"""
    authentication_classes = [CustomerAuthentication]
    permission_classes = [IsCustomer]
    serializer_class = ProjectProgressSerializer

    def get_queryset(self):
        qs = ProjectProgress.objects.select_related('company', 'customer', 'staff') \
            .filter(customer=self.request.user, status=CommonStatus.ACTIVE) \
            .order_by('-created_at')
        company_id = self.request.query_params.get('company')
        if company_id:
            qs = qs.filter(company_id=company_id)
        return qs


class CustomerProjectDetailView(generics.RetrieveAPIView):
    """当前客户的单个项目详情。"""
    authentication_classes = [CustomerAuthentication]
    permission_classes = [IsCustomer]
    serializer_class = ProjectProgressSerializer

    def get_queryset(self):
        return ProjectProgress.objects.select_related('company', 'customer', 'staff') \
            .filter(customer=self.request.user, status=CommonStatus.ACTIVE)
