import base64
import json
from urllib.parse import quote
from uuid import uuid4

from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.db.models import Q
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import get_object_or_404, render
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
from rest_framework.response import Response
from rest_framework.views import APIView

from .forms_dashboard import (
    BaseDashboardForm,
    CaseForm,
    CompanyForm,
    CustomerForm,
    DashboardLoginForm,
    ProjectForm,
    ProjectStageForm,
    StaffPasswordForm,
    get_current_staff,
)
from .oss_storage import OSSNotConfigured, sign_upload_url
from .models import (
    Case,
    CommonStatus,
    Company,
    Customer,
    ProjectProgress,
    ProjectStage,
    Staff,
)
from .serializers import (
    CaseSerializer,
    CompanySerializer,
    ProjectProgressSerializer,
)
from .wechat import WechatError, generate_company_code

# ============================================================
# 后台 dashboard（/dashboard/）
# ============================================================
class CompanyScopedViewMixin:
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
        instance = getattr(form, "instance", None)
        if instance is not None and hasattr(instance, "company_id"):
            instance.company = self._current_staff().company
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

    def _safe_next(self, default):
        """返回表单保存/取消后的回跳地址：仅接受站内路径，防开放重定向。"""
        next_url = self.request.GET.get("next", "").strip()
        if next_url.startswith("/") and not next_url.startswith("//"):
            return next_url
        return default


class DashboardLoginView(View):
    template_name = "dashboard/login.html"

    def dispatch(self, request, *args, **kwargs):
        # 已登录员工直接进后台
        if request.method == "GET" and get_current_staff(request) is not None:
            return HttpResponseRedirect(reverse_lazy("dashboard:index"))
        return super().dispatch(request, *args, **kwargs)

    def get(self, request):
        return render(request, self.template_name, {"form": DashboardLoginForm()})

    def post(self, request):
        form = DashboardLoginForm(request.POST)
        if form.is_valid():
            staff = form.cleaned_data["staff"]
            request.session["staff_id"] = staff.pk
            staff.last_login = timezone.now()
            staff.save(update_fields=["last_login"])
            return HttpResponseRedirect(reverse_lazy("dashboard:index"))
        return render(request, self.template_name, {"form": form})


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
        # 客户归属本公司
        ctx["customer_count"] = Customer.objects.filter(company_id=cid).count()
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
        qs = super().get_queryset().select_related("company")
        q = self.request.GET.get("q", "").strip()
        if q:
            qs = qs.filter(Q(title__icontains=q) | Q(style__icontains=q))
        return qs


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

    def form_valid(self, form):
        # Django 6 的 DeleteView 走 form_valid，不调用视图层的 delete()
        self.object.delete()  # 软删：status=INACTIVE
        messages.success(self.request, "案例已删除")
        return HttpResponseRedirect(self.get_success_url())


class ProjectListView(CompanyScopedViewMixin, ListView):
    model = ProjectProgress
    template_name = "dashboard/project_list.html"
    context_object_name = "projects"
    paginate_by = 20
    ordering = ["-created_at"]

    def get_queryset(self):
        qs = super().get_queryset().select_related("customer", "staff").prefetch_related("stages")
        q = self.request.GET.get("q", "").strip()
        if q:
            qs = qs.filter(Q(project_name__icontains=q) | Q(address__icontains=q))
        return qs


class ProjectCreateView(CompanyScopedViewMixin, CreateView):
    model = ProjectProgress
    form_class = ProjectForm
    template_name = "dashboard/project_form.html"

    def get_success_url(self):
        return reverse_lazy("dashboard:project_list")

    def form_valid(self, form):
        messages.success(self.request, "项目已创建")
        return super().form_valid(form)


class ProjectUpdateView(CompanyScopedViewMixin, UpdateView):
    model = ProjectProgress
    form_class = ProjectForm
    template_name = "dashboard/project_form.html"

    def get_success_url(self):
        # 从详情页进入则回详情页；否则（从列表进入）回列表
        default = reverse_lazy("dashboard:project_detail", kwargs={"pk": self.object.pk})
        return self._safe_next(default)

    def form_valid(self, form):
        messages.success(self.request, "项目已更新")
        return super().form_valid(form)


class ProjectDeleteView(CompanyScopedViewMixin, DeleteView):
    model = ProjectProgress
    template_name = "dashboard/confirm_delete.html"
    success_url = reverse_lazy("dashboard:project_list")

    def form_valid(self, form):
        # Django 6 的 DeleteView 走 form_valid；硬删除连带移除阶段并清理 OSS 图片
        # （移除阶段目前只能通过删除整个项目实现）
        self.object.hard_delete()
        messages.success(self.request, "项目已删除")
        return HttpResponseRedirect(self.get_success_url())


class ProjectDetailView(CompanyScopedViewMixin, DetailView):
    """项目详情：展示全部项目阶段，并提供“添加阶段”入口。"""

    model = ProjectProgress
    template_name = "dashboard/project_detail.html"
    context_object_name = "project"

    def get_queryset(self):
        return super().get_queryset().select_related("customer", "staff").prefetch_related("stages")


class ProjectStageCreateView(CompanyScopedViewMixin, CreateView):
    """新增阶段：从项目列表进入独立页面编辑，保存后返回项目列表。"""

    model = ProjectStage
    form_class = ProjectStageForm
    template_name = "dashboard/project_stage_form.html"

    def dispatch(self, request, *args, **kwargs):
        staff = self._current_staff()
        if staff is None:
            return HttpResponseRedirect(self.login_url)
        self.project = get_object_or_404(
            ProjectProgress, pk=kwargs["pk"], company_id=staff.company_id
        )
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["project"] = self.project
        return ctx

    def form_valid(self, form):
        form.instance.project = self.project
        messages.success(self.request, "阶段已添加")
        return super().form_valid(form)

    def get_success_url(self):
        default = reverse_lazy("dashboard:project_detail", kwargs={"pk": self.project.pk})
        return self._safe_next(default)


class ProjectStageUpdateView(CompanyScopedViewMixin, UpdateView):
    """编辑阶段：独立页面编辑后返回项目列表。"""

    model = ProjectStage
    form_class = ProjectStageForm
    template_name = "dashboard/project_stage_form.html"

    def get_queryset(self):
        return ProjectStage.objects.filter(
            project__company_id=self._current_staff().company_id
        )

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["project"] = self.object.project
        return ctx

    def form_valid(self, form):
        messages.success(self.request, "阶段已更新")
        return super().form_valid(form)

    def get_success_url(self):
        default = reverse_lazy("dashboard:project_detail", kwargs={"pk": self.object.project_id})
        return self._safe_next(default)


class CustomerListView(CompanyScopedViewMixin, ListView):
    model = Customer
    template_name = "dashboard/customer_list.html"
    context_object_name = "customers"
    paginate_by = 20

    def get_queryset(self):
        qs = super().get_queryset()
        q = self.request.GET.get("q", "").strip()
        if q:
            qs = qs.filter(Q(name__icontains=q) | Q(phone__icontains=q))
        return qs.order_by("-created_at")


class CustomerCreateView(CompanyScopedViewMixin, CreateView):
    model = Customer
    form_class = CustomerForm
    template_name = "dashboard/customer_form.html"
    success_url = reverse_lazy("dashboard:customer_list")

    def form_valid(self, form):
        messages.success(self.request, "客户已创建")
        return super().form_valid(form)


class CustomerUpdateView(CompanyScopedViewMixin, UpdateView):
    model = Customer
    form_class = CustomerForm
    template_name = "dashboard/customer_form.html"

    def get_success_url(self):
        return reverse_lazy("dashboard:customer_list")

    def form_valid(self, form):
        messages.success(self.request, "客户已更新")
        return super().form_valid(form)


class CustomerDeleteView(CompanyScopedViewMixin, DeleteView):
    model = Customer
    template_name = "dashboard/confirm_delete.html"
    success_url = reverse_lazy("dashboard:customer_list")

    def form_valid(self, form):
        # Django 6 的 DeleteView 走 form_valid，不调用视图层的 delete()
        self.object.delete()
        messages.success(self.request, "客户已删除")
        return HttpResponseRedirect(self.get_success_url())


class CustomerDetailView(CompanyScopedViewMixin, DetailView):
    model = Customer
    template_name = "dashboard/customer_detail.html"
    context_object_name = "customer"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        qs = self.object.projects.select_related("company", "staff").order_by("-created_at")
        qs = qs.filter(company_id=self._current_staff().company_id)
        ctx["projects"] = qs
        return ctx


class StaffListView(CompanyScopedViewMixin, ListView):
    model = Staff
    template_name = "dashboard/staff_list.html"
    context_object_name = "staff_list"
    paginate_by = 20

    def get_queryset(self):
        qs = super().get_queryset()
        q = self.request.GET.get("q", "").strip()
        if q:
            qs = qs.filter(Q(name__icontains=q) | Q(phone__icontains=q) | Q(email__icontains=q))
        return qs.select_related("company").order_by("-is_active", "name")


class StaffPasswordChangeView(CompanyScopedViewMixin, View):
    """员工自助修改自己的密码。"""

    template_name = "dashboard/staff_password.html"

    def get(self, request):
        form = StaffPasswordForm(staff=self._current_staff())
        return render(request, self.template_name, {"form": form})

    def post(self, request):
        form = StaffPasswordForm(request.POST, staff=self._current_staff())
        if form.is_valid():
            form.save()
            messages.success(request, "密码已修改")
            return HttpResponseRedirect(reverse_lazy("dashboard:index"))
        return render(request, self.template_name, {"form": form})


# ============================================================
# 前台 API（/api/）
# ============================================================


class PublicCompanyList(generics.ListAPIView):
    """公司列表（启用的公司，免登录只读，供扫码校验/选择公司）"""

    authentication_classes = []
    permission_classes = [permissions.AllowAny]
    serializer_class = CompanySerializer
    pagination_class = None

    def get_queryset(self):
        return Company.objects.filter(status=CommonStatus.ACTIVE)


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


class BindProjectView(APIView):
    """小程序订单绑定：凭项目编号返回项目进度 + 客户 + 公司信息。"""

    authentication_classes = []
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        project_no = (request.data.get("project_no") or "").strip()
        if not project_no:
            return Response({"detail": "请输入订单编号"}, status=status.HTTP_400_BAD_REQUEST)
        try:
            project = ProjectProgress.objects.select_related("company", "customer", "staff").get(
                project_no=project_no, status=CommonStatus.ACTIVE
            )
        except ProjectProgress.DoesNotExist:
            return Response({"detail": "订单编号不正确"}, status=status.HTTP_400_BAD_REQUEST)
        return Response(ProjectProgressSerializer(project).data)


# ============================================================
# OSS 直传：生成 PUT 签名 URL
# ============================================================

OSS_ALLOWED_DIRS = {"company_case", "company_logo", "company_project_progress"}


class OssUploadUrlView(View):
    """登录员工/超管获取 OSS 直传签名 URL（前端 PUT 上传，只保存 URL）。"""

    def dispatch(self, request, *args, **kwargs):
        staff = get_current_staff(request)
        is_admin = request.user.is_authenticated and request.user.is_superuser
        if staff is None and not is_admin:
            return JsonResponse({"detail": "无权限"}, status=403)
        return super().dispatch(request, *args, **kwargs)

    def post(self, request):
        try:
            data = json.loads(request.body)
        except (ValueError, TypeError):
            data = request.POST
        dir_name = (data.get("dir") or "").strip()
        filename = (data.get("filename") or "").strip()
        if dir_name not in OSS_ALLOWED_DIRS:
            return JsonResponse({"detail": "非法目录"}, status=400)
        if not filename:
            return JsonResponse({"detail": "缺少文件名"}, status=400)

        staff = get_current_staff(request)
        company_id = staff.company_id if staff else None
        ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else "bin"
        key = f"{dir_name}/{company_id or 'admin'}_{uuid4().hex[:8]}.{ext}"
        try:
            upload_url, file_url = sign_upload_url(key)
        except OSSNotConfigured as exc:
            return JsonResponse({"detail": str(exc)}, status=500)
        return JsonResponse({"upload_url": upload_url, "file_url": file_url})


# ============================================================
# 超管工具：生成公司小程序码
# ============================================================


class QrCodeView(View):
    """超管专用：选择公司生成小程序码（客户扫码直接进入该公司）。"""

    template_name = "qr_tool.html"

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated or not request.user.is_superuser:
            next_url = quote(str(reverse_lazy("qr")))
            return HttpResponseRedirect(f"{reverse_lazy('admin:login')}?next={next_url}")
        return super().dispatch(request, *args, **kwargs)

    def _companies(self):
        return Company.objects.filter(status=CommonStatus.ACTIVE).order_by("name")

    def get(self, request):
        return render(request, self.template_name, {"companies": self._companies()})

    def post(self, request):
        raw_id = (request.POST.get("company_id") or "").strip()
        company = Company.objects.filter(pk=int(raw_id)).first() if raw_id.isdigit() else None
        ctx = {"companies": self._companies(), "company": company}
        if company is None:
            messages.error(request, "请选择要生成二维码的公司。")
            return render(request, self.template_name, ctx)
        try:
            png = generate_company_code(company.pk)
        except WechatError as exc:
            messages.error(request, str(exc))
            return render(request, self.template_name, ctx)
        ctx["qr_data"] = base64.b64encode(png).decode()
        return render(request, self.template_name, ctx)
