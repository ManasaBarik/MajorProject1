from rest_framework import viewsets, status
from django.db import transaction
from rest_framework import serializers
from rest_framework.serializers import ModelSerializer, SerializerMethodField
from common.permissions import IsAdministrator
from common.responses import success
from apps.departments.models import Department
from .models import RequiredDocument, Service


class RequiredDocumentSerializer(ModelSerializer):
    class Meta:
        model = RequiredDocument
        fields = (
            "id", "key", "name", "description", "is_mandatory",
            "allowed_file_types", "max_file_size",
        )
        read_only_fields = ("id",)


class ServiceSerializer(ModelSerializer):
    department_id = serializers.PrimaryKeyRelatedField(
        source="department", queryset=Department.objects.all(),
    )
    department = SerializerMethodField()
    is_active = serializers.BooleanField(source="active", required=False)
    estimated_processing_days = serializers.IntegerField(source="processing_time_days", required=False)
    field_verification_required = serializers.BooleanField(required=False)
    required_documents = RequiredDocumentSerializer(many=True, read_only=True)

    class Meta:
        model = Service
        fields = (
            "id", "name", "code", "department_id", "department",
            "description", "service_type", "eligibility", "procedure",
            "field_verification_required",
            "processing_time_days", "estimated_processing_days", "fee",
            "active", "is_active", "requirements", "required_documents",
            "created_at", "updated_at",
        )
        read_only_fields = ("id", "created_at", "updated_at")

    def get_department(self, obj):
        return {"id": obj.department_id, "name": obj.department.name}

    def validate_requirements(self, value):
        if not isinstance(value, list):
            raise serializers.ValidationError("Requirements must be a JSON array of field definitions.")
        valid_types = {"text", "textarea", "select", "date", "file", "number"}
        seen_keys = set()
        for idx, req in enumerate(value):
            if not isinstance(req, dict):
                raise serializers.ValidationError(f"Requirement at index {idx} must be an object.")
            for key in ("key", "label", "type"):
                if not isinstance(req.get(key), str) or not req[key].strip():
                    raise serializers.ValidationError(f"Requirement at index {idx} is missing field '{key}'.")
            if not req["key"].replace("_", "").replace("-", "").isalnum():
                raise serializers.ValidationError(
                    f"Requirement at index {idx} has an invalid key. Use letters, numbers, underscores, or hyphens."
                )
            if req["key"] in seen_keys:
                raise serializers.ValidationError(f"Requirement key '{req['key']}' is duplicated.")
            seen_keys.add(req["key"])
            if req.get("type") not in valid_types:
                raise serializers.ValidationError(
                    f"Requirement at index {idx} has unsupported type '{req.get('type')}'. "
                    f"Supported types are: {sorted(valid_types)}."
                )
            if "required" in req and not isinstance(req["required"], bool):
                raise serializers.ValidationError(f"Requirement at index {idx} has a non-boolean 'required' value.")
            if req.get("type") == "select":
                options = req.get("options")
                if not isinstance(options, list) or not options or any(not isinstance(option, str) or not option.strip() for option in options):
                    raise serializers.ValidationError(
                        f"Requirement at index {idx} of type 'select' must include non-empty string options."
                    )
            if req.get("type") == "file":
                allowed_types = req.get("allowed_file_types", [])
                if not isinstance(allowed_types, list) or any(not isinstance(ext, str) or not ext.strip() for ext in allowed_types):
                    raise serializers.ValidationError(
                        f"Requirement at index {idx} must use an array of allowed file types."
                    )
                max_file_size = req.get("max_file_size", 10 * 1024 * 1024)
                if isinstance(max_file_size, bool) or not isinstance(max_file_size, int) or max_file_size < 1:
                    raise serializers.ValidationError(
                        f"Requirement at index {idx} must use a positive integer max_file_size."
                    )
        return value

    def _sync_required_documents(self, service, requirements):
        file_requirements = [item for item in requirements if item.get("type") == "file"]
        keys = []
        for item in file_requirements:
            key = item["key"]
            keys.append(key)
            RequiredDocument.objects.update_or_create(
                service=service,
                key=key,
                defaults={
                    "name": item["label"],
                    "description": item.get("description", ""),
                    "is_mandatory": item.get("required", True),
                    "allowed_file_types": item.get("allowed_file_types", []),
                    "max_file_size": item.get("max_file_size", 10 * 1024 * 1024),
                },
            )
        service.required_documents.exclude(key__in=keys).delete()

    @transaction.atomic
    def create(self, validated_data):
        requirements = validated_data.get("requirements", [])
        service = super().create(validated_data)
        self._sync_required_documents(service, requirements)
        return service

    @transaction.atomic
    def update(self, instance, validated_data):
        requirements = validated_data.get("requirements", instance.requirements)
        service = super().update(instance, validated_data)
        self._sync_required_documents(service, requirements)
        return service


class ServiceViewSet(viewsets.ModelViewSet):
    queryset = Service.objects.select_related("department").prefetch_related("required_documents")
    serializer_class = ServiceSerializer

    def get_permissions(self):
        if self.action in ("create", "update", "partial_update", "destroy"):
            return [IsAdministrator()]
        return super().get_permissions()

    def _from_data_to_model(self, data):
        return data

    def list(self, request):
        qs = self.get_queryset().filter(active=True)
        return success(self.get_serializer(qs, many=True).data)

    def retrieve(self, request, *args, **kwargs):
        return success(self.get_serializer(self.get_object()).data)

    def create(self, request, *args, **kwargs):
        data = self._from_data_to_model(request.data)
        s = self.get_serializer(data=data)
        s.is_valid(raise_exception=True)
        s.save()
        return success(s.data, "Service created.", 201)

    def update(self, request, *args, **kwargs):
        p = self.get_object()
        data = self._from_data_to_model(request.data)
        s = self.get_serializer(p, data=data)
        s.is_valid(raise_exception=True)
        s.save()
        return success(s.data, "Service updated.")

    def partial_update(self, request, *args, **kwargs):
        p = self.get_object()
        data = self._from_data_to_model(request.data)
        s = self.get_serializer(p, data=data, partial=True)
        s.is_valid(raise_exception=True)
        s.save()
        return success(s.data, "Service updated.")

    def destroy(self, request, *args, **kwargs):
        self.get_object().delete()
        return success(None, "Service deleted.", status=status.HTTP_204_NO_CONTENT)
