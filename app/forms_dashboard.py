"""公司管理员租户后台（/dashboard/）表单。

员工用手机号+密码登录，身份存 session['staff_id']；所有表单按当前员工所属公司隔离。
"""

from urllib.parse import unquote, urlparse

from django import forms
from django.core.exceptions import ValidationError
from django.core.files.storage import default_storage
from django.forms.formsets import DELETION_FIELD_NAME
from django.forms.models import BaseInlineFormSet

from .widgets import SimpleFileInput

from .models import (
    Case,
    Company,
    Customer,
    ProjectProgress,
    ProjectStage,
    Staff,
    case_gallery_path,
)


def get_current_staff(request):
    """从 session 读取当前登录员工；未登录或已停用返回 None。"""
    session = getattr(request, "session", None)
    staff_id = session.get("staff_id") if session else None
    if not staff_id:
        return None
    return Staff.objects.filter(pk=staff_id, is_active=True).first()


class MultipleFileInput(SimpleFileInput):
    allow_multiple_selected = True


class MultipleFileField(forms.FileField):
    """Django 6.0.7 无内置多文件字段，按官方 snippet 自建。"""

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("widget", MultipleFileInput())
        super().__init__(*args, **kwargs)

    def clean(self, data, initial=None):
        single = super().clean(data, initial)
        if isinstance(single, (list, tuple)):
            return single
        return [single] if single else []

    def widget_attrs(self, widget):
        attrs = super().widget_attrs(widget)
        attrs["multiple"] = True
        return attrs


class BaseDashboardForm(forms.ModelForm):
    """Dashboard 表单基类：透传 request，供 __init__ 里读取当前员工。"""

    required_css_class = "required"

    def __init__(self, *args, request=None, **kwargs):
        self.request = request
        super().__init__(*args, **kwargs)

    def _current_staff(self):
        return get_current_staff(self.request)

    @staticmethod
    def _delete_oss_url(url):
        path = unquote(urlparse(url).path).lstrip("/")
        if path:
            default_storage.delete(path)


class DashboardLoginForm(forms.Form):
    """员工手机号+密码登录表单。"""

    phone = forms.CharField(label="手机号", max_length=30)
    password = forms.CharField(label="密码", widget=forms.PasswordInput)

    def clean(self):
        cleaned = super().clean()
        phone = (cleaned.get("phone") or "").strip()
        password = cleaned.get("password")
        if not phone or not password:
            return cleaned
        staff = Staff.objects.filter(phone=phone, is_active=True).first()
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
            "established_date",
        ]
        widgets = {"logo": SimpleFileInput(attrs={"accept": "image/*"})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # 公司名与信用代码仅系统管理员（admin）可改，员工只读
        self.fields["name"].disabled = True
        self.fields["credit_code"].disabled = True


class CaseForm(BaseDashboardForm):
    """案例表单：封面/视频单文件 + 图片集多文件上传（追加）与勾选删除。"""

    new_images = MultipleFileField(required=False, label="新增图片")
    remove_images = forms.MultipleChoiceField(
        required=False, widget=forms.CheckboxSelectMultiple, label="删除图片"
    )

    class Meta:
        model = Case
        fields = ["title", "cover", "video", "description", "style", "area", "budget"]
        widgets = {
            "cover": SimpleFileInput(attrs={"accept": "image/*"}),
            "video": SimpleFileInput(attrs={"accept": "video/*"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        existing = list(self.instance.images or [])
        self.fields["remove_images"].choices = [(url, url) for url in existing]

    def clean(self):
        cleaned = super().clean()
        company = getattr(self.instance, "company", None)
        if company is None:
            current = self._current_staff()
            company = getattr(current, "company", None)
        if company is None:
            return cleaned

        # 图片数量：现有（扣除勾选删除）+ 新增 <= max_images
        current = list(getattr(self.instance, "images", None) or [])
        remove = set(cleaned.get("remove_images") or [])
        invalid_remove = remove - set(current)
        if invalid_remove:
            raise ValidationError("包含不存在的图片，请刷新后重试。")
        keep = [u for u in current if u not in remove]
        new_count = len(cleaned.get("new_images") or [])
        if len(keep) + new_count > company.max_images:
            raise ValidationError(
                f"图片总数不能超过 {company.max_images} 张（现有 {len(keep)} 张 + 新增 {new_count} 张）。"
            )

        # 视频大小
        video = cleaned.get("video")
        if video is not None and hasattr(video, "size"):
            limit = company.max_video_size * 1024 * 1024
            if video.size > limit:
                raise ValidationError(f"视频大小不能超过 {company.max_video_size}MB。")
        return cleaned

    def save(self, commit=True):
        instance = super().save(commit=False)
        current = list(instance.images or [])
        remove = set(self.cleaned_data.get("remove_images") or [])
        keep = [u for u in current if u not in remove]

        uploaded_keys = []
        try:
            for f in self.cleaned_data.get("new_images") or []:
                key = default_storage.save(case_gallery_path(instance, f.name), f)
                uploaded_keys.append(key)
                keep.append(default_storage.url(key))
        except Exception:
            for key in uploaded_keys:
                default_storage.delete(key)
            raise ValidationError("图片上传失败，请重试。")

        # 删除勾选移除的 OSS 对象
        for url in set(current) - set(keep):
            self._delete_oss_url(url)

        instance.images = keep
        if commit:
            instance.save()
        return instance


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
                company_id=current.company_id, is_active=True
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
        widgets = {f"image_{i}": SimpleFileInput(attrs={"accept": "image/*"}) for i in range(3)}


class StageInlineFormSet(BaseInlineFormSet):
    """把 DELETE 从隐藏框改成可见复选框，便于模板里做勾选删除。"""

    def add_fields(self, form, index):
        super().add_fields(form, index)
        delete_field = form.fields.get(DELETION_FIELD_NAME)
        if delete_field is not None:
            delete_field.widget = forms.CheckboxInput()


StageFormSet = forms.inlineformset_factory(
    ProjectProgress,
    ProjectStage,
    form=ProjectStageForm,
    formset=StageInlineFormSet,
    extra=1,
    can_delete=True,
    can_delete_extra=False,
)


class StaffPasswordForm(forms.Form):
    """员工自助修改密码表单（只允许改自己的）。"""

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
