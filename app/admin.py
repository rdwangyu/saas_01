from django import forms
from django.contrib import admin
from django.utils.html import format_html

from .widgets import SimpleFileInput

from .models import (
    Company,
    Customer,
    Staff,
    Case,
    ProjectProgress,
    ProjectStage,
)


class SuperuserOnlyMixin:
    """admin 仅超级管理员可用；公司管理员走 /dashboard/ 租户后台。"""

    def has_module_permission(self, request):
        return request.user.is_superuser

    def has_view_permission(self, request, obj=None):
        return request.user.is_superuser

    def has_add_permission(self, request):
        return request.user.is_superuser

    def has_change_permission(self, request, obj=None):
        return request.user.is_superuser

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser


def image_preview(obj, field_name, width=80):
    img = getattr(obj, field_name, None)
    if img and hasattr(img, "url"):
        return format_html(
            '<img src="{}" style="max-width:{}px; max-height:{}px; border-radius:4px;" />',
            img.url,
            width,
            width,
        )
    return "-"


class CompanyForm(forms.ModelForm):
    class Meta:
        model = Company
        fields = "__all__"
        widgets = {
            "logo": SimpleFileInput(),
        }

    def clean_credit_code(self):
        val = self.cleaned_data.get("credit_code")
        return val.upper() if val else val


@admin.register(Company)
class CompanyAdmin(SuperuserOnlyMixin, admin.ModelAdmin):
    form = CompanyForm
    list_display = [
        "id",
        "logo_preview",
        "name",
        "credit_code",
        "phone",
        "status",
        "max_video_size_display",
        "user_count",
        "case_count",
        "project_count",
        "created_at",
    ]
    list_display_links = ["id", "name"]
    list_filter = ["status", "created_at"]
    search_fields = ["name", "credit_code", "phone", "address"]
    readonly_fields = ["created_at"]
    date_hierarchy = "created_at"

    fieldsets = (
        (
            "基本信息",
            {
                "fields": ("name", "credit_code", "logo", "description"),
            },
        ),
        (
            "联系方式",
            {
                "fields": ("phone", "address"),
            },
        ),
        (
            "成立日期",
            {
                "fields": ("established_date",),
            },
        ),
        (
            "视频限制",
            {
                "fields": ("max_video_size",),
                "description": "视频上传大小限制，影响案例和项目进度。",
            },
        ),
        (
            "状态",
            {
                "fields": ("status", "created_at"),
            },
        ),
    )

    def logo_preview(self, obj):
        return image_preview(obj, "logo", width=60)

    logo_preview.short_description = "Logo"

    def max_video_size_display(self, obj):
        return f"{obj.max_video_size}MB"

    max_video_size_display.short_description = "视频大小限制"

    def user_count(self, obj):
        return obj.staff.count()

    user_count.short_description = "员工数"

    def case_count(self, obj):
        return obj.cases.count()

    case_count.short_description = "案例数"

    def project_count(self, obj):
        return obj.projects.count()

    project_count.short_description = "项目数"


@admin.register(Customer)
class CustomerAdmin(SuperuserOnlyMixin, admin.ModelAdmin):
    """客户表：全局表，仅超级管理员维护。"""

    list_display = [
        "id",
        "name",
        "phone",
        "address",
        "company_names",
        "project_count",
        "created_at",
    ]
    list_display_links = ["id", "name"]
    search_fields = ["name", "phone", "address"]
    readonly_fields = ["created_at"]

    fieldsets = (
        (
            "基本信息",
            {
                "fields": ("name", "phone", "address"),
            },
        ),
        (
            "时间",
            {
                "fields": ("created_at",),
            },
        ),
    )

    def company_names(self, obj):
        """客户与公司的关系通过项目体现，列出其项目所在公司。"""
        names = set()
        for p in obj.projects.select_related("company"):
            if p.company:
                names.add(p.company.name)
        return "、".join(sorted(names)) or "—"

    company_names.short_description = "所属公司（按项目）"

    def project_count(self, obj):
        return obj.projects.count()

    project_count.short_description = "项目数"


@admin.register(Staff)
class StaffAdmin(SuperuserOnlyMixin, admin.ModelAdmin):
    """员工表（验证码登录，无密码）。"""

    list_display = [
        "name",
        "phone",
        "email",
        "company",
        "role_display",
        "is_active",
        "last_login",
        "created_at",
    ]
    list_display_links = ["phone"]
    list_filter = ["is_active", "company"]
    search_fields = ["name", "phone", "email", "company__name"]
    readonly_fields = ["created_at", "last_login"]

    fieldsets = (
        (
            "基本信息",
            {
                "fields": ("name", "phone", "email"),
            },
        ),
        (
            "公司与角色",
            {
                "fields": ("company", "role"),
            },
        ),
        (
            "状态",
            {
                "fields": ("is_active", "created_at", "last_login"),
            },
        ),
    )

    def role_display(self, obj):
        return obj.get_role_display()

    role_display.short_description = "角色"



@admin.register(Case)
class CaseAdmin(SuperuserOnlyMixin, admin.ModelAdmin):
    list_display = [
        "id",
        "cover_preview",
        "title",
        "company",
        "style",
        "area",
        "budget_display",
        "status",
        "created_at",
    ]
    list_display_links = ["id", "title"]
    list_filter = ["style", "created_at", "company"]
    search_fields = ["title", "description", "style", "company__name"]
    readonly_fields = ["created_at"]
    date_hierarchy = "created_at"

    fieldsets = (
        (
            "基本信息",
            {
                "fields": ("company", "title", "cover", "description"),
            },
        ),
        (
            "案例属性",
            {
                "fields": ("style", "area", "budget"),
            },
        ),
        (
            "视频",
            {
                "fields": ("video",),
            },
        ),
        (
            "状态",
            {
                "fields": ("status", "created_at"),
            },
        ),
    )

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("company")

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj=obj, **kwargs)

        if "cover" in form.base_fields:
            form.base_fields["cover"].widget = SimpleFileInput(
                attrs={"accept": "image/*"}
            )
        if "video" in form.base_fields:
            form.base_fields["video"].widget = SimpleFileInput(
                attrs={"accept": "video/*"}
            )

        return form

    def cover_preview(self, obj):
        return image_preview(obj, "cover", width=80)

    cover_preview.short_description = "封面"

    def budget_display(self, obj):
        if obj.budget:
            return obj.budget
        return "-"

    budget_display.short_description = "预算（万元）"

    def delete_model(self, request, obj):
        obj.hard_delete()

    def delete_queryset(self, request, queryset):
        for obj in queryset:
            obj.hard_delete()


class ProjectStageInline(admin.StackedInline):
    model = ProjectStage
    extra = 1
    can_delete = False
    fieldsets = (
        (
            None,
            {
                "fields": (
                    ("name",),
                    ("image_0", "image_1", "image_2"),
                    "description",
                ),
            },
        ),
    )
    ordering = ("created_at",)


@admin.register(ProjectProgress)
class ProjectProgressAdmin(SuperuserOnlyMixin, admin.ModelAdmin):
    list_display = [
        "id",
        "project_name",
        "customer",
        "staff",
        "stage_display",
        "company",
        "status",
        "created_at",
    ]
    list_display_links = ["id", "project_name"]
    list_filter = ["company", "created_at"]
    search_fields = [
        "project_name",
        "address",
        "company__name",
        "customer__name",
        "customer__phone",
        "staff__name",
    ]
    readonly_fields = ["created_at"]
    inlines = [ProjectStageInline]
    date_hierarchy = "created_at"

    fieldsets = (
        (
            "基本信息",
            {
                "fields": ("company", "project_name", "address"),
            },
        ),
        (
            "客户与负责人",
            {
                "fields": ("customer", "staff"),
            },
        ),
        (
            "状态",
            {
                "fields": ("status", "created_at"),
            },
        ),
    )

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .select_related("company", "customer", "staff")
            .prefetch_related("stages")
        )

    def stage_display(self, obj):
        return obj.current_stage_name

    stage_display.short_description = "当前进度"

    def delete_model(self, request, obj):
        # ProjectStage 无 status，FK 级联 raw delete 会遗留 OSS 文件，先逐条硬删清文件
        for stage in obj.stages.all():
            stage.delete()
        obj.hard_delete()

    def delete_queryset(self, request, queryset):
        for obj in queryset:
            for stage in obj.stages.all():
                stage.delete()
            obj.hard_delete()


admin.site.site_header = "白云企业管理"
admin.site.site_title = "白云企业管理"
admin.site.index_title = "控制面板"
