from django.db import models


class Notification(models.Model):
    class Type(models.TextChoices):
        COMPLAINT = "complaint"
        APPLICATION = "application"
        SYSTEM = "system"

    recipient = models.ForeignKey(
        "accounts.User",
        on_delete=models.CASCADE,
        related_name="notifications",
    )
    title = models.CharField(max_length=200)
    message = models.TextField()
    type = models.CharField(
        max_length=20,
        choices=Type.choices,
        default=Type.SYSTEM,
        db_index=True,
    )
    related_id = models.CharField(max_length=64, blank=True)
    related_object_type = models.CharField(max_length=50, blank=True)
    related_object_id = models.CharField(max_length=64, blank=True)
    read = models.BooleanField(default=False, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    @property
    def user(self):
        return self.recipient

    @property
    def notification_type(self):
        return self.type

    @property
    def is_read(self):
        return self.read
