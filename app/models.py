from django.contrib.auth.models import AbstractUser
from django.core.validators import FileExtensionValidator
from django.db import models
from django.utils.deconstruct import deconstructible
from django.utils.text import slugify


def company_logo_path(instance, filename):
    ext = filename.rsplit('.', 1)[-1] if '.' in filename else 'png'
    safe_name = slugify(instance.name, allow_unicode=True) or 'company'
    return f'company_logo/{safe_name}_logo.{ext}'


def case_media_path(instance, filename):
    ext = filename.rsplit('.', 1)[-1] if '.' in filename else 'bin'
    safe_company = slugify(instance.company.name, allow_unicode=True) or 'unknown'
    safe_title = slugify(instance.title, allow_unicode=True) or 'untitled'
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


STAGE_FIELDS = 16


@deconstructible
class stage_image_path:
    def __init__(self, index):
        self.index = index

    def __call__(self, instance, filename):
        ext = filename.rsplit('.', 1)[-1] if '.' in filename else 'jpg'
        safe_company = slugify(instance.company.name, allow_unicode=True) or 'unknown'
        safe_project = slugify(instance.project_name, allow_unicode=True) or 'unknown'
        stage_name = getattr(instance, f'stage_name_{self.index}', '') or f'stage{self.index}'
        safe_stage = slugify(stage_name, allow_unicode=True) or f'stage{self.index}'
        return f'company_project_progress/{safe_company}_{safe_project}_{safe_stage}.{ext}'


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

    def save(self, *args, **kwargs):
        if self.pk:
            try:
                old = ProjectProgress.objects.get(pk=self.pk)
                for i in range(STAGE_FIELDS):
                    old_val = getattr(old, f'stage_image_{i}', None)
                    new_val = getattr(self, f'stage_image_{i}', None)
                    if old_val and old_val != new_val:
                        old_val.delete(save=False)
            except ProjectProgress.DoesNotExist:
                pass
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        for i in range(STAGE_FIELDS):
            val = getattr(self, f'stage_image_{i}', None)
            if val:
                val.delete(save=False)
        super().delete(*args, **kwargs)

    @property
    def progress_stage(self):
        for i in range(STAGE_FIELDS - 1, -1, -1):
            if getattr(self, f'stage_name_{i}', '') or \
               getattr(self, f'stage_image_{i}', '') or \
               getattr(self, f'stage_desc_{i}', ''):
                return i
        return -1

    @property
    def current_stage_name(self):
        idx = self.progress_stage
        if idx >= 0:
            return getattr(self, f'stage_name_{idx}', '') or f'阶段{idx + 1}'
        return '未开始'


for i in range(STAGE_FIELDS):
    ProjectProgress.add_to_class(f'stage_name_{i}', models.CharField(f'阶段{i+1}名称', max_length=100, blank=True, default=''))
    ProjectProgress.add_to_class(f'stage_image_{i}', models.ImageField(f'阶段{i+1}图片', upload_to=stage_image_path(i), blank=True, null=True))
    ProjectProgress.add_to_class(f'stage_desc_{i}', models.TextField(f'阶段{i+1}描述', blank=True, default=''))
