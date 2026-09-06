from django import forms
from django.core.exceptions import ValidationError

from .models import (Case, Company, Customer, ProjectProgress, ProjectStage,
                     Staff)
from .widgets import OssUrlInput


def get_current_staff(request):
    session = getattr(request, "session", None)
    staff_id = session.get("staff_id") if session else None
    if not staff_id:
        return None
    return Staff.objects.filter(pk=staff_id).first()


class BaseDashboardForm(forms.ModelForm):
    required_css_class = "required"

    def __init__(self, *args, request=None, **kwargs):
        self.request = request
        super().__init__(*args, **kwargs)

    def _current_staff(self):
        return get_current_staff(self.request)


class DashboardLoginForm(forms.Form):
    phone = forms.CharField(label="手机号", max_length=30)
    password = forms.CharField(label="密码", widget=forms.PasswordInput)

    def clean(self):
        cleaned = super().clean()
        phone = (cleaned.get("phone") or "").strip()
        password = cleaned.get("password")
        if not phone or not password:
            return cleaned
        staff = Staff.objects.filter(phone=phone, deleted_at=None).first()
        if staff is None or not staff.check_password(password):
            raise ValidationError("手机号或密码错误。")
        cleaned["staff"] = staff
        return cleaned


class CompanyForm(BaseDashboardForm):
    class Meta:
        model = Company
        fields = [
            "name",
            "credit_code",
            "logo",
            "description",
            "phone",
            "address",
            "established_at",
        ]
        widgets = {"logo": OssUrlInput(accept="image/*", dir="company_logo")}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["name"].disabled = True
        self.fields["credit_code"].disabled = True


class CaseForm(BaseDashboardForm):
    class Meta:
        model = Case
        fields = ["title", "cover", "video", "description", "style", "area", "budget"]
        widgets = {
            "cover": OssUrlInput(accept="image/*", dir="company_case"),
            "video": OssUrlInput(accept="video/*", dir="company_case"),
        }

class ProjectForm(BaseDashboardForm):
    class Meta:
        model = ProjectProgress
        fields = ["project_no", "project_name", "address", "customer", "staff"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        current = self._current_staff()
        if current and current.company_id:
            # 客户与负责人均限定本公司
            self.fields["customer"].queryset = Customer.objects.filter(
                company_id=current.company_id
            )
            self.fields["staff"].queryset = Staff.objects.filter(
                company_id=current.company_id
            )
        # 项目编号由管理员手动输入，必填
        self.fields["project_no"].required = True


class CustomerForm(BaseDashboardForm):
    class Meta:
        model = Customer
        fields = ["name", "phone", "address", "contract"]


class ProjectStageForm(forms.ModelForm):
    class Meta:
        model = ProjectStage
        fields = ["name", "image_0", "image_1", "image_2", "description"]
        widgets = {
            f"image_{i}": OssUrlInput(accept="image/*", dir="company_project_progress")
            for i in range(3)
        }


class StaffPasswordForm(forms.Form):
    old_password = forms.CharField(label="原密码", widget=forms.PasswordInput)
    new_password1 = forms.CharField(label="新密码", widget=forms.PasswordInput)
    new_password2 = forms.CharField(label="确认新密码", widget=forms.PasswordInput)

    def __init__(self, *args, staff=None, **kwargs):
        self.staff = staff
        super().__init__(*args, **kwargs)

    def clean(self):
        cleaned = super().clean()
        old = cleaned.get("old_password")
        if old and (self.staff is None or not self.staff.check_password(old)):
            raise ValidationError("原密码不正确。")
        p1 = cleaned.get("new_password1")
        p2 = cleaned.get("new_password2")
        if not p1:
            raise ValidationError("请输入新密码。")
        if p1 != p2:
            raise ValidationError("两次输入的新密码不一致。")
        return cleaned

    def save(self):
        self.staff.set_password(self.cleaned_data["new_password1"])
        self.staff.save(update_fields=["password"])
