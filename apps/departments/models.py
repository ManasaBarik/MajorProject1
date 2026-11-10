from django.db import models


class Department(models.Model):
    name = models.CharField(max_length=150, unique=True)
    code = models.CharField(max_length=50, unique=True, blank=True, db_index=True)
    description = models.TextField(blank=True)
    contact_email = models.EmailField(blank=True)
    contact_phone = models.CharField(max_length=30, blank=True)
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

    @property
    def is_active(self):
        return self.active

    @property
    def staff_count(self):
        officer_count = self.staff.count()
        engineer_count = getattr(self, "engineers", None).count() or 0
        return officer_count + engineer_count


class CategoryDepartmentMapping(models.Model):
    """Administrator-configurable routing of a complaint category to a department.

    The AI only *suggests* a category; the department is always resolved through
    this table so the mapping stays under municipal control instead of being
    hardcoded in the model prompt.
    """

    category = models.CharField(max_length=80, unique=True, db_index=True)
    department = models.ForeignKey(
        Department,
        on_delete=models.CASCADE,
        related_name="category_mappings",
    )
    default_priority = models.CharField(max_length=10, blank=True)
    active = models.BooleanField(default=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["category"]

    def __str__(self):
        return f"{self.category} -> {self.department.name}"
