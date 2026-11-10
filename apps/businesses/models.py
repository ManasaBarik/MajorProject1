from django.db import models


class BusinessProfile(models.Model):
    class Status(models.TextChoices):
        ACTIVE = "ACTIVE"
        INACTIVE = "INACTIVE"
        PENDING = "PENDING"
        SUSPENDED = "SUSPENDED"

    class BusinessType(models.TextChoices):
        RETAIL = "RETAIL"
        WHOLESALE = "WHOLESALE"
        MANUFACTURING = "MANUFACTURING"
        SERVICE = "SERVICE"
        FOOD = "FOOD"
        HEALTHCARE = "HEALTHCARE"
        EDUCATION = "EDUCATION"
        CONSTRUCTION = "CONSTRUCTION"
        OTHER = "OTHER"

    owner = models.ForeignKey(
        "accounts.User",
        on_delete=models.CASCADE,
        related_name="businesses",
    )
    name = models.CharField(max_length=200)
    registration_number = models.CharField(max_length=100, blank=True)
    owner_name = models.CharField(max_length=200, blank=True)
    type = models.CharField(
        max_length=50,
        choices=BusinessType.choices,
        default=BusinessType.OTHER,
    )
    address = models.TextField()
    city = models.CharField(max_length=100, blank=True)
    state = models.CharField(max_length=100, blank=True)
    pincode = models.CharField(max_length=12, blank=True)
    email = models.EmailField(blank=True)
    gstin = models.CharField(max_length=20, blank=True)
    license_number = models.CharField(max_length=100, blank=True)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        db_index=True,
    )
    phone = models.CharField(max_length=30, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        if not self.owner_name and self.owner:
            self.owner_name = self.owner.name
        super().save(*args, **kwargs)
