from django.contrib.auth.models import AbstractUser
from django.core.validators import FileExtensionValidator
from django.db import models
from django.utils.deconstruct import deconstructible
from django.utils.text import slugify


MAX_SLUG_LEN = 16


def _safe_slug(text: str, fallback: str) -> str:
    """slugify 后截取最多 MAX_SLUG_LEN 个字符，避免文件路径过长"""
    s = slugify(text, allow_unicode=True)
    if not s:
        return fallback
    return s[:MAX_SLUG_LEN]


def company_logo_path(instance, filename):
    ext = filename.rsplit('.', 1)[-1] if '.' in filename else 'png'
    safe_name = _safe_slug(instance.name, 'company')
    return f'company_logo/{safe_name}_logo.{ext}'


def case_media_path(instance, filename):
    ext = filename.rsplit('.', 1)[-1] if '.' in filename else 'bin'
    safe_company = _safe_slug(instance.company.name, 'unknown')
    safe_title = _safe_slug(instance.title, 'untitled')
    return f'company_case/{safe_company}_case_{safe_title}.{ext}'


class Company(models.Model):
    class Status(models.TextChoices):
        ACTIVE = 'active', '启用'
        INACTIVE = 'inactive', '停用'

    name = models.CharField('公司名称', max_length=200)
    logo = models.ImageField('Logo', upload_to=company_logo_path, blank=True, null=True)
    description = models.TextField('公司简介', blank=True, default='')
    phone = models.CharField('联系电话', max_length=30, default='')
    address = models.CharField('公司地址', max_length=300, default='')
    status = models.CharField(
        '状态',
        max_length=20,
        choices=Status.choices,
        default=Status.ACTIVE,
    )
    max_video_size = models.IntegerField(
        '视频大小限制（MB）',
        choices=[(200, '200MB'), (500, '500MB')],
        default=200,
        help_text='影响案例和项目进度的视频上传上限',
    )
    created_at = models.DateTimeField('创建时间', auto_now_add=True)

    class Meta:
        verbose_name = '公司'
        verbose_name_plural = verbose_name
        ordering = ['-created_at']

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if self.pk:
            try:
                old = Company.objects.get(pk=self.pk)
                if old.logo and old.logo != self.logo:
                    old.logo.delete(save=False)
            except Company.DoesNotExist:
                pass
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        if self.logo:
            self.logo.delete(save=False)
        super().delete(*args, **kwargs)

    @property
    def max_images(self) -> int:
        return 8

    @property
    def max_video_size_mb(self) -> int:
        return self.max_video_size


class User(AbstractUser):
    class Role(models.TextChoices):
        ADMIN = 'admin', '公司管理员'

    company = models.ForeignKey(
        Company,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='users',
        verbose_name='所属公司',
        help_text='超级管理员可以不绑定公司',
    )
    phone = models.CharField('联系电话', max_length=30, default='')
    role = models.CharField(
        '角色',
        max_length=20,
        choices=Role.choices,
        default=Role.ADMIN,
    )

    class Meta:
        verbose_name = '用户'
        verbose_name_plural = verbose_name
        ordering = ['company', 'username']

    def __str__(self):
        company_name = self.company.name if self.company else '无公司'
        return f'{self.username} ({company_name})'


class Case(models.Model):
    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name='cases',
        verbose_name='所属公司',
    )
    title = models.CharField('案例标题', max_length=200)
    cover = models.ImageField('封面图', upload_to=case_media_path, null=True)
    images = models.JSONField('图片集', default=list, blank=True)
    video = models.FileField('视频文件', upload_to=case_media_path, null=True,
        validators=[FileExtensionValidator(
            allowed_extensions=['mp4', 'mov', 'avi', 'mkv', 'wmv', 'flv', 'webm', 'm4v'],
            message='仅支持视频文件（mp4/mov/avi/mkv/wmv/flv/webm/m4v）',
        )])
    description = models.TextField('案例描述', blank=True, default='')
    style = models.CharField('风格', max_length=100, blank=True, default='')
    area = models.PositiveSmallIntegerField('面积（㎡）', null=True, blank=True)
    budget = models.DecimalField('预算（万元）', max_digits=10, decimal_places=2,
                                 null=True, blank=True)
    created_at = models.DateTimeField('创建时间', auto_now_add=True)

    class Meta:
        verbose_name = '案例'
        verbose_name_plural = verbose_name
        ordering = ['-created_at']

    def __str__(self):
        return f'[{self.company.name}] {self.title}'

    def save(self, *args, **kwargs):
        if self.pk:
            try:
                old = Case.objects.get(pk=self.pk)
                for f in ['cover', 'video']:
                    old_val = getattr(old, f, None)
                    new_val = getattr(self, f, None)
                    if old_val and old_val != new_val:
                        old_val.delete(save=False)
            except Case.DoesNotExist:
                pass
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        for f in ['cover', 'video']:
            val = getattr(self, f, None)
            if val:
                val.delete(save=False)
        super().delete(*args, **kwargs)


@deconstructible
class stage_image_path:
    def __init__(self, image_num):
        self.image_num = image_num

    def __call__(self, instance, filename):
        ext = filename.rsplit('.', 1)[-1] if '.' in filename else 'jpg'
        safe_company = _safe_slug(instance.project.company.name, 'unknown')
        safe_project = _safe_slug(instance.project.project_name, 'unknown')
        safe_stage = _safe_slug(instance.name, 'unknown')
        return f'company_project_progress/{safe_company}_{safe_project}_{safe_stage}_{self.image_num}.{ext}'


class ProjectStage(models.Model):
    project = models.ForeignKey(
        'ProjectProgress',
        on_delete=models.CASCADE,
        related_name='stages',
        verbose_name='所属项目',
    )
    name = models.CharField('阶段名称', max_length=100, blank=True, default='')
    image_0 = models.ImageField('图片1', upload_to=stage_image_path(0), blank=True, null=True)
    image_1 = models.ImageField('图片2', upload_to=stage_image_path(1), blank=True, null=True)
    image_2 = models.ImageField('图片3', upload_to=stage_image_path(2), blank=True, null=True)
    description = models.TextField('阶段描述', blank=True, default='')
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)

    class Meta:
        verbose_name = '项目阶段'
        verbose_name_plural = verbose_name
        ordering = ['created_at']

    def __str__(self):
        return f'#{self.name}' if self.name is not None else '#'

    def save(self, *args, **kwargs):
        if self.pk:
            try:
                old = ProjectStage.objects.get(pk=self.pk)
                for f in ['image_0', 'image_1', 'image_2']:
                    old_val = getattr(old, f, None)
                    new_val = getattr(self, f, None)
                    if old_val and old_val != new_val:
                        old_val.delete(save=False)
            except ProjectStage.DoesNotExist:
                pass
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        for f in ['image_0', 'image_1', 'image_2']:
            val = getattr(self, f, None)
            if val:
                val.delete(save=False)
        super().delete(*args, **kwargs)


class ProjectProgress(models.Model):
    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name='projects',
        verbose_name='所属公司',
    )
    project_name = models.CharField('项目名称', max_length=200)
    customer_name = models.CharField('客户姓名', max_length=100)
    phone = models.CharField('客户电话', max_length=30)
    address = models.CharField('项目地址', max_length=300)
    created_at = models.DateTimeField('创建时间', auto_now_add=True)

    class Meta:
        verbose_name = '项目进度'
        verbose_name_plural = verbose_name
        ordering = ['-created_at']

    def __str__(self):
        name = self.project_name or self.customer_name
        return f'[{self.company.name}] {name}'


    @property
    def current_stage_name(self):
        last = None
        for stage in self.stages.all().order_by('-created_at'):
            if stage.image_0 or stage.image_1 or stage.image_2 or stage.description:
                last = stage
        return last.name if last is not None else '未开始'
