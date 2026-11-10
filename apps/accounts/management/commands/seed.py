from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from django.db import transaction
from django.contrib.auth.hashers import make_password


_DEPARTMENTS = [
    {"name": "Drainage & Sewage", "code": "DRAIN", "description": "Storm water drainage and sewage management."},
    {"name": "Roads & Transport", "code": "ROAD", "description": "Road maintenance, traffic and public transport."},
    {"name": "Water Supply", "code": "WATER", "description": "Potable water distribution and quality."},
    {"name": "Solid Waste Management", "code": "SWM", "description": "Collection, segregation and disposal of municipal waste."},
    {"name": "Health & Sanitation", "code": "HEALTH", "description": "Public health, sanitation and disease control."},
    {"name": "Town Planning & Licenses", "code": "TPL", "description": "Building permits, zoning and business licenses."},
]


def _text_req(key, label, required=True):
    return {"key": key, "label": label, "type": "text", "required": required}


def _textarea_req(key, label, required=True):
    return {"key": key, "label": label, "type": "textarea", "required": required}


def _date_req(key, label, required=True):
    return {"key": key, "label": label, "type": "date", "required": required}


def _file_req(key, label, required=True):
    return {"key": key, "label": label, "type": "file", "required": required}


def _select_req(key, label, options, required=True):
    return {"key": key, "label": label, "type": "select", "options": options, "required": required}


_SERVICES = [
    {
        "name": "Birth Certificate",
        "code": "BIRTH-CERT",
        "department_index": 4,
        "description": "Official birth certificate issued by the Health & Sanitation department.",
        "processing_time_days": 7,
        "fee": 50.00,
        "requirements": [
            _text_req("applicant_name", "Applicant full name"),
            _text_req("child_name", "Child full name"),
            _date_req("date_of_birth", "Date of birth"),
            _text_req("place_of_birth", "Place of birth"),
            _text_req("mother_name", "Mother's full name"),
            _text_req("father_name", "Father's full name"),
            _file_req("hospital_record", "Hospital record / discharge slip"),
            _file_req("address_proof", "Address proof of parents"),
        ],
    },
    {
        "name": "Death Certificate",
        "code": "DEATH-CERT",
        "department_index": 4,
        "description": "Official death certificate issued by the Health & Sanitation department.",
        "processing_time_days": 5,
        "fee": 75.00,
        "requirements": [
            _text_req("applicant_name", "Applicant full name"),
            _text_req("deceased_name", "Deceased full name"),
            _date_req("date_of_death", "Date of death"),
            _text_req("place_of_death", "Place of death"),
            _textarea_req("cause_of_death", "Cause of death (if known)", required=False),
            _file_req("death_report", "Hospital / doctor death report"),
            _file_req("applicant_id", "Applicant ID proof"),
        ],
    },
    {
        "name": "New Water Connection",
        "code": "WATER-NEW",
        "department_index": 2,
        "description": "Application for a new domestic water supply connection.",
        "processing_time_days": 15,
        "fee": 1500.00,
        "requirements": [
            _text_req("applicant_name", "Applicant full name"),
            _textarea_req("installation_address", "Installation address"),
            _text_req("ward", "Ward number"),
            _select_req("connection_type", "Connection type", options=["DOMESTIC", "COMMERCIAL", "INDUSTRIAL"]),
            _text_req("property_id", "Property ID / Khata number"),
            _file_req("property_deed", "Property deed / ownership proof"),
            _file_req("id_proof", "Applicant ID proof"),
        ],
    },
    {
        "name": "Trade License",
        "code": "TRADE-LIC",
        "department_index": 5,
        "description": "Business / trade license for commercial establishments.",
        "processing_time_days": 14,
        "fee": 2500.00,
        "requirements": [
            _text_req("applicant_name", "Applicant full name"),
            _text_req("business_name", "Business name"),
            _select_req("business_type", "Business type", options=[
                "RETAIL", "WHOLESALE", "MANUFACTURING", "SERVICE", "FOOD", "HEALTHCARE", "EDUCATION", "CONSTRUCTION", "OTHER",
            ]),
            _textarea_req("business_address", "Business address"),
            _text_req("gstin", "GSTIN (if applicable)", required=False),
            _text_req("owner_contact", "Owner contact number"),
            _file_req("ownership_proof", "Premises ownership / rent agreement"),
            _file_req("id_proof", "Owner ID proof"),
            _file_req("site_plan", "Premises site plan"),
        ],
    },
    {
        "name": "Building Permission (Residential)",
        "code": "BLDG-RES",
        "department_index": 5,
        "description": "Construction approval for residential buildings.",
        "processing_time_days": 30,
        "fee": 5000.00,
        "requirements": [
            _text_req("applicant_name", "Applicant full name"),
            _textarea_req("site_address", "Site address"),
            _text_req("plot_number", "Plot / khata number"),
            _text_req("ward", "Ward"),
            _select_req("building_type", "Building type", options=[
                "G+1", "G+2", "G+3", "G+4", "APARTMENT",
            ]),
            _file_req("site_plan", "Approved site plan"),
            _file_req("building_plan", "Structural building plan"),
            _file_req("property_deed", "Property deed / ownership proof"),
            _file_req("id_proof", "Applicant ID proof"),
        ],
    },
    {
        "name": "Property Tax Assessment",
        "code": "PROP-TAX",
        "department_index": 5,
        "description": "Assessment or reassessment of a property for municipal taxation.",
        "processing_time_days": 21,
        "fee": 200.00,
        "requirements": [
            _text_req("applicant_name", "Applicant full name"),
            _textarea_req("property_address", "Property address"),
            _text_req("old_assessment_number", "Old assessment number (if any)", required=False),
            _select_req("property_type", "Property type", options=[
                "RESIDENTIAL", "COMMERCIAL", "INDUSTRIAL", "VACANT_LAND",
            ]),
            _text_req("built_up_area_sqft", "Built-up area in sq ft"),
            _file_req("property_deed", "Property deed / registration copy"),
            _file_req("id_proof", "Applicant ID proof"),
        ],
    },
    {
        "name": "Street Light Complaint (Service)",
        "code": "STREET-LIGHT",
        "department_index": 1,
        "description": "Service request for non-operational street lights in a ward.",
        "processing_time_days": 3,
        "fee": 0.00,
        "requirements": [
            _text_req("applicant_name", "Applicant full name"),
            _text_req("ward", "Ward number"),
            _textarea_req("location_description", "Pole / location description"),
            _text_req("pole_number", "Pole number (if available)", required=False),
        ],
    },
]


_COMPLAINT_SAMPLES = [
    {
        "title": "Storm water drain blocked near Govind Nagar",
        "description": "Heavy plastic waste and sediment have blocked the main storm drain. Water stagnates after light rains.",
        "category": "DRAINAGE",
        "priority": "HIGH",
        "department_idx": 0,
        "ward": "Ward 3",
        "address": "Near Govind Nagar Park, Ward 3, Bhubaneswar",
        "latitude": 20.2961,
        "longitude": 85.8245,
    },
    {
        "title": "Deep pothole on Jaydev Vihar road",
        "description": "A 2x2 ft pothole has formed right after the speed breaker, causing two-wheelers to skid.",
        "category": "ROADS",
        "priority": "HIGH",
        "department_idx": 1,
        "ward": "Ward 5",
        "address": "Jaydev Vihar Main Road, Ward 5",
        "latitude": 20.3011,
        "longitude": 85.8185,
    },
    {
        "title": "Water supply contamination in Khandagiri area",
        "description": "Water is cloudy and smells of chlorine overdose. Several households report stomach issues.",
        "category": "WATER_QUALITY",
        "priority": "CRITICAL",
        "department_idx": 2,
        "ward": "Ward 8",
        "address": "Khandagiri, Ward 8",
        "latitude": 20.2602,
        "longitude": 85.7860,
    },
    {
        "title": "Garbage not lifted for 4 days",
        "description": "Sector 7 dumpster is overflowing with mixed waste, attracting dogs and mosquitoes.",
        "category": "WASTE_MANAGEMENT",
        "priority": "MEDIUM",
        "department_idx": 3,
        "ward": "Ward 11",
        "address": "Sector 7 dumpster, Ward 11",
        "latitude": 20.3154,
        "longitude": 85.8423,
    },
    {
        "title": "Mosquito menace in Saheed Nagar",
        "description": "Increased mosquito activity after rains; stagnant water around under-construction site.",
        "category": "HEALTH",
        "priority": "MEDIUM",
        "department_idx": 4,
        "ward": "Ward 2",
        "address": "Saheed Nagar, Ward 2",
        "latitude": 20.2899,
        "longitude": 85.8412,
    },
    {
        "title": "Encroachment on footpath",
        "description": "Temporary shops have completely occupied the footpath, forcing pedestrians on road.",
        "category": "ENCROACHMENT",
        "priority": "MEDIUM",
        "department_idx": 5,
        "ward": "Ward 1",
        "address": "Rajmahal Square footpath, Ward 1",
        "latitude": 20.3200,
        "longitude": 85.8320,
    },
]


_COMPLAINT_STATUSES_TO_SAMPLE = [
    "SUBMITTED",
    "AI_PROCESSING",
    "CLASSIFIED",
    "ASSIGNED",
    "IN_PROGRESS",
    "ON_HOLD",
    "RESOLUTION_SUBMITTED",
    "VERIFICATION_PENDING",
    "RESOLVED",
    "REOPENED",
    "REJECTED",
    "CLOSED",
]


class Command(BaseCommand):
    help = "Seed the development database with departments, services, users, and sample records."

    def add_arguments(self, parser):
        parser.add_argument("--demo", action="store_true", help="Opt in to creating disposable sample users and records.")
        parser.add_argument(
            "--password",
            type=str,
            default=None,
            help="Required password for disposable sample users.",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        from apps.accounts.models import (
            User, CitizenProfile, OfficerProfile, EngineerProfile,
        )
        from apps.departments.models import Department
        from apps.services.models import Service
        from apps.complaints.models import (
            Complaint, ComplaintStatusHistory, AIAnalysis, ComplaintAssignment,
        )
        from apps.businesses.models import BusinessProfile
        from apps.applications.models import (
            BusinessApplication, ApplicationStatusHistory, ApplicationDocument,
        )

        if not options.get("demo"):
            self.stdout.write("No demo data was created. Use the seed_data command with an operator-supplied catalog file.")
            return
        password = options.get("password")
        if not password:
            raise CommandError("Pass --password when explicitly seeding demo users.")
        reset = False

        if reset:
            self.stdout.write("Resetting civic records...")
            ApplicationDocument.objects.all().delete()
            ApplicationStatusHistory.objects.all().delete()
            BusinessApplication.objects.all().delete()
            ComplaintAssignment.objects.all().delete()
            ComplaintStatusHistory.objects.all().delete()
            AIAnalysis.objects.all().delete()
            Complaint.objects.all().delete()
            BusinessProfile.objects.all().delete()
            Service.objects.all().delete()
            OfficerProfile.objects.all().delete()
            EngineerProfile.objects.all().delete()
            CitizenProfile.objects.all().delete()
            Department.objects.all().delete()
            User.objects.filter(is_superuser=False).delete()

        depts = []
        for d in _DEPARTMENTS:
            obj, _ = Department.objects.get_or_create(
                code=d["code"],
                defaults={"name": d["name"], "description": d["description"]},
            )
            depts.append(obj)
        self.stdout.write(f"Departments: {len(depts)}")

        services = []
        for svc in _SERVICES:
            dept = depts[svc["department_index"]]
            obj, _ = Service.objects.get_or_create(
                code=svc["code"],
                defaults={
                    "name": svc["name"],
                    "department": dept,
                    "description": svc["description"],
                    "processing_time_days": svc["processing_time_days"],
                    "fee": svc["fee"],
                    "requirements": svc["requirements"],
                },
            )
            services.append(obj)
        self.stdout.write(f"Services: {len(services)}")

        pw = make_password(password)

        def get_or_create_user(email, name, role, **extras):
            user, created = User.objects.get_or_create(
                email=email,
                defaults={
                    "name": name,
                    "role": role,
                    "password": pw,
                    "is_active": True,
                    **extras,
                },
            )
            if not created and user.password != pw:
                user.password = pw
                user.save(update_fields=["password"])
            return user

        admin = get_or_create_user("admin@civic.gov.in", "Civic Administrator", "ADMINISTRATOR")
        officer1 = get_or_create_user("officer.drain@civic.gov.in", "Officer Pradip Das", "OFFICER")
        officer2 = get_or_create_user("officer.health@civic.gov.in", "Officer Meena Kumari", "OFFICER")
        officer3 = get_or_create_user("officer.tpl@civic.gov.in", "Officer Rajesh Patil", "OFFICER")
        engineer_u1 = get_or_create_user("eng.roads@civic.gov.in", "Eng. Suresh Nayak", "ENGINEER")
        engineer_u2 = get_or_create_user("eng.water@civic.gov.in", "Eng. Anita Mohanty", "ENGINEER")
        engineer_u3 = get_or_create_user("eng.drain@civic.gov.in", "Eng. Devendra Sahu", "ENGINEER")
        citizen1 = get_or_create_user("citizen.ramesh@example.com", "Ramesh Patra", "CITIZEN")
        citizen2 = get_or_create_user("citizen.sangita@example.com", "Sangita Behera", "CITIZEN")
        biz1 = get_or_create_user("biz.rajesh@example.com", "Rajesh Gupta", "BUSINESS_OWNER")

        CitizenProfile.objects.get_or_create(user=citizen1, defaults={"ward": "Ward 3"})
        CitizenProfile.objects.get_or_create(user=citizen2, defaults={"ward": "Ward 5"})

        oprof1, _ = OfficerProfile.objects.get_or_create(
            user=officer1,
            defaults={"department": depts[0], "designation": "Assistant Engineer, Drainage"},
        )
        oprof2, _ = OfficerProfile.objects.get_or_create(
            user=officer2,
            defaults={"department": depts[4], "designation": "Health Inspector"},
        )
        oprof3, _ = OfficerProfile.objects.get_or_create(
            user=officer3,
            defaults={"department": depts[5], "designation": "Town Planner"},
        )
        _ = oprof2

        eprof1, _ = EngineerProfile.objects.get_or_create(
            user=engineer_u1,
            defaults={"department": depts[1], "available": True},
        )
        eprof2, _ = EngineerProfile.objects.get_or_create(
            user=engineer_u2,
            defaults={"department": depts[2], "available": True},
        )
        eprof3, _ = EngineerProfile.objects.get_or_create(
            user=engineer_u3,
            defaults={"department": depts[0], "available": True},
        )
        # Profile references for FK fields; keep user refs for history actors
        engineer_p1, engineer_p2, engineer_p3 = eprof1, eprof2, eprof3
        self.stdout.write("Users created / synced.")

        business, _ = BusinessProfile.objects.get_or_create(
            owner=biz1,
            name="Gupta General Store",
            defaults={
                "owner_name": biz1.name,
                "type": "RETAIL",
                "gstin": "21ABCDE1234F1Z5",
                "license_number": "",
                "status": "PENDING",
                "address": "Market Building, Unit - 4, Bhubaneswar",
                "phone": "+919800000001",
            },
        )
        self.stdout.write(f"Business: {business.name}")

        complaints_created = 0
        complaints = []
        citizens = [citizen1, citizen2]
        for idx, sample in enumerate(_COMPLAINT_SAMPLES):
            status = _COMPLAINT_STATUSES_TO_SAMPLE[idx % len(_COMPLAINT_STATUSES_TO_SAMPLE)]
            citizen = citizens[idx % len(citizens)]
            dept = depts[sample["department_idx"]]
            complaint = Complaint.objects.create(
                citizen=citizen,
                title=sample["title"],
                description=sample["description"],
                category=sample["category"],
                priority=sample["priority"],
                department=dept,
                address=sample["address"],
                ward=sample["ward"],
                latitude=sample["latitude"],
                longitude=sample["longitude"],
                status="SUBMITTED",
            )
            complaints.append(complaint)
            complaints_created += 1

            force_complaint_to_status(complaint, status, engineer_u3, officer1)
            ai_conf = {
                "category_prediction": sample["category"],
                "priority_prediction": sample["priority"],
                "department_recommendation": dept,
                "confidence": max(0.62, 0.98 - (0.04 * idx)),
                "summary": f"AI detected a {sample['category']} case in {sample['ward']}.",
                "reason": f"Matched against {sample['department_idx'] + 1} dept rules; high similarity to historical category samples.",
                "provider": settings.AI_PROVIDER or "seed",
            }
            if status in ("CLASSIFIED", "ASSIGNED", "IN_PROGRESS", "ON_HOLD",
                          "RESOLUTION_SUBMITTED", "VERIFICATION_PENDING",
                          "RESOLVED", "REOPENED", "CLOSED"):
                AIAnalysis.objects.create(complaint=complaint, **ai_conf)

            if status in ("ASSIGNED", "IN_PROGRESS", "ON_HOLD",
                           "RESOLUTION_SUBMITTED", "VERIFICATION_PENDING",
                           "RESOLVED", "CLOSED", "REOPENED"):
                complaint.assigned_engineer = engineer_p3
                complaint.save(update_fields=["assigned_engineer"])
                ComplaintAssignment.objects.get_or_create(
                    complaint=complaint,
                    engineer=engineer_p3,
                    defaults={"assigned_by": officer1},
                )

        self.stdout.write(f"Complaints: {complaints_created}")

        apps_created = 0
        app_1_service = services[3]  # Trade License (TPL dept)
        app1 = BusinessApplication.objects.create(
            applicant=biz1,
            business=business,
            service=app_1_service,
            application_number="MUN-2026-1001",
            department=app_1_service.department,
            assigned_officer=officer3.officer_profile,
            status="UNDER_REVIEW",
            data={
                "applicant_name": biz1.name,
                "business_name": business.name,
                "business_type": "RETAIL",
                "business_address": business.address,
                "gstin": business.gstin,
                "owner_contact": business.phone,
            },
        )
        ApplicationStatusHistory.objects.create(
            application=app1,
            old_status="",
            new_status="SUBMITTED",
            changed_by=biz1,
            remarks="Application submitted.",
        )
        ApplicationStatusHistory.objects.create(
            application=app1,
            old_status="SUBMITTED",
            new_status="UNDER_REVIEW",
            changed_by=officer3,
            remarks="Officer review in progress.",
        )
        apps_created += 1

        app_2_service = services[0]  # Birth Certificate
        app2 = BusinessApplication.objects.create(
            applicant=citizen1,
            service=app_2_service,
            application_number="MUN-2026-1002",
            department=app_2_service.department,
            assigned_officer=officer2.officer_profile,
            status="SUBMITTED",
            data={
                "applicant_name": citizen1.name,
                "child_name": "Ankit Patra",
                "date_of_birth": "2026-02-10",
                "place_of_birth": "Capital Hospital, Bhubaneswar",
                "mother_name": "Laxmi Patra",
                "father_name": citizen1.name,
            },
        )
        ApplicationStatusHistory.objects.create(
            application=app2,
            old_status="",
            new_status="SUBMITTED",
            changed_by=citizen1,
            remarks="Application submitted.",
        )
        apps_created += 1

        app_3_service = services[2]  # New Water Connection
        app3 = BusinessApplication.objects.create(
            applicant=citizen2,
            service=app_3_service,
            application_number="MUN-2026-1003",
            department=app_3_service.department,
            status="CLARIFICATION_REQUESTED",
            data={
                "applicant_name": citizen2.name,
                "installation_address": "Plot 12, Khandagiri",
                "ward": "Ward 8",
                "connection_type": "DOMESTIC",
                "property_id": "KHD-12-9001",
            },
        )
        ApplicationStatusHistory.objects.create(
            application=app3,
            old_status="",
            new_status="SUBMITTED",
            changed_by=citizen2,
            remarks="Application submitted.",
        )
        ApplicationStatusHistory.objects.create(
            application=app3,
            old_status="SUBMITTED",
            new_status="CLARIFICATION_REQUESTED",
            changed_by=officer1,
            remarks="Clarification requested: upload signed property deed.",
        )
        apps_created += 1

        self.stdout.write(f"Applications: {apps_created}")
        self.stdout.write("Seeding complete.")


def force_complaint_to_status(complaint, target_status, engineer, officer):
    from apps.complaints.models import ComplaintStatusHistory

    path = build_path_to(complaint.status, target_status)
    for i, status in enumerate(path):
        old = complaint.status
        if status == old:
            continue
        complaint.status = status
        complaint.save(update_fields=["status", "updated_at"])
        actor = officer
        if status in ("RESOLUTION_SUBMITTED",):
            actor = engineer
        ComplaintStatusHistory.objects.create(
            complaint=complaint,
            old_status=old,
            new_status=status,
            changed_by=actor,
            remarks=f"Seeded transition to {status}.",
        )
    return complaint


_PATH_GRAPH = {
    "SUBMITTED": ["AI_PROCESSING", "CLASSIFIED", "REJECTED"],
    "AI_PROCESSING": ["CLASSIFIED", "REJECTED"],
    "CLASSIFIED": ["ASSIGNED", "REJECTED"],
    "ASSIGNED": ["IN_PROGRESS", "ON_HOLD"],
    "IN_PROGRESS": ["ON_HOLD", "RESOLUTION_SUBMITTED"],
    "ON_HOLD": ["IN_PROGRESS", "REJECTED"],
    "RESOLUTION_SUBMITTED": ["VERIFICATION_PENDING"],
    "VERIFICATION_PENDING": ["RESOLVED", "REOPENED"],
    "RESOLVED": ["CLOSED", "REOPENED"],
    "REOPENED": ["ASSIGNED", "IN_PROGRESS", "ON_HOLD"],
    "REJECTED": [],
    "CLOSED": [],
}


def build_path_to(current, target):
    if current == target:
        return [current]
    from collections import deque
    q = deque([(current, [current])])
    visited = {current}
    while q:
        node, path = q.popleft()
        for nxt in _PATH_GRAPH.get(node, []):
            if nxt in visited:
                continue
            new_path = path + [nxt]
            if nxt == target:
                return new_path
            visited.add(nxt)
            q.append((nxt, new_path))
    return [target]
