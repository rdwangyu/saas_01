"""视图：/dashboard/ 后台（员工手机号+密码登录 + 公司隔离）与 /api/ 前台（公开 + 订单绑定）API。

后台：员工用手机号+密码登录，身份存 session['staff_id']；数据按当前员工所属公司隔离，
有 status 的模型只显示 ACTIVE。删除语义：员工软删（status=INACTIVE）。
前台：公开只读接口 + 小程序凭订单编号绑定项目。
"""

import base64
from urllib.parse import quote

from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.db.models import Q
from django.http import HttpResponseRedirect
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
from rest_framework.response import Response
from rest_framework.views import APIView

from .forms_dashboard import (
    BaseDashboardForm,
    CaseForm,
    CompanyForm,
    CustomerForm,
    DashboardLoginForm,
    ProjectForm,
    StageFormSet,
    StaffPasswordForm,
    get_current_staff,
)
from .models import (
    Case,
    CommonStatus,
    Company,
    Customer,
    ProjectProgress,
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
    """租户后台基类：手机号+密码登录 + 按当前员工所属公司隔离。"""

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
        # 删除确认表单等无 instance，仅对 ModelForm 设置公司
        # 注意：新对象 FK 未赋值时访问 instance.company 会抛异常，hasattr 返回 False，
        # 因此用 company_id（普通整型属性）判断模型是否有该字段。
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


class DashboardLoginView(View):
    """手机号 + 密码登录，身份写 session['staff_id']。"""

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
        # 按当前员工所属公司过滤（CompanyScopedViewMixin 已按 company 过滤）
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

    def delete(self, request, *args, **kwargs):
        obj = self.get_object()
        obj.delete()
        messages.success(request, "客户已删除")
        return HttpResponseRedirect(self.get_success_url())


class CustomerDetailView(CompanyScopedViewMixin, DetailView):
    model = Customer
    template_name = "dashboard/customer_detail.html"
    context_object_name = "customer"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        qs = self.object.projects.select_related("company", "staff").order_by("-created_at")
        # 客户归属本公司，关联项目只展示本公司的
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
