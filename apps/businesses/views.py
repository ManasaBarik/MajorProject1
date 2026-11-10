from rest_framework import viewsets, status as http_status
from rest_framework.serializers import ModelSerializer, SerializerMethodField
from rest_framework.exceptions import PermissionDenied
from common.responses import success
from .models import BusinessProfile


class BusinessSerializer(ModelSerializer):
    business_name = SerializerMethodField()
    business_type = SerializerMethodField()
    contact_number = SerializerMethodField()

    class Meta:
        model = BusinessProfile
        fields = (
            "id", "name", "business_name", "owner_name", "type", "business_type",
            "registration_number", "address", "city", "state", "pincode", "email",
            "gstin", "license_number", "status", "phone", "contact_number",
            "created_at", "updated_at",
        )
        read_only_fields = ("owner", "status", "created_at", "updated_at")

    def get_business_name(self, obj):
        return obj.name

    def get_business_type(self, obj):
        return obj.type

    def get_contact_number(self, obj):
        return obj.phone

    def to_internal_value(self, data):
        data = data.copy()
        for alias, field in (("business_name", "name"), ("business_type", "type"), ("contact_number", "phone")):
            if alias in data and field not in data:
                data[field] = data[alias]
            data.pop(alias, None)
        return super().to_internal_value(data)


class BusinessViewSet(viewsets.ModelViewSet):
    queryset = BusinessProfile.objects.none()
    serializer_class = BusinessSerializer
    http_method_names = ["get", "post", "patch", "head", "options"]

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return self.queryset
        u = self.request.user
        if u.role in ("ADMINISTRATOR", "OFFICER"):
            return BusinessProfile.objects.all()
        return BusinessProfile.objects.filter(owner=u)

    def get_object(self):
        obj = super().get_object()
        u = self.request.user
        if u.role in ("ADMINISTRATOR", "OFFICER") or obj.owner_id == u.id:
            return obj
        from rest_framework.exceptions import NotFound
        raise NotFound()

    def list(self, request):
        return success(self.get_serializer(self.get_queryset(), many=True).data)

    def retrieve(self, request, *args, **kwargs):
        return success(self.get_serializer(self.get_object()).data)

    def create(self, request, *args, **kwargs):
        if request.user.role != "BUSINESS_OWNER":
            raise PermissionDenied("Only business owners can create businesses.")
        s = self.get_serializer(data=request.data)
        s.is_valid(raise_exception=True)
        s.save(owner=request.user)
        return success(s.data, "Business created.", 201)

    def partial_update(self, request, *args, **kwargs):
        p = self.get_object()
        if p.owner_id != request.user.id:
            raise PermissionDenied("Only the business owner may update this business.")
        s = self.get_serializer(p, data=request.data, partial=True)
        s.is_valid(raise_exception=True)
        s.save()
        return success(s.data, "Business updated.")

    def update(self, request, *args, **kwargs):
        p = self.get_object()
        if p.owner_id != request.user.id:
            raise PermissionDenied("Only the business owner may update this business.")
        s = self.get_serializer(p, data=request.data)
        s.is_valid(raise_exception=True)
        s.save()
        return success(s.data, "Business updated.")

    def destroy(self, request, *args, **kwargs):
        raise PermissionDenied("Deletion is not allowed for businesses.")
