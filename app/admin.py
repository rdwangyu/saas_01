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
    ProjectProgressImage,
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
    readonly_fields = ['created_at', 'stage_preview']
    date_hierarchy = 'created_at'

    fieldsets = (
        ('基本信息', {
            'fields': ('name', 'logo', 'description'),
        }),
        ('联系方式', {
            'fields': ('phone', 'address'),
        }),
        ('项目配置', {
            'fields': ('progress_stages', 'stage_preview'),
            'description': 'progress_stages 以英文逗号分隔，例如: 开始,水电,泥瓦,木工,验收',
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
        """非超级管理员不能编辑视频大小限制和状态。"""
        readonly = list(super().get_readonly_fields(request, obj) or [])
        if not request.user.is_superuser:
            if 'max_video_size' not in readonly:
                readonly.append('max_video_size')
            if 'status' not in readonly:
                readonly.append('status')
        return readonly

    def stage_preview(self, obj):
        """展示阶段列表的友好预览。"""
        stages = obj.stage_list
        items = [(f'第{i}阶段', name) for i, name in enumerate(stages)]
        html = format_html_join(
            '', '<div style="margin:2px 0;">🔹 {}: <b>{}</b></div>',
            items,
        )
        return html
    stage_preview.short_description = '阶段预览'

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
# ProjectProgressImage Inline — 现场图片上传
# ============================================================
class ProjectProgressImageInline(admin.TabularInline):
    model = ProjectProgressImage
    extra = 1
    verbose_name = '现场图片'
    verbose_name_plural = '现场图片'
    fields = ['image_tag', 'image', 'sort_order']
    readonly_fields = ['image_tag']

    def get_max_num(self, request, obj=None, **kwargs):
        company = None
        if obj and obj.company_id:
            company = obj.company
        elif request.user.company:
            company = request.user.company
        return company.max_images if company else 4

    def image_tag(self, obj):
        if obj and obj.pk and obj.image:
            return format_html(
                '<img src="{}" style="max-width:120px; max-height:90px; '
                'border-radius:4px; border:1px solid #ddd;" />',
                obj.image.url,
            )
        return '（上传后将显示预览）'
    image_tag.short_description = '预览'


# ============================================================
# ProjectProgress Admin Form — 视频校验
# ============================================================
class ProjectProgressAdminForm(forms.ModelForm):
    class Meta:
        model = ProjectProgress
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        self._request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)

    def clean_video_file(self):
        video = self.cleaned_data.get('video_file')
        if not video:
            return video
        company = self._get_company()
        if company:
            max_bytes = company.max_video_size_mb * 1024 * 1024
            if video.size > max_bytes:
                raise forms.ValidationError(
                    f'视频文件大小不能超过 {company.max_video_size_mb}MB'
                    f'（当前公司配置），请压缩后重新上传。'
                )
        return video

    def _get_company(self):
        if self.instance and self.instance.pk and self.instance.company_id:
            return self.instance.company
        if self._request and self._request.user.company:
            return self._request.user.company
        return None


# ============================================================
# ProjectProgress Admin — 项目进度
# ============================================================
@admin.register(ProjectProgress)
class ProjectProgressAdmin(CompanyAdminMixin, admin.ModelAdmin):
    form = ProjectProgressAdminForm
    inlines = [ProjectProgressImageInline]

    list_display = [
        'id', 'customer_name', 'stage_display', 'company',
        'phone', 'images_count_display', 'created_at',
    ]
    list_display_links = ['id', 'customer_name']
    list_filter = ['company', 'created_at']
    search_fields = ['customer_name', 'phone', 'address', 'content', 'company__name']
    readonly_fields = ['created_at', 'stage_name_snapshot', 'images_preview',
                       'video_preview']
    date_hierarchy = 'created_at'

    fieldsets = (
        ('基本信息', {
            'fields': ('company', 'customer_name', 'phone', 'address'),
        }),
        ('进度信息', {
            'fields': ('current_stage', 'stage_name_snapshot', 'content'),
        }),
        ('视频', {
            'fields': ('video_url', 'video_file', 'video_preview'),
        }),
        ('时间', {
            'fields': ('created_at',),
        }),
    )

    def get_form(self, request, obj=None, **kwargs):
        form_class = super().get_form(request, obj=obj, **kwargs)

        class RequestAwareForm(form_class):
            def __init__(self, *args, **fkwargs):
                fkwargs.setdefault('request', request)
                super().__init__(*args, **fkwargs)
        return RequestAwareForm

    def save_related(self, request, form, formsets, change):
        super().save_related(request, form, formsets, change)
        obj = form.instance
        urls = [
            img.image.url
            for img in obj.progress_images.order_by('sort_order')
            if img.image
        ]
        if obj.images != urls:
            obj.images = urls
            obj.save(update_fields=['images'])
        if obj.video_file and obj.video_url != obj.video_file.url:
            obj.video_url = obj.video_file.url
            obj.save(update_fields=['video_url'])

    def stage_display(self, obj):
        """在列表中以颜色标签显示当前阶段。"""
        stage = obj.stage_name_snapshot or f'阶段{obj.current_stage}'
        colors = ['#4CAF50', '#2196F3', '#FF9800', '#9C27B0', '#F44336']
        idx = obj.current_stage % len(colors)
        return format_html(
            '<span style="background:{}; color:#fff; padding:2px 10px; '
            'border-radius:12px; font-size:12px;">{}</span>',
            colors[idx], stage,
        )
    stage_display.short_description = '当前阶段'

    def images_preview(self, obj):
        imgs = obj.progress_images.order_by('sort_order')[:8] if obj.pk else []
        if not imgs:
            return '（暂无现场图片 — 请先保存项目，再通过下方"现场图片"区域上传）'
        tags = []
        for img in imgs:
            tags.append(format_html(
                '<img src="{}" style="max-width:120px; max-height:90px; '
                'margin:3px; border-radius:4px; border:1px solid #ddd;" />',
                img.image.url,
            ))
        return format_html(
            '<div style="display:flex; flex-wrap:wrap;">{}</div>',
            format_html(''.join(['{}'] * len(tags)), *tags),
        )
    images_preview.short_description = '已上传现场图片'

    def images_count_display(self, obj):
        count = obj.progress_images.count() if obj.pk else 0
        max_n = obj.company.max_images if obj.company_id else 4
        return f'{count}/{max_n}'
    images_count_display.short_description = '图片数'

    def video_preview(self, obj):
        if obj.video_file:
            return format_html(
                '<video width="360" controls style="max-width:100%;">'
                '<source src="{}" type="video/mp4">'
                '您的浏览器不支持视频播放。'
                '</video>',
                obj.video_file.url,
            )
        if obj.video_url:
            return format_html(
                '<a href="{}" target="_blank" rel="noopener">'
                '📺 打开视频链接</a>',
                obj.video_url,
            )
        return '（未上传视频）'
    video_preview.short_description = '视频预览'

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('company')

    def save_model(self, request, obj, form, change):
        """
        保存时自动填充 stage_name_snapshot。
        CompanyAdminMixin.save_model 会自动设置 company。
        """
        super().save_model(request, obj, form, change)


# ============================================================
# Admin 站点全局配置
# ============================================================
admin.site.site_header = '装修公司 SaaS 管理后台'
admin.site.site_title = '装修公司 SaaS'
admin.site.index_title = '控制面板'
