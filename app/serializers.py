from rest_framework import serializers

from .models import Company, User, Case, ProjectProgress, ProjectStage


class CompanySerializer(serializers.ModelSerializer):
    class Meta:
        model = Company
        fields = [
            'id', 'name', 'logo', 'description', 'phone', 'address',
            'status', 'created_at',
        ]
        read_only_fields = ['id', 'created_at']


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
        password = validated_data.pop('password', None)
        user = super().create(validated_data)
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

    def create(self, validated_data):
        request = self.context.get('request')
        if request and hasattr(request.user, 'company'):
            if not request.user.is_superuser:
                validated_data['company'] = request.user.company
        return super().create(validated_data)


class ProjectStageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProjectStage
        fields = ['id', 'name', 'image_0', 'image_1', 'image_2', 'description', 'updated_time', 'created_time']
        read_only_fields = ['id', 'updated_time', 'created_time']


class ProjectProgressSerializer(serializers.ModelSerializer):
    company_name = serializers.CharField(source='company.name', read_only=True)
    progress_stage = serializers.IntegerField(read_only=True)
    current_stage_name = serializers.CharField(read_only=True)
    stages = ProjectStageSerializer(many=True, read_only=True)

    class Meta:
        model = ProjectProgress
        fields = [
            'id', 'company', 'company_name', 'project_name', 'customer_name',
            'phone', 'address', 'created_at',
            'current_stage_name', 'stages',
        ]
        read_only_fields = ['id', 'company', 'created_at',
                           'progress_stage', 'current_stage_name', 'stages']

    def create(self, validated_data):
        request = self.context.get('request')
        if request and hasattr(request.user, 'company'):
            if not request.user.is_superuser:
                validated_data['company'] = request.user.company
        return super().create(validated_data)
