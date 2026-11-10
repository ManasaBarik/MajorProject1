from django.db import models


class Service(models.Model):
    class ServiceType(models.TextChoices):
        MUNICIPAL = "MUNICIPAL"
        BUSINESS = "BUSINESS"

    name = models.CharField(max_length=150)
    code = models.CharField(max_length=50, unique=True, blank=True, db_index=True)
    department = models.ForeignKey(
        "departments.Department",
        on_delete=models.PROTECT,
        related_name="services",
    )
    description = models.TextField(blank=True)
    service_type = models.CharField(
        max_length=50,
        choices=ServiceType.choices,
        blank=True,
        default="",
    )
    field_verification_required = models.BooleanField(default=False)
    eligibility = models.TextField(blank=True)
    procedure = models.TextField(blank=True)
    processing_time_days = models.PositiveIntegerField(default=7)
    estimated_processing_days = models.PositiveIntegerField(default=7)
    fee = models.DecimalField(max_digits=10, decimal_places=2, default=0.0)
    active = models.BooleanField(default=True)
    requirements = models.JSONField(default=list, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name


class RequiredDocument(models.Model):
    service = models.ForeignKey(
        Service,
        on_delete=models.CASCADE,
        related_name="required_documents",
    )
    key = models.SlugField(max_length=100)
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    is_mandatory = models.BooleanField(default=True)
    allowed_file_types = models.JSONField(default=list, blank=True)
    max_file_size = models.PositiveIntegerField(default=10 * 1024 * 1024)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=("service", "key"), name="service_document_key_uniq"),
        ]
