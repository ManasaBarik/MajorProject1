from django.contrib.auth.password_validation import validate_password
from django.contrib.auth.tokens import default_token_generator
from django.core.exceptions import ValidationError as DjangoValidationError
from django.core.mail import send_mail
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from rest_framework import generics, permissions, status
from rest_framework import serializers
from drf_spectacular.utils import extend_schema
from rest_framework.exceptions import ValidationError, NotFound
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from rest_framework_simplejwt.tokens import RefreshToken
from common.responses import success
from common.schemas import (
    APIEnvelopeSerializer, LogoutRequestSerializer,
    PasswordResetRequestSerializer, PasswordResetConfirmRequestSerializer,
)
from common.permissions import IsAdministrator
from .models import User, OfficerProfile, EngineerProfile, CitizenProfile
from apps.services.models import Service
from .serializers import (
    RegisterSerializer,
    UserSerializer,
    PublicUserSerializer,
    AdminUserListSerializer,
    MeUpdateSerializer,
)


class OfficerAdminSchemaSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    user_id = serializers.IntegerField()
    name = serializers.CharField()
    department_id = serializers.IntegerField()
    designation = serializers.CharField()
    available = serializers.BooleanField()


class EngineerAdminSchemaSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    user_id = serializers.IntegerField()
    name = serializers.CharField()
    department_id = serializers.IntegerField()
    available = serializers.BooleanField()
    workload = serializers.IntegerField()
    service_ids = serializers.ListField(child=serializers.IntegerField())
    services = serializers.ListField(child=serializers.CharField())


class RegisterView(generics.CreateAPIView):
    permission_classes = [permissions.AllowAny]
    serializer_class = RegisterSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        department_id = serializer.validated_data.get("department_id")
        service_ids = serializer.validated_data.get("service_ids", [])
        user = serializer.save()
        if user.role == User.Role.CITIZEN:
            CitizenProfile.objects.get_or_create(user=user)
        elif user.role == User.Role.OFFICER:
            OfficerProfile.objects.update_or_create(
                user=user,
                defaults={
                    "department_id": request.data.get("department_id"),
                    "designation": request.data.get("designation", ""),
                },
            )
        elif user.role == User.Role.ENGINEER:
            profile, _ = EngineerProfile.objects.update_or_create(
                user=user,
                defaults={
                    "department_id": department_id,
                    "specialization": request.data.get("specialization", ""),
                },
            )
            profile.services.set(service_ids)
        data = {
            "user": PublicUserSerializer(user).data,
        }
        from apps.audit.services import record_audit
        record_audit(
            actor=user,
            action="USER_CREATED",
            entity_type="user",
            entity_id=user.pk,
            new_value={"email": user.email, "role": user.role},
            ip_address=request.META.get("REMOTE_ADDR"),
        )
        return success(data, "Registered successfully.", 201)


class LoginView(TokenObtainPairView):
    permission_classes = [permissions.AllowAny]

    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)
        tokens = response.data
        from rest_framework_simplejwt.tokens import AccessToken
        access = tokens.get("access")
        user_id = None
        if access:
            try:
                decoded = AccessToken(access)
                user_id = decoded.get("user_id")
            except Exception:
                pass
        user = None
        if user_id:
            user = User.objects.filter(id=user_id).first()
        if user is None:
            from django.contrib.auth import authenticate
            user = authenticate(request, email=request.data.get("email"), password=request.data.get("password"))
        user_shape = PublicUserSerializer(user).data if user else {}
        user_shape.pop("email", None)
        if user:
            from apps.audit.services import record_audit
            record_audit(
                actor=user,
                action="LOGIN",
                entity_type="user",
                entity_id=user.pk,
                ip_address=request.META.get("REMOTE_ADDR"),
            )
        return success(
            {
                "access": tokens.get("access"),
                "refresh": tokens.get("refresh"),
                "user": user_shape,
            },
            "Authenticated successfully.",
        )


class RefreshView(TokenRefreshView):
    permission_classes = [permissions.AllowAny]

    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)
        data = response.data
        return success(
            {
                "access": data.get("access"),
                "refresh": data.get("refresh", request.data.get("refresh")),
            },
            "Token refreshed.",
        )


class MeView(generics.RetrieveUpdateAPIView):
    serializer_class = UserSerializer

    def get_object(self):
        return self.request.user

    def get(self, request, *args, **kwargs):
        return success(self.get_serializer(self.get_object()).data)

    def patch(self, request, *args, **kwargs):
        s = MeUpdateSerializer(self.get_object(), data=request.data, partial=True)
        s.is_valid(raise_exception=True)
        profile_fields = ("address", "city", "state", "pincode", "ward")
        profile = getattr(request.user, "citizen_profile", None)
        old_value = {"name": request.user.name, "phone": request.user.phone}
        if profile:
            old_value["profile"] = {key: getattr(profile, key) for key in profile_fields}
        s.save()
        updated_user = self.get_object()
        updated_profile = getattr(updated_user, "citizen_profile", None)
        new_value = {"name": updated_user.name, "phone": updated_user.phone}
        if updated_profile:
            new_value["profile"] = {key: getattr(updated_profile, key) for key in profile_fields}
        from apps.audit.services import record_audit
        record_audit(
            actor=request.user,
            action="USER_UPDATED",
            entity_type="user",
            entity_id=request.user.pk,
            old_value=old_value,
            new_value=new_value,
            ip_address=request.META.get("REMOTE_ADDR"),
        )
        return success(UserSerializer(self.get_object()).data, "Profile updated successfully.")


class LogoutView(generics.GenericAPIView):
    permission_classes = [permissions.AllowAny]
    serializer_class = LogoutRequestSerializer

    @extend_schema(request=LogoutRequestSerializer, responses=APIEnvelopeSerializer)
    def post(self, request):
        token_value = request.data.get("refresh")
        if not token_value:
            raise ValidationError({"refresh": "This field is required."})
        actor = request.user if request.user.is_authenticated else None
        try:
            refresh_token = RefreshToken(token_value)
            if actor is None:
                actor = User.objects.filter(pk=refresh_token.get("user_id")).first()
            refresh_token.blacklist()
        except Exception:
            pass
        if actor:
            from apps.audit.services import record_audit
            record_audit(
                actor=actor,
                action="LOGOUT",
                entity_type="user",
                entity_id=actor.pk,
                ip_address=request.META.get("REMOTE_ADDR"),
            )
        return success(None, "Logged out successfully.", 200)


class PasswordResetView(generics.GenericAPIView):
    permission_classes = [permissions.AllowAny]
    serializer_class = PasswordResetRequestSerializer

    @extend_schema(request=PasswordResetRequestSerializer, responses=APIEnvelopeSerializer)
    def post(self, request):
        email = request.data.get("email")
        if not email:
            raise ValidationError({"email": "This field is required."})
        user = User.objects.filter(email__iexact=email.strip(), is_active=True).first()
        if user:
            reset_token = (
                f"{urlsafe_base64_encode(force_bytes(user.pk))}:"
                f"{default_token_generator.make_token(user)}"
            )
            send_mail(
                "Civic portal password reset",
                f"Use this one-time reset token to change your password: {reset_token}",
                None,
                [user.email],
                fail_silently=False,
            )
        return success({}, "If the address exists, reset instructions will be sent.")


class PasswordResetConfirmView(generics.GenericAPIView):
    permission_classes = [permissions.AllowAny]
    serializer_class = PasswordResetConfirmRequestSerializer

    @extend_schema(request=PasswordResetConfirmRequestSerializer, responses=APIEnvelopeSerializer)
    def post(self, request):
        reset_token = request.data.get("reset_token")
        new_password = request.data.get("new_password")
        if not reset_token or not new_password:
            raise ValidationError(
                {"reset_token": "This field is required.", "new_password": "This field is required."}
            )
        try:
            uidb64, token = reset_token.split(":", 1)
            uid = urlsafe_base64_decode(uidb64).decode()
            user = User.objects.get(pk=uid)
        except Exception:
            raise ValidationError({"reset_token": "Invalid or expired reset token."})
        if not default_token_generator.check_token(user, token):
            raise ValidationError({"reset_token": "Invalid or expired reset token."})
        try:
            validate_password(new_password, user)
        except DjangoValidationError as exc:
            raise ValidationError({"new_password": exc.messages}) from exc
        user.set_password(new_password)
        user.save(update_fields=["password", "updated_at"])
        return success({}, "Password reset successfully.")


class AdminUserListView(generics.ListAPIView):
    permission_classes = [IsAdministrator]
    serializer_class = AdminUserListSerializer
    queryset = User.objects.select_related(
        "officer_profile", "engineer_profile",
        "officer_profile__department", "engineer_profile__department",
    ).all()

    def get(self, request, *args, **kwargs):
        return success(self.get_serializer(self.get_queryset(), many=True).data)


class AdminUserUpdateView(generics.GenericAPIView):
    permission_classes = [IsAdministrator]
    serializer_class = AdminUserListSerializer
    queryset = User.objects.all()

    def patch(self, request, pk):
        user = self.get_object()
        old_value = {"is_active": user.is_active}
        if "is_active" in request.data:
            if not isinstance(request.data["is_active"], bool):
                raise ValidationError({"is_active": "This field must be true or false."})
            user.is_active = request.data["is_active"]
        elif request.data.get("status") in ("ACTIVE", "INACTIVE"):
            user.is_active = request.data["status"] == "ACTIVE"
        else:
            raise ValidationError({"status": "Provide is_active or ACTIVE/INACTIVE status."})
        user.save(update_fields=["is_active", "updated_at"])
        from apps.audit.services import record_audit
        record_audit(
            actor=request.user,
            action="USER_UPDATED",
            entity_type="user",
            entity_id=user.pk,
            old_value=old_value,
            new_value={"is_active": user.is_active},
            ip_address=request.META.get("REMOTE_ADDR"),
        )
        return success(AdminUserListSerializer(user).data, "User status updated.")


class AdminOfficerListView(generics.ListAPIView):
    permission_classes = [IsAdministrator]
    serializer_class = OfficerAdminSchemaSerializer
    queryset = OfficerProfile.objects.none()

    @extend_schema(responses=APIEnvelopeSerializer)
    def get(self, request):
        return success(
            [
                {
                    "id": o.id,
                    "user_id": o.user_id,
                    "name": o.user.name,
                    "department_id": o.department_id,
                    "designation": o.designation,
                    "available": o.available,
                }
                for o in OfficerProfile.objects.select_related("user")
            ]
        )


class AdminOfficerDetailView(generics.UpdateAPIView):
    permission_classes = [IsAdministrator]
    serializer_class = OfficerAdminSchemaSerializer
    queryset = OfficerProfile.objects.all()

    @extend_schema(request=OfficerAdminSchemaSerializer, responses=APIEnvelopeSerializer)
    def patch(self, request, *args, **kwargs):
        obj = self.get_object()
        department_id = request.data.get("department_id", obj.department_id)
        available = request.data.get("available", obj.available)
        if not isinstance(available, bool):
            raise ValidationError({"available": "This field must be true or false."})
        if available and OfficerProfile.objects.filter(
            department_id=department_id,
            available=True,
        ).exclude(pk=obj.pk).exists():
            raise ValidationError({"department_id": "This department already has an available officer."})
        obj.department_id = department_id
        obj.available = available
        obj.designation = request.data.get("designation", obj.designation)
        obj.save()
        return success(
            {
                "id": obj.id,
                "user_id": obj.user_id,
                "name": obj.user.name,
                "department_id": obj.department_id,
                "designation": obj.designation,
                "available": obj.available,
            },
            "Officer updated.",
        )


class AdminEngineerListView(generics.ListAPIView):
    permission_classes = [IsAdministrator]
    serializer_class = EngineerAdminSchemaSerializer
    queryset = EngineerProfile.objects.none()

    @extend_schema(responses=APIEnvelopeSerializer)
    def get(self, request):
        return success(
            [
                {
                    "id": e.id,
                    "user_id": e.user_id,
                    "name": e.user.name,
                    "department_id": e.department_id,
                    "available": e.available,
                    "workload": e.workload,
                    "service_ids": list(e.services.values_list("id", flat=True)),
                    "services": list(e.services.values_list("name", flat=True)),
                }
                for e in EngineerProfile.objects.select_related("user")
            ]
        )


class AdminEngineerDetailView(generics.UpdateAPIView):
    permission_classes = [IsAdministrator]
    serializer_class = EngineerAdminSchemaSerializer
    queryset = EngineerProfile.objects.all()

    @extend_schema(request=EngineerAdminSchemaSerializer, responses=APIEnvelopeSerializer)
    def patch(self, request, *args, **kwargs):
        obj = self.get_object()
        department_id = request.data.get("department_id", obj.department_id)
        service_ids = request.data.get("service_ids", list(obj.services.values_list("id", flat=True)))
        if not isinstance(service_ids, list) or any(isinstance(value, bool) or not isinstance(value, int) for value in service_ids):
            raise ValidationError({"service_ids": "Provide a list of service IDs."})
        services = Service.objects.filter(pk__in=service_ids, department_id=department_id, active=True)
        if services.count() != len(set(service_ids)):
            raise ValidationError({"service_ids": "Engineers may only be qualified for active services in their department."})
        obj.department_id = department_id
        obj.available = request.data.get("available", obj.available)
        if "workload" in request.data:
            obj.workload = request.data.get("workload")
        obj.save()
        obj.services.set(service_ids)
        return success(
            {
                "id": obj.id,
                "user_id": obj.user_id,
                "name": obj.user.name,
                "department_id": obj.department_id,
                "available": obj.available,
                "workload": obj.workload,
                "service_ids": list(obj.services.values_list("id", flat=True)),
                "services": list(obj.services.values_list("name", flat=True)),
            },
            "Engineer updated.",
        )
