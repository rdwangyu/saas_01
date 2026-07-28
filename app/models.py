from django.contrib.auth.models import AbstractUser
from django.db import models


class Company(models.Model):
    class Status(models.TextChoices):
        ACTIVE = 'active', '启用'
        INACTIVE = 'inactive', '停用'

    name = models.CharField('公司名称', max_length=200)
    logo = models.ImageField('Logo', upload_to='company_logos/', blank=True, null=True)
    description = models.TextField('公司简介', blank=True, default='')
    phone = models.CharField('联系电话', max_length=30, default='')
    address = models.CharField('公司地址', max_length=300, default='')
    progress_stages = models.CharField(
        '项目阶段',
        max_length=500,
        default='开始,进行中,结束',
        help_text='以英文逗号分隔的阶段名称，例如: 开始,水电,泥瓦,木工,验收',
    )
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

    @property
    def stage_list(self):
        return [s.strip() for s in self.progress_stages.split(',') if s.strip()]

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
    cover = models.ImageField('封面图', upload_to='case_covers/', blank=True, null=True)
    images = models.JSONField('图片集', default=list, blank=True)
    video_url = models.URLField('视频链接', blank=True, default='')
    description = models.TextField('案例描述', blank=True, default='')
    style = models.CharField('风格', max_length=100, blank=True, default='')
    area = models.CharField('面积', max_length=50, blank=True, default='',
                            help_text='例如: 120㎡')
    budget = models.DecimalField('预算（万元）', max_digits=10, decimal_places=2,
                                 null=True, blank=True)
    created_at = models.DateTimeField('创建时间', auto_now_add=True)

    class Meta:
        verbose_name = '案例'
        verbose_name_plural = verbose_name
        ordering = ['-created_at']

    def __str__(self):
        return f'[{self.company.name}] {self.title}'


class ProjectProgress(models.Model):
    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name='projects',
        verbose_name='所属公司',
    )
    project_name = models.CharField('项目名称', max_length=200, default='')
    customer_name = models.CharField('客户姓名', max_length=100)
    phone = models.CharField('客户电话', max_length=30, blank=True, default='')
    address = models.CharField('项目地址', max_length=300, blank=True, default='')
    current_stage = models.IntegerField('当前阶段', default=0,
                                        help_text='对应公司项目阶段列表中的序号，从 0 开始')
    stage_name_snapshot = models.CharField('阶段名称快照', max_length=100, blank=True, default='',
                                           help_text='创建/更新时自动保存的阶段名称')
    content = models.TextField('进度描述', blank=True, default='')
    images = models.JSONField('阶段图片', default=dict, blank=True)
    created_at = models.DateTimeField('创建时间', auto_now_add=True)

    class Meta:
        verbose_name = '项目进度'
        verbose_name_plural = verbose_name
        ordering = ['-created_at']

    def __str__(self):
        name = self.project_name or self.customer_name
        return f'[{self.company.name}] {name} — {self.stage_name_snapshot}'

    def save(self, *args, **kwargs):
        if self.company_id:
            stages = self.company.stage_list
            if 0 <= self.current_stage < len(stages):
                self.stage_name_snapshot = stages[self.current_stage]
            else:
                self.stage_name_snapshot = f'阶段{self.current_stage}'
        super().save(*args, **kwargs)
