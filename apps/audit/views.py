from rest_framework.generics import ListAPIView
from rest_framework.serializers import ModelSerializer, SerializerMethodField
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema_field
from common.permissions import IsAdministrator
from common.responses import success
from .models import AuditLog


class AuditSerializer(ModelSerializer):
    actor = SerializerMethodField()
    target = SerializerMethodField()

    class Meta:
        model = AuditLog
        fields = ("id", "actor", "action", "target", "timestamp")
        read_only_fields = fields

    @extend_schema_field(OpenApiTypes.STR)
    def get_actor(self, obj):
        if obj.user_id:
            return obj.user.name
        return "System"

    @extend_schema_field(OpenApiTypes.STR)
    def get_target(self, obj):
        if obj.entity_id:
            return f"{obj.entity}:{obj.entity_id}" if obj.entity else obj.entity_id
        return obj.entity or ""


class AuditView(ListAPIView):
    permission_classes = [IsAdministrator]
    serializer_class = AuditSerializer
    queryset = AuditLog.objects.select_related("user").all().order_by("-timestamp")

    def get(self, request, *args, **kwargs):
        return success(self.get_serializer(self.get_queryset(), many=True).data)
