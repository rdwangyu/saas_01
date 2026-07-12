"""
装修公司 SaaS 系统 — 权限控制

1. CompanyAdminMixin: Django Admin 端的公司数据隔离
2. IsCompanyUser / IsSameCompany: DRF API 端的权限类
"""

from django.contrib import admin
from rest_framework import permissions


# ============================================================
# Django Admin — 公司数据隔离混入类
# ============================================================
class CompanyAdminMixin:
    """
    用于 Admin 的混入类，实现：
    - 普通管理员只能看到自己公司的数据
    - 新增/编辑时自动绑定公司（不可手动选择）
    - 超级管理员可以看到全部数据
    """

    # ============================================================
    # 权限：有公司的 staff 用户即可访问，不再依赖 Django 模型权限
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
        if request.user.is_superuser:
            return True
        return self._is_company_user(request.user)

    def has_change_permission(self, request, obj=None):
        if request.user.is_superuser:
            return True
        return self._is_company_user(request.user)

    def has_delete_permission(self, request, obj=None):
        if request.user.is_superuser:
            return True
        return self._is_company_user(request.user)

    # ============================================================
    # 数据隔离
    # ============================================================
    def get_queryset(self, request):
        """非超级管理员只能看到自己公司的数据。"""
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        return qs.filter(company=request.user.company)

    def save_model(self, request, obj, form, change):
        """
        保存时自动将 company 设置为当前用户所属公司。
        超级管理员如果没有选择公司则保持不变（允许手动指定）。
        """
        if not request.user.is_superuser:
            obj.company = request.user.company
        super().save_model(request, obj, form, change)

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        """
        对于 company 外键字段：
        - 超级管理员：可以看到全部公司
        - 普通用户：限制为自己的公司（新建时可见，编辑时只读）
        """
        if db_field.name == 'company':
            if not request.user.is_superuser:
                from .models import Company
                if request.user.company:
                    kwargs['queryset'] = Company.objects.filter(
                        id=request.user.company_id
                    )
                else:
                    kwargs['queryset'] = Company.objects.none()
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def get_form(self, request, obj=None, **kwargs):
        """定制表单，限制 company 字段的选择范围。"""
        form = super().get_form(request, obj=obj, **kwargs)
        if 'company' in form.base_fields:
            if request.user.is_superuser:
                from .models import Company
                form.base_fields['company'].queryset = Company.objects.filter(status='active')
            else:
                form.base_fields['company'].disabled = True
                form.base_fields['company'].required = False
                # 新建时预设当前用户公司，使公司名在表单中可见
                if obj is None and request.user.company:
                    form.base_fields['company'].initial = request.user.company
        return form

    def get_readonly_fields(self, request, obj=None):
        """
        非超级管理员时，company 字段在编辑时设为只读。
        新建时（obj is None）保留可交互状态以便显示公司名。
        """
        readonly = list(super().get_readonly_fields(request, obj) or [])
        if not request.user.is_superuser and obj is not None \
                and 'company' not in readonly:
            readonly.append('company')
        return readonly


# ============================================================
# DRF — 权限类
# ============================================================
class IsCompanyUser(permissions.BasePermission):
    """
    全局权限：用户必须绑定公司（或者是超级管理员）。
    用于确保只有合法的公司用户才能访问业务 API。
    """

    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        # 超级管理员或者有公司的用户
        return request.user.is_superuser or request.user.company is not None


class IsSameCompany(permissions.BasePermission):
    """
    对象级权限：用户只能访问自己公司的数据。
    超级管理员可以访问全部数据。
    """

    def has_object_permission(self, request, view, obj):
        if request.user.is_superuser:
            return True
        # 对象的 company 必须等于用户的 company
        return obj.company == request.user.company
