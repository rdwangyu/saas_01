from rest_framework import permissions


class CompanyAdminMixin:
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
        if obj is not None:
            return getattr(obj, 'company_id', None) == request.user.company_id
        return self._is_company_user(request.user)

    def has_delete_permission(self, request, obj=None):
        if request.user.is_superuser:
            return True
        return self._is_company_user(request.user)

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        # Company 自身没有 company 字段，跳过按公司过滤（CompanyAdmin 已自行按 id 过滤）
        if not hasattr(self.model, 'company'):
            return qs
        return qs.filter(company=request.user.company)

    def save_model(self, request, obj, form, change):
        if not request.user.is_superuser:
            obj.company = request.user.company
        super().save_model(request, obj, form, change)

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
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
        form = super().get_form(request, obj=obj, **kwargs)
        if 'company' in form.base_fields:
            if request.user.is_superuser:
                from .models import Company
                form.base_fields['company'].queryset = Company.objects.filter(status='active')
            else:
                form.base_fields['company'].disabled = True
                form.base_fields['company'].required = False
                if obj is None and request.user.company:
                    form.base_fields['company'].initial = request.user.company
        return form

    def get_readonly_fields(self, request, obj=None):
        readonly = list(super().get_readonly_fields(request, obj) or [])
        if not request.user.is_superuser and obj is not None \
                and 'company' not in readonly:
            readonly.append('company')
        return readonly


class IsCompanyUser(permissions.BasePermission):
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        return request.user.is_superuser or request.user.company is not None


class IsSameCompany(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        if request.user.is_superuser:
            return True
        return obj.company == request.user.company
