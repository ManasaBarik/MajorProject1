from django.core.management.base import BaseCommand
from django.db import transaction

from apps.departments.models import Department
from apps.services.models import RequiredDocument, Service


MAX_UPLOAD_SIZE = 10 * 1024 * 1024


def _text(key, label, required=True):
    return {"key": key, "label": label, "type": "text", "required": required}


def _textarea(key, label, required=True):
    return {"key": key, "label": label, "type": "textarea", "required": required}


def _date(key, label, required=True):
    return {"key": key, "label": label, "type": "date", "required": required}


def _select(key, label, options, required=True):
    return {"key": key, "label": label, "type": "select", "options": options, "required": required}


def _file(key, label, required=True):
    return {
        "key": key,
        "label": label,
        "type": "file",
        "required": required,
        "allowed_file_types": ["pdf", "jpg", "jpeg", "png"],
        "max_file_size": MAX_UPLOAD_SIZE,
    }


_SERVICES = [
    {
        "code": "START-BIRTH-CERT",
        "name": "Birth Certificate",
        "service_type": "MUNICIPAL",
        "department": "health",
        "description": "Apply for an official record of a birth registered in the municipality.",
        "eligibility": "Parent or legal guardian of the child.",
        "procedure": "Submit the birth details and hospital record for officer verification.",
        "processing_time_days": 7,
        "fee": 50,
        "requirements": [
            _text("applicant_name", "Applicant full name"),
            _text("child_name", "Child full name"),
            _date("date_of_birth", "Date of birth"),
            _text("place_of_birth", "Place of birth"),
            _file("hospital_record", "Hospital record / birth proof"),
            _file("address_proof", "Parent or guardian address proof"),
        ],
    },
    {
        "code": "START-DEATH-CERT",
        "name": "Death Certificate",
        "service_type": "MUNICIPAL",
        "department": "health",
        "description": "Apply for an official death record for a death registered in the municipality.",
        "eligibility": "Immediate family member or authorized representative.",
        "procedure": "Submit the deceased person's details and supporting medical record.",
        "processing_time_days": 7,
        "fee": 75,
        "requirements": [
            _text("applicant_name", "Applicant full name"),
            _text("deceased_name", "Deceased full name"),
            _date("date_of_death", "Date of death"),
            _file("death_report", "Hospital / doctor death report"),
            _file("applicant_id", "Applicant ID proof"),
        ],
    },
    {
        "code": "START-WATER-CONNECTION",
        "name": "New Water Connection",
        "service_type": "MUNICIPAL",
        "department": "water",
        "description": "Apply for a new water supply connection at a municipal property.",
        "eligibility": "Property owner or an authorized representative.",
        "procedure": "Submit property and connection details. The department may schedule a site inspection.",
        "processing_time_days": 15,
        "fee": 1500,
        "field_verification_required": True,
        "requirements": [
            _text("applicant_name", "Applicant full name"),
            _textarea("installation_address", "Installation address"),
            _select("connection_type", "Connection type", ["DOMESTIC", "COMMERCIAL"]),
            _file("property_proof", "Property ownership / authorization proof"),
            _file("id_proof", "Applicant ID proof"),
        ],
    },
    {
        "code": "START-WASTE-COLLECTION",
        "name": "Waste Collection Setup",
        "service_type": "MUNICIPAL",
        "department": "waste",
        "description": "Request or update regular municipal waste collection for an address.",
        "eligibility": "Resident, property owner, or authorized business representative.",
        "procedure": "Submit the service address and collection type for routing to the waste department.",
        "processing_time_days": 5,
        "fee": 0,
        "requirements": [
            _text("applicant_name", "Applicant full name"),
            _textarea("service_address", "Collection address"),
            _select("collection_type", "Collection type", ["RESIDENTIAL", "BUSINESS"]),
            _file("address_proof", "Address proof"),
        ],
    },
    {
        "code": "START-TRADE-LICENSE",
        "name": "New Trade License",
        "service_type": "BUSINESS",
        "department": "planning",
        "description": "Apply for a municipal trade license for a new commercial establishment.",
        "eligibility": "Owner or authorized representative of a business operating in the municipality.",
        "procedure": "Submit business details and premises documents. An officer may request clarification or a site visit.",
        "processing_time_days": 14,
        "fee": 2500,
        "field_verification_required": True,
        "requirements": [
            _text("business_name", "Business name"),
            _select("business_type", "Business type", ["RETAIL", "WHOLESALE", "MANUFACTURING", "SERVICE", "FOOD", "OTHER"]),
            _textarea("business_address", "Business address"),
            _text("gstin", "GSTIN", required=False),
            _file("premises_proof", "Ownership / rent agreement"),
            _file("owner_id", "Owner ID proof"),
        ],
    },
    {
        "code": "START-TRADE-LICENSE-RENEWAL",
        "name": "Trade License Renewal",
        "service_type": "BUSINESS",
        "department": "planning",
        "description": "Renew an existing municipal trade license.",
        "eligibility": "Holder of a current or recently expired municipal trade license.",
        "procedure": "Provide the existing license number and updated business documents for review.",
        "processing_time_days": 10,
        "fee": 1500,
        "requirements": [
            _text("business_name", "Business name"),
            _text("license_number", "Existing license number"),
            _textarea("business_address", "Business address"),
            _file("current_license", "Existing trade license"),
        ],
    },
    {
        "code": "START-SIGNBOARD-PERMIT",
        "name": "Signboard Permit",
        "service_type": "BUSINESS",
        "department": "planning",
        "description": "Request approval to install or replace a business signboard.",
        "eligibility": "Business owner or authorized representative with premises permission.",
        "procedure": "Submit sign dimensions, installation location, and a mock-up for officer review.",
        "processing_time_days": 10,
        "fee": 600,
        "field_verification_required": True,
        "requirements": [
            _text("business_name", "Business name"),
            _textarea("installation_location", "Signboard installation location"),
            _text("sign_dimensions", "Signboard dimensions"),
            _file("sign_mockup", "Signboard design / mock-up"),
            _file("premises_permission", "Premises ownership / permission proof"),
        ],
    },
]


_DEPARTMENTS = {
    "health": {
        "name": "Public Health & Civil Registration",
        "description": "Civil registration and public health records.",
        "codes": ("HEALTH", "004"),
        "keywords": ("health", "civil registration"),
    },
    "water": {
        "name": "Water Supply & Utilities",
        "description": "Municipal water connections and utility services.",
        "codes": ("WATER", "WATER_DEMO"),
        "keywords": ("water", "utilities"),
    },
    "waste": {
        "name": "Solid Waste Management",
        "description": "Municipal collection and disposal of solid waste.",
        "codes": ("SWM", "WASTE"),
        "keywords": ("waste", "solid waste"),
    },
    "planning": {
        "name": "Planning & Business Licensing",
        "description": "Planning approvals and municipal business permits.",
        "codes": ("TPL", "003"),
        "keywords": ("planning", "license"),
    },
}


class Command(BaseCommand):
    help = "Add an editable municipal and business starter service catalog."

    @transaction.atomic
    def handle(self, *args, **options):
        departments = {}
        for key, spec in _DEPARTMENTS.items():
            department = Department.objects.filter(code__in=spec["codes"]).first()
            if not department:
                for keyword in spec["keywords"]:
                    department = Department.objects.filter(name__icontains=keyword).first()
                    if department:
                        break
            if not department:
                department, _ = Department.objects.get_or_create(
                    code=f"START-{key.upper()}",
                    defaults={"name": spec["name"], "description": spec["description"]},
                )
            departments[key] = department

        created = 0
        for spec in _SERVICES:
            service, was_created = Service.objects.get_or_create(
                code=spec["code"],
                defaults={
                    "name": spec["name"],
                    "service_type": spec["service_type"],
                    "department": departments[spec["department"]],
                    "description": spec["description"],
                    "eligibility": spec["eligibility"],
                    "procedure": spec["procedure"],
                    "processing_time_days": spec["processing_time_days"],
                    "estimated_processing_days": spec["processing_time_days"],
                    "fee": spec["fee"],
                    "field_verification_required": spec.get("field_verification_required", False),
                    "requirements": spec["requirements"],
                    "active": True,
                },
            )
            if was_created:
                created += 1
            elif not service.service_type:
                service.service_type = spec["service_type"]
                service.save(update_fields=["service_type", "updated_at"])

            for requirement in spec["requirements"]:
                if requirement.get("type") == "file":
                    RequiredDocument.objects.get_or_create(
                        service=service,
                        key=requirement["key"],
                        defaults={
                            "name": requirement["label"],
                            "is_mandatory": requirement.get("required", True),
                            "allowed_file_types": requirement.get("allowed_file_types", []),
                            "max_file_size": requirement.get("max_file_size", MAX_UPLOAD_SIZE),
                        },
                    )

        known_municipal_codes = (
            "SRV-001", "SRV-002", "DEMO-WATER-CONNECTION",
            "DEMO-WATER-QUALITY", "DEMO-PARKS-MAINTENANCE",
        )
        Service.objects.filter(code__in=known_municipal_codes, service_type="").update(service_type="MUNICIPAL")
        self.stdout.write(self.style.SUCCESS(f"Starter catalog ready; {created} new services added."))
