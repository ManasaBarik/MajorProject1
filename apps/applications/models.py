from django.db import models


class BusinessApplication(models.Model):
    class Status(models.TextChoices):
        DRAFT = "DRAFT"
        SUBMITTED = "SUBMITTED"
        UNDER_REVIEW = "UNDER_REVIEW"
        ENGINEER_REVIEW = "ENGINEER_REVIEW"
        DOCUMENT_VERIFICATION = "DOCUMENT_VERIFICATION"
        CLARIFICATION_REQUIRED = "CLARIFICATION_REQUIRED"
        CLARIFICATION_REQUESTED = "CLARIFICATION_REQUESTED"
        APPROVED = "APPROVED"
        REJECTED = "REJECTED"
        COMPLETED = "COMPLETED"
        CANCELLED = "CANCELLED"
        FIELD_VERIFICATION = "FIELD_VERIFICATION"

    applicant = models.ForeignKey(
        "accounts.User",
        on_delete=models.PROTECT,
        related_name="applications",
    )
    business = models.ForeignKey(
        "businesses.BusinessProfile",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="applications",
    )
    service = models.ForeignKey(
        "services.Service",
        on_delete=models.PROTECT,
        related_name="applications",
    )
    application_number = models.CharField(max_length=32, unique=True, db_index=True)
    department = models.ForeignKey(
        "departments.Department",
        on_delete=models.PROTECT,
        related_name="applications",
    )
    assigned_officer = models.ForeignKey(
        "accounts.OfficerProfile",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="assigned_applications",
    )
    assigned_engineer = models.ForeignKey(
        "accounts.EngineerProfile",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="assigned_applications",
    )
    status = models.CharField(
        max_length=24,
        choices=Status.choices,
        default=Status.SUBMITTED,
        db_index=True,
    )
    data = models.JSONField(default=dict, blank=True)
    remarks = models.TextField(blank=True)
    rejection_reason = models.TextField(blank=True)
    submitted_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-submitted_at"]
        indexes = [
            models.Index(fields=["status", "submitted_at"]),
            models.Index(fields=["department", "status"]),
        ]


class ApplicationDocument(models.Model):
    class DocStatus(models.TextChoices):
        PENDING = "PENDING"
        VERIFIED = "VERIFIED"
        REJECTED = "REJECTED"

    application = models.ForeignKey(
        BusinessApplication,
        on_delete=models.CASCADE,
        related_name="documents",
    )
    key = models.CharField(max_length=100, blank=True)
    label = models.CharField(max_length=200, blank=True)
    filename = models.CharField(max_length=255, blank=True)
    file = models.FileField(upload_to="applications/%Y/%m/")
    status = models.CharField(
        max_length=20,
        choices=DocStatus.choices,
        default=DocStatus.PENDING,
    )
    remarks = models.TextField(blank=True)
    uploaded_by = models.ForeignKey(
        "accounts.User",
        null=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )
    verified_by = models.ForeignKey(
        "accounts.User",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="verified_application_documents",
    )
    verified_at = models.DateTimeField(null=True, blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if not self.filename and self.file:
            self.filename = getattr(self.file, "name", "")
        super().save(*args, **kwargs)


class ApplicationStatusHistory(models.Model):
    application = models.ForeignKey(
        BusinessApplication,
        on_delete=models.CASCADE,
        related_name="history",
    )
    old_status = models.CharField(max_length=24, blank=True)
    new_status = models.CharField(max_length=24)
    changed_by = models.ForeignKey(
        "accounts.User",
        null=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )
    remarks = models.TextField(blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["timestamp", "id"]


class ApplicationEngineerAssignment(models.Model):
    application = models.ForeignKey(
        BusinessApplication,
        on_delete=models.CASCADE,
        related_name="engineer_assignments",
    )
    engineer = models.ForeignKey(
        "accounts.EngineerProfile",
        on_delete=models.PROTECT,
        related_name="application_assignments",
    )
    assigned_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.PROTECT,
        related_name="application_engineer_assignments_made",
    )
    assigned_at = models.DateTimeField(auto_now_add=True)
    unassigned_at = models.DateTimeField(null=True, blank=True)
    remarks = models.TextField(blank=True)

    class Meta:
        ordering = ["assigned_at", "id"]
