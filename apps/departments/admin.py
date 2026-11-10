from django.contrib import admin

from .models import CategoryDepartmentMapping, Department


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "active", "created_at")
    list_filter = ("active",)
    search_fields = ("name", "code")


@admin.register(CategoryDepartmentMapping)
class CategoryDepartmentMappingAdmin(admin.ModelAdmin):
    list_display = ("category", "department", "default_priority", "active", "updated_at")
    list_filter = ("active", "department")
    search_fields = ("category", "department__name")
