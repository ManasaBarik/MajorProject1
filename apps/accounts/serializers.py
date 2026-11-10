from django.contrib.auth.password_validation import validate_password
from rest_framework.exceptions import PermissionDenied
from rest_framework import serializers
from .models import CitizenProfile, User
from apps.departments.models import Department
from apps.services.models import Service
from .models import OfficerProfile


class PublicUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ("id", "name", "email", "role")
        read_only_fields = fields


class UserSerializer(serializers.ModelSerializer):
    address = serializers.SerializerMethodField()
    city = serializers.SerializerMethodField()
    state = serializers.SerializerMethodField()
    pincode = serializers.SerializerMethodField()
    ward = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = (
            "id", "name", "email", "phone", "role", "is_verified",
            "date_joined", "created_at", "updated_at", "address", "city",
            "state", "pincode", "ward",
        )
        read_only_fields = fields

    def _citizen_value(self, obj, field):
        profile = getattr(obj, "citizen_profile", None)
        return getattr(profile, field, "") if profile else ""

    def get_address(self, obj):
        return self._citizen_value(obj, "address")

    def get_city(self, obj):
        return self._citizen_value(obj, "city")

    def get_state(self, obj):
        return self._citizen_value(obj, "state")

    def get_pincode(self, obj):
        return self._citizen_value(obj, "pincode")

    def get_ward(self, obj):
        return self._citizen_value(obj, "ward")


class AdminUserListSerializer(serializers.ModelSerializer):
    department = serializers.SerializerMethodField()
    status = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ("id", "name", "email", "role", "department", "status")

    def get_department(self, obj) -> str | None:
        if hasattr(obj, "officer_profile") and obj.officer_profile.department_id:
            return obj.officer_profile.department.name
        if hasattr(obj, "engineer_profile") and obj.engineer_profile.department_id:
            return obj.engineer_profile.department.name
        return None

    def get_status(self, obj):
        return "ACTIVE" if obj.is_active else "INACTIVE"

    def to_representation(self, instance):
        return super().to_representation(instance)


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, validators=[validate_password])
    role = serializers.ChoiceField(
        choices=User.Role.choices,
        required=False,
        default=User.Role.CITIZEN,
    )
    department_id = serializers.IntegerField(required=False, allow_null=True)
    designation = serializers.CharField(required=False, allow_blank=True)
    specialization = serializers.CharField(required=False, allow_blank=True)
    service_ids = serializers.ListField(
        child=serializers.IntegerField(),
        required=False,
        default=list,
    )

    class Meta:
        model = User
        fields = ("name", "email", "phone", "password", "role", "department_id", "designation", "specialization", "service_ids")

    def validate(self, attrs):
        role = attrs.get("role", User.Role.CITIZEN)
        department_id = attrs.get("department_id")
        if role in {User.Role.OFFICER, User.Role.ENGINEER}:
            if department_id in (None, ""):
                raise serializers.ValidationError({"department_id": "This field is required for officers and engineers."})
            department = Department.objects.filter(pk=department_id, active=True).first()
            if not department:
                raise serializers.ValidationError({"department_id": "Department not found or inactive."})
        if role == User.Role.OFFICER and department_id:
            if OfficerProfile.objects.filter(department_id=department_id, available=True).exists():
                raise serializers.ValidationError({"department_id": "This department already has an available officer."})
        service_ids = attrs.get("service_ids", [])
        if role == User.Role.ENGINEER:
            if not service_ids:
                raise serializers.ValidationError({"service_ids": "Select at least one service for this engineer."})
            if len(service_ids) != len(set(service_ids)):
                raise serializers.ValidationError({"service_ids": "A service may only be selected once."})
            services = Service.objects.filter(
                pk__in=service_ids,
                department_id=department_id,
                active=True,
            )
            if services.count() != len(service_ids):
                raise serializers.ValidationError({"service_ids": "Select active services from the engineer's department."})
        elif service_ids:
            raise serializers.ValidationError({"service_ids": "Only engineers can be qualified for services."})
        return super().validate(attrs)

    def validate_email(self, value):
        value = value.strip().lower()
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError("An account with this email already exists.")
        return value

    def validate_role(self, value):
        request = self.context.get("request")
        user = request.user if request and hasattr(request, "user") else None
        elevated = {User.Role.OFFICER, User.Role.ENGINEER, User.Role.ADMINISTRATOR}
        if value in elevated:
            if not (user and user.is_authenticated and user.role == User.Role.ADMINISTRATOR):
                raise PermissionDenied("Only administrators may register officers, engineers, or other administrators.")
        return value

    def create(self, validated_data):
        validated_data.pop("department_id", None)
        validated_data.pop("designation", None)
        validated_data.pop("specialization", None)
        validated_data.pop("service_ids", None)
        return User.objects.create_user(**validated_data)


class MeUpdateSerializer(serializers.ModelSerializer):
    address = serializers.CharField(required=False, allow_blank=True)
    city = serializers.CharField(required=False, allow_blank=True)
    state = serializers.CharField(required=False, allow_blank=True)
    pincode = serializers.CharField(required=False, allow_blank=True)
    ward = serializers.CharField(required=False, allow_blank=True)

    class Meta:
        model = User
        fields = ("name", "phone", "address", "city", "state", "pincode", "ward")

    def update(self, instance, validated_data):
        profile_data = {
            key: validated_data.pop(key)
            for key in ("address", "city", "state", "pincode", "ward")
            if key in validated_data
        }
        if profile_data and instance.role != User.Role.CITIZEN:
            raise serializers.ValidationError({"profile": "Address fields are only available for citizen profiles."})
        user = super().update(instance, validated_data)
        if profile_data:
            profile, _ = CitizenProfile.objects.get_or_create(user=user)
            for key, value in profile_data.items():
                setattr(profile, key, value)
            profile.save(update_fields=[*profile_data.keys(), "updated_at"])
        return user

    def validate(self, attrs):
        if "role" in self.initial_data:
            raise serializers.ValidationError({"role": "Role cannot be changed."})
        requested_email = self.initial_data.get("email")
        if requested_email is not None and requested_email.strip().lower() != self.instance.email.lower():
            raise serializers.ValidationError({"email": "Email cannot be changed here."})
        return super().validate(attrs)
