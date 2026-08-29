from rest_framework import serializers

from .models import Company, Customer, Case, ProjectProgress, ProjectStage


class CompanySerializer(serializers.ModelSerializer):
    class Meta:
        model = Company
        fields = [
            "id",
            "name",
            "credit_code",
            "logo",
            "description",
            "phone",
            "address",
            "status",
            "established_date",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]


class CustomerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Customer
        fields = [
            "id",
            "company",
            "name",
            "phone",
            "address",
            "contract",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]


class CaseSerializer(serializers.ModelSerializer):
    company_name = serializers.CharField(source="company.name", read_only=True)

    class Meta:
        model = Case
        fields = [
            "id",
            "company",
            "company_name",
            "title",
            "cover",
            "video",
            "description",
            "style",
            "area",
            "budget",
            "created_at",
        ]
        read_only_fields = ["id", "company", "video", "created_at"]

    def validate_cover(self, value):
        if value:
            ext = value.name.rsplit(".", 1)[-1].lower() if "." in value.name else ""
            allowed = ["jpg", "jpeg", "png"]
            if ext not in allowed:
                raise serializers.ValidationError(
                    "封面图仅支持图片格式(jpg/jpeg/png)"
                )
        return value


class ProjectStageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProjectStage
        fields = [
            "id",
            "name",
            "image_0",
            "image_1",
            "image_2",
            "description",
            "updated_at",
            "created_at",
        ]
        read_only_fields = ["id", "updated_at", "created_at"]


class ProjectProgressSerializer(serializers.ModelSerializer):
    company_name = serializers.CharField(source="company.name", read_only=True)
    company_logo = serializers.ImageField(source="company.logo", read_only=True)
    customer_name = serializers.CharField(source="customer.name", read_only=True)
    customer_phone = serializers.CharField(source="customer.phone", read_only=True)
    customer_address = serializers.CharField(source="customer.address", read_only=True)
    customer_contract = serializers.CharField(source="customer.contract", read_only=True)
    staff_name = serializers.CharField(source="staff.name", read_only=True)
    staff_phone = serializers.CharField(source="staff.phone", read_only=True)
    current_stage_name = serializers.CharField(read_only=True)
    stages = ProjectStageSerializer(many=True, read_only=True)

    class Meta:
        model = ProjectProgress
        fields = [
            "id",
            "project_no",
            "company",
            "company_name",
            "company_logo",
            "project_name",
            "customer",
            "customer_name",
            "customer_phone",
            "customer_address",
            "customer_contract",
            "address",
            "staff",
            "staff_name",
            "staff_phone",
            "created_at",
            "current_stage_name",
            "stages",
        ]
        read_only_fields = [
            "id",
            "company",
            "created_at",
            "current_stage_name",
            "stages",
            "customer_name",
            "customer_phone",
            "customer_address",
            "customer_contract",
            "staff_name",
            "staff_phone",
        ]
