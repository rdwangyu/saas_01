from django.core.validators import FileExtensionValidator
from django.db import models
from django.utils.deconstruct import deconstructible
from django.utils.text import slugify
from uuid import uuid4

MAX_SLUG_LEN = 16


class CommonStatus(models.TextChoices):
    ACTIVE = "active", "启用"
    INACTIVE = "inactive", "停用"


class SoftDeleteQuerySet(models.QuerySet):
    """软删除：将 status 改为 INACTIVE 代替真删除。"""

    def delete(self):
        self.update(status=CommonStatus.INACTIVE)

    def hard_delete(self):
        super().delete()


class SoftDeleteManager(models.Manager):
    """返回 SoftDeleteQuerySet 的管理器。"""

    def get_queryset(self):
        return SoftDeleteQuerySet(self.model, using=self._db)


def _safe_slug(text: str, fallback: str) -> str:
    """slugify 后截取最多 MAX_SLUG_LEN 个字符，避免文件路径过长"""
    s = slugify(text, allow_unicode=True)
    if not s:
        return fallback
    return s[:MAX_SLUG_LEN]


def company_logo_path(instance, filename):
    ext = filename.rsplit(".", 1)[-1] if "." in filename else "png"
    safe_name = _safe_slug(instance.name, "company")
    return f"company_logo/{safe_name}_logo.{ext}"


def case_media_path(instance, filename):
    ext = filename.rsplit(".", 1)[-1] if "." in filename else "bin"
    safe_company = _safe_slug(instance.company.name, "unknown")
    safe_title = _safe_slug(instance.title, "untitled")
    return f"company_case/{safe_company}_case_{safe_title}.{ext}"


def case_gallery_path(instance, filename):
    """案例图片集路径：case_media_path 无唯一段，同公司+同标题会覆盖；这里加 uuid 后缀。"""
    ext = filename.rsplit(".", 1)[-1] if "." in filename else "bin"
    safe_company = _safe_slug(instance.company.name, "unknown")
    safe_title = _safe_slug(instance.title, "untitled")
    return f"company_case/{safe_company}_case_{safe_title}_{uuid4().hex[:8]}.{ext}"


class Company(models.Model):
    name = models.CharField("公司名称", max_length=200)
    credit_code = models.CharField(
        "社会统一信用代码", max_length=18, help_text="仅系统管理员可编辑"
    )
    logo = models.ImageField("Logo", upload_to=company_logo_path, blank=True, null=True)
    description = models.TextField("公司简介", blank=True, default="")
    phone = models.CharField("联系电话", max_length=30, default="")
    address = models.CharField("公司地址", max_length=300, default="")
    status = models.CharField(
        "状态",
        max_length=20,
        choices=CommonStatus.choices,
        default=CommonStatus.ACTIVE,
    )
    max_video_size = models.IntegerField(
        "视频大小限制（MB）",
        choices=[(200, "200MB"), (500, "500MB")],
        default=200,
        help_text="影响案例和项目进度的视频上传上限",
    )
    created_at = models.DateTimeField("创建时间", auto_now_add=True)
    established_date = models.DateField("成立日期", null=True, blank=True, help_text="公司成立日期")

    objects = SoftDeleteManager()

    class Meta:
        verbose_name = "公司"
        verbose_name_plural = verbose_name
        ordering = ["-created_at"]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if self.pk:
            try:
                old = Company.objects.get(pk=self.pk)
                if old.logo and old.logo != self.logo:
                    old.logo.delete(save=False)
                if old.status == CommonStatus.ACTIVE and self.status == CommonStatus.INACTIVE:
                    self.cases.all().update(status=CommonStatus.INACTIVE)
                    self.projects.all().update(status=CommonStatus.INACTIVE)
            except Company.DoesNotExist:
                pass
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        self.status = CommonStatus.INACTIVE
        self.save(update_fields=["status"])

    def hard_delete(self, *args, **kwargs):
        if self.logo:
            self.logo.delete(save=False)
        super().delete(*args, **kwargs)

    @property
    def max_images(self) -> int:
        return 8


class Customer(models.Model):
    """客户：公司服务的人员，通过手机号+短信验证码登录小程序。

    客户是全局表（仅超级管理员可维护），不直接归属某家公司，
    公司与客户的关系通过「项目 → 客户」体现。
    """

    name = models.CharField("姓名", max_length=100)
    phone = models.CharField("电话", max_length=30, unique=True)
    address = models.CharField("住址", max_length=300, default="")
    created_at = models.DateTimeField("创建时间", auto_now_add=True)

    class Meta:
        verbose_name = "客户"
        verbose_name_plural = "客户"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.name}（{self.phone}）"

    @property
    def is_authenticated(self):
        # 客户由 CustomerAuthentication 认证，DRF 权限需要该属性
        return True

    @property
    def is_anonymous(self):
        return False


class Staff(models.Model):
    """公司员工：独立于 admin 认证用户（auth.User）的员工表，验证码登录。"""

    class Role(models.TextChoices):
        ADMIN = "项目负责人", "公司管理员"

    name = models.CharField("姓名", max_length=150)
    phone = models.CharField("联系电话", max_length=30, unique=True, help_text="用于短信验证码登录")
    email = models.EmailField("电子邮件地址", blank=True)
    company = models.ForeignKey(
        Company,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="staff",
        verbose_name="所属公司",
    )
    role = models.CharField(
        "角色",
        max_length=20,
        choices=Role.choices,
        default=Role.ADMIN,
    )
    is_active = models.BooleanField("启用", default=True)
    created_at = models.DateTimeField("创建时间", auto_now_add=True)
    last_login = models.DateTimeField("上次登录时间", null=True, blank=True)

    class Meta:
        db_table = "app_staff"
        verbose_name = "员工"
        verbose_name_plural = "员工"
        ordering = ["company", "name"]

    def __str__(self):
        company_name = self.company.name if self.company else "无公司"
        return f"{self.name}（{company_name}）"


class Case(models.Model):
    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name="cases",
        verbose_name="所属公司",
    )
    title = models.CharField("案例标题", max_length=200)
    cover = models.ImageField(
        "封面图",
        upload_to=case_media_path,
        null=True,
        validators=[
            FileExtensionValidator(
                allowed_extensions=["jpg", "jpeg", "png", "gif", "webp", "bmp", "tiff", "svg"],
                message="封面图仅支持图片格式（jpg/jpeg/png/gif/webp/bmp/tiff/svg）",
            )
        ],
    )
    images = models.JSONField("图片集", default=list, blank=True)
    video = models.FileField(
        "视频文件",
        upload_to=case_media_path,
        null=True,
        validators=[
            FileExtensionValidator(
                allowed_extensions=["mp4", "mov", "avi", "mkv", "wmv", "flv", "webm", "m4v"],
                message="仅支持视频文件（mp4/mov/avi/mkv/wmv/flv/webm/m4v）",
            )
        ],
    )
    description = models.TextField("案例描述", blank=True, default="")
    style = models.CharField("风格", max_length=100, blank=True, default="")
    area = models.PositiveSmallIntegerField("面积（㎡）", null=True, blank=True)
    budget = models.DecimalField(
        "预算（万元）", max_digits=10, decimal_places=2, null=True, blank=True
    )
    status = models.CharField(
        "状态",
        max_length=20,
        choices=CommonStatus.choices,
        default=CommonStatus.ACTIVE,
    )
    created_at = models.DateTimeField("创建时间", auto_now_add=True)

    objects = SoftDeleteManager()

    class Meta:
        verbose_name = "案例"
        verbose_name_plural = verbose_name
        ordering = ["-created_at"]

    def __str__(self):
        return f"[{self.company.name}] {self.title}"

    def save(self, *args, **kwargs):
        if self.pk:
            try:
                old = Case.objects.get(pk=self.pk)
                for f in ["cover", "video"]:
                    old_val = getattr(old, f, None)
                    new_val = getattr(self, f, None)
                    if old_val and old_val != new_val:
                        old_val.delete(save=False)
            except Case.DoesNotExist:
                pass
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        self.status = CommonStatus.INACTIVE
        self.save(update_fields=["status"])

    def hard_delete(self, *args, **kwargs):
        for f in ["cover", "video"]:
            val = getattr(self, f, None)
            if val:
                val.delete(save=False)
        super().delete(*args, **kwargs)


@deconstructible
class stage_image_path:
    def __init__(self, image_num):
        self.image_num = image_num

    def __call__(self, instance, filename):
        ext = filename.rsplit(".", 1)[-1] if "." in filename else "jpg"
        safe_company = _safe_slug(instance.project.company.name, "unknown")
        safe_project = _safe_slug(instance.project.project_name, "unknown")
        safe_stage = _safe_slug(instance.name, "unknown")
        return f"company_project_progress/{safe_company}_{safe_project}_{safe_stage}_{self.image_num}.{ext}"


class ProjectStage(models.Model):
    project = models.ForeignKey(
        "ProjectProgress",
        on_delete=models.CASCADE,
        related_name="stages",
        verbose_name="所属项目",
    )
    name = models.CharField("阶段名称", max_length=100, blank=True, default="")
    image_0 = models.ImageField("图片1", upload_to=stage_image_path(0), blank=True, null=True)
    image_1 = models.ImageField("图片2", upload_to=stage_image_path(1), blank=True, null=True)
    image_2 = models.ImageField("图片3", upload_to=stage_image_path(2), blank=True, null=True)
    description = models.TextField("阶段描述", blank=True, default="")
    created_at = models.DateTimeField("创建时间", auto_now_add=True)
    updated_at = models.DateTimeField("更新时间", auto_now=True)

    objects = SoftDeleteManager()

    class Meta:
        verbose_name = "项目阶段"
        verbose_name_plural = verbose_name
        ordering = ["created_at"]

    def __str__(self):
        return f"#{self.name}" if self.name is not None else "#"

    def save(self, *args, **kwargs):
        if self.pk:
            try:
                old = ProjectStage.objects.get(pk=self.pk)
                for f in ["image_0", "image_1", "image_2"]:
                    old_val = getattr(old, f, None)
                    new_val = getattr(self, f, None)
                    if old_val and old_val != new_val:
                        old_val.delete(save=False)
            except ProjectStage.DoesNotExist:
                pass
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        for f in ["image_0", "image_1", "image_2"]:
            val = getattr(self, f, None)
            if val:
                val.delete(save=False)
        super().delete(*args, **kwargs)


class ProjectProgress(models.Model):
    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name="projects",
        verbose_name="所属公司",
    )
    customer = models.ForeignKey(
        Customer,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="projects",
        verbose_name="客户",
        help_text="客户信息由客户表提供",
    )
    staff = models.ForeignKey(
        Staff,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="projects",
        verbose_name="负责人",
    )
    project_name = models.CharField("项目名称", max_length=200)
    address = models.CharField("项目地址", max_length=300)
    status = models.CharField(
        "状态",
        max_length=20,
        choices=CommonStatus.choices,
        default=CommonStatus.ACTIVE,
    )
    created_at = models.DateTimeField("创建时间", auto_now_add=True)

    objects = SoftDeleteManager()

    class Meta:
        verbose_name = "项目进度"
        verbose_name_plural = verbose_name
        ordering = ["-created_at"]

    def __str__(self):
        customer_name = self.customer.name if self.customer else ""
        name = self.project_name or customer_name
        return f"[{self.company.name}] {name}"

    def delete(self, *args, **kwargs):
        self.status = CommonStatus.INACTIVE
        self.save(update_fields=["status"])

    def hard_delete(self, *args, **kwargs):
        super().delete(*args, **kwargs)

    @property
    def current_stage_name(self):
        last = None
        for stage in self.stages.all().order_by("-created_at"):
            if stage.image_0 or stage.image_1 or stage.image_2 or stage.description:
                last = stage
        return last.name if last is not None else "未开始"


class SmsCode(models.Model):
    """短信验证码：发送后暂存，校验成功后作废。purpose 区分客户/员工登录。"""

    class Purpose(models.TextChoices):
        CUSTOMER_LOGIN = "customer_login", "客户登录"
        STAFF_LOGIN = "staff_login", "员工登录"

    phone = models.CharField("手机号", max_length=30, db_index=True)
    code = models.CharField("验证码", max_length=10)
    purpose = models.CharField(
        "用途",
        max_length=20,
        choices=Purpose.choices,
        default=Purpose.CUSTOMER_LOGIN,
    )
    created_at = models.DateTimeField("发送时间", auto_now_add=True)
    used = models.BooleanField("已使用", default=False)

    class Meta:
        verbose_name = "短信验证码"
        verbose_name_plural = "短信验证码"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.phone} - {self.code}"


class CustomerToken(models.Model):
    """客户登录令牌：手机号+验证码登录后签发，代替 JWT（客户不是 Django 用户）。"""

    key = models.CharField("令牌", max_length=64, unique=True)
    customer = models.ForeignKey(
        Customer,
        on_delete=models.CASCADE,
        related_name="tokens",
        verbose_name="客户",
    )
    created_at = models.DateTimeField("签发时间", auto_now_add=True)
    expires_at = models.DateTimeField("过期时间")

    class Meta:
        verbose_name = "客户令牌"
        verbose_name_plural = "客户令牌"

    def __str__(self):
        return f"{self.customer} - {self.key[:8]}..."
