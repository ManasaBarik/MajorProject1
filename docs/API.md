# API contract notes

Base path: `/api/v1/`. All protected endpoints expect `Authorization: Bearer <access-token>`.

Every successful response is `{ "success": true, "data": ..., "message": "..." }`; errors are `{ "success": false, "error": { "code", "message", "details" } }`.

Implemented endpoint groups: authentication (`auth/*`, `users/me/`), departments, services, complaints (including `timeline`, `images`, assignment, status, resolution, feedback, and AI review), businesses, applications/documents/workflow, notifications, analytics/GIS, chatbot, and audit logs.

The exact request fields and status values are defined by the supplied frozen specification. The only deliberate provider behaviour is that an unconfigured AI provider returns a stored, zero-confidence advisory result; it never approves or rejects an application or complaint.
