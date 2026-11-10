import json

from django.test import TestCase, TransactionTestCase, override_settings
from django.core import mail
from django.conf import settings
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken
from apps.accounts.models import User, OfficerProfile, EngineerProfile, CitizenProfile
from apps.departments.models import Department, CategoryDepartmentMapping
from apps.services.models import RequiredDocument, Service
from apps.complaints.models import Complaint, ComplaintStatusHistory, AIAnalysis, ComplaintAssignment, ComplaintResolution
from apps.businesses.models import BusinessProfile
from apps.applications.models import ApplicationDocument, BusinessApplication, ApplicationStatusHistory
from apps.notifications.models import Notification
from apps.audit.models import AuditLog
from apps.chatbot.models import Conversation, Message
from apps.complaints.validators import validate_upload
from apps.ai.constants import CANONICAL_CATEGORIES
from apps.ai.duplicates import find_similar_complaints
from apps.ai.schemas import normalize_category, validate_analysis
from apps.ai.services import get_provider, resolve_department
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.exceptions import ValidationError as DRFValidationError


@override_settings(AI_PROVIDER="mock")
class BaseTestCase(TransactionTestCase):
    def setUp(self):
        self.client = APIClient()
        self.password = "SafePass123!"
        self.drain_dept, _ = Department.objects.get_or_create(
            code="DRAIN", defaults={"name": "Drainage & Sewage", "description": ""}
        )
        self.health_dept, _ = Department.objects.get_or_create(
            code="HEALTH", defaults={"name": "Health & Sanitation", "description": ""}
        )
        self.road_dept, _ = Department.objects.get_or_create(
            code="ROAD", defaults={"name": "Roads & Transport", "description": ""}
        )
        self.tpl_dept, _ = Department.objects.get_or_create(
            code="TPL", defaults={"name": "Town Planning & Licenses", "description": ""}
        )

        self.admin = self._make_user("admin@civic.gov.in", "Civic Administrator", "ADMINISTRATOR")
        self.officer = self._make_user("officer.drain@civic.gov.in", "Pradip Das", "OFFICER")
        self.officer2 = self._make_user("officer.health@civic.gov.in", "Meena Kumari", "OFFICER")
        self.engineer = self._make_user("eng.drain@civic.gov.in", "Suresh Nayak", "ENGINEER")
        self.engineer2 = self._make_user("eng.roads@civic.gov.in", "Anita Mohanty", "ENGINEER")
        self.citizen = self._make_user("citizen.ramesh@example.com", "Ramesh Patra", "CITIZEN")
        self.citizen2 = self._make_user("citizen.sangita@example.com", "Sangita Behera", "CITIZEN")
        self.biz_owner = self._make_user("biz.rajesh@example.com", "Rajesh Gupta", "BUSINESS_OWNER")

        OfficerProfile.objects.get_or_create(user=self.officer, defaults={"department": self.drain_dept, "designation": "AE"})
        OfficerProfile.objects.get_or_create(user=self.officer2, defaults={"department": self.health_dept, "designation": "HI"})
        EngineerProfile.objects.get_or_create(user=self.engineer, defaults={"department": self.drain_dept, "available": True})
        EngineerProfile.objects.get_or_create(user=self.engineer2, defaults={"department": self.road_dept, "available": True})
        CitizenProfile.objects.get_or_create(user=self.citizen, defaults={"ward": "Ward 3"})
        CitizenProfile.objects.get_or_create(user=self.citizen2, defaults={"ward": "Ward 5"})

    def _make_user(self, email, name, role):
        return User.objects.create_user(email=email, name=name, password=self.password, role=role)

    def login(self, user):
        self.client.force_authenticate(user=user)

    def _login_http(self, user):
        client = APIClient()
        resp = client.post("/api/v1/auth/login/", {"email": user.email, "password": self.password}, format="json")
        return client, resp.data

    def _make_complaint(self, citizen=None, status=None, dept=None, assigned_engineer=None):
        c = Complaint.objects.create(
            citizen=citizen or self.citizen,
            title="Drain Blocked",
            description="Main drain blocked with plastic.",
            category="DRAINAGE",
            priority="HIGH",
            department=dept or self.drain_dept,
            ward="Ward 3",
            address="Near park",
            latitude=20.2961,
            longitude=85.8245,
            status="SUBMITTED",
        )
        if assigned_engineer:
            c.assigned_engineer = assigned_engineer
            c.save(update_fields=["assigned_engineer"])
            ComplaintAssignment.objects.get_or_create(
                complaint=c, engineer=assigned_engineer, defaults={"assigned_by": self.officer}
            )
        if status and status != "SUBMITTED":
            ComplaintStatusHistory.objects.create(
                complaint=c, old_status="", new_status="SUBMITTED", changed_by=self.citizen, remarks="Init"
            )
            prev = "SUBMITTED"
            for next_status in _build_path(status):
                if next_status == prev:
                    continue
                actor = self.officer if next_status != "RESOLUTION_SUBMITTED" else (assigned_engineer or self.engineer)
                ComplaintStatusHistory.objects.create(
                    complaint=c, old_status=prev, new_status=next_status, changed_by=actor, remarks="seed"
                )
                c.status = next_status
                c.save(update_fields=["status", "updated_at"])
                prev = next_status
        return c


class AuthFlowTests(BaseTestCase):
    def test_api_schema_and_docs_are_available(self):
        client = APIClient()
        schema = client.get("/api/schema/")
        self.assertEqual(schema.status_code, 200, msg=schema.data)
        self.assertIn("/api/v1/auth/login/", schema.data["paths"])
        docs = client.get("/api/docs/")
        self.assertEqual(docs.status_code, 200)

    def test_register_returns_201_user_shape_no_tokens(self):
        client = APIClient()
        payload = {"name": "New Citizen", "email": "new@citizen.com", "password": "NewPass123!"}
        resp = client.post("/api/v1/auth/register/", payload, format="json")
        self.assertEqual(resp.status_code, 201)
        self.assertTrue(resp.data["success"])
        data = resp.data["data"]
        self.assertIn("user", data)
        user = data["user"]
        self.assertEqual(user["name"], "New Citizen")
        self.assertEqual(user["email"], "new@citizen.com")
        self.assertEqual(user["role"], "CITIZEN")
        self.assertIn("id", user)
        self.assertNotIn("access", data)
        self.assertNotIn("refresh", data)
        self.assertTrue(AuditLog.objects.filter(
            action="USER_CREATED", entity_id=str(user["id"]),
        ).exists())

    def test_register_admin_only_can_create_officer(self):
        client = APIClient()
        client.force_authenticate(user=self.citizen)
        resp = client.post(
            "/api/v1/auth/register/",
            {"name": "Bad Officer", "email": "spy@x.com", "password": "OfficerPass123!", "role": "OFFICER"},
            format="json",
        )
        self.assertEqual(resp.status_code, 403)
        client2 = APIClient()
        client2.force_authenticate(user=self.admin)
        resp2 = client2.post(
            "/api/v1/auth/register/",
            {"name": "Good Officer", "email": "officer.new@civic.gov.in", "password": "OfficerPass123!", "role": "OFFICER", "department_id": self.tpl_dept.id},
            format="json",
        )
        self.assertEqual(resp2.status_code, 201)
        self.assertEqual(resp2.data["data"]["user"]["role"], "OFFICER")

    def test_admin_can_attach_department_profiles_for_staff_members(self):
        client = APIClient()
        client.force_authenticate(user=self.admin)

        officer_resp = client.post(
            "/api/v1/auth/register/",
            {
                "name": "New Planning Officer",
                "email": "officer.new@civic.gov.in",
                "password": "OfficerPass123!",
                "role": "OFFICER",
                "department_id": self.tpl_dept.id,
                "designation": "Assistant Engineer",
            },
            format="json",
        )
        self.assertEqual(officer_resp.status_code, 201, officer_resp.data)
        self.assertTrue(OfficerProfile.objects.filter(user__email="officer.new@civic.gov.in", department=self.tpl_dept).exists())

        road_service = Service.objects.create(
            name="Road Maintenance",
            code="TEST-ROAD-MAINTENANCE",
            department=self.road_dept,
        )
        engineer_resp = client.post(
            "/api/v1/auth/register/",
            {
                "name": "New Road Engineer",
                "email": "engineer.new@civic.gov.in",
                "password": "EngineerPass123!",
                "role": "ENGINEER",
                "department_id": self.road_dept.id,
                "specialization": "Road maintenance",
                "service_ids": [road_service.id],
            },
            format="json",
        )
        self.assertEqual(engineer_resp.status_code, 201, engineer_resp.data)
        profile = EngineerProfile.objects.get(user__email="engineer.new@civic.gov.in", department=self.road_dept)
        self.assertEqual(list(profile.services.values_list("id", flat=True)), [road_service.id])

    def test_admin_cannot_create_second_available_officer_in_department(self):
        client = APIClient()
        client.force_authenticate(user=self.admin)
        response = client.post(
            "/api/v1/auth/register/",
            {
                "name": "Duplicate Department Officer",
                "email": "officer.duplicate@civic.gov.in",
                "password": "OfficerPass123!",
                "role": "OFFICER",
                "department_id": self.drain_dept.id,
            },
            format="json",
        )
        self.assertEqual(response.status_code, 400, msg=response.data)
        self.assertFalse(User.objects.filter(email="officer.duplicate@civic.gov.in").exists())

    def test_login_returns_access_refresh_and_user_shape(self):
        client = APIClient()
        resp = client.post(
            "/api/v1/auth/login/",
            {"email": self.citizen.email, "password": self.password},
            format="json",
        )
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.data["success"])
        data = resp.data["data"]
        self.assertIn("access", data)
        self.assertIn("refresh", data)
        self.assertIn("user", data)
        user = data["user"]
        self.assertEqual(user["id"], self.citizen.id)
        self.assertEqual(user["name"], self.citizen.name)
        self.assertEqual(user["role"], "CITIZEN")
        self.assertNotIn("email", user)
        self.assertTrue(AuditLog.objects.filter(
            action="LOGIN", entity_id=str(self.citizen.id),
        ).exists())

    def test_auth_me_and_patch_users_me(self):
        self.login(self.citizen)
        me_resp = self.client.get("/api/v1/auth/me/")
        self.assertEqual(me_resp.status_code, 200)
        self.assertEqual(me_resp.data["data"]["email"], self.citizen.email)
        patch = self.client.patch(
            "/api/v1/users/me/",
            {
                "name": "Ramesh Kumar Patra",
                "email": self.citizen.email,
                "phone": "+919800000000",
                "address": "12 Civic Road",
                "city": "Bhubaneswar",
                "pincode": "751001",
            },
            format="json",
        )
        self.assertEqual(patch.status_code, 200)
        self.citizen.refresh_from_db()
        self.assertEqual(self.citizen.name, "Ramesh Kumar Patra")
        self.assertEqual(self.citizen.citizen_profile.address, "12 Civic Road")
        self.assertEqual(me_resp.data["data"]["address"], "")
        changed_email = self.client.patch(
            "/api/v1/users/me/",
            {"email": "other@example.com"},
            format="json",
        )
        self.assertEqual(changed_email.status_code, 400)
        patch2 = self.client.patch("/api/v1/users/me/", {"role": "ADMINISTRATOR"}, format="json")
        self.assertEqual(patch2.status_code, 400)
        self.citizen.refresh_from_db()
        self.assertEqual(self.citizen.role, "CITIZEN")

    def test_token_refresh_and_logout_blacklist(self):
        client, login = self._login_http(self.citizen)
        refresh = login["data"]["refresh"]
        ref_resp = client.post("/api/v1/auth/token/refresh/", {"refresh": refresh}, format="json")
        self.assertEqual(ref_resp.status_code, 200)
        self.assertIn("access", ref_resp.data["data"])
        new_refresh = ref_resp.data["data"]["refresh"]
        logout_resp = client.post("/api/v1/auth/logout/", {"refresh": new_refresh}, format="json")
        self.assertIn(logout_resp.status_code, (200, 204))
        ref_resp2 = client.post("/api/v1/auth/token/refresh/", {"refresh": new_refresh}, format="json")
        self.assertEqual(ref_resp2.status_code, 401)

    def test_password_reset_email_token_changes_password_once(self):
        client = APIClient()
        with self.settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend"):
            mail.outbox.clear()
            started = client.post(
                "/api/v1/auth/password-reset/",
                {"email": self.citizen.email},
                format="json",
            )
            self.assertEqual(started.status_code, 200, msg=started.data)
            self.assertEqual(len(mail.outbox), 1)
            reset_token = mail.outbox[0].body.rsplit(" ", 1)[-1]
            changed = client.post(
                "/api/v1/auth/password-reset/confirm/",
                {"reset_token": reset_token, "new_password": "ChangedPass456!"},
                format="json",
            )
            self.assertEqual(changed.status_code, 200, msg=changed.data)
            reused = client.post(
                "/api/v1/auth/password-reset/confirm/",
                {"reset_token": reset_token, "new_password": "ChangedPass789!"},
                format="json",
            )
            self.assertEqual(reused.status_code, 400)
        self.citizen.refresh_from_db()
        self.assertTrue(self.citizen.check_password("ChangedPass456!"))

    def test_unauthenticated_endpoints_return_401(self):
        client = APIClient()
        for url in [
            "/api/v1/auth/me/",
            "/api/v1/complaints/",
            "/api/v1/applications/",
            "/api/v1/notifications/",
            "/api/v1/departments/",
            "/api/v1/analytics/overview/",
        ]:
            resp = client.get(url)
            self.assertIn(resp.status_code, (401, 403), msg=f"{url} returned {resp.status_code}")


class ChatbotTests(BaseTestCase):
    def test_chatbot_returns_placeholder_and_persists_conversation(self):
        self.login(self.citizen)
        response = self.client.post(
            "/api/v1/chatbot/chat/",
            {"message": "How do I get a permit?", "language": "en", "context": "CITIZEN"},
            format="json",
        )
        self.assertEqual(response.status_code, 200, msg=response.data)
        self.assertIn("not configured", response.data["data"]["message"].lower())
        self.assertEqual(Conversation.objects.filter(user=self.citizen).count(), 1)
        self.assertEqual(Message.objects.filter(conversation__user=self.citizen).count(), 2)


class ComplaintLifecycleTests(BaseTestCase):
    def test_categories_are_served_by_backend(self):
        self.login(self.citizen)
        response = self.client.get("/api/v1/complaints/categories/")
        self.assertEqual(response.status_code, 200, msg=response.data)
        self.assertIn("DRAINAGE", response.data["data"])
        self.assertIn("WATER_SUPPLY", response.data["data"])

    def test_upload_validator_rejects_executables_and_fake_images(self):
        executable = SimpleUploadedFile("payload.exe", b"MZ", content_type="application/octet-stream")
        with self.assertRaises(DRFValidationError):
            validate_upload(executable)

        fake_image = SimpleUploadedFile("photo.png", b"not an image", content_type="image/png")
        with self.assertRaises(DRFValidationError):
            validate_upload(fake_image)

    def test_create_complaint_runs_auto_ai_and_awaits_officer_review(self):
        self.login(self.citizen)

        payload = {
            "title": "Water clogging",
            "description": "Water stagnates after rains.",
            "latitude": "20.2961",
            "longitude": "85.8245",
            "address": "Ward 3",
            "ward": "Ward 3",
        }
        resp = self.client.post("/api/v1/complaints/", payload, format="json")
        self.assertEqual(resp.status_code, 201, msg=resp.data)
        self.assertTrue(resp.data["success"])
        c = Complaint.objects.get(id=resp.data["data"]["id"])
        self.assertEqual(c.complaint_number, f"CIV-{c.created_at.year}-{c.id:08d}")
        self.assertEqual(c.citizen, self.citizen)
        self.assertEqual(c.ward, "Ward 3")
        # AI triage runs automatically and parks the complaint for officer review.
        self.assertEqual(c.status, "AI_PROCESSING")
        self.assertTrue(
            ComplaintStatusHistory.objects.filter(complaint=c, new_status="SUBMITTED").exists()
        )
        self.assertTrue(
            ComplaintStatusHistory.objects.filter(complaint=c, new_status="AI_PROCESSING").exists()
        )
        self.assertFalse(
            ComplaintStatusHistory.objects.filter(complaint=c, new_status="CLASSIFIED").exists()
        )
        analysis = c.ai_analyses.first()
        self.assertIsNotNone(analysis)
        self.assertIn(analysis.category_prediction, CANONICAL_CATEGORIES)
        # No category->department mapping exists yet, so a human must route it.
        self.assertTrue(analysis.requires_manual_review)
        self.assertTrue(Notification.objects.filter(
            recipient=self.citizen, related_object_id=str(c.id),
        ).exists())
        self.assertTrue(AuditLog.objects.filter(
            action="COMPLAINT_CREATED", entity_id=str(c.id),
        ).exists())
        self.assertTrue(AuditLog.objects.filter(
            action="AI_ANALYSIS_COMPLETED", entity_id=str(c.id),
        ).exists())

    def test_valid_status_transitions(self):
        complaint = self._make_complaint(status="CLASSIFIED", assigned_engineer=self.engineer)
        self.login(self.officer)
        resp = self.client.patch(
            f"/api/v1/complaints/{complaint.id}/status/",
            {"status": "ASSIGNED", "remarks": "Assigning field team."},
            format="json",
        )
        self.assertEqual(resp.status_code, 200, msg=resp.data)
        complaint.refresh_from_db()
        self.assertEqual(complaint.status, "ASSIGNED")

        resp2 = self.client.patch(
            f"/api/v1/complaints/{complaint.id}/status/",
            {"status": "IN_PROGRESS", "remarks": "Site work started."},
            format="json",
        )
        self.assertEqual(resp2.status_code, 200, msg=resp2.data)

    def test_officer_manually_classifies_unassigned_complaint(self):
        self.login(self.citizen)
        create = self.client.post(
            "/api/v1/complaints/",
            {
                "title": "Blocked drain",
                "description": "The street drain is blocked.",
                "latitude": "20.2961",
                "longitude": "85.8245",
                "address": "Ward 3",
            },
            format="json",
        )
        complaint_id = create.data["data"]["id"]
        self.login(self.officer)
        classified = self.client.patch(
            f"/api/v1/complaints/{complaint_id}/status/",
            {
                "status": "CLASSIFIED",
                "category": "DRAINAGE",
                "priority": "HIGH",
                "department_id": self.drain_dept.id,
            },
            format="json",
        )
        self.assertEqual(classified.status_code, 200, msg=classified.data)
        complaint = Complaint.objects.get(pk=complaint_id)
        self.assertEqual(complaint.status, "CLASSIFIED")
        self.assertEqual(complaint.category, "DRAINAGE")
        self.assertEqual(complaint.department_id, self.drain_dept.id)


    def test_invalid_transition_returns_422_business_error(self):
        complaint = self._make_complaint(status="SUBMITTED")
        self.login(self.officer)
        resp = self.client.patch(
            f"/api/v1/complaints/{complaint.id}/status/",
            {"status": "RESOLVED"},
            format="json",
        )
        self.assertEqual(resp.status_code, 422, msg=resp.data)
        self.assertFalse(resp.data["success"])
        self.assertEqual(resp.data["error"]["code"], "BUSINESS_ERROR")

    def test_assign_and_reassign_engineer(self):
        complaint = self._make_complaint(status="CLASSIFIED")
        self.login(self.officer)
        resp = self.client.post(
            f"/api/v1/complaints/{complaint.id}/assign/",
            {"engineer_id": self.engineer.id},
            format="json",
        )
        self.assertEqual(resp.status_code, 200, msg=resp.data)
        complaint.refresh_from_db()
        self.assertEqual(complaint.assigned_engineer, self.engineer)
        self.assertEqual(complaint.status, "ASSIGNED")

        replacement = self._make_user("eng.drain.replacement@civic.gov.in", "Replacement engineer", "ENGINEER")
        EngineerProfile.objects.create(user=replacement, department=self.drain_dept, available=True)
        resp2 = self.client.post(
            f"/api/v1/complaints/{complaint.id}/reassign/",
            {"engineer_id": replacement.id},
            format="json",
        )
        self.assertEqual(resp2.status_code, 200, msg=resp2.data)
        complaint.refresh_from_db()
        self.assertEqual(complaint.assigned_engineer, replacement)

    def test_unassign_records_history_and_reopens_complaint(self):
        complaint = self._make_complaint(status="CLASSIFIED")
        self.login(self.officer)
        self.client.post(
            f"/api/v1/complaints/{complaint.id}/assign/",
            {"engineer_id": self.engineer.id},
            format="json",
        )
        response = self.client.post(
            f"/api/v1/complaints/{complaint.id}/unassign/",
            {"remarks": "Work reassigned to another team."},
            format="json",
        )
        self.assertEqual(response.status_code, 200, msg=response.data)
        complaint.refresh_from_db()
        assignment = ComplaintAssignment.objects.filter(complaint=complaint).latest("assigned_time")
        self.assertIsNone(complaint.assigned_engineer)
        self.assertEqual(complaint.status, "REOPENED")
        self.assertIsNotNone(assignment.unassigned_at)

    def test_resolution_and_verification_flow(self):
        complaint = self._make_complaint(status="IN_PROGRESS", assigned_engineer=self.engineer)
        self.login(self.engineer)
        resp = self.client.post(
            f"/api/v1/complaints/{complaint.id}/resolution/",
            {"description": "Drain cleared with suction vehicle.", "evidence": None},
            format="json",
        )
        self.assertEqual(resp.status_code, 200, msg=resp.data)
        complaint.refresh_from_db()
        self.assertIn(complaint.status, ("RESOLUTION_SUBMITTED", "VERIFICATION_PENDING"))

        self.login(self.officer)
        resp2 = self.client.post(
            f"/api/v1/complaints/{complaint.id}/verify-resolution/",
            {"approved": True, "remarks": "Verified."},
            format="json",
        )
        self.assertEqual(resp2.status_code, 200, msg=resp2.data)
        complaint.refresh_from_db()
        self.assertEqual(complaint.status, "RESOLVED")

    def test_resolution_rejected_flows_back_to_in_progress(self):
        complaint = self._make_complaint(status="IN_PROGRESS", assigned_engineer=self.engineer)
        ComplaintResolution.objects.create(
            complaint=complaint,
            description="Resolution awaiting officer verification.",
            submitted_by=self.engineer,
        )
        ComplaintStatusHistory.objects.filter(complaint=complaint, new_status="IN_PROGRESS").delete()
        complaint.status = "VERIFICATION_PENDING"
        complaint.save(update_fields=["status", "updated_at"])
        ComplaintStatusHistory.objects.create(
            complaint=complaint, old_status="RESOLUTION_SUBMITTED", new_status="VERIFICATION_PENDING",
            changed_by=self.engineer, remarks="seeded",
        )
        self.login(self.officer)
        resp = self.client.post(
            f"/api/v1/complaints/{complaint.id}/verify-resolution/",
            {"approved": False, "remarks": "Work not satisfactory; redo."},
            format="json",
        )
        self.assertEqual(resp.status_code, 200, msg=resp.data)
        complaint.refresh_from_db()
        self.assertEqual(complaint.status, "REOPENED")

    def test_feedback_only_after_resolved(self):
        complaint = self._make_complaint(status="RESOLVED", assigned_engineer=self.engineer)
        self.login(self.citizen)
        resp = self.client.post(
            f"/api/v1/complaints/{complaint.id}/feedback/",
            {"rating": 5, "comment": "Quick and thorough."},
            format="json",
        )
        self.assertEqual(resp.status_code, 200, msg=resp.data)

    def test_ai_analysis_persists_recommendation_without_changing_workflow(self):
        complaint = self._make_complaint(status="CLASSIFIED", assigned_engineer=self.engineer)
        self.login(self.officer)
        analyze = self.client.post(f"/api/v1/complaints/{complaint.id}/ai/analyze/", format="json")
        self.assertEqual(analyze.status_code, 200, msg=analyze.data)
        self.assertTrue(analyze.data["success"])
        data = analyze.data["data"]
        self.assertTrue(data["configured"])
        self.assertIn(data["category"], CANONICAL_CATEGORIES)
        self.assertTrue(AIAnalysis.objects.filter(complaint=complaint).exists())
        # On-demand analysis must never move the complaint by itself.
        complaint.refresh_from_db()
        self.assertEqual(complaint.status, "CLASSIFIED")

    def test_officer_can_review_stored_ai_recommendation(self):
        complaint = self._make_complaint(status="CLASSIFIED", assigned_engineer=self.engineer)
        analysis = AIAnalysis.objects.create(
            complaint=complaint,
            provider="future-provider",
            category_prediction=None,
            priority_prediction=None,
            confidence=None,
            summary="",
            reason="",
        )
        self.login(self.officer)
        review = self.client.patch(
            f"/api/v1/complaints/{complaint.id}/ai-review/",
            {"category": "ROADS", "priority": "CRITICAL"},
            format="json",
        )
        self.assertEqual(review.status_code, 200, msg=review.data)
        latest = AIAnalysis.objects.get(pk=analysis.pk)
        self.assertEqual(latest.human_category, "ROADS")
        self.assertEqual(latest.human_priority, "CRITICAL")
        self.assertTrue(latest.is_overridden)
        self.assertIsNotNone(latest.reviewed_at)

        get_ai = self.client.get(f"/api/v1/complaints/{complaint.id}/ai/")
        self.assertEqual(get_ai.status_code, 200)
        self.assertEqual(get_ai.data["data"]["category"], "ROADS")


class ComplaintAIEngineTests(BaseTestCase):
    """Coverage for the AI triage engine: validation, providers, duplicates, routing."""

    def test_category_normalisation_folds_legacy_values(self):
        self.assertEqual(normalize_category("ROADS"), "ROAD")
        self.assertEqual(normalize_category("water supply"), "WATER_SUPPLY")
        self.assertEqual(normalize_category("street_light"), "STREETLIGHT")
        self.assertIsNone(normalize_category("nonsense-value"))

    def test_validate_analysis_clamps_confidence_and_flags_low_confidence(self):
        out = validate_analysis(
            {"category": "ROADS", "priority": "urgent", "summary": "", "confidence": 88}
        )
        self.assertEqual(out["category"], "ROAD")
        self.assertEqual(out["priority"], "MEDIUM")  # invalid value -> safe default
        self.assertTrue(out["requires_manual_review"])  # empty summary + invalid priority
        self.assertAlmostEqual(out["confidence"], 0.88, places=2)

    def test_mock_provider_classifies_drainage_complaint(self):
        complaint = self._make_complaint()
        result = get_provider().analyze_complaint(complaint)
        self.assertTrue(result["configured"])
        self.assertEqual(result["provider"], "mock")
        self.assertEqual(result["category"], "DRAINAGE")

    def test_duplicate_detection_flags_near_identical_complaint(self):
        first = self._make_complaint()
        second = Complaint.objects.create(
            citizen=self.citizen2,
            title="Drain blocked",
            description="Main drain blocked with plastic.",
            latitude=20.2962,
            longitude=85.8246,
            status="SUBMITTED",
        )
        matched_ids = {m["id"] for m in find_similar_complaints(second)}
        self.assertIn(first.id, matched_ids)

    def test_department_mapping_drives_routing(self):
        CategoryDepartmentMapping.objects.create(
            category="DRAINAGE", department=self.drain_dept
        )
        self.assertEqual(resolve_department("DRAINAGE"), self.drain_dept)
        self.assertIsNone(resolve_department("GARBAGE"))

    def test_admin_configures_mapping_and_officer_accepts_ai_recommendation(self):
        self.login(self.citizen)
        forbidden = self.client.post(
            "/api/v1/category-mappings/",
            {"category": "DRAINAGE", "department": self.drain_dept.id},
            format="json",
        )
        self.assertEqual(forbidden.status_code, 403)

        self.login(self.admin)
        created = self.client.post(
            "/api/v1/category-mappings/",
            {"category": "DRAINAGE", "department": self.drain_dept.id},
            format="json",
        )
        self.assertEqual(created.status_code, 201, msg=created.data)
        self.assertEqual(created.data["data"]["category"], "DRAINAGE")

        complaint = self._make_complaint()
        self.login(self.officer)
        analyze = self.client.post(
            f"/api/v1/complaints/{complaint.id}/ai/analyze/", format="json"
        )
        self.assertEqual(analyze.status_code, 200, msg=analyze.data)
        self.assertFalse(analyze.data["data"]["requires_manual_review"])

        accept = self.client.post(
            f"/api/v1/complaints/{complaint.id}/ai/accept/", format="json"
        )
        self.assertEqual(accept.status_code, 200, msg=accept.data)
        complaint.refresh_from_db()
        self.assertEqual(complaint.status, "CLASSIFIED")
        self.assertEqual(complaint.category, "DRAINAGE")
        self.assertEqual(complaint.department_id, self.drain_dept.id)
        self.assertTrue(AuditLog.objects.filter(
            action="AI_RECOMMENDATION_ACCEPTED", entity_id=str(complaint.id),
        ).exists())


class ApplicationWorkflowTests(BaseTestCase):
    def setUp(self):
        super().setUp()
        self.biz, _ = BusinessProfile.objects.get_or_create(
            owner=self.biz_owner,
            name="Gupta General Store",
            defaults={
                "owner_name": self.biz_owner.name,
                "type": "RETAIL",
                "gstin": "21ABCDE1234F1Z5",
                "address": "Market Building",
                "phone": "+919800000000",
                "status": "PENDING",
            },
        )
        self.svc, _ = Service.objects.get_or_create(
            code="TRADE-LIC",
            defaults={
                "name": "Trade License",
                "department": self.tpl_dept,
                "processing_time_days": 14,
                "fee": 2500.00,
                "requirements": [
                    {"key": "applicant_name", "label": "Applicant", "type": "text", "required": True},
                    {"key": "business_name", "label": "Business Name", "type": "text", "required": True},
                    {"key": "address_proof", "label": "Address Proof", "type": "file", "required": True},
                ],
            },
        )
        self.birth_svc, _ = Service.objects.get_or_create(
            code="BIRTH-CERT",
            defaults={
                "name": "Birth Certificate",
                "department": self.health_dept,
                "processing_time_days": 7,
                "fee": 50.00,
                "requirements": [
                    {"key": "applicant_name", "label": "Applicant", "type": "text", "required": True},
                    {"key": "child_name", "label": "Child", "type": "text", "required": True},
                ],
            },
        )

    def test_draft_submission_requires_all_mandatory_fields(self):
        self.login(self.citizen)
        created = self.client.post(
            "/api/v1/applications/",
            {"service_id": self.birth_svc.id, "draft": True, "data": {"applicant_name": self.citizen.name}},
            format="json",
        )
        self.assertEqual(created.status_code, 201, msg=created.data)
        application_id = created.data["data"]["id"]
        self.assertEqual(created.data["data"]["status"], "DRAFT")
        submitted = self.client.post(f"/api/v1/applications/{application_id}/submit/", format="json")
        self.assertEqual(submitted.status_code, 400, msg=submitted.data)
        self.assertIn("child_name", submitted.data["error"]["details"]["required_fields"])
        self.assertEqual(BusinessApplication.objects.get(pk=application_id).status, "DRAFT")

    def test_complete_draft_can_be_submitted(self):
        self.login(self.citizen)
        created = self.client.post(
            "/api/v1/applications/",
            {
                "service_id": self.birth_svc.id,
                "draft": True,
                "data": {"applicant_name": self.citizen.name, "child_name": "Ankit Patra"},
            },
            format="json",
        )
        application_id = created.data["data"]["id"]
        submitted = self.client.post(f"/api/v1/applications/{application_id}/submit/", format="json")
        self.assertEqual(submitted.status_code, 200, msg=submitted.data)
        self.assertEqual(submitted.data["data"]["status"], "SUBMITTED")
        self.assertTrue(ApplicationStatusHistory.objects.filter(
            application_id=application_id, new_status="SUBMITTED",
        ).exists())

    def test_applicant_can_update_and_resubmit_clarification(self):
        self.login(self.citizen)
        created = self.client.post(
            "/api/v1/applications/",
            {
                "service_id": self.birth_svc.id,
                "data": {"applicant_name": self.citizen.name, "child_name": "Baby"},
            },
            format="json",
        )
        application_id = created.data["data"]["id"]
        self.login(self.officer2)
        clarification = self.client.post(
            f"/api/v1/applications/{application_id}/clarification/",
            {"message": "Correct the child's name."},
            format="json",
        )
        self.assertEqual(clarification.status_code, 200, msg=clarification.data)

        self.login(self.citizen)
        updated = self.client.patch(
            f"/api/v1/applications/{application_id}/",
            {"data": {"child_name": "Corrected Name"}},
            format="json",
        )
        self.assertEqual(updated.status_code, 200, msg=updated.data)
        submitted = self.client.post(f"/api/v1/applications/{application_id}/submit/", format="json")
        self.assertEqual(submitted.status_code, 200, msg=submitted.data)
        self.assertEqual(submitted.data["data"]["status"], "UNDER_REVIEW")
        self.assertEqual(submitted.data["data"]["data"]["child_name"], "Corrected Name")

    def test_required_document_upload_and_officer_verification(self):
        self.login(self.biz_owner)
        created = self.client.post(
            "/api/v1/applications/",
            {
                "service_id": self.svc.id,
                "draft": True,
                "business_id": self.biz.id,
                "data": {"applicant_name": self.biz_owner.name, "business_name": self.biz.name},
            },
            format="json",
        )
        application_id = created.data["data"]["id"]
        upload = self.client.post(
            f"/api/v1/applications/{application_id}/documents/",
            {
                "key": "address_proof",
                "label": "Address proof",
                "file": SimpleUploadedFile("proof.pdf", b"%PDF-1.4\n%%EOF", content_type="application/pdf"),
            },
            format="multipart",
        )
        self.assertEqual(upload.status_code, 201, msg=upload.data)
        document_id = upload.data["data"]["id"]
        download = self.client.get(
            f"/api/v1/applications/{application_id}/documents/{document_id}/download/"
        )
        self.assertEqual(download.status_code, 200)
        self.assertIn("attachment", download["Content-Disposition"])
        self.login(self.biz_owner)
        submitted = self.client.post(f"/api/v1/applications/{application_id}/submit/", format="json")
        self.assertEqual(submitted.status_code, 200, msg=submitted.data)
        self.login(self.citizen)
        forbidden_download = self.client.get(
            f"/api/v1/applications/{application_id}/documents/{document_id}/download/"
        )
        self.assertEqual(forbidden_download.status_code, 404)

        self.login(self.admin)
        self.client.patch(
            f"/api/v1/applications/{application_id}/status/",
            {"status": "UNDER_REVIEW"},
            format="json",
        )
        verified = self.client.patch(
            f"/api/v1/applications/{application_id}/documents/{document_id}/verify/",
            {"status": "VERIFIED", "remarks": "Document is legible."},
            format="json",
        )
        self.assertEqual(verified.status_code, 200, msg=verified.data)
        document = ApplicationDocument.objects.get(pk=document_id)
        self.assertEqual(document.status, "VERIFIED")
        self.assertEqual(document.verified_by, self.admin)
        self.assertEqual(BusinessApplication.objects.get(pk=application_id).status, "DOCUMENT_VERIFICATION")

    def test_multipart_draft_saves_file_then_submits(self):
        self.login(self.biz_owner)
        response = self.client.post(
            "/api/v1/applications/",
            {
                "service_id": str(self.svc.id),
                "business_id": str(self.biz.id),
                "draft": "true",
                "data": json.dumps({"applicant_name": self.biz_owner.name, "business_name": self.biz.name}),
                "document:address_proof": SimpleUploadedFile(
                    "proof.pdf", b"%PDF-1.4\n%%EOF", content_type="application/pdf",
                ),
            },
            format="multipart",
        )
        self.assertEqual(response.status_code, 201, msg=response.data)
        application_id = response.data["data"]["id"]
        self.assertEqual(response.data["data"]["status"], "DRAFT")
        self.assertTrue(ApplicationDocument.objects.filter(
            application_id=application_id, key="address_proof",
        ).exists())
        submitted = self.client.post(f"/api/v1/applications/{application_id}/submit/", format="json")
        self.assertEqual(submitted.status_code, 200, msg=submitted.data)
        self.assertEqual(submitted.data["data"]["status"], "SUBMITTED")

    def test_create_application_as_citizen(self):
        self.login(self.citizen)
        payload = {
            "service_id": self.birth_svc.id,
            "data": {
                "applicant_name": self.citizen.name,
                "child_name": "Ankit Patra",
            },
        }
        resp = self.client.post("/api/v1/applications/", payload, format="json")
        self.assertEqual(resp.status_code, 201, msg=resp.data)
        app = BusinessApplication.objects.get(id=resp.data["data"]["id"])
        self.assertEqual(app.status, "SUBMITTED")
        self.assertTrue(app.application_number.startswith("MUN-"))
        self.assertEqual(app.applicant, self.citizen)
        self.assertEqual(app.department, self.health_dept)
        self.assertEqual(app.service, self.birth_svc)

    def test_create_application_as_business_owner(self):
        self.login(self.biz_owner)
        payload = {
            "service_id": self.svc.id,
            "draft": True,
            "business_id": self.biz.id,
            "data": {
                "applicant_name": self.biz_owner.name,
                "business_name": self.biz.name,
            },
        }
        resp = self.client.post("/api/v1/applications/", payload, format="json")
        self.assertEqual(resp.status_code, 201, msg=resp.data)
        app = BusinessApplication.objects.get(id=resp.data["data"]["id"])
        self.assertEqual(app.business, self.biz)
        self.assertEqual(app.status, "DRAFT")

    def test_direct_submission_cannot_skip_required_documents(self):
        self.login(self.biz_owner)
        response = self.client.post(
            "/api/v1/applications/",
            {
                "service_id": self.svc.id,
                "business_id": self.biz.id,
                "data": {"applicant_name": self.biz_owner.name, "business_name": self.biz.name},
            },
            format="json",
        )
        self.assertEqual(response.status_code, 400, msg=response.data)
        self.assertIn("address_proof", response.data["error"]["details"]["required_fields"])

    def test_field_verification_is_service_configured_and_tracked(self):
        self.login(self.citizen)
        response = self.client.post(
            "/api/v1/applications/",
            {
                "service_id": self.birth_svc.id,
                "data": {"applicant_name": self.citizen.name, "child_name": "Field Visit"},
            },
            format="json",
        )
        application_id = response.data["data"]["id"]

        self.login(self.officer2)
        disabled = self.client.patch(
            f"/api/v1/applications/{application_id}/status/",
            {"status": "FIELD_VERIFICATION"},
            format="json",
        )
        self.assertEqual(disabled.status_code, 400, msg=disabled.data)

        self.birth_svc.field_verification_required = True
        self.birth_svc.save(update_fields=["field_verification_required"])
        started = self.client.post(f"/api/v1/applications/{application_id}/review/", {}, format="json")
        self.assertEqual(started.status_code, 200, msg=started.data)
        field_visit = self.client.patch(
            f"/api/v1/applications/{application_id}/status/",
            {"status": "FIELD_VERIFICATION", "remarks": "Site visit required."},
            format="json",
        )
        self.assertEqual(field_visit.status_code, 200, msg=field_visit.data)
        completed = self.client.patch(
            f"/api/v1/applications/{application_id}/status/",
            {"status": "UNDER_REVIEW", "remarks": "Site visit completed."},
            format="json",
        )
        self.assertEqual(completed.status_code, 200, msg=completed.data)
        self.assertEqual(
            list(BusinessApplication.objects.get(pk=application_id).history.values_list("new_status", flat=True)),
            ["SUBMITTED", "UNDER_REVIEW", "FIELD_VERIFICATION", "UNDER_REVIEW"],
        )

    def test_officer_assigns_only_service_qualified_department_engineers(self):
        routing_service = Service.objects.create(
            name="Qualified Routing Service",
            code="QUALIFIED-ROUTING",
            department=self.tpl_dept,
        )
        officer_user = self._make_user("tpl.assigning.officer@civic.gov.in", "TPL Assigning Officer", "OFFICER")
        officer = OfficerProfile.objects.create(user=officer_user, department=self.tpl_dept)
        qualified_user = self._make_user("tpl.qualified.engineer@civic.gov.in", "Qualified Engineer", "ENGINEER")
        qualified = EngineerProfile.objects.create(user=qualified_user, department=self.tpl_dept, specialization="Permits")
        qualified.services.add(routing_service)
        unqualified_user = self._make_user("tpl.unqualified.engineer@civic.gov.in", "Unqualified Engineer", "ENGINEER")
        unqualified = EngineerProfile.objects.create(user=unqualified_user, department=self.tpl_dept, specialization="Other")
        application = BusinessApplication.objects.create(
            applicant=self.citizen,
            service=routing_service,
            application_number="MUN-2026-QUALIFIED",
            department=self.tpl_dept,
            assigned_officer=officer,
            status="UNDER_REVIEW",
        )

        self.login(officer_user)
        eligible = self.client.get(f"/api/v1/applications/{application.id}/eligible-engineers/")
        self.assertEqual(eligible.status_code, 200, msg=eligible.data)
        self.assertEqual([item["id"] for item in eligible.data["data"]], [qualified.id])

        rejected = self.client.post(
            f"/api/v1/applications/{application.id}/assign-engineer/",
            {"engineer_profile_id": unqualified.id},
            format="json",
        )
        self.assertEqual(rejected.status_code, 400, msg=rejected.data)

        assigned = self.client.post(
            f"/api/v1/applications/{application.id}/assign-engineer/",
            {"engineer_profile_id": qualified.id},
            format="json",
        )
        self.assertEqual(assigned.status_code, 200, msg=assigned.data)
        application.refresh_from_db()
        self.assertEqual(application.assigned_engineer, qualified)

    def test_submission_auto_assigns_least_loaded_department_officer(self):
        routing_service = Service.objects.create(
            name="Routing Test Service",
            code="ROUTING-ASSIGN",
            department=self.tpl_dept,
        )
        officer_user = self._make_user("tpl.primary.officer@civic.gov.in", "TPL Primary Officer", "OFFICER")
        officer = OfficerProfile.objects.create(user=officer_user, department=self.tpl_dept)

        self.login(self.biz_owner)
        response = self.client.post(
            "/api/v1/applications/",
            {"service_id": routing_service.id, "data": {}},
            format="json",
        )
        self.assertEqual(response.status_code, 201, msg=response.data)
        application = BusinessApplication.objects.get(pk=response.data["data"]["id"])
        self.assertEqual(application.assigned_officer, officer)

    def test_unassigned_application_remains_in_department_officer_queue(self):
        routing_service = Service.objects.create(
            name="Unassigned Routing Test Service",
            code="ROUTING-UNASSIGNED",
            department=self.tpl_dept,
        )
        unavailable_user = self._make_user("tpl.officer.unavailable@civic.gov.in", "Unavailable TPL Officer", "OFFICER")
        OfficerProfile.objects.create(user=unavailable_user, department=self.tpl_dept, available=False)

        self.login(self.biz_owner)
        response = self.client.post(
            "/api/v1/applications/",
            {"service_id": routing_service.id, "data": {}},
            format="json",
        )
        self.assertEqual(response.status_code, 201, msg=response.data)
        application = BusinessApplication.objects.get(pk=response.data["data"]["id"])
        self.assertIsNone(application.assigned_officer_id)

        self.login(unavailable_user)
        queue = self.client.get("/api/v1/applications/assigned/")
        self.assertEqual(queue.status_code, 200, msg=queue.data)
        self.assertIn(application.id, [item["id"] for item in queue.data["data"]])

    def test_clarification_and_review_flow(self):
        self.login(self.citizen)
        payload = {
            "service_id": self.birth_svc.id,
            "data": {"applicant_name": self.citizen.name, "child_name": "Baby"},
        }
        app_id = self.client.post("/api/v1/applications/", payload, format="json").data["data"]["id"]
        self.login(self.officer2)
        cl_resp = self.client.post(
            f"/api/v1/applications/{app_id}/clarification/",
            {"message": "Please upload hospital record."},
            format="json",
        )
        self.assertEqual(cl_resp.status_code, 200, msg=cl_resp.data)
        app = BusinessApplication.objects.get(id=app_id)
        self.assertEqual(app.status, "CLARIFICATION_REQUESTED")

        status_resp = self.client.patch(
            f"/api/v1/applications/{app_id}/status/",
            {"status": "UNDER_REVIEW", "remarks": "Docs re-uploaded."},
            format="json",
        )
        self.assertEqual(status_resp.status_code, 200, msg=status_resp.data)
        app.refresh_from_db()
        self.assertEqual(app.status, "UNDER_REVIEW")

    def test_approve_and_reject_endpoints(self):
        self.login(self.citizen)
        payload = {
            "service_id": self.birth_svc.id,
            "data": {"applicant_name": self.citizen.name, "child_name": "A"},
        }
        app_id = self.client.post("/api/v1/applications/", payload, format="json").data["data"]["id"]

        self.login(self.officer2)
        self.client.patch(
            f"/api/v1/applications/{app_id}/status/",
            {"status": "UNDER_REVIEW"},
            format="json",
        )
        approve = self.client.post(
            f"/api/v1/applications/{app_id}/approve/",
            {"remarks": "All records verified."},
            format="json",
        )
        self.assertEqual(approve.status_code, 200, msg=approve.data)
        app = BusinessApplication.objects.get(id=app_id)
        self.assertEqual(app.status, "APPROVED")

    def test_approval_certificate_is_only_available_after_approval(self):
        self.login(self.citizen)
        created = self.client.post(
            "/api/v1/applications/",
            {
                "service_id": self.birth_svc.id,
                "data": {"applicant_name": self.citizen.name, "child_name": "Certificate Test"},
            },
            format="json",
        )
        application_id = created.data["data"]["id"]
        before_approval = self.client.get(f"/api/v1/applications/{application_id}/certificate/")
        self.assertEqual(before_approval.status_code, 400, msg=before_approval.data)

        self.login(self.officer2)
        approved = self.client.post(
            f"/api/v1/applications/{application_id}/approve/",
            {"remarks": "Records verified."},
            format="json",
        )
        self.assertEqual(approved.status_code, 200, msg=approved.data)

        self.login(self.citizen)
        certificate = self.client.get(f"/api/v1/applications/{application_id}/certificate/")
        self.assertEqual(certificate.status_code, 200)
        self.assertEqual(certificate["Content-Type"], "application/pdf")
        self.assertTrue(certificate.content.startswith(b"%PDF"))

        self.login(self.citizen2)
        unauthorized = self.client.get(f"/api/v1/applications/{application_id}/certificate/")
        self.assertEqual(unauthorized.status_code, 404)

    def test_reject_requires_reason(self):
        self.login(self.citizen)
        payload = {
            "service_id": self.birth_svc.id,
            "data": {"applicant_name": self.citizen.name, "child_name": "A2"},
        }
        app_id = self.client.post("/api/v1/applications/", payload, format="json").data["data"]["id"]
        self.login(self.officer2)
        reject_missing = self.client.post(
            f"/api/v1/applications/{app_id}/reject/",
            {},
            format="json",
        )
        self.assertEqual(reject_missing.status_code, 400)
        reject_good = self.client.post(
            f"/api/v1/applications/{app_id}/reject/",
            {"reason": "Documents are not legible."},
            format="json",
        )
        self.assertEqual(reject_good.status_code, 200, msg=reject_good.data)
        app = BusinessApplication.objects.get(id=app_id)
        self.assertEqual(app.status, "REJECTED")
        self.assertEqual(
            list(app.history.values_list("new_status", flat=True)),
            ["SUBMITTED", "UNDER_REVIEW", "REJECTED"],
        )

    def test_application_response_shape(self):
        self.login(self.citizen)
        payload = {
            "service_id": self.birth_svc.id,
            "data": {"applicant_name": self.citizen.name, "child_name": "Shape Tester"},
        }
        app_id = self.client.post("/api/v1/applications/", payload, format="json").data["data"]["id"]
        detail = self.client.get(f"/api/v1/applications/{app_id}/")
        self.assertEqual(detail.status_code, 200)
        data = detail.data["data"]
        self.assertIn("application_number", data)
        self.assertIn("id", data)
        self.assertEqual(set(data["service"].keys()), {"id", "name", "code"})
        self.assertEqual(set(data["department"].keys()), {"id", "name"})
        self.assertIn("applicant_name", data)
        self.assertIn("data", data)
        self.assertIsInstance(data["documents"], list)
        self.assertIsInstance(data["timeline"], list)

    def test_invalid_application_status_returns_422(self):
        self.login(self.citizen)
        payload = {
            "service_id": self.birth_svc.id,
            "data": {"applicant_name": self.citizen.name, "child_name": "Invalid"},
        }
        app_id = self.client.post("/api/v1/applications/", payload, format="json").data["data"]["id"]
        self.login(self.officer2)
        resp = self.client.patch(
            f"/api/v1/applications/{app_id}/status/",
            {"status": "APPROVED"},
            format="json",
        )
        self.assertEqual(resp.status_code, 422, msg=resp.data)
        self.assertEqual(resp.data["error"]["code"], "BUSINESS_ERROR")


class PermissionTests(BaseTestCase):
    def test_only_admin_can_activate_or_deactivate_users(self):
        self.login(self.citizen)
        forbidden = self.client.patch(
            f"/api/v1/users/{self.citizen2.id}/",
            {"status": "INACTIVE"},
            format="json",
        )
        self.assertEqual(forbidden.status_code, 403)

        self.login(self.admin)
        updated = self.client.patch(
            f"/api/v1/users/{self.citizen2.id}/",
            {"is_active": False},
            format="json",
        )
        self.assertEqual(updated.status_code, 200, msg=updated.data)
        self.citizen2.refresh_from_db()
        self.assertFalse(self.citizen2.is_active)
        self.assertTrue(AuditLog.objects.filter(
            action="USER_UPDATED", entity_id=str(self.citizen2.id),
        ).exists())

    def test_service_file_requirements_are_normalized(self):
        self.login(self.admin)
        response = self.client.post(
            "/api/v1/services/",
            {
                "name": "Documented Service",
                "code": "DOC-SERVICE",
                "department_id": self.tpl_dept.id,
                "requirements": [
                    {
                        "key": "identity_proof",
                        "label": "Identity proof",
                        "type": "file",
                        "required": True,
                        "allowed_file_types": ["pdf"],
                        "max_file_size": 1048576,
                    },
                ],
            },
            format="json",
        )
        self.assertEqual(response.status_code, 201, msg=response.data)
        service_id = response.data["data"]["id"]
        document = RequiredDocument.objects.get(service_id=service_id, key="identity_proof")
        self.assertEqual(document.name, "Identity proof")
        self.assertEqual(document.allowed_file_types, ["pdf"])
        self.assertEqual(response.data["data"]["requirements"][0]["key"], "identity_proof")
        self.assertEqual(response.data["data"]["required_documents"][0]["id"], document.id)

    def test_service_catalog_supports_workflow_type_and_verification(self):
        self.login(self.admin)
        response = self.client.post(
            "/api/v1/services/",
            {
                "name": "Business Permit Example",
                "code": "BUS-PERMIT-EXAMPLE",
                "department_id": self.tpl_dept.id,
                "service_type": "BUSINESS",
                "eligibility": "Businesses operating in this municipality.",
                "procedure": "Submit documents for officer review.",
                "field_verification_required": True,
                "requirements": [
                    {
                        "key": "business_name",
                        "label": "Business name",
                        "type": "text",
                        "required": True,
                    },
                    {
                        "key": "registration_proof",
                        "label": "Registration proof",
                        "type": "file",
                        "required": True,
                        "allowed_file_types": ["pdf"],
                        "max_file_size": 2097152,
                    },
                ],
            },
            format="json",
        )
        self.assertEqual(response.status_code, 201, msg=response.data)
        data = response.data["data"]
        self.assertEqual(data["service_type"], "BUSINESS")
        self.assertTrue(data["field_verification_required"])
        self.assertEqual(data["eligibility"], "Businesses operating in this municipality.")
        self.assertEqual(data["requirements"][1]["max_file_size"], 2097152)

    def test_service_catalog_rejects_invalid_type_and_duplicate_requirement_keys(self):
        self.login(self.admin)
        invalid_type = self.client.post(
            "/api/v1/services/",
            {
                "name": "Invalid Catalog Service",
                "code": "INVALID-CATALOG",
                "department_id": self.tpl_dept.id,
                "service_type": "UNKNOWN",
                "requirements": [],
            },
            format="json",
        )
        self.assertEqual(invalid_type.status_code, 400, msg=invalid_type.data)

        duplicate_keys = self.client.post(
            "/api/v1/services/",
            {
                "name": "Duplicate Fields Service",
                "code": "DUPLICATE-FIELDS",
                "department_id": self.tpl_dept.id,
                "service_type": "MUNICIPAL",
                "requirements": [
                    {"key": "applicant", "label": "Applicant", "type": "text"},
                    {"key": "applicant", "label": "Other applicant", "type": "text"},
                ],
            },
            format="json",
        )
        self.assertEqual(duplicate_keys.status_code, 400, msg=duplicate_keys.data)

    def test_admin_only_create_department(self):
        self.login(self.citizen)
        resp = self.client.post(
            "/api/v1/departments/",
            {"name": "New Dept", "code": "NEW", "description": "x"},
            format="json",
        )
        self.assertEqual(resp.status_code, 403)

        self.login(self.admin)
        resp2 = self.client.post(
            "/api/v1/departments/",
            {"name": "New Dept", "code": "NEW", "description": "x"},
            format="json",
        )
        self.assertEqual(resp2.status_code, 201, msg=resp2.data)

    def test_admin_only_create_service(self):
        self.login(self.officer)
        resp = self.client.post(
            "/api/v1/services/",
            {"name": "S", "code": "S-SVC", "department_id": self.drain_dept.id,
             "processing_time_days": 5, "fee": 100, "requirements": []},
            format="json",
        )
        self.assertEqual(resp.status_code, 403)

    def test_users_list_admin_only(self):
        self.login(self.officer)
        resp = self.client.get("/api/v1/users/")
        self.assertEqual(resp.status_code, 403)
        self.login(self.admin)
        resp2 = self.client.get("/api/v1/users/")
        self.assertEqual(resp2.status_code, 200, msg=resp2.data)

    def test_audit_logs_admin_only(self):
        self.login(self.officer)
        resp = self.client.get("/api/v1/audit-logs/")
        self.assertEqual(resp.status_code, 403)
        self.login(self.admin)
        resp2 = self.client.get("/api/v1/audit-logs/")
        self.assertEqual(resp2.status_code, 200)

    def test_non_owner_citizen_cannot_see_others_complaint(self):
        c = Complaint.objects.create(
            citizen=self.citizen, title="Mine", description="x", category="DRAINAGE",
            priority="MEDIUM", department=self.drain_dept, ward="Ward 3", address="a",
            latitude=20, longitude=85, status="CLASSIFIED",
        )
        self.login(self.citizen2)
        resp = self.client.get(f"/api/v1/complaints/{c.id}/")
        self.assertEqual(resp.status_code, 404)

    def test_officer_can_see_own_dept_complaints(self):
        other_dept_c = Complaint.objects.create(
            citizen=self.citizen, title="Other", description="x", category="HEALTH",
            priority="LOW", department=self.health_dept, ward="Ward 1", address="a",
            latitude=20, longitude=85, status="CLASSIFIED",
        )
        drain_c = Complaint.objects.create(
            citizen=self.citizen, title="Mine", description="x", category="DRAINAGE",
            priority="HIGH", department=self.drain_dept, ward="Ward 3", address="a",
            latitude=20, longitude=85, status="CLASSIFIED",
        )
        self.login(self.officer)  # DRAIN dept
        resp_list = self.client.get("/api/v1/complaints/")
        self.assertEqual(resp_list.status_code, 200)
        ids = [c["id"] for c in resp_list.data["data"]]
        self.assertIn(drain_c.id, ids)
        self.assertNotIn(other_dept_c.id, ids)

    def test_complaint_filter_and_opt_in_pagination(self):
        first = Complaint.objects.create(
            citizen=self.citizen, title="Submitted drain", description="Blocked drain",
            category="DRAINAGE", priority="HIGH", department=self.drain_dept,
            ward="Ward 3", address="A", latitude=20, longitude=85, status="SUBMITTED",
        )
        Complaint.objects.create(
            citizen=self.citizen, title="Road repair", description="Pothole",
            category="ROADS", priority="MEDIUM", department=self.road_dept,
            ward="Ward 5", address="B", latitude=20, longitude=85, status="IN_PROGRESS",
        )
        self.login(self.admin)
        paged = self.client.get("/api/v1/complaints/?status=SUBMITTED&search=drain&page=1&page_size=1")
        self.assertEqual(paged.status_code, 200, msg=paged.data)
        self.assertEqual(paged.data["data"]["count"], 1)
        self.assertEqual(paged.data["data"]["results"][0]["id"], first.id)
        unpaged = self.client.get("/api/v1/complaints/")
        self.assertIsInstance(unpaged.data["data"], list)

    def test_engineer_can_update_resolution_only_when_assigned(self):
        c = Complaint.objects.create(
            citizen=self.citizen, title="X", description="x", category="DRAINAGE",
            priority="HIGH", department=self.drain_dept, ward="Ward 3", address="a",
            latitude=20, longitude=85, status="IN_PROGRESS", assigned_engineer=self.engineer2,
        )
        ComplaintAssignment.objects.create(complaint=c, engineer=self.engineer2, assigned_by=self.officer)
        self.login(self.engineer)  # not assigned
        resp = self.client.post(
            f"/api/v1/complaints/{c.id}/resolution/",
            {"description": "done"},
            format="json",
        )
        self.assertEqual(resp.status_code, 404)

    def test_engineer_cannot_view_unassigned_department_complaints(self):
        complaint = Complaint.objects.create(
            citizen=self.citizen, title="Unassigned drain", description="Needs triage",
            category="DRAINAGE", priority="LOW", department=self.drain_dept,
            ward="Ward 3", address="a", latitude=20, longitude=85, status="CLASSIFIED",
        )
        self.login(self.engineer)
        self.assertEqual(self.client.get(f"/api/v1/complaints/{complaint.id}/").status_code, 404)
        response = self.client.get("/api/v1/complaints/")
        self.assertEqual(response.status_code, 200)
        self.assertNotIn(complaint.id, [item["id"] for item in response.data["data"]])

    def test_business_owner_can_manage_own_business(self):
        self.login(self.biz_owner)
        create = self.client.post(
            "/api/v1/businesses/",
            {"name": "New Biz", "type": "RETAIL", "address": "a",
             "gstin": "GST", "license_number": "", "status": "PENDING"},
            format="json",
        )
        self.assertEqual(create.status_code, 201, msg=create.data)
        biz_id = create.data["data"]["id"]
        self.login(self.citizen)
        self.assertEqual(self.client.get(f"/api/v1/businesses/{biz_id}/").status_code, 404)

    def test_analytics_visible_to_admin_and_officers(self):
        self.login(self.citizen)
        overview = self.client.get("/api/v1/analytics/overview/")
        self.assertEqual(overview.status_code, 403)
        self.login(self.officer)
        self.assertEqual(self.client.get("/api/v1/analytics/overview/").status_code, 200)
        self.login(self.admin)
        self.assertEqual(self.client.get("/api/v1/analytics/overview/").status_code, 200)


class AnalyticsAggregationTests(BaseTestCase):
    def setUp(self):
        super().setUp()
        from django.utils import timezone
        from datetime import timedelta
        import datetime
        self.login(self.admin)
        self._make_complaint("Ward 1", "DRAINAGE", self.drain_dept, "SUBMITTED")
        self._make_complaint("Ward 1", "ROADS", self.road_dept, "IN_PROGRESS")
        self._make_complaint("Ward 2", "DRAINAGE", self.drain_dept, "RESOLVED", duration_hours=48)
        self._make_complaint("Ward 3", "WASTE", None, "CLOSED", duration_hours=3)
        self._make_complaint("Ward 3", "DRAINAGE", self.drain_dept, "OVERDUE_PENDING", overdue_days=60)
        self._make_complaint("Ward 3", "HEALTH", self.health_dept, "RESOLVED", duration_hours=12)

        self._make_application("SUBMITTED")
        self._make_application("UNDER_REVIEW")
        self._make_application("APPROVED")

    def _make_complaint(self, ward, category, department, status_target, duration_hours=None, overdue_days=None):
        from django.utils import timezone
        from datetime import timedelta
        created = timezone.now() - timedelta(days=overdue_days or 5)
        updated = created
        c = Complaint.objects.create(
            citizen=self.citizen,
            title=f"Complaint {category}-{ward}-{status_target}",
            description="x",
            category=category,
            priority="MEDIUM",
            department=department or self.drain_dept,
            ward=ward,
            address="a",
            latitude=20.296,
            longitude=85.824,
            status="SUBMITTED",
            created_at=created,
            updated_at=updated,
        )
        Complaint.objects.filter(pk=c.pk).update(created_at=created, updated_at=updated)
        c.refresh_from_db()
        ComplaintStatusHistory.objects.create(
            complaint=c, old_status="", new_status="SUBMITTED", changed_by=self.citizen, remarks="seed",
            created_at=created,
        )
        target_status = status_target if status_target != "OVERDUE_PENDING" else "IN_PROGRESS"
        path = _build_path(target_status)
        prev = "SUBMITTED"
        current_time = created
        for s in path:
            if s == prev:
                continue
            if s == target_status and duration_hours is not None:
                current_time = created + timedelta(hours=duration_hours)
            ComplaintStatusHistory.objects.create(
                complaint=c, old_status=prev, new_status=s,
                changed_by=self.officer, remarks="seed",
                created_at=current_time,
            )
            prev = s
        c.status = target_status
        c.updated_at = current_time
        c.save()
        if status_target == "OVERDUE_PENDING":
            ComplaintStatusHistory.objects.filter(
                complaint=c, new_status="SUBMITTED"
            ).update(created_at=timezone.now() - timedelta(days=overdue_days))
            c.created_at = timezone.now() - timedelta(days=overdue_days)
            c.save(update_fields=["created_at"])
        return c

    def _make_application(self, status):
        svc, _ = Service.objects.get_or_create(
            code="ANA-SVC",
            defaults={"name": "A", "department": self.drain_dept, "processing_time_days": 3, "fee": 0,
                      "requirements": []},
        )
        app = BusinessApplication.objects.create(
            applicant=self.citizen,
            service=svc,
            application_number=f"MUN-2026-ANA{BusinessApplication.objects.count()}",
            department=svc.department,
            status="SUBMITTED",
            data={},
        )
        ApplicationStatusHistory.objects.create(
            application=app, old_status="", new_status="SUBMITTED", changed_by=self.citizen, remarks="seed",
        )
        if status != "SUBMITTED":
            app.status = status
            app.save(update_fields=["status"])
            ApplicationStatusHistory.objects.create(
                application=app, old_status="SUBMITTED", new_status=status, changed_by=self.officer,
                remarks="seed",
            )
        return app

    def test_overview_correct_fields(self):
        resp = self.client.get("/api/v1/analytics/overview/")
        self.assertEqual(resp.status_code, 200, msg=resp.data)
        data = resp.data["data"]
        keys = {"total_complaints", "open_complaints", "resolved_complaints",
                "overdue_complaints", "average_resolution_time_hours",
                "total_applications", "pending_applications"}
        self.assertEqual(set(data.keys()), keys)
        self.assertEqual(data["total_complaints"], 6)
        self.assertEqual(data["total_applications"], 3)
        self.assertGreaterEqual(data["overdue_complaints"], 1)
        self.assertAlmostEqual(data["average_resolution_time_hours"], 20.0, delta=10)

    def test_categories(self):
        resp = self.client.get("/api/v1/analytics/complaints/categories/")
        self.assertEqual(resp.status_code, 200)
        items = resp.data["data"]
        self.assertTrue(any(i["category"] == "DRAINAGE" and i["count"] >= 3 for i in items))

    def test_departments(self):
        resp = self.client.get("/api/v1/analytics/complaints/departments/")
        self.assertEqual(resp.status_code, 200)
        items = resp.data["data"]
        self.assertTrue(all("department" in i and "count" in i for i in items))
        self.assertTrue(any("Drainage" in i["department"] for i in items))

    def test_wards(self):
        resp = self.client.get("/api/v1/analytics/complaints/wards/")
        self.assertEqual(resp.status_code, 200)
        items = resp.data["data"]
        self.assertTrue(all("ward" in i and "count" in i for i in items))
        ward3 = next((i for i in items if i["ward"] == "Ward 3"), None)
        self.assertIsNotNone(ward3)
        self.assertGreaterEqual(ward3["count"], 3)

    def test_trends(self):
        resp = self.client.get("/api/v1/analytics/complaints/trends/")
        self.assertEqual(resp.status_code, 200)
        items = resp.data["data"]
        if items:
            first = items[0]
            self.assertEqual(set(first.keys()), {"month", "complaints", "resolved"})


class MapPrivacyTests(BaseTestCase):
    def setUp(self):
        super().setUp()
        for ward in ("Ward 1", "Ward 2", "Ward 3"):
            Complaint.objects.create(
                citizen=self.citizen,
                title="Test",
                description="Sensitive description",
                category="DRAINAGE",
                priority="HIGH",
                department=self.drain_dept,
                ward=ward,
                address=f"Near Citizen Home, {self.citizen.name}",
                latitude=20.29,
                longitude=85.82,
                status="CLASSIFIED",
            )
        self.login(self.admin)

    def test_map_complaints_no_pii(self):
        resp = self.client.get("/api/v1/analytics/map/complaints/")
        self.assertEqual(resp.status_code, 200)
        items = resp.data["data"]
        allowed = {"id", "latitude", "longitude", "priority", "status", "category", "ward"}
        disallowed = {"citizen_name", "name", "email", "address", "phone", "user_id",
                      "citizen", "citizen_id", "assigned_engineer", "description", "title"}
        for entry in items:
            self.assertEqual(set(entry.keys()), allowed)
            leaked = set(str(entry.values())) & {"Ramesh", "ramesh@example.com", "Near Citizen Home"}
            self.assertEqual(leaked, set())
            for bad_key in disallowed:
                self.assertNotIn(bad_key, entry)

    def test_heatmap_shape(self):
        resp = self.client.get("/api/v1/analytics/map/heatmap/")
        self.assertEqual(resp.status_code, 200)
        items = resp.data["data"]
        for entry in items:
            self.assertEqual(set(entry.keys()), {"lat", "lng", "intensity"})
            self.assertTrue(0 <= entry["intensity"] <= 1)
            self.assertIsInstance(entry["lat"], (int, float))
            self.assertIsInstance(entry["lng"], (int, float))


_PATH_GRAPH = {
    "SUBMITTED": ["AI_PROCESSING", "CLASSIFIED", "REJECTED"],
    "AI_PROCESSING": ["CLASSIFIED"],
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


def _build_path(target):
    from collections import deque
    start = "SUBMITTED"
    if start == target:
        return [start]
    q = deque([(start, [start])])
    visited = {start}
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
