from django.db.models import Count
from rest_framework import viewsets, status
from rest_framework import serializers
from rest_framework.decorators import action
from rest_framework.serializers import ModelSerializer, SerializerMethodField
from common.permissions import IsAdministrator
from common.responses import success
from .models import Department, CategoryDepartmentMapping
from apps.accounts.models import OfficerProfile, EngineerProfile


class DepartmentSerializer(ModelSerializer):
    staff_count = SerializerMethodField()
    is_active = serializers.BooleanField(source="active", required=False)

    class Meta:
        model = Department
        fields = (
            "id", "name", "code", "description", "contact_email", "contact_phone",
            "active", "is_active", "staff_count", "created_at", "updated_at",
        )
        read_only_fields = ("id", "staff_count", "created_at", "updated_at")

    def get_staff_count(self, obj) -> int:
        return getattr(obj, "staff_count", 0) or (
            (getattr(obj, "staff", None).count() if hasattr(obj, "staff") else 0)
            + (getattr(obj, "engineers", None).count() if hasattr(obj, "engineers") else 0)
        )


class DepartmentViewSet(viewsets.ModelViewSet):
    queryset = Department.objects.all()
    serializer_class = DepartmentSerializer

    def get_permissions(self):
        if self.action in ("create", "update", "partial_update", "destroy"):
            return [IsAdministrator()]
        return super().get_permissions()

    def list(self, request, *args, **kwargs):
        qs = self.get_queryset()
        return success(self.get_serializer(qs, many=True).data)

    def retrieve(self, request, *args, **kwargs):
        return success(self.get_serializer(self.get_object()).data)

    def create(self, request, *args, **kwargs):
        s = self.get_serializer(data=request.data)
        s.is_valid(raise_exception=True)
        self.perform_create(s)
        return success(s.data, "Department created.", 201)

    def update(self, request, *args, **kwargs):
        p = self.get_object()
        s = self.get_serializer(p, data=request.data)
        s.is_valid(raise_exception=True)
        s.save()
        return success(s.data, "Department updated.")

    def partial_update(self, request, *args, **kwargs):
        p = self.get_object()
        s = self.get_serializer(p, data=request.data, partial=True)
        s.is_valid(raise_exception=True)
        s.save()
        return success(s.data, "Department updated.")

    def destroy(self, request, *args, **kwargs):
        self.get_object().delete()
        return success(None, "Department deleted.", status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=["get"])
    def staff(self, request, pk=None):
        dept = self.get_object()
        staff = []
        for officer in OfficerProfile.objects.filter(department=dept).select_related("user"):
            staff.append({
                "id": officer.user_id,
                "name": officer.user.name,
                "role": "OFFICER",
            })
        for engineer in EngineerProfile.objects.filter(department=dept).select_related("user"):
            staff.append({
                "id": engineer.user_id,
                "name": engineer.user.name,
                "role": "ENGINEER",
            })
        return success(staff)


class CategoryDepartmentMappingSerializer(ModelSerializer):
    department_name = serializers.CharField(source="department.name", read_only=True)

    class Meta:
        model = CategoryDepartmentMapping
        fields = (
            "id", "category", "department", "department_name",
            "default_priority", "active", "notes", "created_at", "updated_at",
        )
        read_only_fields = ("id", "department_name", "created_at", "updated_at")

    def validate_category(self, value):
        from apps.complaints.models import Complaint
        candidate = (value or "").strip().upper()
        if candidate not in Complaint.Category.values:
            raise serializers.ValidationError("Unknown complaint category.")
        return candidate

    def validate_default_priority(self, value):
        from apps.complaints.models import Complaint
        if value and value.upper() not in Complaint.Priority.values:
            raise serializers.ValidationError("Invalid priority.")
        return value.upper() if value else ""


class CategoryDepartmentMappingViewSet(viewsets.ModelViewSet):
    """Administrator-configurable routing of complaint categories to departments."""

    queryset = CategoryDepartmentMapping.objects.select_related("department").all()
    serializer_class = CategoryDepartmentMappingSerializer

    def get_permissions(self):
        if self.action in ("create", "update", "partial_update", "destroy"):
            return [IsAdministrator()]
        return super().get_permissions()

    def list(self, request, *args, **kwargs):
        return success(self.get_serializer(self.get_queryset(), many=True).data)

    def retrieve(self, request, *args, **kwargs):
        return success(self.get_serializer(self.get_object()).data)

    def create(self, request, *args, **kwargs):
        s = self.get_serializer(data=request.data)
        s.is_valid(raise_exception=True)
        s.save()
        return success(s.data, "Category mapping created.", 201)

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        s = self.get_serializer(instance, data=request.data)
        s.is_valid(raise_exception=True)
        s.save()
        return success(s.data, "Category mapping updated.")

    def partial_update(self, request, *args, **kwargs):
        instance = self.get_object()
        s = self.get_serializer(instance, data=request.data, partial=True)
        s.is_valid(raise_exception=True)
        s.save()
        return success(s.data, "Category mapping updated.")

    def destroy(self, request, *args, **kwargs):
        self.get_object().delete()
        return success(None, "Category mapping deleted.", status=status.HTTP_204_NO_CONTENT)
