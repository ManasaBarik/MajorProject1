import json
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.departments.models import Department
from apps.services.models import RequiredDocument, Service


class Command(BaseCommand):
    help = "Import configured departments and services from an operator-supplied JSON file."

    def add_arguments(self, parser):
        parser.add_argument(
            "--catalog-file",
            type=Path,
            help="JSON file containing configured departments and services.",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        catalog_file = options.get("catalog_file")
        if not catalog_file:
            self.stdout.write("No catalog file supplied; no data was changed. Create the first administrator with createsuperuser.")
            return
        try:
            catalog = json.loads(catalog_file.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise CommandError(f"Unable to read catalog file: {exc}") from exc
        if not isinstance(catalog, dict):
            raise CommandError("Catalog file must contain a JSON object.")

        departments = catalog.get("departments", [])
        services = catalog.get("services", [])
        if not isinstance(departments, list) or not isinstance(services, list):
            raise CommandError("departments and services must be JSON arrays.")

        department_count = 0
        for item in departments:
            if not isinstance(item, dict) or not item.get("name") or not item.get("code"):
                raise CommandError("Each department requires name and code.")
            Department.objects.update_or_create(
                code=item["code"],
                defaults={
                    "name": item["name"],
                    "description": item.get("description", ""),
                    "contact_email": item.get("contact_email", ""),
                    "contact_phone": item.get("contact_phone", ""),
                    "active": item.get("is_active", True),
                },
            )
            department_count += 1

        service_count = 0
        for item in services:
            if not isinstance(item, dict) or not item.get("name") or not item.get("code"):
                raise CommandError("Each service requires name and code.")
            department = Department.objects.filter(code=item.get("department_code")).first()
            if not department:
                raise CommandError(f"Unknown department_code for service {item['code']}.")
            requirements = item.get("requirements", [])
            if not isinstance(requirements, list):
                raise CommandError(f"requirements for service {item['code']} must be a JSON array.")
            processing_days = item.get("estimated_processing_days", item.get("processing_time_days", 7))
            service, _ = Service.objects.update_or_create(
                code=item["code"],
                defaults={
                    "name": item["name"],
                    "department": department,
                    "description": item.get("description", ""),
                    "service_type": item.get("service_type", ""),
                    "eligibility": item.get("eligibility", ""),
                    "procedure": item.get("procedure", ""),
                    "processing_time_days": processing_days,
                    "estimated_processing_days": processing_days,
                    "fee": item.get("fee", 0),
                    "active": item.get("is_active", True),
                    "requirements": requirements,
                },
            )
            for requirement in requirements:
                if not isinstance(requirement, dict) or requirement.get("type") != "file":
                    continue
                if not requirement.get("key") or not requirement.get("label"):
                    raise CommandError(f"File requirements for {item['code']} require key and label.")
                RequiredDocument.objects.update_or_create(
                    service=service,
                    key=requirement["key"],
                    defaults={
                        "name": requirement["label"],
                        "description": requirement.get("description", ""),
                        "is_mandatory": requirement.get("required", True),
                        "allowed_file_types": requirement.get("allowed_file_types", []),
                        "max_file_size": requirement.get("max_file_size", 10 * 1024 * 1024),
                    },
                )
            service_count += 1

        self.stdout.write(f"Imported {department_count} departments and {service_count} services. No user or demo activity records were created.")
