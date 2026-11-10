from rest_framework import serializers


class APIEnvelopeSerializer(serializers.Serializer):
    success = serializers.BooleanField()
    data = serializers.JSONField()
    message = serializers.CharField()


class LogoutRequestSerializer(serializers.Serializer):
    refresh = serializers.CharField()


class PasswordResetRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()


class PasswordResetConfirmRequestSerializer(serializers.Serializer):
    reset_token = serializers.CharField()
    new_password = serializers.CharField(write_only=True)


class ChatRequestSerializer(serializers.Serializer):
    message = serializers.CharField()
    language = serializers.CharField(required=False, default="en")
    context = serializers.CharField(required=False, default="CITIZEN")
    conversation_id = serializers.IntegerField(required=False)
