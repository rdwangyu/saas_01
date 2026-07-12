"""
装修公司 SaaS 系统 — DRF 序列化器

- company 字段自动绑定当前用户所属公司，不可手动指定
- 超级管理员可以手动指定 company
"""

from rest_framework import serializers

from .models import Company, User, Case, ProjectProgress


# ============================================================
# Company
# ============================================================
class CompanySerializer(serializers.ModelSerializer):
    stage_list = serializers.ListField(child=serializers.CharField(), read_only=True)

    class Meta:
        model = Company
        fields = [
            'id', 'name', 'logo', 'description', 'phone', 'address',
            'progress_stages', 'stage_list', 'status', 'created_at',
        ]
        read_only_fields = ['id', 'created_at']


# ============================================================
# User
# ============================================================
class UserSerializer(serializers.ModelSerializer):
    company_name = serializers.CharField(source='company.name', read_only=True)
    role_display = serializers.CharField(source='get_role_display', read_only=True)

    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'company', 'company_name',
            'role', 'role_display', 'is_active', 'date_joined',
        ]
        read_only_fields = ['id', 'date_joined']
        extra_kwargs = {
            'password': {'write_only': True, 'required': False},
        }

    def create(self, validated_data):
        """创建用户时自动设置密码。"""
        password = validated_data.pop('password', None)
        user = super().create(validated_data)
        if password:
            user.set_password(password)
            user.save()
        return user


# ============================================================
# Case
# ============================================================
class CaseSerializer(serializers.ModelSerializer):
    company_name = serializers.CharField(source='company.name', read_only=True)

    class Meta:
        model = Case
        fields = [
            'id', 'company', 'company_name', 'title', 'cover',
            'images', 'video_url', 'description',
            'style', 'area', 'budget', 'created_at',
        ]
        read_only_fields = ['id', 'company', 'images', 'video_url',
                           'created_at']

    def create(self, validated_data):
        """自动绑定 company 为当前用户所属公司（超级管理员除外）。"""
        request = self.context.get('request')
        if request and hasattr(request.user, 'company'):
            if not request.user.is_superuser:
                validated_data['company'] = request.user.company
        return super().create(validated_data)


# ============================================================
# ProjectProgress
# ============================================================
class ProjectProgressSerializer(serializers.ModelSerializer):
    company_name = serializers.CharField(source='company.name', read_only=True)

    class Meta:
        model = ProjectProgress
        fields = [
            'id', 'company', 'company_name', 'project_name', 'customer_name',
            'phone', 'address', 'current_stage', 'stage_name_snapshot',
            'content', 'images', 'created_at',
        ]
        read_only_fields = ['id', 'company', 'images',
                           'stage_name_snapshot', 'created_at']

    def create(self, validated_data):
        """自动绑定 company 为当前用户所属公司。"""
        request = self.context.get('request')
        if request and hasattr(request.user, 'company'):
            if not request.user.is_superuser:
                validated_data['company'] = request.user.company
        return super().create(validated_data)
