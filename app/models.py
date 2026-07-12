"""
装修公司 SaaS 系统 — 数据模型

多租户架构：所有业务数据通过 ForeignKey(Company) 实现数据隔离。
"""

from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.db import models


# ============================================================
# Company — 装修公司（租户）
# ============================================================
class Company(models.Model):
    """
    每个装修公司对应一条 Company 记录。
    progress_stages 定义了该公司项目的阶段列表，以逗号分隔。
    """

    class Status(models.TextChoices):
        ACTIVE = 'active', '启用'
        INACTIVE = 'inactive', '停用'

    name = models.CharField('公司名称', max_length=200)
    logo = models.ImageField('Logo', upload_to='company_logos/', blank=True, null=True)
    description = models.TextField('公司简介', blank=True, default='')
    phone = models.CharField('联系电话', max_length=30, blank=True, default='')
    address = models.CharField('公司地址', max_length=300, blank=True, default='')

    # 项目进度阶段，字符串格式: "开始,水电,泥瓦,木工,验收"
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

    # 视频大小限制（仅超级管理员可配置）
    max_video_size = models.IntegerField(
        '视频大小限制（MB）',
        choices=[(200, '200MB'), (500, '500MB')],
        default=200,
        help_text='影响案例和项目进度的视频上传上限',
    )

    created_at = models.DateTimeField('创建时间', auto_now_add=True)

    class Meta:
        verbose_name = '装修公司'
        verbose_name_plural = verbose_name
        ordering = ['-created_at']

    def __str__(self):
        return self.name

    @property
    def stage_list(self):
        """将 progress_stages 解析为列表，方便视图和模板使用。"""
        return [s.strip() for s in self.progress_stages.split(',') if s.strip()]

    @property
    def max_images(self) -> int:
        """返回此公司的图片数量上限（固定值）。"""
        return 8

    @property
    def max_video_size_mb(self) -> int:
        """返回此公司的视频大小上限（MB）。"""
        return self.max_video_size


# ============================================================
# User — 自定义用户（必须绑定公司）
# ============================================================
class User(AbstractUser):
    """
    继承 Django 默认用户，增加 company 外键和 role 字段。
    超级管理员 (is_superuser=True) 的 company 可以为空，可以看到全部数据。
    """

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


# ============================================================
# Case — 装修案例
# ============================================================
class Case(models.Model):
    """
    装修案例，属于某个公司，用于展示给客户看。
    """

    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name='cases',
        verbose_name='所属公司',
    )
    title = models.CharField('案例标题', max_length=200)
    cover = models.ImageField('封面图', upload_to='case_covers/', blank=True, null=True)

    # 案例图片集，JSON 格式: ["url1", "url2", ...]
    images = models.JSONField('图片集', default=list, blank=True)

    video_url = models.URLField('视频链接', blank=True, default='')
    description = models.TextField('案例描述', blank=True, default='')

    style = models.CharField('装修风格', max_length=100, blank=True, default='')
    area = models.CharField('面积', max_length=50, blank=True, default='',
                            help_text='例如: 120㎡')
    budget = models.DecimalField('预算（万元）', max_digits=10, decimal_places=2,
                                 null=True, blank=True)

    created_at = models.DateTimeField('创建时间', auto_now_add=True)

    class Meta:
        verbose_name = '装修案例'
        verbose_name_plural = verbose_name
        ordering = ['-created_at']

    def __str__(self):
        return f'[{self.company.name}] {self.title}'


# ============================================================
# ProjectProgress — 项目进度
# ============================================================
class ProjectProgress(models.Model):
    """
    在建项目进度跟踪。
    current_stage 是一个整数索引，指向 Company.progress_stages 中的某个阶段。
    stage_name_snapshot 记录阶段名称快照，防止阶段名称变更后历史数据失真。
    """

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

    # current_stage 为 Company.progress_stages 的索引（从 0 开始）
    current_stage = models.IntegerField('当前阶段', default=0,
                                        help_text='对应公司项目阶段列表中的序号，从 0 开始')
    stage_name_snapshot = models.CharField('阶段名称快照', max_length=100, blank=True, default='',
                                           help_text='创建/更新时自动保存的阶段名称')

    content = models.TextField('进度描述', blank=True, default='')

    # 阶段图片，JSON 格式: {"0": "https://oss.../img1.jpg", "1": "https://oss.../img2.jpg", ...}
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
        """保存时自动填充 stage_name_snapshot。"""
        if self.company_id:
            stages = self.company.stage_list
            if 0 <= self.current_stage < len(stages):
                self.stage_name_snapshot = stages[self.current_stage]
            else:
                self.stage_name_snapshot = f'阶段{self.current_stage}'
        super().save(*args, **kwargs)
