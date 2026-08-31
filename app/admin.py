from django import forms
from django.contrib import admin
from django.utils.html import format_html

from .models import (Case, Company, Customer, ProjectProgress, ProjectStage,
                     Staff)


def image_preview(obj, field_name, width=80):
    img = getattr(obj, field_name, None)
    if img:
        return format_html(
            '<img src="{}" style="max-width:{}px; max-height:{}px; border-radius:4px;" />',
            img,
            width,
            width,
        )
    return "-"


@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
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
class CustomerAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "name",
        "phone",
        "company",
        "contract",
        "project_count",
        "created_at",
    ]
    list_display_links = ["id", "name"]
    list_filter = ["company"]
    search_fields = ["name", "phone", "address", "contract", "company__name"]
    readonly_fields = ["created_at"]

    fieldsets = (
        (
            "基本信息",
            {
                "fields": ("company", "name", "phone", "address", "contract"),
            },
        ),
        (
            "时间",
            {
                "fields": ("created_at",),
            },
        ),
    )

    def project_count(self, obj):
        return obj.projects.count()

    project_count.short_description = "项目数"


class StaffAdminForm(forms.ModelForm):
    password1 = forms.CharField(label="密码", widget=forms.PasswordInput, required=False)
    password2 = forms.CharField(label="确认密码", widget=forms.PasswordInput, required=False)

    class Meta:
        model = Staff
        fields = ["name", "phone", "email", "company", "role", "is_active"]

    def clean(self):
        cleaned = super().clean()
        p1 = cleaned.get("password1")
        p2 = cleaned.get("password2")
        if p1 or p2:
            if p1 != p2:
                raise forms.ValidationError("两次输入的密码不一致。")
        if not self.instance.pk and not p1:
            raise forms.ValidationError("新建员工必须设置密码。")
        return cleaned

    def save(self, commit=True):
        staff = super().save(commit=False)
        p1 = self.cleaned_data.get("password1")
        if p1:
            staff.set_password(p1)
        if commit:
            staff.save()
        return staff


@admin.register(Staff)
class StaffAdmin(admin.ModelAdmin):
    form = StaffAdminForm
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
            "登录密码",
            {
                "fields": ("password1", "password2"),
                "description": "新建员工必填；留空则不修改原密码。",
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
class CaseAdmin(admin.ModelAdmin):
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


class ProjectProgressForm(forms.ModelForm):
    class Meta:
        model = ProjectProgress
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            company_id = self.instance.company_id
            # 根据当前对象的 company_id 来过滤外键字段的查询集
            self.fields['customer'].queryset = Customer.objects.filter(company_id=company_id)
            self.fields['staff'].queryset = Staff.objects.filter(company_id=company_id)

    
@admin.register(ProjectProgress)
class ProjectProgressAdmin(admin.ModelAdmin):
    form = ProjectProgressForm
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
        "project_no",
        "project_name",
        "address",
        "company__name",
        "customer__name",
        "customer__phone",
        "staff__name",
    ]
    readonly_fields = ["created_at"]
    date_hierarchy = "created_at"
    fieldsets = (
        (
            "基本信息",
            {
                "fields": ("company", "project_no", "project_name", "address"),
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
        obj.hard_delete()

    def delete_queryset(self, request, queryset):
        for obj in queryset:
            obj.hard_delete()


class ProjectStageAdminForm(forms.ModelForm):
    class Meta:
        model = ProjectStage
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # 编辑时按当前阶段所属公司过滤项目下拉框
        if self.instance and self.instance.pk:
            company_id = self.instance.project.company_id
            self.fields["project"].queryset = ProjectProgress.objects.filter(company_id=company_id)


@admin.register(ProjectStage)
class ProjectStageAdmin(admin.ModelAdmin):
    form = ProjectStageAdminForm
    list_display = [
        "id",
        "project",
        "name",
        "image_0_preview",
        "image_1_preview",
        "image_2_preview",
        "created_at",
    ]
    list_display_links = ["id", "name"]
    list_filter = ["project__company", "created_at"]
    search_fields = ["name", "project__project_name", "project__project_no"]
    readonly_fields = ["created_at"]
    date_hierarchy = "created_at"
    ordering = ("-created_at",)

    fieldsets = (
        (
            "所属项目",
            {
                "fields": ("project",),
            },
        ),
        (
            "阶段内容",
            {
                "fields": (("name",), ("image_0", "image_1", "image_2"), "description"),
            },
        ),
        (
            "时间",
            {
                "fields": ("created_at",),
            },
        ),
    )

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("project", "project__company")

    def image_0_preview(self, obj):
        return image_preview(obj, "image_0", width=60)

    image_0_preview.short_description = "图片1"

    def image_1_preview(self, obj):
        return image_preview(obj, "image_1", width=60)

    image_1_preview.short_description = "图片2"

    def image_2_preview(self, obj):
        return image_preview(obj, "image_2", width=60)

    image_2_preview.short_description = "图片3"

    def delete_model(self, request, obj):
        obj.delete()  # 模型自定义 delete：硬删并清理 OSS 图片

    def delete_queryset(self, request, queryset):
        for obj in queryset:
            obj.delete()

admin.site.site_header = "白云企业管理"
admin.site.site_title = "白云企业管理"
admin.site.index_title = "控制面板"
