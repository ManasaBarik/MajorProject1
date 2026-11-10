from rest_framework import serializers
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema_field
from .models import (
    Complaint, ComplaintImage, ComplaintFeedback, AIAnalysis,
)


class ComplaintImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ComplaintImage
        fields = ("id", "file", "caption", "uploaded_by", "metadata", "created_at")
        read_only_fields = ("id", "uploaded_by", "created_at")


class ComplaintFeedbackSerializer(serializers.ModelSerializer):
    class Meta:
        model = ComplaintFeedback
        fields = ("rating", "comment", "created_at")
        read_only_fields = ("created_at",)

    def validate_rating(self, v):
        if not 1 <= v <= 5:
            raise serializers.ValidationError("Rating must be between 1 and 5.")
        return v


class AIAnalysisSerializer(serializers.ModelSerializer):
    category = serializers.SerializerMethodField()
    priority = serializers.SerializerMethodField()
    department = serializers.SerializerMethodField()
    department_id = serializers.SerializerMethodField()
    similar_complaints = serializers.JSONField(read_only=True)
    is_overridden = serializers.BooleanField(read_only=True)
    reviewed_at = serializers.DateTimeField(read_only=True)
    review_remarks = serializers.CharField(read_only=True)

    class Meta:
        model = AIAnalysis
        fields = (
            "id", "category", "priority", "department", "department_id",
            "confidence", "summary", "reason",
            "requires_manual_review", "similar_complaints",
            "provider", "model_name", "is_overridden",
            "reviewed_at", "review_remarks", "created_at",
        )

    @extend_schema_field(OpenApiTypes.STR)
    def get_category(self, obj):
        return obj.human_category or obj.category_prediction

    @extend_schema_field(OpenApiTypes.STR)
    def get_priority(self, obj):
        return obj.human_priority or obj.priority_prediction

    @extend_schema_field(serializers.CharField(allow_null=True))
    def get_department(self, obj):
        dept = obj.human_department or obj.department_recommendation
        return dept.name if dept else None

    @extend_schema_field(serializers.IntegerField(allow_null=True))
    def get_department_id(self, obj):
        dept = obj.human_department or obj.department_recommendation
        return dept.id if dept else None


class ComplaintListSerializer(serializers.ModelSerializer):
    department = serializers.SerializerMethodField()
    assigned_engineer = serializers.SerializerMethodField()
    citizen_name = serializers.SerializerMethodField()
    ai = serializers.SerializerMethodField()
    resolution = serializers.SerializerMethodField()
    images = ComplaintImageSerializer(many=True, read_only=True)
    feedback = ComplaintFeedbackSerializer(read_only=True)

    class Meta:
        model = Complaint
        fields = (
            "id", "complaint_number", "title", "description", "category",
            "status", "priority", "department",
            "latitude", "longitude", "address", "ward",
            "created_at", "updated_at", "citizen_name",
            "assigned_engineer", "ai",
            "images", "feedback", "resolution_description", "resolution",
        )
        read_only_fields = (
            "id", "citizen", "status", "created_at", "updated_at",
            "resolution_description",
        )

    @extend_schema_field(OpenApiTypes.OBJECT)
    def get_department(self, obj):
        if obj.department_id:
            return {"id": obj.department_id, "name": obj.department.name}
        return None

    @extend_schema_field(OpenApiTypes.OBJECT)
    def get_assigned_engineer(self, obj):
        if obj.assigned_engineer_id:
            return {
                "id": obj.assigned_engineer_id,
                "name": obj.assigned_engineer.name,
            }
        return None

    @extend_schema_field(OpenApiTypes.STR)
    def get_citizen_name(self, obj):
        return obj.citizen.name if obj.citizen_id else ""

    @extend_schema_field(OpenApiTypes.OBJECT)
    def get_ai(self, obj):
        latest = obj.ai_analyses.first()
        if not latest:
            return None
        return AIAnalysisSerializer(latest).data

    @extend_schema_field(OpenApiTypes.OBJECT)
    def get_resolution(self, obj):
        resolution = obj.resolutions.first()
        if not resolution:
            return None
        return {
            "description": resolution.description,
            "evidence_image": resolution.evidence_image.url if resolution.evidence_image else None,
            "submitted_by": resolution.submitted_by.name,
            "submitted_at": resolution.submitted_at,
            "verification_status": resolution.verification_status,
            "verified_by": resolution.verified_by.name if resolution.verified_by else None,
            "verified_at": resolution.verified_at,
            "verification_remarks": resolution.verification_remarks,
        }


class ComplaintSerializer(ComplaintListSerializer):
    timeline = serializers.SerializerMethodField()

    class Meta(ComplaintListSerializer.Meta):
        fields = ComplaintListSerializer.Meta.fields + ("timeline",)

    @extend_schema_field(serializers.ListField(child=serializers.DictField()))
    def get_timeline(self, obj):
        out = []
        for h in obj.history.select_related("changed_by").all():
            out.append({
                "status": h.new_status,
                "timestamp": h.created_at,
                "actor": h.changed_by.name if h.changed_by else "System",
                "remarks": h.remarks or "",
            })
        return out

    def validate(self, a):
        if "latitude" in a and "longitude" in a:
            if not (-90 <= float(a["latitude"]) <= 90) or not (-180 <= float(a["longitude"]) <= 180):
                raise serializers.ValidationError("Invalid geographic coordinates.")
        return a


class ComplaintCreateSerializer(serializers.ModelSerializer):
    image = serializers.FileField(required=False, write_only=True)
    video = serializers.FileField(required=False, write_only=True)

    class Meta:
        model = Complaint
        fields = (
            "title", "description", "category",
            "latitude", "longitude", "address", "ward",
            "image", "video",
        )

    def validate(self, a):
        lat = a.get("latitude")
        lng = a.get("longitude")
        if lat is not None and lng is not None:
            if not (-90 <= float(lat) <= 90) or not (-180 <= float(lng) <= 180):
                raise serializers.ValidationError("Invalid geographic coordinates.")
        return a
