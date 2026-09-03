from urllib.parse import unquote, urlparse

from django.contrib.auth.hashers import check_password, make_password
from django.core.files.storage import default_storage
from django.db import models
from django.utils.text import slugify

MAX_SLUG_LEN = 16


class CommonStatus(models.TextChoices):
    ACTIVE = "active", "启用"
    INACTIVE = "inactive", "停用"


class SoftDeleteQuerySet(models.QuerySet):
    def delete(self):
        self.update(status=CommonStatus.INACTIVE)


class SoftDeleteManager(models.Manager):
    def get_queryset(self):
        return SoftDeleteQuerySet(self.model, using=self._db)


def _safe_slug(text: str, fallback: str) -> str:
    """slugify 后截取最多 MAX_SLUG_LEN 个字符，避免文件路径过长"""
    s = slugify(text, allow_unicode=True)
    if not s:
        return fallback
    return s[:MAX_SLUG_LEN]


def _delete_oss_url(url):
    """把 OSS URL 转成对象路径并从存储中删除。"""
    if not url:
        return
    path = unquote(urlparse(url).path).lstrip("/")
    if path:
        default_storage.delete(path)


class Company(models.Model):
    name = models.CharField("公司名称", max_length=200)
    credit_code = models.CharField(
        "社会统一信用代码", max_length=18, help_text="仅系统管理员可编辑"
    )
    logo = models.CharField(
        "Logo", max_length=500, blank=True, default="", help_text="OSS 直传后保存的 URL"
    )
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
    established_date = models.DateField(
        "成立日期", null=True, blank=True, help_text="公司成立日期"
    )

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
                    _delete_oss_url(old.logo)
                if (
                    old.status == CommonStatus.ACTIVE
                    and self.status == CommonStatus.INACTIVE
                ):
                    self.cases.all().update(status=CommonStatus.INACTIVE)
                    self.projects.all().update(status=CommonStatus.INACTIVE)
            except Company.DoesNotExist:
                pass
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        self.status = CommonStatus.INACTIVE
        self.save(update_fields=["status"])

    @property
    def max_images(self) -> int:
        return 8


class Customer(models.Model):
    """客户：公司服务的人员，归属于某家公司，由该公司管理员增删改查。"""

    company = models.ForeignKey(
        Company,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="customers",
        verbose_name="所属公司",
    )
    name = models.CharField("姓名", max_length=100)
    phone = models.CharField("电话", max_length=30, unique=True)
    address = models.CharField("住址", max_length=300, default="")
    contract = models.CharField("合同编号", max_length=100, blank=True, default="")
    created_at = models.DateTimeField("创建时间", auto_now_add=True)

    class Meta:
        verbose_name = "客户"
        verbose_name_plural = "客户"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.name}（{self.phone}）"


class Staff(models.Model):
    """公司员工：独立于 admin 认证用户（auth.User）的员工表，手机号+密码登录。"""

    class Role(models.TextChoices):
        ADMIN = "项目负责人", "公司管理员"

    name = models.CharField("姓名", max_length=150)
    phone = models.CharField(
        "联系电话", max_length=30, unique=True, help_text="登录账号（手机号）"
    )
    password = models.CharField(
        "密码", max_length=128, default="", help_text="由超管在后台设置/员工自助修改"
    )
    email = models.EmailField("电子邮件地址", blank=True)
    company = models.ForeignKey(
        Company,
        on_delete=models.PROTECT,
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

    def set_password(self, raw_password):
        self.password = make_password(raw_password)

    def check_password(self, raw_password):
        return check_password(raw_password, self.password)


class Case(models.Model):
    company = models.ForeignKey(
        Company,
        on_delete=models.PROTECT,
        related_name="cases",
        verbose_name="所属公司",
    )
    title = models.CharField("案例标题", max_length=200)
    cover = models.CharField(
        "封面图",
        max_length=500,
        blank=True,
        default="",
        help_text="OSS 直传后保存的 URL",
    )
    video = models.CharField(
        "视频文件",
        max_length=500,
        blank=True,
        default="",
        help_text="OSS 直传后保存的 URL",
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
                        _delete_oss_url(old_val)
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
                _delete_oss_url(val)
        super().delete(*args, **kwargs)


class ProjectStage(models.Model):
    project = models.ForeignKey(
        "ProjectProgress",
        on_delete=models.CASCADE,
        related_name="stages",
        verbose_name="所属项目",
    )
    name = models.CharField("阶段名称", max_length=100, blank=True, default="")
    image_0 = models.CharField(
        "图片1",
        max_length=500,
        blank=True,
        default="",
        help_text="OSS 直传后保存的 URL",
    )
    image_1 = models.CharField(
        "图片2",
        max_length=500,
        blank=True,
        default="",
        help_text="OSS 直传后保存的 URL",
    )
    image_2 = models.CharField(
        "图片3",
        max_length=500,
        blank=True,
        default="",
        help_text="OSS 直传后保存的 URL",
    )
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
                        _delete_oss_url(old_val)
            except ProjectStage.DoesNotExist:
                pass
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        for f in ["image_0", "image_1", "image_2"]:
            val = getattr(self, f, None)
            if val:
                _delete_oss_url(val)
        super().delete(*args, **kwargs)


class ProjectProgress(models.Model):
    company = models.ForeignKey(
        Company,
        on_delete=models.PROTECT,
        related_name="projects",
        verbose_name="所属公司",
    )
    customer = models.ForeignKey(
        Customer,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="projects",
        verbose_name="客户",
        help_text="客户信息由客户表提供",
    )
    staff = models.ForeignKey(
        Staff,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="projects",
        verbose_name="负责人",
    )
    project_no = models.CharField(
        "项目编号",
        max_length=50,
        unique=True,
        null=True,
        blank=True,
        help_text="由公司管理员手动输入，供小程序客户绑定查看项目进度",
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
        for stage in self.stages.all():
            stage.delete()
        super().delete(*args, **kwargs)

    @property
    def current_stage_name(self):
        last = None
        for stage in self.stages.all().order_by("-created_at"):
            if stage.image_0 or stage.image_1 or stage.image_2 or stage.description:
                last = stage
                break
        return last.name if last is not None else "未开始"


class WechatAccessToken(models.Model):
    token = models.CharField("access_token", max_length=512)
    expires_at = models.DateTimeField("过期时间")

    class Meta:
        verbose_name = "微信 access_token"
        verbose_name_plural = verbose_name

    def __str__(self):
        return self.token[:16] + "..."
