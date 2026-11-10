"""Bootstrap ``CategoryDepartmentMapping`` rows from existing department names.

Run once after creating departments, then adjust the mappings in Django admin
(or via ``/api/v1/category-mappings/``) so the AI routes complaints correctly.
"""
from django.core.management.base import BaseCommand

from apps.ai.constants import CANONICAL_CATEGORIES, CATEGORY_DEPARTMENT_HINTS
from apps.departments.models import CategoryDepartmentMapping, Department


class Command(BaseCommand):
    help = "Seed category -> department mappings by matching existing department names."

    def add_arguments(self, parser):
        parser.add_argument(
            "--overwrite",
            action="store_true",
            help="Re-point existing mappings to the matched department.",
        )

    def handle(self, *args, **options):
        departments = list(Department.objects.filter(active=True))
        if not departments:
            self.stdout.write(self.style.WARNING(
                "No active departments found. Create departments first."
            ))
            return

        created = updated = skipped = 0
        for category in CANONICAL_CATEGORIES:
            if category == "OTHER":
                continue
            hints = CATEGORY_DEPARTMENT_HINTS.get(category, ())
            match = None
            for department in departments:
                haystack = f"{department.name} {department.code}".lower()
                if any(hint in haystack for hint in hints):
                    match = department
                    break
            if match is None:
                skipped += 1
                continue

            mapping, was_created = CategoryDepartmentMapping.objects.get_or_create(
                category=category,
                defaults={
                    "department": match,
                    "notes": "Auto-seeded from department names; review and adjust.",
                },
            )
            if was_created:
                created += 1
            elif options["overwrite"]:
                mapping.department = match
                mapping.save(update_fields=["department", "updated_at"])
                updated += 1

        self.stdout.write(self.style.SUCCESS(
            f"Category mappings: created={created} updated={updated} skipped={skipped}"
        ))
