from django.db import models
from django.utils import timezone


class Complaint(models.Model):
    class Category(models.TextChoices):
        ROAD = "ROAD"
        ROADS = "ROADS"
        DRAINAGE = "DRAINAGE"
        WATER = "WATER"
        WATER_SUPPLY = "WATER_SUPPLY"
        WATER_QUALITY = "WATER_QUALITY"
        STREET_LIGHT = "STREET_LIGHT"
        STREETLIGHT = "STREETLIGHT"
        WASTE_MANAGEMENT = "WASTE_MANAGEMENT"
        GARBAGE = "GARBAGE"
        SEWERAGE = "SEWERAGE"
        SEWAGE = "SEWAGE"
        SANITATION = "SANITATION"
        PARKS = "PARKS"
        TRAFFIC = "TRAFFIC"
        HEALTH = "HEALTH"
        ENCROACHMENT = "ENCROACHMENT"
        OTHER = "OTHER"

    class Status(models.TextChoices):
        SUBMITTED = "SUBMITTED"
        AI_PROCESSING = "AI_PROCESSING"
        CLASSIFIED = "CLASSIFIED"
        ASSIGNED = "ASSIGNED"
        IN_PROGRESS = "IN_PROGRESS"
        ON_HOLD = "ON_HOLD"
        RESOLUTION_SUBMITTED = "RESOLUTION_SUBMITTED"
        VERIFICATION_PENDING = "VERIFICATION_PENDING"
        RESOLVED = "RESOLVED"
        REOPENED = "REOPENED"
        REJECTED = "REJECTED"
        CLOSED = "CLOSED"

    class Priority(models.TextChoices):
        LOW = "LOW"
        MEDIUM = "MEDIUM"
        HIGH = "HIGH"
        CRITICAL = "CRITICAL"

    def save(self, *args, **kwargs):
        needs_number = not self.complaint_number
        super().save(*args, **kwargs)
        if needs_number:
            year = self.created_at.year if self.created_at else timezone.now().year
            self.complaint_number = f"CIV-{year}-{self.pk:08d}"
            type(self).objects.filter(pk=self.pk).update(complaint_number=self.complaint_number)

    complaint_number = models.CharField(max_length=32, unique=True, null=True, blank=True, db_index=True)
    citizen = models.ForeignKey(
        "accounts.User",
        on_delete=models.PROTECT,
        related_name="complaints",
    )
    title = models.CharField(max_length=255)
    description = models.TextField()
    category = models.CharField(max_length=80, choices=Category.choices, blank=True)
    priority = models.CharField(
        max_length=10,
        choices=Priority.choices,
        default=Priority.MEDIUM,
    )
    department = models.ForeignKey(
        "departments.Department",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="complaints",
    )
    address = models.TextField(blank=True)
    ward = models.CharField(max_length=80, blank=True, db_index=True)
    latitude = models.DecimalField(max_digits=9, decimal_places=6)
    longitude = models.DecimalField(max_digits=9, decimal_places=6)
    status = models.CharField(
        max_length=24,
        choices=Status.choices,
        default=Status.SUBMITTED,
        db_index=True,
    )
    assigned_engineer = models.ForeignKey(
        "accounts.User",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="assigned_complaints",
    )
    resolution_description = models.TextField(blank=True)
    sla_due_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["status", "created_at"]),
            models.Index(fields=["department", "status"]),
            models.Index(fields=["ward"]),
        ]


class ComplaintImage(models.Model):
    complaint = models.ForeignKey(
        Complaint,
        on_delete=models.CASCADE,
        related_name="images",
    )
    file = models.FileField(upload_to="complaints/%Y/%m/")
    caption = models.CharField(max_length=255, blank=True)
    uploaded_by = models.ForeignKey(
        "accounts.User",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="complaint_images",
    )
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)


class ComplaintVideo(models.Model):
    complaint = models.ForeignKey(
        Complaint,
        on_delete=models.CASCADE,
        related_name="videos",
    )
    file = models.FileField(upload_to="complaints/videos/%Y/%m/")
    created_at = models.DateTimeField(auto_now_add=True)


class ComplaintStatusHistory(models.Model):
    complaint = models.ForeignKey(
        Complaint,
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
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["created_at", "id"]


class ComplaintAssignment(models.Model):
    complaint = models.ForeignKey(
        Complaint,
        on_delete=models.CASCADE,
        related_name="assignments",
    )
    engineer = models.ForeignKey(
        "accounts.User",
        on_delete=models.PROTECT,
    )
    assigned_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.PROTECT,
        related_name="assignments_made",
    )
    assigned_time = models.DateTimeField(auto_now_add=True)
    completed_time = models.DateTimeField(null=True, blank=True)
    unassigned_at = models.DateTimeField(null=True, blank=True)
    remarks = models.TextField(blank=True)


class ComplaintResolution(models.Model):
    class VerificationStatus(models.TextChoices):
        PENDING = "PENDING"
        APPROVED = "APPROVED"
        REJECTED = "REJECTED"

    complaint = models.ForeignKey(
        Complaint,
        on_delete=models.CASCADE,
        related_name="resolutions",
    )
    description = models.TextField()
    evidence_image = models.FileField(upload_to="complaints/resolutions/%Y/%m/", blank=True)
    submitted_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.PROTECT,
        related_name="submitted_resolutions",
    )
    submitted_at = models.DateTimeField(auto_now_add=True)
    verification_status = models.CharField(
        max_length=20,
        choices=VerificationStatus.choices,
        default=VerificationStatus.PENDING,
    )
    verified_by = models.ForeignKey(
        "accounts.User",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="verified_resolutions",
    )
    verified_at = models.DateTimeField(null=True, blank=True)
    verification_remarks = models.TextField(blank=True)

    class Meta:
        ordering = ["-submitted_at", "-id"]


class AIAnalysis(models.Model):
    complaint = models.ForeignKey(
        Complaint,
        on_delete=models.CASCADE,
        related_name="ai_analyses",
    )
    category_prediction = models.CharField(max_length=80, blank=True, null=True)
    priority_prediction = models.CharField(max_length=10, blank=True, null=True)
    department_recommendation = models.ForeignKey(
        "departments.Department",
        null=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )
    confidence = models.FloatField(null=True, blank=True)
    summary = models.TextField(blank=True)
    reason = models.TextField(blank=True)
    provider = models.CharField(max_length=100, blank=True)
    model_name = models.CharField(max_length=100, blank=True)
    raw_response = models.JSONField(null=True, blank=True)
    requires_manual_review = models.BooleanField(default=False)
    similar_complaints = models.JSONField(default=list, blank=True)
    is_overridden = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    human_category = models.CharField(max_length=80, blank=True)
    human_priority = models.CharField(max_length=10, blank=True)
    human_department = models.ForeignKey(
        "departments.Department",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )
    reviewed_by = models.ForeignKey(
        "accounts.User",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    review_remarks = models.TextField(blank=True)

    class Meta:
        ordering = ["-created_at"]


class ComplaintFeedback(models.Model):
    complaint = models.OneToOneField(
        Complaint,
        on_delete=models.CASCADE,
        related_name="feedback",
    )
    citizen = models.ForeignKey("accounts.User", on_delete=models.PROTECT)
    rating = models.PositiveSmallIntegerField()
    comment = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)


class ComplaintCluster(models.Model):
    cluster_id = models.CharField(max_length=32, unique=True, db_index=True)
    category = models.CharField(max_length=80, blank=True)
    confidence = models.FloatField(default=0.0)
    reason = models.TextField(blank=True)
    complaints = models.ManyToManyField(Complaint, related_name="clusters")
    created_at = models.DateTimeField(auto_now_add=True)
