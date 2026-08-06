from rest_framework import serializers

from .models import Company, Customer, User, Case, ProjectProgress, ProjectStage


class CompanySerializer(serializers.ModelSerializer):
    class Meta:
        model = Company
        fields = [
            'id', 'name', 'credit_code', 'logo', 'description', 'phone', 'address',
            'status', 'established_date', 'created_at',
        ]
        read_only_fields = ['id', 'created_at']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        request = self.context.get('request')
        if request and not request.user.is_superuser:
            self.fields['credit_code'].read_only = True
            self.fields['status'].read_only = True
            self.fields['name'].read_only = True


class CustomerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Customer
        fields = [
            'id', 'name', 'phone', 'address', 'created_at',
        ]
        read_only_fields = ['id', 'created_at']


class UserSerializer(serializers.ModelSerializer):
    company_name = serializers.CharField(source='company.name', read_only=True)
    role_display = serializers.CharField(source='get_role_display', read_only=True)

    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'password', 'company', 'company_name',
            'role', 'role_display', 'is_active', 'date_joined',
        ]
        read_only_fields = ['id', 'date_joined']
        extra_kwargs = {
            'password': {'write_only': True, 'required': False},
        }

    def create(self, validated_data):
        password = validated_data.pop('password', None)
        user = super().create(validated_data)
        if password:
            user.set_password(password)
            user.save()
        return user

    def update(self, instance, validated_data):
        """更新时对密码进行哈希，避免明文入库导致无法登录"""
        password = validated_data.pop('password', None)
        user = super().update(instance, validated_data)
        if password:
            user.set_password(password)
            user.save()
        return user


class CaseSerializer(serializers.ModelSerializer):
    company_name = serializers.CharField(source='company.name', read_only=True)

    class Meta:
        model = Case
        fields = [
            'id', 'company', 'company_name', 'title', 'cover',
            'images', 'video', 'description',
            'style', 'area', 'budget', 'created_at',
        ]
        read_only_fields = ['id', 'company', 'images', 'video',
                           'created_at']

    def validate_cover(self, value):
        if value:
            ext = value.name.rsplit('.', 1)[-1].lower() if '.' in value.name else ''
            allowed = ['jpg', 'jpeg', 'png', 'gif', 'webp', 'bmp', 'tiff', 'svg']
            if ext not in allowed:
                raise serializers.ValidationError('封面图仅支持图片格式（jpg/jpeg/png/gif/webp/bmp/tiff/svg）')
        return value

    def create(self, validated_data):
        request = self.context.get('request')
        if request and hasattr(request.user, 'company'):
            if not request.user.is_superuser:
                validated_data['company'] = request.user.company
        return super().create(validated_data)


class ProjectStageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProjectStage
        fields = ['id', 'name', 'image_0', 'image_1', 'image_2', 'description', 'updated_at', 'created_at']
        read_only_fields = ['id', 'updated_at', 'created_at']


class ProjectProgressSerializer(serializers.ModelSerializer):
    company_name = serializers.CharField(source='company.name', read_only=True)
    customer_name = serializers.CharField(source='customer.name', read_only=True)
    customer_phone = serializers.CharField(source='customer.phone', read_only=True)
    staff_name = serializers.CharField(source='staff.username', read_only=True)
    staff_phone = serializers.CharField(source='staff.phone', read_only=True)
    current_stage_name = serializers.CharField(read_only=True)
    stages = ProjectStageSerializer(many=True, read_only=True)

    class Meta:
        model = ProjectProgress
        fields = [
            'id', 'company', 'company_name', 'project_name',
            'customer', 'customer_name', 'customer_phone', 'address',
            'staff', 'staff_name', 'staff_phone',
            'created_at', 'current_stage_name', 'stages',
        ]
        read_only_fields = ['id', 'company', 'created_at',
                           'current_stage_name', 'stages',
                           'customer_name', 'customer_phone',
                           'staff_name', 'staff_phone']

    def create(self, validated_data):
        request = self.context.get('request')
        if request and hasattr(request.user, 'company'):
            if not request.user.is_superuser:
                validated_data['company'] = request.user.company
        return super().create(validated_data)
