from rest_framework import generics
from django.shortcuts import get_object_or_404
from common.responses import success
from .models import Notification
from rest_framework.serializers import ModelSerializer, SerializerMethodField
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema_field


class NotificationSerializer(ModelSerializer):
    notification_type = SerializerMethodField()
    related_object_type = SerializerMethodField()
    related_object_id = SerializerMethodField()
    is_read = SerializerMethodField()

    class Meta:
        model = Notification
        fields = (
            "id", "title", "message", "type", "notification_type",
            "related_object_type", "related_object_id", "read", "is_read",
            "created_at",
        )
        read_only_fields = fields

    @extend_schema_field(OpenApiTypes.STR)
    def get_notification_type(self, obj):
        return obj.type

    @extend_schema_field(OpenApiTypes.STR)
    def get_related_object_type(self, obj):
        return obj.related_object_type

    @extend_schema_field(OpenApiTypes.STR)
    def get_related_object_id(self, obj):
        return obj.related_object_id

    @extend_schema_field(OpenApiTypes.BOOL)
    def get_is_read(self, obj):
        return obj.read


class ListView(generics.ListAPIView):
    serializer_class = NotificationSerializer

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return Notification.objects.none()
        return Notification.objects.filter(recipient=self.request.user)

    def get(self, request, *args, **kwargs):
        qs = self.get_queryset()
        if request.query_params.get("unread_count") in ("1", "true", "True"):
            data = {
                "items": self.get_serializer(qs, many=True).data,
                "unread_count": qs.filter(read=False).count(),
            }
            return success(data)
        return success(self.get_serializer(qs, many=True).data)


class ReadView(generics.GenericAPIView):
    serializer_class = NotificationSerializer

    def patch(self, request, pk):
        o = get_object_or_404(Notification, pk=pk, recipient=request.user)
        o.read = True
        o.save(update_fields=["read"])
        return success(NotificationSerializer(o).data, "Notification marked read.")


class ReadAllView(generics.GenericAPIView):
    serializer_class = NotificationSerializer

    def post(self, request):
        Notification.objects.filter(recipient=request.user, read=False).update(read=True)
        return success({}, "All notifications marked read.")
