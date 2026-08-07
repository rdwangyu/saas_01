"""视图：/dashboard/ 后台（员工验证码登录 + 公司隔离）与 /api/ 前台（客户 + 公开）API。

后台：员工用手机号+验证码登录，身份存 session['staff_id']；数据按当前员工所属公司隔离，
有 status 的模型只显示 ACTIVE。删除语义：员工软删（status=INACTIVE）。
前台：客户用手机号+验证码登录签发 CustomerToken，公开接口免登录。
"""

import random
import secrets
from datetime import timedelta

from django.conf import settings
from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.db.models import Q
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import render
from django.urls import reverse_lazy
from django.utils import timezone
from django.views import View
from django.views.generic import (
    CreateView,
    DeleteView,
    DetailView,
    ListView,
    TemplateView,
    UpdateView,
)
from rest_framework import generics, permissions, status
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.response import Response
from rest_framework.views import APIView

from .forms_dashboard import (
    BaseDashboardForm,
    CaseForm,
    CompanyForm,
    DashboardLoginForm,
    ProjectForm,
    StageFormSet,
    StaffCreateForm,
    StaffEditForm,
    get_current_staff,
)
from .models import (
    Case,
    CommonStatus,
    Company,
    Customer,
    CustomerToken,
    ProjectProgress,
    SmsCode,
    Staff,
)
from .serializers import (
    CaseSerializer,
    CompanySerializer,
    CustomerSerializer,
    ProjectProgressSerializer,
)

# ============================================================
# 后台 dashboard（/dashboard/）
# ============================================================


class CompanyScopedViewMixin:
    """租户后台基类：验证码登录 + 按当前员工所属公司隔离。"""

    login_url = reverse_lazy("dashboard:login")

    def _current_staff(self):
        return get_current_staff(self.request)

    def dispatch(self, request, *args, **kwargs):
        if self._current_staff() is None:
            return HttpResponseRedirect(self.login_url)
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        qs = super().get_queryset()
        if hasattr(self.model, "company"):
            qs = qs.filter(company_id=self._current_staff().company_id)
            if hasattr(self.model, "status"):
                qs = qs.filter(status=CommonStatus.ACTIVE)
        return qs

    def get_object(self, queryset=None):
        obj = super().get_object(queryset)
        if hasattr(self.model, "company_id") and (
            getattr(obj, "company_id", None) != self._current_staff().company_id
        ):
            raise PermissionDenied
        return obj

    def form_valid(self, form):
        if hasattr(form.instance, "company"):
            form.instance.company = self._current_staff().company
        return super().form_valid(form)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        fc = self.get_form_class()
        if isinstance(fc, type) and issubclass(fc, BaseDashboardForm):
            kwargs["request"] = self.request
        return kwargs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["current_staff"] = self._current_staff()
        return ctx


class DashboardLoginView(View):
    """手机号 + 验证码登录，身份写 session['staff_id']。"""

    template_name = "dashboard/login.html"

    def dispatch(self, request, *args, **kwargs):
        # 已登录员工直接进后台
        if request.method == "GET" and get_current_staff(request) is not None:
            return HttpResponseRedirect(reverse_lazy("dashboard:index"))
        return super().dispatch(request, *args, **kwargs)

    def get(self, request):
        ctx = {"form": DashboardLoginForm()}
        ctx.update(self._debug_context())
        return render(request, self.template_name, ctx)

    def post(self, request):
        form = DashboardLoginForm(request.POST)
        if form.is_valid():
            staff = form.cleaned_data["staff"]
            request.session["staff_id"] = staff.pk
            staff.last_login = timezone.now()
            staff.save(update_fields=["last_login"])
            return HttpResponseRedirect(reverse_lazy("dashboard:index"))
        ctx = {"form": form}
        ctx.update(self._debug_context())
        return render(request, self.template_name, ctx)

    def _debug_context(self):
        """测试模式：把发送验证码时暂存的 debug_code 取出来展示在登录页。"""
        session = self.request.session
        ctx = {"debug_code": None, "debug_phone": None}
        if session.get("debug_code"):
            ctx["debug_code"] = session.pop("debug_code")
            ctx["debug_phone"] = session.pop("debug_phone", None)
        return ctx


class DashboardSendCodeView(View):
    """发送员工登录验证码（测试模式：验证码存 session 显示在登录页）。"""

    def post(self, request):
        phone = (request.POST.get("phone") or "").strip()
        is_ajax = request.headers.get("X-Requested-With") == "XMLHttpRequest"

        if not phone:
            msg = "请输入手机号。"
            if is_ajax:
                return JsonResponse({"ok": False, "message": msg})
            messages.error(request, msg)
            return HttpResponseRedirect(reverse_lazy("dashboard:login"))

        if not Staff.objects.filter(phone=phone, is_active=True).exists():
            msg = "该手机号未登记为员工，请联系管理员。"
            if is_ajax:
                return JsonResponse({"ok": False, "message": msg})
            messages.error(request, msg)
            return HttpResponseRedirect(reverse_lazy("dashboard:login"))

        last = (
            SmsCode.objects.filter(phone=phone, purpose=SmsCode.Purpose.STAFF_LOGIN)
            .order_by("-created_at")
            .first()
        )
        if last and (timezone.now() - last.created_at).total_seconds() < 60:
            msg = "发送过于频繁，请稍后再试。"
            if is_ajax:
                return JsonResponse({"ok": False, "message": msg})
            messages.error(request, msg)
            return HttpResponseRedirect(reverse_lazy("dashboard:login"))

        code = f"{random.randint(0, 999999):06d}"
        SmsCode.objects.create(phone=phone, code=code, purpose=SmsCode.Purpose.STAFF_LOGIN)
        if getattr(settings, "SMS_TEST_MODE", True):
            request.session["debug_code"] = code
            request.session["debug_phone"] = phone
            print(f"[SMS] 员工验证码: {code} -> {phone}")
            msg = "验证码已发送（测试模式）。"
            if is_ajax:
                return JsonResponse({"ok": True, "message": msg, "debug_code": code})
            messages.success(request, msg)
        else:
            msg = "验证码已发送。"
            if is_ajax:
                return JsonResponse({"ok": True, "message": msg})
            messages.success(request, msg)

        return HttpResponseRedirect(reverse_lazy("dashboard:login"))


class DashboardLogoutView(View):
    def get(self, request):
        return self._logout(request)

    def post(self, request):
        return self._logout(request)

    def _logout(self, request):
        request.session.flush()
        return HttpResponseRedirect(reverse_lazy("dashboard:login"))


class DashboardIndexView(CompanyScopedViewMixin, TemplateView):
    template_name = "dashboard/index.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        staff = self._current_staff()
        company = staff.company if staff else None
        if company is None:
            ctx["no_company"] = True
            return ctx
        cid = company.id
        ctx["company"] = company
        ctx["case_count"] = Case.objects.filter(company_id=cid, status=CommonStatus.ACTIVE).count()
        ctx["project_count"] = ProjectProgress.objects.filter(
            company_id=cid, status=CommonStatus.ACTIVE
        ).count()
        # 客户为全局表，与客户列表页范围一致
        ctx["customer_count"] = Customer.objects.count()
        ctx["staff_count"] = Staff.objects.filter(company_id=cid).count()
        ctx["recent_projects"] = (
            ProjectProgress.objects.filter(company_id=cid, status=CommonStatus.ACTIVE)
            .select_related("customer", "staff")
            .order_by("-created_at")[:5]
        )
        return ctx


class CompanyUpdateView(CompanyScopedViewMixin, UpdateView):
    model = Company
    form_class = CompanyForm
    template_name = "dashboard/company_form.html"
    success_url = reverse_lazy("dashboard:company")

    def get_object(self, queryset=None):
        cid = self._current_staff().company_id
        if not cid:
            raise PermissionDenied
        return Company.objects.get(id=cid)

    def form_valid(self, form):
        messages.success(self.request, "公司信息已更新")
        return super().form_valid(form)


class CaseListView(CompanyScopedViewMixin, ListView):
    model = Case
    template_name = "dashboard/case_list.html"
    context_object_name = "cases"
    paginate_by = 20
    ordering = ["-created_at"]

    def get_queryset(self):
        return super().get_queryset().select_related("company")


class CaseCreateView(CompanyScopedViewMixin, CreateView):
    model = Case
    form_class = CaseForm
    template_name = "dashboard/case_form.html"
    success_url = reverse_lazy("dashboard:case_list")

    def form_valid(self, form):
        messages.success(self.request, "案例已创建")
        return super().form_valid(form)


class CaseUpdateView(CompanyScopedViewMixin, UpdateView):
    model = Case
    form_class = CaseForm
    template_name = "dashboard/case_form.html"

    def get_success_url(self):
        return reverse_lazy("dashboard:case_update", kwargs={"pk": self.object.pk})

    def form_valid(self, form):
        messages.success(self.request, "案例已更新")
        return super().form_valid(form)


class CaseDeleteView(CompanyScopedViewMixin, DeleteView):
    model = Case
    template_name = "dashboard/confirm_delete.html"
    success_url = reverse_lazy("dashboard:case_list")

    def delete(self, request, *args, **kwargs):
        obj = self.get_object()
        obj.delete()  # 软删：status=INACTIVE
        messages.success(request, "案例已删除")
        return HttpResponseRedirect(self.get_success_url())


class ProjectListView(CompanyScopedViewMixin, ListView):
    model = ProjectProgress
    template_name = "dashboard/project_list.html"
    context_object_name = "projects"
    paginate_by = 20
    ordering = ["-created_at"]

    def get_queryset(self):
        return super().get_queryset().select_related("customer", "staff").prefetch_related("stages")


class ProjectCreateView(CompanyScopedViewMixin, CreateView):
    model = ProjectProgress
    form_class = ProjectForm
    template_name = "dashboard/project_form.html"

    def get_success_url(self):
        return reverse_lazy("dashboard:project_update", kwargs={"pk": self.object.pk})

    def get_context_data(self, **kwargs):
        if "stage_formset" not in kwargs:
            kwargs["stage_formset"] = StageFormSet(instance=getattr(self, "object", None))
        return super().get_context_data(**kwargs)

    def post(self, request, *args, **kwargs):
        self.object = None
        form = self.get_form()
        formset = StageFormSet(request.POST, request.FILES)
        if form.is_valid() and formset.is_valid():
            form.instance.company = self._current_staff().company
            self.object = form.save()
            formset.instance = self.object
            formset.save()
            messages.success(request, "项目已创建")
            return HttpResponseRedirect(self.get_success_url())
        return self.render_to_response(self.get_context_data(form=form, stage_formset=formset))


class ProjectUpdateView(CompanyScopedViewMixin, UpdateView):
    model = ProjectProgress
    form_class = ProjectForm
    template_name = "dashboard/project_form.html"

    def get_success_url(self):
        return reverse_lazy("dashboard:project_update", kwargs={"pk": self.object.pk})

    def get_context_data(self, **kwargs):
        if "stage_formset" not in kwargs:
            data = self.request.POST if self.request.method == "POST" else None
            files = self.request.FILES if self.request.method == "POST" else None
            kwargs["stage_formset"] = StageFormSet(
                data, files, instance=getattr(self, "object", None)
            )
        return super().get_context_data(**kwargs)

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        form = self.get_form()
        formset = StageFormSet(request.POST, request.FILES, instance=self.object)
        if form.is_valid() and formset.is_valid():
            self.object = form.save()
            formset.save()
            messages.success(request, "项目已更新")
            return HttpResponseRedirect(self.get_success_url())
        return self.render_to_response(self.get_context_data(form=form, stage_formset=formset))


class ProjectDeleteView(CompanyScopedViewMixin, DeleteView):
    model = ProjectProgress
    template_name = "dashboard/confirm_delete.html"
    success_url = reverse_lazy("dashboard:project_list")

    def delete(self, request, *args, **kwargs):
        obj = self.get_object()
        obj.delete()  # 软删：stages 不触碰，随父项目被过滤隐藏
        messages.success(request, "项目已删除")
        return HttpResponseRedirect(self.get_success_url())


class CustomerListView(CompanyScopedViewMixin, ListView):
    model = Customer
    template_name = "dashboard/customer_list.html"
    context_object_name = "customers"
    paginate_by = 20

    def get_queryset(self):
        # 客户为全局表（仅超管维护），员工只读查看全部
        qs = Customer.objects.all()
        q = self.request.GET.get("q", "").strip()
        if q:
            qs = qs.filter(Q(name__icontains=q) | Q(phone__icontains=q))
        return qs.order_by("-created_at")


class CustomerDetailView(CompanyScopedViewMixin, DetailView):
    model = Customer
    template_name = "dashboard/customer_detail.html"
    context_object_name = "customer"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        qs = self.object.projects.select_related("company", "staff").order_by("-created_at")
        # 客户为全局表，但关联项目只展示本公司的，避免泄露他租户项目
        qs = qs.filter(company_id=self._current_staff().company_id)
        ctx["projects"] = qs
        return ctx


class StaffListView(CompanyScopedViewMixin, ListView):
    model = Staff
    template_name = "dashboard/staff_list.html"
    context_object_name = "staff_list"

    def get_queryset(self):
        qs = super().get_queryset()  # 已按本公司过滤
        return qs.select_related("company").order_by("-is_active", "name")


class StaffCreateView(CompanyScopedViewMixin, CreateView):
    model = Staff
    form_class = StaffCreateForm
    template_name = "dashboard/staff_form.html"
    success_url = reverse_lazy("dashboard:staff_list")

    def form_valid(self, form):
        messages.success(self.request, "员工已创建")
        return super().form_valid(form)


class StaffUpdateView(CompanyScopedViewMixin, UpdateView):
    model = Staff
    form_class = StaffEditForm
    template_name = "dashboard/staff_form.html"

    def get_success_url(self):
        return reverse_lazy("dashboard:staff_update", kwargs={"pk": self.object.pk})

    def form_valid(self, form):
        messages.success(self.request, "员工已更新")
        return super().form_valid(form)


# ============================================================
# 前台 API（/api/）
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
        qs = Case.objects.select_related("company").filter(status=CommonStatus.ACTIVE)
        company_id = self.request.query_params.get("company")
        if company_id:
            qs = qs.filter(company_id=company_id)
        return qs


class PublicCaseDetail(generics.RetrieveAPIView):
    """案例详情（免登录只读）"""

    authentication_classes = []
    permission_classes = [permissions.AllowAny]
    serializer_class = CaseSerializer
    queryset = Case.objects.filter(status=CommonStatus.ACTIVE)


class CustomerAuthentication(BaseAuthentication):
    """用 CustomerToken 认证客户。"""

    keyword = "Bearer"

    def authenticate(self, request):
        auth = request.META.get("HTTP_AUTHORIZATION", "")
        if not auth:
            return None
        try:
            parts = auth.split()
            if len(parts) != 2 or parts[0].lower() != "bearer":
                return None
            key = parts[1]
        except Exception:
            return None
        try:
            token = CustomerToken.objects.select_related("customer").get(
                key=key,
                expires_at__gt=timezone.now(),
            )
        except CustomerToken.DoesNotExist:
            raise AuthenticationFailed("登录已失效，请重新登录")
        return (token.customer, token)


class IsCustomer(permissions.BasePermission):
    """仅已认证客户可访问。"""

    def has_permission(self, request, view):
        return isinstance(request.user, Customer)


class SendCodeView(APIView):
    """发送客户短信验证码（测试模式：验证码打印日志并随响应返回）。"""

    authentication_classes = []
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        phone = (request.data.get("phone") or "").strip()
        if not phone:
            return Response({"detail": "请输入手机号"}, status=status.HTTP_400_BAD_REQUEST)
        if not Customer.objects.filter(phone=phone).exists():
            return Response(
                {"detail": "该手机号未登记，请联系公司工作人员"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        last = (
            SmsCode.objects.filter(phone=phone, purpose=SmsCode.Purpose.CUSTOMER_LOGIN)
            .order_by("-created_at")
            .first()
        )
        if last and (timezone.now() - last.created_at).total_seconds() < 60:
            return Response(
                {"detail": "发送过于频繁，请稍后再试"},
                status=status.HTTP_429_TOO_MANY_REQUESTS,
            )
        code = f"{random.randint(0, 999999):06d}"
        SmsCode.objects.create(phone=phone, code=code, purpose=SmsCode.Purpose.CUSTOMER_LOGIN)
        if getattr(settings, "SMS_TEST_MODE", True):
            # 测试模式：不真正发短信，验证码打印到日志并返回，方便联调
            print(f"[SMS] 验证码: {code} -> {phone}")
            return Response({"detail": "验证码已发送（测试模式）", "debug_code": code})
        # TODO: 接入阿里云短信后在此处调用发送
        return Response({"detail": "验证码已发送"})


class CustomerLoginView(APIView):
    """手机号 + 验证码 登录，签发客户 token。"""

    authentication_classes = []
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        phone = (request.data.get("phone") or "").strip()
        code = (request.data.get("code") or "").strip()
        if not phone or not code:
            return Response({"detail": "请输入手机号和验证码"}, status=status.HTTP_400_BAD_REQUEST)
        sms = (
            SmsCode.objects.filter(
                phone=phone, code=code, used=False, purpose=SmsCode.Purpose.CUSTOMER_LOGIN
            )
            .order_by("-created_at")
            .first()
        )
        if not sms:
            return Response({"detail": "验证码错误或已过期"}, status=status.HTTP_400_BAD_REQUEST)
        if (timezone.now() - sms.created_at).total_seconds() > 300:
            return Response(
                {"detail": "验证码已过期，请重新获取"}, status=status.HTTP_400_BAD_REQUEST
            )
        try:
            customer = Customer.objects.get(phone=phone)
        except Customer.DoesNotExist:
            return Response(
                {"detail": "该手机号未登记，请联系公司工作人员"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        sms.used = True
        sms.save(update_fields=["used"])
        token = CustomerToken.objects.create(
            key=secrets.token_urlsafe(32),
            customer=customer,
            expires_at=timezone.now() + timedelta(days=30),
        )
        return Response(
            {
                "token": token.key,
                "customer": CustomerSerializer(customer).data,
            }
        )


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
        qs = (
            ProjectProgress.objects.select_related("company", "customer", "staff")
            .filter(customer=self.request.user, status=CommonStatus.ACTIVE)
            .order_by("-created_at")
        )
        company_id = self.request.query_params.get("company")
        if company_id:
            qs = qs.filter(company_id=company_id)
        return qs


class CustomerProjectDetailView(generics.RetrieveAPIView):
    """当前客户的单个项目详情。"""

    authentication_classes = [CustomerAuthentication]
    permission_classes = [IsCustomer]
    serializer_class = ProjectProgressSerializer

    def get_queryset(self):
        return ProjectProgress.objects.select_related("company", "customer", "staff").filter(
            customer=self.request.user, status=CommonStatus.ACTIVE
        )
