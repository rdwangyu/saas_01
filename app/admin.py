"""
装修公司 SaaS 系统 — Django Admin 配置

关键设计：
1. 公司管理员只能看到自己公司的业务数据
2. 新增数据时 company 自动绑定
3. 超级管理员可以管理全部数据
4. 列表展示、搜索、过滤、图片预览、JSON 友好显示
"""

from django import forms
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.html import format_html, format_html_join
from django.db.models import Count

from .models import (
    Company, User, Case, ProjectProgress,
)
from .permissions import CompanyAdminMixin


# ============================================================
# 通用工具函数
# ============================================================
def image_preview(obj, field_name, width=80):
    """生成图片预览 HTML 片段。"""
    img = getattr(obj, field_name, None)
    if img and hasattr(img, 'url'):
        return format_html(
            '<img src="{}" style="max-width:{}px; max-height:{}px; border-radius:4px;" />',
            img.url, width, width,
        )
    return '-'


def json_display(value, max_items=5):
    """将 JSON 列表/字典友好渲染为 HTML。"""
    if not value:
        return '-'
    if isinstance(value, list):
        items = value[:max_items]
        html = '<ul style="margin:0; padding-left:16px;">'
        for item in items:
            if isinstance(item, str) and item.startswith(('http://', 'https://', '/')):
                html += f'<li><a href="{item}" target="_blank">📎 链接</a></li>'
            else:
                html += f'<li>{item}</li>'
        if len(value) > max_items:
            html += f'<li>... 共 {len(value)} 项</li>'
        html += '</ul>'
        return format_html(html)
    return format_html('<pre style="margin:0; font-size:12px;">{}</pre>', str(value))


# ============================================================
# Company Admin
# ============================================================
@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = [
        'id', 'logo_preview', 'name', 'phone', 'status',
        'max_video_size_display',
        'user_count', 'case_count', 'project_count', 'created_at',
    ]
    list_display_links = ['id', 'name']
    list_filter = ['status', 'created_at']
    search_fields = ['name', 'phone', 'address']
    readonly_fields = ['created_at']
    date_hierarchy = 'created_at'

    fieldsets = (
        ('基本信息', {
            'fields': ('name', 'logo', 'description'),
        }),
        ('联系方式', {
            'fields': ('phone', 'address'),
        }),
        ('项目配置', {
            'fields': ('progress_stages',),
            'description': '以英文逗号分隔的阶段名称，例如: 开始,水电,泥瓦,木工,验收',
        }),
        ('视频限制', {
            'fields': ('max_video_size',),
            'description': '视频上传大小限制，影响案例和项目进度（仅超级管理员可配置）。',
        }),
        ('状态', {
            'fields': ('status', 'created_at'),
        }),
    )

    def _is_company_user(self, user):
        return user.is_staff and user.company is not None

    def has_module_permission(self, request):
        if request.user.is_superuser:
            return True
        return self._is_company_user(request.user)

    def has_view_permission(self, request, obj=None):
        if request.user.is_superuser:
            return True
        return self._is_company_user(request.user)

    def has_add_permission(self, request):
        return request.user.is_superuser

    def has_change_permission(self, request, obj=None):
        if request.user.is_superuser:
            return True
        if obj is not None:
            return obj == request.user.company
        return self._is_company_user(request.user)

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        return qs.filter(id=request.user.company_id)

    def get_form(self, request, obj=None, **kwargs):
        """Logo 使用 FileInput（无清除复选框）。"""
        form = super().get_form(request, obj=obj, **kwargs)
        if 'logo' in form.base_fields:
            form.base_fields['logo'].widget = forms.FileInput()
        return form

    def logo_preview(self, obj):
        return image_preview(obj, 'logo', width=60)
    logo_preview.short_description = 'Logo'

    def max_video_size_display(self, obj):
        return f'{obj.max_video_size}MB'
    max_video_size_display.short_description = '视频大小限制'

    def get_readonly_fields(self, request, obj=None):
        """非超级管理员不能编辑项目阶段、视频大小限制和状态。"""
        readonly = list(super().get_readonly_fields(request, obj) or [])
        if not request.user.is_superuser:
            for f in ['progress_stages', 'max_video_size', 'status']:
                if f not in readonly:
                    readonly.append(f)
        return readonly

    def user_count(self, obj):
        return obj.users.count()
    user_count.short_description = '用户数'

    def case_count(self, obj):
        return obj.cases.count()
    case_count.short_description = '案例数'

    def project_count(self, obj):
        return obj.projects.count()
    project_count.short_description = '项目数'


# ============================================================
# User Admin
# ============================================================
@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """
    自定义用户管理：
    - 超级管理员可管理全部用户
    - 非超级管理员（公司管理员）只能看到自己公司的用户
    """

    list_display = [
        'username', 'company', 'role_display', 'email', 'is_active', 'date_joined',
    ]
    list_filter = ['is_active', 'company']
    search_fields = ['username', 'email', 'company__name']

    # 重写 fieldsets，加入 company 和 role
    fieldsets = (
        ('登录信息', {
            'fields': ('username', 'password'),
        }),
        ('个人信息', {
            'fields': ('first_name', 'last_name', 'email'),
        }),
        ('公司与角色', {
            'fields': ('company', 'role'),
        }),
        ('时间', {
            'fields': ('last_login', 'date_joined'),
        }),
    )

    # 新增用户时的表单（无需 role，默认就是公司管理员）
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'email', 'company', 'password1', 'password2'),
        }),
    )

    # ============================================================
    # 权限：有公司的 staff 用户即可访问，不依赖 Django 模型权限
    # ============================================================
    def _is_company_user(self, user):
        return user.is_staff and user.company is not None

    def has_module_permission(self, request):
        if request.user.is_superuser:
            return True
        return self._is_company_user(request.user)

    def has_view_permission(self, request, obj=None):
        if request.user.is_superuser:
            return True
        return self._is_company_user(request.user)

    def has_add_permission(self, request):
        return request.user.is_superuser

    def has_change_permission(self, request, obj=None):
        return request.user.is_superuser

    def has_delete_permission(self, request, obj=None):
        if request.user.is_superuser:
            return True
        return self._is_company_user(request.user)

    def role_display(self, obj):
        return obj.get_role_display()
    role_display.short_description = '角色'

    def get_queryset(self, request):
        """非超级管理员只能看到自己公司的用户。"""
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        return qs.filter(company=request.user.company)

    def get_form(self, request, obj=None, **kwargs):
        """非超级管理员不能修改 company 字段。"""
        form = super().get_form(request, obj=obj, **kwargs)
        if 'company' in form.base_fields and not request.user.is_superuser:
            form.base_fields['company'].disabled = True
            form.base_fields['company'].required = False
        return form

    def save_model(self, request, obj, form, change):
        """新建用户默认可登录后台，公司管理员创建的用户自动绑定公司。"""
        if not request.user.is_superuser:
            obj.company = request.user.company
            if change and obj.pk:
                original = self.model.objects.get(pk=obj.pk)
                obj.is_superuser = original.is_superuser
                obj.is_staff = original.is_staff
                obj.is_active = original.is_active
        if not change:
            obj.is_staff = True
            obj.is_active = True
            if not request.user.is_superuser:
                obj.is_superuser = False
        super().save_model(request, obj, form, change)


# ============================================================
# Case Admin — 装修案例
# ============================================================
@admin.register(Case)
class CaseAdmin(CompanyAdminMixin, admin.ModelAdmin):
    list_display = [
        'id', 'cover_preview', 'title', 'company', 'style', 'area',
        'budget_display', 'created_at',
    ]
    list_display_links = ['id', 'title']
    list_filter = ['style', 'created_at', 'company']
    search_fields = ['title', 'description', 'style', 'company__name']
    readonly_fields = ['created_at']
    date_hierarchy = 'created_at'

    fieldsets = (
        ('基本信息', {
            'fields': ('company', 'title', 'cover', 'description'),
        }),
        ('案例属性', {
            'fields': ('style', 'area', 'budget'),
        }),
        ('视频', {
            'fields': ('video_url',),
        }),
        ('时间', {
            'fields': ('created_at',),
        }),
    )

    def get_form(self, request, obj=None, **kwargs):
        """封面图使用 FileInput（无清除复选框），其余逻辑由 Mixin 处理。"""
        form = super().get_form(request, obj=obj, **kwargs)
        if 'cover' in form.base_fields:
            form.base_fields['cover'].widget = forms.FileInput()
        return form

    def cover_preview(self, obj):
        return image_preview(obj, 'cover', width=80)
    cover_preview.short_description = '封面'

    def budget_display(self, obj):
        if obj.budget:
            return f'{obj.budget} 万'
        return '-'
    budget_display.short_description = '预算'

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('company')


# ============================================================
# ProjectProgress Admin — 项目进度
# ============================================================
@admin.register(ProjectProgress)
class ProjectProgressAdmin(CompanyAdminMixin, admin.ModelAdmin):
    list_display = [
        'id', 'project_name', 'customer_name', 'stage_display', 'company',
        'phone', 'created_at',
    ]
    list_display_links = ['id', 'project_name']
    list_filter = ['company', 'created_at']
    search_fields = ['project_name', 'customer_name', 'phone', 'address', 'content', 'company__name']
    readonly_fields = ['created_at']
    date_hierarchy = 'created_at'

    fieldsets = (
        ('基本信息', {
            'fields': ('company', 'project_name', 'customer_name', 'phone', 'address'),
        }),
        ('进度信息', {
            'fields': ('current_stage', 'content'),
        }),
        ('时间', {
            'fields': ('created_at',),
        }),
    )

    # ---- helpers ----
    def _resolve_company(self, request, obj):
        """解析当前表单所属的公司。"""
        if obj and obj.pk and obj.company_id:
            return obj.company
        if request and request.user.company:
            return request.user.company
        return None

    # ---- form: dynamic stage dropdown + per-stage OSS URL fields ----
    def get_form(self, request, obj=None, **kwargs):
        # 只传模型字段给 modelform_factory，排除动态 stage_image_* 字段
        kwargs['fields'] = [
            'company', 'project_name', 'customer_name', 'phone', 'address',
            'current_stage', 'content',
        ]
        form = super().get_form(request, obj=obj, **kwargs)
        company = self._resolve_company(request, obj)
        stages = company.stage_list if company else []

        # current_stage → 下拉选框
        if stages and 'current_stage' in form.base_fields:
            form.base_fields['current_stage'].widget = forms.Select(
                choices=[(i, name) for i, name in enumerate(stages)]
            )
            form.base_fields['current_stage'].help_text = '选择当前项目所处的阶段'

        # 每个阶段一个 OSS 图片 URL 输入框
        existing = obj.images if obj and isinstance(obj.images, dict) else {}
        for i, name in enumerate(stages):
            field_name = f'stage_image_{i}'
            form.base_fields[field_name] = forms.URLField(
                label=f'「{name}」阶段图片',
                required=False,
                initial=existing.get(str(i), ''),
                help_text='阿里云 OSS 图片地址（选填）',
            )

        return form

    def get_fieldsets(self, request, obj=None):
        """动态插入阶段图片字段集。"""
        fieldsets = list(super().get_fieldsets(request, obj))
        company = self._resolve_company(request, obj)
        stages = company.stage_list if company else []
        if stages:
            stage_fields = tuple(f'stage_image_{i}' for i in range(len(stages)))
            fieldsets.insert(2, ('阶段图片', {
                'fields': stage_fields,
                'description': '每个阶段可填写一个阿里云 OSS 图片地址（选填）',
            }))
        return fieldsets

    def save_model(self, request, obj, form, change):
        """保存时收集阶段图片 URL 到 images JSON 字段。"""
        stage_images = {}
        for key, value in form.cleaned_data.items():
            if key.startswith('stage_image_') and value:
                idx = key.replace('stage_image_', '')
                stage_images[idx] = value
        obj.images = stage_images
        super().save_model(request, obj, form, change)

    # ---- list / display helpers ----
    def stage_display(self, obj):
        stages = obj.company.stage_list if obj.company_id else []
        if 0 <= obj.current_stage < len(stages):
            stage = stages[obj.current_stage]
        else:
            stage = obj.stage_name_snapshot or f'阶段{obj.current_stage}'
        colors = ['#4CAF50', '#2196F3', '#FF9800', '#9C27B0', '#F44336']
        idx = obj.current_stage % len(colors)
        return format_html(
            '<span style="background:{}; color:#fff; padding:2px 10px; '
            'border-radius:12px; font-size:12px;">{}</span>',
            colors[idx], stage,
        )
    stage_display.short_description = '当前阶段'

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('company')


# ============================================================
# Admin 站点全局配置
# ============================================================
admin.site.site_header = '装修公司 SaaS 管理后台'
admin.site.site_title = '装修公司 SaaS'
admin.site.index_title = '控制面板'
