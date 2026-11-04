# FaceTrack AI — System Architecture & Agent Guide

**Status:** Living project standard  
**Audience:** AI coding agents, Python engineers, UI/UX designers, database engineers, QA, and security reviewers  
**Purpose:** Maintain and improve FaceTrack AI, a bilingual workforce management and attendance system with optional facial verification.

> **Core rule:** Inspect the existing repository before changing it. Preserve working behavior, follow this guide, and explain any conflict or necessary deviation. Do not claim a feature is complete until its implementation and tests have been verified.

## 1. Product goals

Build a reliable, secure, responsive workforce system that supports:

- Employee and department directory management.
- Attendance check-in/check-out, correction workflows, shifts, holidays, and reports.
- Role-governed administration and audit history.
- Optional facial verification with explicit consent and privacy controls.
- English and Khmer UI, dark/light themes, and accessible layouts.
- Fast search and data entry for everyday HR and security workflows.

Prioritize **correctness, usability, data integrity, privacy, and speed** over decorative effects. Facial recognition must not be the only way to record attendance; provide an accessible manual or alternative verification workflow.

## 2. Existing stack and architecture

Use the current stack unless the owner approves a change:

- Python, FastAPI, Uvicorn, Jinja2 server-side rendering.
- SQLAlchemy 2.x ORM; PostgreSQL/Neon as production database and SQLite for local development where supported.
- Pydantic for request validation.
- OpenCV YuNet/SFace ONNX models for the existing face pipeline.
- HTML, CSS, vanilla JavaScript, and the project's existing Tailwind/Chart.js/Lucide CDN setup.
- English/Khmer translations in `app/translations.py`.

Do not introduce Node.js, a frontend framework, a new database, or a runtime dependency without a clear benefit and owner approval. Pin dependencies and CDN versions. Add SRI where supported. Do not assume SQLite and PostgreSQL behave identically; test both supported database modes.

### Target architecture

Keep the current project operational while moving toward clear domain boundaries:

```text
app/
  main.py                 # App creation, middleware, router registration
  config.py               # Validated environment configuration
  database.py             # Engine, sessions, transaction dependencies
  models/                 # ORM models (split by domain as project grows)
  schemas/                # Pydantic input/output schemas
  routers/                # HTTP endpoints; thin request/response layer
  services/               # Business rules and use cases
  repositories/           # Reusable query/data-access operations when useful
  security.py             # Authentication, permissions, CSRF, session helpers
  face_recognition.py     # Detection, quality checks, embeddings, matching
  translations.py         # English/Khmer UI strings
  templates/              # Jinja2 pages and shared components
  static/css/              # Design tokens and styles
  static/js/               # Small, reusable UI behaviors
  migrations/              # Alembic migration history
tests/
  unit/
  integration/
  security/
  e2e/
```

This is a target structure, not permission to perform a large rewrite. If the repository currently uses a single `models.py` or `main.py`, make incremental changes and keep imports working. Split modules when a domain becomes difficult to maintain, not just to match a diagram.

## 3. Agent workflow (mandatory)

For every task:

1. **Inspect:** Read relevant routes, models, templates, translations, configuration, tests, and Git changes before editing.
2. **Plan:** Identify affected screens, endpoints, tables, permissions, translations, migrations, and tests. State assumptions where requirements are unclear.
3. **Implement narrowly:** Reuse existing patterns and components. Avoid unrelated refactors, duplicate logic, or replacing working code without reason.
4. **Protect data:** Use migrations for schema changes; never silently drop tables, columns, or user data.
5. **Test:** Run focused tests, then the full available suite. Test authorization, validation, empty states, and error paths.
6. **Review:** Check secrets, logs, accessibility, responsive layouts, query performance, and English/Khmer parity.
7. **Report honestly:** Summarize files changed, behavior delivered, commands/tests run, results, migrations, and remaining risks. Clearly disclose tests that could not be run.

Never invent repository files, test results, database contents, or completed features. Do not overwrite user changes. Ask before destructive operations, production data changes, or scope-expanding dependency changes.

## 4. Layering and request lifecycle

Routes should **authenticate → authorize → validate → call service → return response**. Keep business rules out of templates and avoid large route handlers.

- **Routers:** HTTP parsing, dependencies, status codes, redirects, and response serialization.
- **Schemas:** Validate types, lengths, formats, ranges, and allowed values.
- **Services:** Business rules, workflow transitions, transaction coordination, and audit events.
- **Repositories/queries:** Shared, optimized data-access operations where useful.
- **Models:** Columns, relationships, constraints, and indexes.
- **Templates/JavaScript:** Presentation and interaction only; never enforce security or authoritative business rules.

Use one clear transaction boundary per use case. Roll back on failure. Keep audit events for sensitive mutations in the same transaction when possible. Use UTC-aware timestamps in storage and convert to the configured display timezone (`Asia/Phnom_Penh` by default) at the UI boundary.

## 5. Core data model and table plan

Inspect the actual schema before adding tables. Prefer normalized relational data, explicit foreign keys, constraints, and documented deletion behavior. Use plural `snake_case` names and consistent `created_at`/`updated_at` fields where appropriate. Use Alembic migrations for schema evolution; do not rely on `create_all()` as a production migration strategy.

### Recommended core tables

| Table | Purpose | Important fields / rules |
|---|---|---|
| `users` | Login identities and account status | `id`, `username`, `email`, `password_hash`, `role_id`, `is_active`, `last_login_at` |
| `roles` | Named access roles | `id`, `name` unique, description |
| `permissions` | Fine-grained capabilities if needed | `id`, `key` unique, description |
| `role_permissions` | Role-to-permission mapping | `role_id`, `permission_id`, unique pair |
| `employees` | Employee profile and employment state | `employee_code` unique, name, contact fields, `department_id`, `user_id` optional, status, hire/termination dates |
| `departments` | Organization structure | `name` unique as business rules require, manager reference optional |
| `shifts` | Shift definitions | name, start/end times, grace period, overnight flag, active status |
| `employee_shifts` | Effective-dated shift assignment | employee, shift, start/end dates; prevent conflicting assignments |
| `attendance_records` | Check-in/out and attendance result | employee, timestamp, event type, source, status, correction reference, actor/device |
| `attendance_corrections` | Reviewed corrections with reason | record, requested values, reason, requester, reviewer, decision timestamps |
| `leave_types` | Annual/sick/other leave categories | name, paid flag, policy settings |
| `leave_requests` | Leave workflow | employee, type, start/end dates, reason, status, reviewer, decision time |
| `holidays` | Organization holidays | date, name, scope, optional department |
| `biometric_templates` | Restricted biometric template storage | employee, encrypted/protected template, model/version metadata, enrollment status |
| `biometric_consents` | Consent and withdrawal records | employee, purpose, notice version, consent status, timestamps |
| `devices` | Registered attendance terminals/cameras | name, identifier, location, status, last_seen_at; store secrets securely |
| `notifications` | In-app notices | recipient, type, title/body keys, read status, created time |
| `audit_logs` | Append-only security/business event history | actor, action, entity type/id, outcome, request ID, timestamp, safe metadata |
| `system_settings` | Controlled application settings | unique key, typed/validated value, updated by/time |
| `sessions` | Server-side sessions if this strategy is used | hashed session token, user, expiry, revocation time |
| `refresh_tokens` | Only if token-based auth is implemented | hashed token, user, expiry, rotation/revocation metadata |

Do not create every table automatically. Add tables when the feature is in scope, and keep the data model as simple as the real requirements allow. Avoid storing redundant employee fields in attendance rows; store immutable snapshots only when legally or operationally necessary.

### Database standards

- Primary keys: use a consistent type; UUIDs may be appropriate for public identifiers, while integer keys can remain for existing internal records.
- Add foreign keys and deliberate `ON DELETE` behavior. Prefer `RESTRICT` for historical/business records; use `CASCADE` only when deletion is safe and intended.
- Add `NOT NULL`, `UNIQUE`, `CHECK`, and foreign-key constraints for rules that must always hold.
- Use `Numeric`/decimal for money, not binary floating-point. Use appropriate date/time types and timezone-aware timestamps.
- Store password hashes only. Never store plaintext passwords, raw session tokens, or unnecessary biometric images.
- Use Alembic migrations with reviewable upgrade/downgrade steps. Back up before production migrations and test migrations on a copy/staging database.
- Keep seed data development-only. Never create known demo credentials in production.
- Avoid hard deletes for employees with attendance history. Use deactivation/soft deletion when appropriate and define retention rules.

## 6. Fast data entry and retrieval

Fast operations should come from efficient queries and clear workflows, not from skipping validation.

### List/table requirements

All large lists should support, where relevant:

- Server-side pagination with a sensible default (for example 25 rows) and selectable page sizes with a safe maximum.
- Search across explicitly selected fields, using parameterized queries.
- Filters for status, department, date range, shift, and other relevant dimensions.
- Allow-listed sorting; never pass arbitrary client input into SQL identifiers.
- Stable ordering with a unique tie-breaker to prevent duplicate/missing rows between pages.
- Debounced search in the UI, request cancellation or stale-response protection, and clear loading/error states.
- Query-string persistence for search, filters, sort, and page so a view can be bookmarked.
- Empty state, no-results state, retry state, and permission-denied state.
- Bulk actions only when authorized, with a confirmation step and an audit trail.

### Database performance rules

- Add indexes for common filters, joins, foreign keys, and sort columns after checking real query patterns.
- Consider composite indexes such as `(attendance_date, employee_id)` or `(department_id, status)` only when query plans support them.
- Use database-side `COUNT`, `GROUP BY`, and date aggregation for dashboards; do not load entire tables to calculate totals.
- Prevent N+1 queries with appropriate eager loading and explicit projections.
- Select only fields required by the page. Avoid returning biometric templates or sensitive fields in general employee queries.
- Use `EXPLAIN ANALYZE` on slow PostgreSQL queries with representative data. Measure before adding caching.
- Configure connection pooling and timeouts appropriately for the deployment platform. Handle transient database errors safely.
- Use caching only for safe, frequently reused data; define invalidation rules and never let cache bypass authorization.
- Use bulk inserts/updates for genuine bulk workflows, but validate each item and report partial failures clearly.

### Attendance correctness

- Define the business timezone and attendance-day boundary explicitly.
- Prevent duplicate check-ins and invalid check-out sequences with service-level rules and, where feasible, database constraints/idempotency keys.
- Keep the original event and correction history; do not silently overwrite attendance evidence.
- Store source (`manual`, `scanner`, `device`, etc.), actor, timestamp, and correction reason.
- Make duplicate scan suppression configurable and concurrency-safe.
- Define handling for overnight shifts, missing punches, grace periods, holidays, leave, and late/early calculations before implementing reports.

## 7. Authentication, authorization, and application security

Use defense in depth and follow current OWASP guidance appropriate to the deployed application.

### Authentication and sessions

- Hash passwords with Argon2id (preferred) or a maintained bcrypt implementation with a strong cost.
- Use generic login errors and rate-limit failed attempts by account and source. Avoid account enumeration.
- Enforce secure password reset and account recovery flows if implemented.
- Generate session secrets with a cryptographically secure random generator. Never invent fallback production secrets.
- Use `HttpOnly`, `Secure` in production, and suitable `SameSite` cookie settings. Rotate sessions after login and privilege changes; expire idle and absolute sessions.
- Invalidate the server-side session on logout and account revocation.
- Require MFA for privileged users when supported by deployment requirements.

### Authorization

- Deny by default. Centralize role/permission definitions and use server-side checks on every protected page, API, export, and object.
- Apply object-level checks to prevent IDOR: verify that the actor may access the specific employee, record, department, or export.
- Hiding a menu item is a usability feature, never an authorization control.
- Prevent an administrator from removing their own access when it would leave the system without an active administrator.
- Test every role against both allowed and forbidden actions.

### Web and API defenses

- CSRF protection for every state-changing cookie-authenticated request; `GET` must not mutate state.
- Use SQLAlchemy queries or bound parameters; never interpolate user input into SQL.
- Keep Jinja2 autoescaping enabled. Avoid `|safe` for user-controlled values; use safe JSON serialization for script data.
- Validate input on the server using allow-lists, length limits, type checks, and domain rules.
- Validate redirect destinations against an allow-list or same-origin relative paths.
- Set appropriate security headers, including a restrictive Content Security Policy, frame protection, MIME sniffing protection, and a suitable Referrer Policy.
- Configure trusted hosts, CORS only if needed, request size limits, timeouts, and HTTPS at the reverse proxy.
- Do not expose stack traces, SQL errors, secrets, internal file paths, or biometric data in client responses.
- Rate-limit login, scan, export, and other abuse-prone endpoints.
- Keep dependencies patched and review security advisories.

### Uploads and exports

- Enforce file-size and request limits; allow only necessary formats.
- Verify actual file content by decoding it, not only by trusting filename or MIME type. Generate server-side filenames and store uploads outside the public web root.
- Re-encode images where appropriate to remove EXIF/GPS metadata. Reject malformed or decompression-bomb files.
- Authorize exports separately, apply date/row limits, and audit sensitive downloads.
- Protect CSV exports against spreadsheet formula injection; escape cells beginning with formula-triggering characters.
- Do not put private data or credentials in URLs, browser logs, analytics, or error messages.

## 8. Biometric privacy and responsible use

Facial templates are highly sensitive biometric data. Treat facial matching as probabilistic, not infallible.

- Obtain and record informed consent where required; provide a clear notice describing purpose, retention, access, and withdrawal.
- Provide a non-biometric attendance alternative and a way to correct false matches or missed matches.
- Use biometric data only for the approved attendance/identity purpose. Do not repurpose it for emotion inference, surveillance profiling, or unrelated monitoring.
- Minimize collection. Process camera frames in memory and discard them unless a separately approved, documented purpose requires retention.
- Restrict template access to the biometric service and specifically authorized operators. Never return embeddings through normal APIs, HTML, logs, analytics, or exports.
- Protect templates at rest and in transit; assess encryption/key management and database access controls. Store model/version metadata needed for controlled re-enrollment.
- Support template deletion and consent withdrawal, subject to applicable legal retention requirements. Keep only the minimum non-biometric audit evidence necessary to document the action.
- Define retention periods, access reviews, incident response, and breach notification procedures before production use.
- Evaluate accuracy across relevant lighting, camera, skin-tone, age, accessibility, and environmental conditions. Measure false-acceptance and false-rejection rates with representative consented test data.
- Do not claim “zero false positives” or assume a universal similarity threshold is safe. Calibrate thresholds using documented validation, monitor errors, and require human review for consequential disputes.
- Basic face detection is not proof of liveness. Do not describe a quality check as anti-spoofing unless a validated liveness mechanism exists.

## 9. Face pipeline and camera UI

Maintain the existing YuNet/SFace implementation unless a measured issue justifies change.

1. Validate frame size, type, and request rate.
2. Detect face and landmarks.
3. Apply quality checks for size, blur, lighting, and detection confidence.
4. Align/crop using the model's documented input requirements.
5. Generate and normalize the embedding.
6. Compare only with authorized, active enrolled templates.
7. Apply a validated threshold and duplicate-scan cooldown.
8. Record a minimal attendance event and safe audit metadata.
9. Return a clear match, no-match, unavailable, or error state.

Load ONNX models once at startup where practical. Handle missing model files without crashing unrelated pages. Protect native inference calls from unsafe concurrent access if required by the runtime. Never trust client-supplied identity, similarity score, attendance status, or employee ID as proof of a match.

For mirrored camera previews, mirror the video only. Keep overlay canvas text readable and transform bounding-box coordinates mathematically to align with the preview. Handle camera permission denial, missing devices, insecure-origin restrictions, loading, camera disconnect, and model-unavailable states. Stop media tracks when leaving the scanner page.

## 10. UI/UX design system

Aim for a clean, calm, professional operations interface. Use consistent spacing, typography, surface colors, borders, icons, button sizes, form patterns, and status labels. Avoid unnecessary glow, animation, excessive gradients, oversized empty dashboards, and decorative effects that slow daily work.

### Layout

- Shared sidebar, top navigation, page title, breadcrumbs where useful, and consistent content width.
- Dashboard cards should answer real operational questions: present today, absent, late, pending approvals, and recent activity.
- Keep primary actions visible and predictable. Put secondary/destructive actions in menus or clearly separated areas.
- Use responsive layouts for desktop, tablet, and mobile; tables may scroll horizontally or switch to compact cards on narrow screens.
- Use confirmation dialogs for destructive or consequential actions, and show success/error feedback near the relevant workflow.

### Data tables

- Clear column headings, compact but readable rows, consistent alignment, and visible status badges with text (not color alone).
- Keep key fields first; place actions in a consistent final column.
- Include search, filters, sort indicators, pagination, total result count, and a reset-filters action where relevant.
- Preserve filter state after edits and navigation where practical.
- Provide skeleton/loading state, empty state, error/retry state, and clear validation messages.
- Do not load huge datasets into the browser. Avoid making every row contain many heavy dropdowns or modals; use reusable forms and fetch details on demand.
- Support keyboard navigation and accessible labels.

### Forms and fast data entry

- Group related fields and use sensible tab order, labels, required indicators, inline validation, and helpful examples.
- Preserve valid input after validation failure. Disable duplicate submissions while saving.
- Use autocomplete only where it improves speed and protects sensitive data; ensure it is keyboard accessible.
- For bulk import, validate a preview before committing, show row-level errors, and provide a downloadable error report.
- Use clear confirmation and undo/reversal workflows where possible instead of irreversible actions.

### Themes and accessibility

- Support the existing light and dark themes using centralized CSS variables.
- Target WCAG 2.1 AA contrast and keyboard accessibility. Do not rely on color alone to convey status.
- Respect reduced-motion preferences. Provide focus indicators and accessible names for icon-only controls.
- Use a fallback for missing avatars and broken images.
- Avoid uppercase transforms and wide letter spacing on Khmer script. Use appropriate Khmer-capable fonts such as Kantumruy Pro, Battambang, or Noto Sans Khmer.
- Test both languages for clipping, line wrapping, date/number formatting, table widths, and long labels.

## 11. English and Khmer localization

- Use language routes `/en/...` and `/kh/...` consistently.
- Keep all user-facing strings in the translation dictionary or an established localization layer; do not hardcode text in new templates or JavaScript.
- Every new key must exist in both English and Khmer. Keep keys semantically consistent.
- Preserve the selected language in redirects, validation errors, forms, modals, notifications, and exports where appropriate.
- Translate statuses, table headings, button labels, empty states, errors, confirmation text, date labels, and accessibility text.
- Never apply uppercase or letter-spacing styling that damages Khmer typography.
- Use a safe, consistent date/time and number format and display the active timezone when it affects attendance interpretation.

## 12. API and error conventions

Use predictable resource-oriented routes and appropriate HTTP methods/status codes. Existing route patterns may remain for compatibility.

- `200` successful read/update; `201` created; `204` successful no-content delete where appropriate.
- `400` malformed request; `401` unauthenticated; `403` forbidden; `404` not found; `409` conflict; `413` payload too large; `422` validation failure; `429` rate limited; `500` unexpected error; `503` temporary dependency unavailable.
- Return stable error codes and safe messages. Do not expose internal exception details.
- Use Pydantic schemas for request and response shapes. Do not serialize ORM objects indiscriminately.
- Keep pagination metadata consistent, such as `items`, `page`, `page_size`, `total`, and `pages`.
- Make retryable mutations idempotent where practical, especially attendance device events and imports.
- Preserve existing API contracts unless a versioned change is planned.

## 13. Logging, audit, and observability

- Use structured logs with timestamp, level, request ID, route, status, duration, and actor ID where safe.
- Never log passwords, session tokens, raw biometric templates, full sensitive payloads, or secrets.
- Add a request/correlation ID and propagate it through logs and audit events.
- Audit sensitive actions: account/role changes, employee changes, attendance corrections, biometric enrollment/deletion, exports, settings changes, and failed privileged operations.
- Audit logs should be append-only through normal application workflows. Restrict database-level alteration and define retention/archival controls.
- Monitor application errors, slow requests, failed logins, database pool exhaustion, model failures, and repeated scan errors.
- Provide user-friendly error pages and actionable operator logs without leaking internal details to users.

## 14. Testing and quality gates

Use the test framework already established in the repository; add pytest if approved and appropriate.

- **Unit tests:** service rules, validation, date/shift calculations, translation keys, permission helpers.
- **Integration tests:** routes, database constraints, transactions, migrations, uploads, and audit records.
- **Security tests:** unauthenticated access, RBAC matrix, IDOR, CSRF, session expiry, rate limits, injection/XSS handling, unsafe uploads, and export permissions.
- **UI/E2E tests:** core flows, mobile layout, keyboard navigation, theme switching, and English/Khmer parity.
- **Performance tests:** large employee/attendance lists, dashboard aggregates, and search under representative data volumes.
- **Biometric validation:** controlled, consented test datasets; report false-acceptance/false-rejection rates and limitations.

Before completing a change, run focused tests and the existing full test suite. Test PostgreSQL behavior for production-critical schema/query changes; SQLite tests alone are not sufficient evidence of PostgreSQL compatibility. Do not claim passing tests unless commands were actually executed and passed.

## 15. Configuration and deployment

Use environment variables validated at startup. Keep `.env`, database files, uploads, model weights where appropriate, secrets, and generated reports out of Git.

Typical settings include:

- `APP_ENV`, `SECRET_KEY`, `DATABASE_URL`
- `ALLOWED_HOSTS`, trusted proxy configuration
- session idle/absolute timeout settings
- `DEFAULT_LANG`, `BUSINESS_TIMEZONE`
- upload/request size limits
- login and API rate limits
- biometric model paths and validated matching configuration
- logging level and retention settings

Fail safely when required production configuration is missing. Never use a hard-coded production secret or development credentials in production. Use TLS, secure cookies, database TLS, least-privilege database credentials, managed secret storage where available, backups, restore tests, health checks, and a documented rollback plan. Run behind a supported production ASGI process manager and reverse proxy. Camera access requires a secure browser context (HTTPS or localhost).

## 16. Git and change management

- Keep `main` stable and deployable.
- Use concise commits such as `feat:`, `fix:`, `security:`, `refactor:`, `test:`, and `docs:`.
- Do not bypass tests or hooks to force a change through.
- Keep pull requests focused and describe migration, security, UI, and compatibility impacts.
- Never commit `.env`, credentials, personal data, real biometric samples, local databases, or private uploads.
- For a schema change, include migration files, rollback notes, and tests.
- For a UI change, check desktop/mobile and both languages.
- For a security-sensitive change, include negative tests and explain the threat addressed.

## 17. Forbidden patterns

- Raw SQL string interpolation or unvalidated dynamic sort/filter identifiers.
- Business rules duplicated across routes, templates, and JavaScript.
- Frontend-only authorization or trust in hidden form fields.
- Plaintext passwords, known production demo accounts, hard-coded secrets.
- Returning biometric templates or sensitive internal fields in normal responses.
- Full-table loading for search, dashboards, or reports.
- Schema changes without migrations or unreviewed destructive data operations.
- Silent attendance overwrites or untraceable manual corrections.
- Unbounded exports, uploads, queries, or inference requests.
- Broad `except:` handlers, swallowed errors, or exposing stack traces to users.
- Claiming validated liveness, perfect accuracy, or zero false positives without evidence.
- Rewriting the whole application or changing stacks without explicit approval.

## 18. Definition of done

A task is complete only when applicable items are satisfied:

- [ ] Requirements and edge cases are implemented.
- [ ] Existing behavior and user changes are preserved.
- [ ] Authentication, role checks, and object-level authorization are correct.
- [ ] Validation, transactions, constraints, and audit events are handled.
- [ ] Migrations are included and safely reviewed for schema changes.
- [ ] Search, pagination, filtering, and indexes are appropriate for large datasets.
- [ ] UI is clean, responsive, accessible, and has loading/empty/error states.
- [ ] English and Khmer strings are complete and visually checked.
- [ ] Biometric privacy and alternative attendance paths are respected.
- [ ] Relevant tests run and results are reported honestly.
- [ ] No secrets or sensitive test data were added to Git.
- [ ] Documentation and setup instructions reflect the actual implementation.

## 19. Implementation priority

When asked to improve the system, prioritize in this order unless the owner specifies otherwise:

1. **Critical security/data integrity:** authentication, authorization, CSRF, migrations, backup/restore, attendance correctness.
2. **Core workflows:** employee/department CRUD, shifts, attendance, correction approvals, leave, holidays, reports.
3. **Fast data access:** indexed server-side search, filters, pagination, efficient aggregates, import validation.
4. **Clean UI:** reusable tables/forms, responsive layout, clear states, bilingual parity.
5. **Operational maturity:** audit visibility, notifications, monitoring, performance tests, deployment hardening.
6. **Optional enhancement:** advanced analytics and biometric improvements only after privacy, accuracy, and fallback workflows are validated.

Do not add complexity just to appear enterprise-grade. Implement only what the project needs, in small, testable steps.

## 20. Reference notes

The current repository may still use a simpler structure or contain unfinished hardening items. Treat this guide as the target standard, not proof that each control already exists. Verify the code before reporting compliance. Keep this document updated when the actual architecture or approved requirements change.
