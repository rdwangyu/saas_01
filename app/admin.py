from django.conf import settings
from django import forms
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.html import format_html

from .models import (
    Company, User, Case, ProjectProgress, STAGE_FIELDS,
)
from .permissions import CompanyAdminMixin


def image_preview(obj, field_name, width=80):
    img = getattr(obj, field_name, None)
    if img and hasattr(img, 'url'):
        return format_html(
            '<img src="{}" style="max-width:{}px; max-height:{}px; border-radius:4px;" />',
            img.url, width, width,
        )
    return '-'


def json_display(value, max_items=5):
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
        readonly = list(super().get_readonly_fields(request, obj) or [])
        if not request.user.is_superuser:
            for f in ['max_video_size', 'status']:
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


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = [
        'username', 'company', 'role_display', 'phone', 'email', 'is_active', 'date_joined',
    ]
    list_filter = ['is_active', 'company']
    search_fields = ['username', 'email', 'phone', 'company__name']

    fieldsets = (
        ('登录信息', {
            'fields': ('username', 'password'),
        }),
        ('个人信息', {
            'fields': ('first_name', 'last_name', 'phone', 'email'),
        }),
        ('公司与角色', {
            'fields': ('company', 'role'),
        }),
        ('时间', {
            'fields': ('last_login', 'date_joined'),
        }),
    )

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'phone', 'email', 'company', 'password1', 'password2'),
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
        return request.user.is_superuser

    def has_delete_permission(self, request, obj=None):
        if request.user.is_superuser:
            return True
        return self._is_company_user(request.user)

    def role_display(self, obj):
        return obj.get_role_display()
    role_display.short_description = '角色'

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        return qs.filter(company=request.user.company)

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj=obj, **kwargs)
        if 'company' in form.base_fields and not request.user.is_superuser:
            form.base_fields['company'].disabled = True
            form.base_fields['company'].required = False
        return form

    def save_model(self, request, obj, form, change):
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
            'fields': ('video',),
        }),
        ('时间', {
            'fields': ('created_at',),
        }),
    )

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj=obj, **kwargs)
        for f in ('cover', 'video'):
            if f in form.base_fields:
                form.base_fields[f].widget = forms.FileInput()
        return form

    def cover_preview(self, obj):
        return image_preview(obj, 'cover', width=80)
    cover_preview.short_description = '封面'

    def budget_display(self, obj):
        if obj.budget:
            return obj.budget
        return '-'
    budget_display.short_description = '预算（万元）'

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('company')


@admin.register(ProjectProgress)
class ProjectProgressAdmin(CompanyAdminMixin, admin.ModelAdmin):
    list_display = [
        'id', 'project_name', 'customer_name', 'stage_display', 'company',
        'phone', 'created_at',
    ]
    list_display_links = ['id', 'project_name']
    list_filter = ['company', 'created_at']
    search_fields = ['project_name', 'customer_name', 'phone', 'address', 'company__name']
    readonly_fields = ['created_at']
    date_hierarchy = 'created_at'

    fieldsets = (
        ('基本信息', {
            'fields': ('company', 'project_name', 'customer_name', 'phone', 'address'),
        }),
        ('时间', {
            'fields': ('created_at',),
        }),
    )

    def get_form(self, request, obj=None, **kwargs):
        base_fields = ['company', 'project_name', 'customer_name', 'phone', 'address']
        for i in range(STAGE_FIELDS):
            base_fields += [f'stage_name_{i}', f'stage_image_{i}', f'stage_desc_{i}']
        kwargs['fields'] = base_fields
        form = super().get_form(request, obj=obj, **kwargs)

        for i in range(STAGE_FIELDS):
            fn = f'stage_name_{i}'
            if fn in form.base_fields:
                form.base_fields[fn].widget = forms.TextInput(attrs={'placeholder': '选填阶段名称'})
            si = f'stage_image_{i}'
            if si in form.base_fields:
                form.base_fields[si].widget = forms.FileInput()
            fd = f'stage_desc_{i}'
            if fd in form.base_fields:
                form.base_fields[fd].widget = forms.Textarea(attrs={'rows': 2, 'placeholder': '选填阶段描述'})

        return form

    def get_fieldsets(self, request, obj=None):
        fieldsets = list(super().get_fieldsets(request, obj))
        for i in range(STAGE_FIELDS):
            stage_fields = (f'stage_name_{i}', f'stage_image_{i}', f'stage_desc_{i}')
            fieldsets.insert(1 + i, (f'阶段 {i + 1}', {
                'fields': stage_fields,
                'classes': ('collapse',),
            }))
        return fieldsets

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)

    def stage_display(self, obj):
        idx = obj.progress_stage
        stage = obj.current_stage_name
        colors = ['#4CAF50', '#2196F3', '#FF9800', '#9C27B0', '#F44336']
        ci = idx % len(colors) if idx >= 0 else len(colors) - 1
        return format_html(
            '<span style="background:{}; color:#fff; padding:2px 10px; '
            'border-radius:12px; font-size:12px;">{}</span>',
            colors[ci], stage,
        )
    stage_display.short_description = '当前进度'

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('company')


admin.site.site_header = '白云企业管理'
admin.site.site_title = '白云企业管理'
admin.site.index_title = '控制面板'
