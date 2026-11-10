# AI-Driven Unified Smart Civic Governance Platform

Django REST Framework modular monolith for the existing React + Vite frontend.
The backend owns authentication, role permissions, complaint and application
workflows, notifications, audit records, analytics, and municipal configuration.
It also ships an advisory AI triage layer (Google Gemini) that suggests a
complaint category, priority, and department for officer review. The platform
runs fully without an AI key: when no credentials are configured it degrades to
an offline heuristic analyzer, so no workflow is blocked.

## Tech Stack

- Python 3.11+, Django 5.x, Django REST Framework
- SQLite for local development; PostgreSQL may be configured with `DATABASE_URL`
- JWT auth (`djangorestframework-simplejwt`) with token blacklist + refresh rotation
- `django-cors-headers` for the Vite dev origin
- `django-filter` and bounded optional pagination for complaint/application lists
- Pillow and content/signature checks for image and document uploads
- drf-spectacular at `/api/schema/` and `/api/docs/`

## Roles (exact strings)

`CITIZEN`, `BUSINESS_OWNER`, `OFFICER`, `ENGINEER`, `ADMINISTRATOR`.

## Quick Setup

1. **Python environment**
   ```bash
   python -m venv .venv
   # Windows: .venv\Scripts\activate
   # macOS/Linux: source .venv/bin/activate
   pip install -r requirements.txt
   ```

2. **Environment**
   ```bash
   copy .env.example .env
   # or: cp .env.example .env
   ```
   Leave `DATABASE_URL` unset for the local SQLite database. Set a strong
   `SECRET_KEY` and production database URL when deploying. `CORS_ALLOWED_ORIGINS`
   includes the Vite development origin.

3. **Database**
   ```bash
   python manage.py makemigrations
   python manage.py migrate
   ```

4. **Create the first administrator**
   ```bash
   python manage.py createsuperuser
   ```
   Use your real administrator email and a strong password. No credentials or
   demo activity are created automatically.

5. **Load configured municipal catalogs (optional)**
   ```bash
   python manage.py seed_data --catalog-file path/to/municipality.json
   ```
   The command imports only departments, services, and normalized file
   requirements from the supplied JSON. Without `--catalog-file` it changes
   nothing. The legacy sample fixture requires explicit `seed --demo --password
   "..."`; use it only with a disposable database. There is no reset flag.

   To add the editable development starter catalog instead, run:
   ```bash
   python manage.py seed_starter_catalog
   ```
   This idempotently adds common municipal and business service examples and
   their document requirements. Names, fees, eligibility, forms, and required
   documents are illustrative and must be confirmed for the local municipality.

6. **Run the dev server**
   ```bash
   python manage.py runserver
   ```
   API base: `http://127.0.0.1:8000/api/v1/`.

## Run Tests

```bash
python manage.py test tests
```

Tests cover auth/JWT, role and ownership restrictions, manual complaint
classification, assignment/reassignment/unassignment, resolution verification,
file validation, application draft/upload/clarification/decision flows,
notification/audit writes, analytics, map privacy, chatbot placeholder, the AI
triage engine (validation, providers, duplicate detection, category→department
routing, accept/override), and OpenAPI availability. Tests run against the
offline mock provider, so no network or API key is required.

## AI Setup (optional)

The AI triage layer is provider-based and configured entirely through `.env`:

| Variable | Default | Purpose |
| --- | --- | --- |
| `AI_PROVIDER` | `gemini` | `gemini`, `mock` (offline heuristic), or `none` (disabled) |
| `GEMINI_API_KEY` | *(empty)* | Server-side Google Gemini key. Never sent to the browser |
| `GEMINI_MODEL` | `gemini-3.5-flash-lite` | Free-tier friendly model; change as models evolve |
| `GEMINI_API_BASE` | `https://generativelanguage.googleapis.com/v1beta` | Gemini REST base |
| `AI_AUTO_ANALYZE` | `True` | Run triage automatically when a complaint is submitted |
| `AI_SIMILARITY_THRESHOLD` | `0.42` | Cosine cutoff for near-duplicate detection |
| `AI_LOW_CONFIDENCE_THRESHOLD` | `0.55` | Below this the result is flagged for manual review |
| `AI_REQUEST_TIMEOUT` / `AI_MAX_RETRIES` | `20` / `2` | Per-request timeout and retry budget |

Set `GEMINI_API_KEY` to enable live analysis. With `AI_PROVIDER=gemini` and no
key (or `AI_PROVIDER=mock`), the platform uses an offline keyword heuristic so
triage, duplicate detection, and routing still work. `AI_PROVIDER=none` disables
AI entirely. The provider never receives citizen PII—only the complaint title,
description, stated category, and ward are sent.

To route recommendations to departments, seed the category→department mapping
(or manage it in the admin / `POST category-mappings/`):

```bash
python manage.py seed_category_mappings --overwrite
```

## URL Prefix & Envelope

Every route lives under `/api/v1/`.

Success envelope: `{ "success": true, "data": <object|array>, "message": "..." }`
Error envelope:   `{ "success": false, "error": { "code": "...", "message": "...", "details": {} } }`

Error codes: `VALIDATION_ERROR`, `UNAUTHENTICATED`, `UNAUTHORIZED`, `NOT_FOUND`,
`CONFLICT`, `BUSINESS_ERROR` (HTTP 422), `RATE_LIMITED`, `SERVER_ERROR`.

Lists default to a bare array inside `data`; add `?page=1` to opt into pagination
(`count`, `next`, `previous`, `results`). Complaint and application lists accept
status, priority, department, service, search, and ordering filters.

## Endpoints

All API endpoints are below `/api/v1/` and return the standard success/error
envelopes above.

- Auth: `POST auth/register/`, `POST auth/login/`, `POST auth/token/refresh/`, `POST auth/logout/`, `GET auth/me/`, `PATCH users/me/`, `POST auth/password-reset/`, `POST auth/password-reset/confirm/`.
- Users/admin: `GET users/`, `PATCH users/{id}/`, `GET admin/officers/`, `PATCH admin/officers/{id}/`, `GET admin/engineers/`.
- Departments: `GET/POST departments/`, `GET/PATCH/DELETE departments/{id}/`, `GET departments/{id}/staff/`; category→department routing via `GET/POST category-mappings/`, `GET/PATCH/DELETE category-mappings/{id}/` (write is admin-only).
- Services: `GET/POST services/`, `GET/PATCH/DELETE services/{id}/`; `service_type` is `MUNICIPAL` or `BUSINESS`, `field_verification_required` controls the optional site-check step, and file requirements are included in service data and stored as normalized records.
- Complaints: collection/detail, `timeline/`, `images/`, `assign/`, `reassign/`, `unassign/`, `status/`, `resolution/`, `verify-resolution/`, `feedback/`, `ai/`, `ai/analyze/`, `ai/accept/`, `ai-review/`.
- Businesses: collection/detail create, read, and update endpoints.
- Applications: collection/detail, `documents/`, `documents/{document_id}/verify/`, `timeline/`, `assigned/`, `submit/`, `cancel/`, `review/`, `clarification/`, `status/`, `approve/`, `reject/`.
- Notifications: collection, `{id}/read/`, `read-all/`.
- Analytics/GIS: `analytics/overview/`, complaint categories/departments/wards/trends, `analytics/map/complaints/`, `analytics/map/heatmap/`.
- Chatbot: `chatbot/chat/`, `chatbot/conversations/`, `chatbot/conversations/{id}/`.
- Audit/docs: `audit-logs/`, `/api/schema/`, `/api/docs/`.

## Workflows

Complaint: `SUBMITTED` -> automatic AI triage runs and parks the report in
`AI_PROCESSING` with an advisory category / priority / department recommendation
-> officer accepts the recommendation (`ai/accept/`) or overrides it
(`ai-review/`) -> `CLASSIFIED` -> engineer assignment -> `ASSIGNED` ->
`IN_PROGRESS` -> engineer resolution -> `VERIFICATION_PENDING` -> officer
verifies to `RESOLVED` or reopens. Citizen feedback closes a resolved
complaint. AI is advisory only; a human always records the official
classification, and analysis never blocks submission.

Application: applicant selects a municipal or business service, completes its
dynamic form, uploads required files, and submits -> application number is
generated and an available officer in the service department is auto-assigned
(least active workload). If no officer is available, the unassigned application
remains visible in the department queue. Workflow continues through `SUBMITTED`
-> officer `UNDER_REVIEW` -> optional `DOCUMENT_VERIFICATION`, configured
`FIELD_VERIFICATION`, or clarification/resubmission -> human approval/rejection
-> optional `COMPLETED`. Applicants track status/history and can download an
approval certificate after approval. Notifications are in-app only. No AI
decision, SMS/email delivery, or payment processing is part of this workflow.

## Roles

| Role | Access |
| --- | --- |
| CITIZEN | Own profile, complaints, feedback, service applications, and documents |
| BUSINESS_OWNER | Own business profiles and applications/documents |
| OFFICER | Department complaints, manual classification, assignment, verification, applications |
| ENGINEER | Assigned complaints, field status, resolution submissions |
| ADMINISTRATOR | Users, departments, services, audit logs, analytics, all records |

The backend enforces roles and object ownership; frontend route guards are not
authorization controls.

## Data Model

`User` has one-to-one citizen/officer/engineer profiles. Departments own services
and staff. Citizens own complaints; complaints have images, assignment history,
status history, resolutions, feedback, optional AIAnalysis, and notifications.
Services own normalized RequiredDocument rows. Applications link an applicant,
optional business, service, department, document records, and status history.
AuditLog records actor, action, entity, old/new values, IP, and timestamp.

## AI Layer

`apps/ai/` holds the triage engine:

- `providers/` — `GeminiProvider` (stdlib `urllib`, no extra dependencies),
  `MockAIProvider` (offline keyword heuristic), and `PlaceholderAIProvider`
  (explicitly disabled). `services.get_provider()` selects one from `AI_PROVIDER`
  and falls back to the mock when a Gemini key is missing.
- `prompts.py` — injection-hardened system instruction; only title, description,
  stated category, and ward are sent (no PII).
- `schemas.py` — strict output validation; unknown categories/priorities are
  normalized or replaced with a safe default and flagged for manual review.
- `duplicates.py` — pure-Python TF-IDF cosine similarity with a 90-day / 3 km
  window for near-duplicate detection, independent of the LLM.

Every run is stored on `AIAnalysis` (prediction, confidence, summary, reasoning,
`requires_manual_review`, `similar_complaints`, provider/model) and audited as
`AI_ANALYSIS_COMPLETED` / `AI_ANALYSIS_FAILED`. Recommendations are advisory:
officers accept (`ai/accept/`) or override them, and the complaint is never
mutated by the analyzer itself. Chatbot responses remain FAQ-backed.

## Frontend Integration

Set `VITE_API_BASE_URL=http://127.0.0.1:8000/api/v1` in the Vite environment.
The existing `src/services/api/` modules use the backend envelope and JWT
refresh flow. For production, configure PostgreSQL and email delivery separately;
neither was verified in this local SQLite setup.
