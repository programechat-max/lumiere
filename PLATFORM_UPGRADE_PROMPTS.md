🎯 LUMIERE - Multi-User Platform Upgrade Guide
Comprehensive Analysis & Development Prompts
📋 PROJECT OVERVIEW
Current State: Single-user fitness/wellness AI coach platform with:

✅ React + Vite frontend

✅ FastAPI backend

✅ SQLAlchemy ORM + SQLite

✅ Gemini AI integration

✅ iOS support (Capacitor)

✅ iOS App Notification System (Local & APNs Push)

✅ Basic authentication (JWT)

✅ Workout tracking & muscle heatmap

✅ Nutrition planning & logging

✅ User memory system (AI personalization)

Target: Enterprise-grade multi-user SaaS platform with security, scalability, monitoring, and compliance.

🔴 CRITICAL ISSUES TO ADDRESS
1. Security Vulnerabilities
⚠️ CORS configured with allow_origins=["*"] (production risk)

⚠️ Password hashing uses passlib/bcrypt (outdated pattern)

⚠️ No rate limiting on auth endpoints (brute force risk)

⚠️ File uploads not validated (video/audio could contain malware)

⚠️ No HTTPS enforcement mentioned

⚠️ Secrets stored in .env (no vault integration)

2. Data & Infrastructure Issues
⚠️ SQLite database (not suitable for concurrent users)

⚠️ No database transactions/rollback mechanisms

⚠️ No connection pooling configured

⚠️ Single server deployment (no load balancing)

⚠️ No caching layer (Redis/Memcached)

⚠️ Gemini API calls not rate-limited or cached

3. User Management Issues
⚠️ No user roles/permissions system

⚠️ No subscription/billing management

⚠️ No user data isolation verification

⚠️ No audit logging

⚠️ Notification dispatches tied to synchronous backend requests

4. Scalability Issues
⚠️ File uploads stored locally (should use S3/cloud storage)

⚠️ No async task queue (Celery/Bull)

⚠️ No background job scheduling

⚠️ No API versioning

⚠️ No request/response pagination

⚠️ Push notification delivery runs inline (blocking)

5. Monitoring & Operations
⚠️ Logging configured but no structured logging

⚠️ No error tracking (Sentry integration)

⚠️ No performance monitoring

⚠️ No health checks

⚠️ No graceful shutdown

✅ DETAILED UPGRADE PROMPTS
PROMPT 1: Database Migration (SQLite → PostgreSQL)
You are upgrading a FastAPI fitness platform from SQLite to PostgreSQL.

CURRENT STATE:
- Database: SQLite (backend/database.py)
- ORM: SQLAlchemy with 11 tables (User, UserProfile, WorkoutProgram, Exercise, 
  WorkoutLog, NutritionLog, BodyMetric, UserMemory, ChatMessage, DailyCheckIn, 
  MealPlanItem)
- Connection: Direct connection in get_db()

REQUIREMENTS:
1. Create PostgreSQL setup:
   - Docker Compose config for local dev (postgres:16-alpine + pgAdmin)
   - Connection string management (dev/test/prod configs)
   - Environment variables for DB credentials
   
2. Implement connection pooling:
   - Use SQLAlchemy's create_engine with pool_size=20, max_overflow=40
   - Connection pool monitoring (track active/idle connections)
   - Retry logic for transient connection failures
   
3. Database schema improvements:
   - Add database indexes for frequent queries (user_id, date filters)
   - Add constraints (unique, foreign key cascade options)
   - Document schema with comments
   - Create migration script (SQLAlchemy Alembic)
   
4. Data integrity:
   - Wrap all mutations in transactions with proper rollback
   - Add decimal types for monetary/caloric values (not float)
   - Add created_at/updated_at timestamps to all tables
   - Add soft-delete support (is_deleted column)
   
5. Testing:
   - Unit tests using pytest + TestClient with in-memory SQLite
   - Integration tests with real PostgreSQL (Docker test container)
   - Migration testing (schema before/after validation)

DELIVERABLES:
- docker-compose.yml with postgres + pgAdmin
- Updated database.py with pooling & retry logic
- Alembic migration scripts
- Updated requirements.txt (psycopg2/asyncpg)
- Migration guide for production deployment
- Unit + integration test suite

CONSTRAINTS:
- Zero downtime migration strategy
- Maintain backward compatibility with existing SQLite data (migration tool)
- No breaking changes to ORM models

TONE: Technical, production-ready, defensive programming
PROMPT 2: Authentication & Authorization System
You are implementing enterprise-grade authentication for a multi-user SaaS platform.

CURRENT STATE:
- Auth: Basic JWT in auth.py (simple token, no refresh)
- User model: Just id, email, name, hashed_password
- No roles, permissions, or access control

REQUIREMENTS:
1. Multi-tier authentication:
   - JWT access tokens (15-min expiry)
   - Refresh tokens (7-day expiry, stored in HttpOnly cookies)
   - Email verification (on signup)
   - Optional: 2FA/MFA (TOTP, SMS backup codes)
   - Optional: OAuth2 (Google/Apple sign-in)
   
2. Authorization system:
   - Role-based access control (RBAC):
     * ADMIN: Full platform access + billing/user management
     * COACH: Can see/modify client data if assigned
     * USER: Can only access own data
     * FREE_TRIAL: Limited features
     * PREMIUM: Full features
   - Row-level security: Users can only access own data
   - Scope-based permissions: Granular endpoint protection
   
3. Security hardening:
   - Password requirements (min 12 chars, complexity rules)
   - Password hashing: Argon2 instead of bcrypt (via argon2-cffi)
   - Account lockout after 5 failed login attempts (15-min cooldown)
   - Device fingerprinting / session management
   - CSRF protection (if cookies used)
   - Rate limiting: 5 login attempts/min per IP
   
4. Session management:
   - User session table (track device, IP, last_active, user_agent)
   - Concurrent session limits (e.g., max 3 devices per user)
   - Session invalidation on logout
   - Automatic logout after 30-day inactivity
   
5. Audit logging:
   - Log all authentication events (login, logout, failed attempts, MFA)
   - Store: user_id, action, timestamp, IP, user_agent, result
   - API for viewing user's own login history
   
6. API improvements:
   - Endpoints: /api/auth/register, /api/auth/login, /api/auth/refresh, 
     /api/auth/logout, /api/auth/verify-email, /api/auth/change-password,
     /api/auth/sessions (list), /api/auth/sessions/{id}/revoke
   - Error messages: Generic ("Invalid credentials") to prevent user enumeration
   - CORS: Restrict to known frontend domains only

DELIVERABLES:
- Updated auth.py with Argon2, JWT refresh, MFA support
- models.py: Add Role, UserSession, AuditLog tables
- crud.py: Role assignment, session management operations
- main.py: New auth endpoints with validation
- Security.md: Best practices documentation
- Example .env.secure template
- Test suite: 30+ unit tests covering auth flows

CONSTRAINTS:
- Backward compatible with existing user accounts (migration script)
- GDPR compliant (right to delete, data export)
- All sensitive operations must have audit logs
- No hardcoded secrets

TONE: Security-first, paranoid but practical
PROMPT 3: Subscription & Billing System
You are implementing Stripe-based SaaS billing for a fitness platform.

CURRENT STATE:
- No subscription model
- No payment processing
- No feature gating

REQUIREMENTS:
1. Subscription models:
   - FREE: Limited features (1 meal plan/month, no AI coaching)
   - PREMIUM_MONTHLY: $14.99/month (all features, AI chat, progress tracking)
   - PREMIUM_ANNUAL: $149.99/year (20% discount)
   - COACHING: $99/month (1-on-1 coach access + premium features)
   
2. Stripe integration:
   - Setup Stripe customer database sync
   - Stripe webhooks: payment_intent.succeeded, customer.subscription.updated,
     customer.subscription.deleted, invoice.payment_failed
   - Idempotent webhook processing (prevent double-charging)
   - Subscription lifecycle: active, past_due, canceled, unpaid
   
3. Database schema:
   - Subscription table: user_id, stripe_subscription_id, plan_type, 
     status, current_period_start/end, cancel_at
   - Invoice table: stripe_invoice_id, amount, status, pdf_url
   - Payment method table: last4, exp_month/year, billing_postal_code
   - Usage tracking (for metered billing in future)
   
4. Billing endpoints:
   - GET /api/billing/subscription (current subscription)
   - POST /api/billing/subscribe (start free trial / upgrade)
   - POST /api/billing/checkout (redirect to Stripe checkout)
   - POST /api/billing/manage (Stripe customer portal)
   - GET /api/billing/invoices (list past invoices)
   - POST /api/billing/cancel (cancel subscription)
   - GET /api/billing/usage (current month usage)
   
5. Feature gating:
   - Middleware to check subscription status before endpoint access
   - Feature matrix: Define which endpoints/features per plan
   - Graceful degradation: Show "Upgrade to Premium" instead of errors
   - Trial period: 7-day free trial with feature access
   
6. Invoicing & compliance:
   - Auto-generate invoices with tax calculations
   - VAT/GST support (based on user location)
   - Downloadable PDF invoices
   - Billing email notifications
   - Refund/dispute handling documentation
   
7. Analytics:
   - MRR (monthly recurring revenue) tracking
   - Churn rate monitoring
   - Conversion funnel (free → trial → paid)
   - Dashboard: revenue, active subscriptions, failed payments

DELIVERABLES:
- models.py: Subscription, Invoice, PaymentMethod tables
- stripe_client.py: Stripe API wrapper (create subscription, process webhooks, etc.)
- main.py: 7+ billing endpoints
- webhook_handler.py: Stripe webhook processing with idempotency
- middleware.py: Subscription check middleware
- Feature gating logic (decorator + config)
- billing_service.py: Business logic (trial eligibility, trial extension, etc.)
- Test suite: Stripe webhook tests (mock + fixture-based)
- Admin dashboard: Revenue, churn, LTV metrics

CONSTRAINTS:
- PCI DSS compliance (never store full card numbers)
- GDPR: Right to delete doesn't break invoice history
- Tax calculation accuracy (use tax library like TaxJar if complex)
- Webhook security: Verify Stripe signatures

TONE: Compliance-focused, business logic clarity
PROMPT 4: File Storage & Handling (Local → Cloud)
You are migrating file uploads from local filesystem to AWS S3.

CURRENT STATE:
- Video uploads: backend/user_videos/
- Audio uploads: backend/user_audio/
- Local storage only (no backup)
- No virus scanning
- No CDN

REQUIREMENTS:
1. AWS S3 setup:
   - Create S3 bucket with versioning enabled
   - Bucket encryption at rest (SSE-S3)
   - Public access blocked (all private)
   - Lifecycle policy: Move old files to Glacier after 90 days
   - CORS configuration for browser uploads
   
2. File upload pipeline:
   - Presigned URLs for direct browser/app → S3 uploads (bypass backend)
   - File validation: Size (max 300MB), type (mp4, wav, jpg), MIME type checks
   - Virus scanning: ClamAV or VirusTotal API integration
   - File metadata: Store in DB (s3_key, size, uploaded_at, scan_status)
   
3. Upload endpoints:
   - POST /api/files/presigned-url (get S3 presigned URL)
   - POST /api/files/confirm (confirm upload complete, trigger processing)
   - GET /api/files/{file_id} (download/redirect to S3)
   - DELETE /api/files/{file_id} (delete from S3)
   - GET /api/files (list user's files with pagination)
   
4. Processing pipeline:
   - Queue upload jobs (video processing, AI analysis) using Celery + SQS
   - Video transcoding: Convert to streaming formats (HLS)
   - Thumbnail generation for videos
   - Async AI analysis (Gemini) after file validation
   - Webhook callback when processing complete
   
5. Database schema:
   - File table: id, user_id, s3_key, original_filename, size, mime_type,
     uploaded_at, processing_status, scan_status, error_message
   - Add file_id foreign key to UserMemory, WorkoutLog, etc.
   
6. Backup & disaster recovery:
   - S3 cross-region replication (backup to another region)
   - Backup retention: 30 days minimum
   - Restore procedure documentation
   
7. Performance & CDN:
   - CloudFront CDN for asset delivery
   - Cache headers for static files (1 year)
   - Signed URLs for private video streams
   
8. Monitoring:
   - Track upload success/failure rates
   - Monitor S3 costs (size, requests)
   - Alert on large/suspicious uploads

DELIVERABLES:
- aws_s3_client.py: S3 operations wrapper (upload, download, delete, presigned URLs)
- file_service.py: Business logic (validation, processing queue, metadata)
- virus_scanner.py: ClamAV/API integration
- main.py: File upload endpoints
- celery_tasks.py: Async file processing jobs
- models.py: File, FileMetadata tables
- Test suite: File upload tests (mock S3, virus scanner)
- AWS setup guide: Terraform/CloudFormation templates
- Cost estimation & monitoring dashboard

CONSTRAINTS:
- PII protection: Encrypt sensitive files with KMS
- GDPR: Right to deletion includes S3 backups (retention policy)
- Performance: Presigned URLs must not be guessable (36-char random suffix)
- Backwards compatibility: Migrate existing local files to S3

TONE: Infrastructure-focused, detail-oriented on security
PROMPT 5: Async Task Queue & Job Scheduling
You are implementing Celery + Redis for background job processing and iOS Push Notifications.

CURRENT STATE:
- Push notification delivery runs inline (blocking)
- AI processing (Gemini) runs synchronously
- Large file processing blocks requests
- Weekly analysis job runs inline or not at all
- No retry logic for failed operations

REQUIREMENTS:
1. Redis setup:
   - Docker Redis container (dev) + Redis Cloud / ElastiCache (prod)
   - Connection pooling
   - Key expiration policies
   
2. Celery configuration:
   - Task routing (specific queues for different priorities)
   - Retry logic: Exponential backoff (3s, 9s, 27s max 3x)
   - Task timeouts: 30s for fast tasks, 5min for AI processing
   - Dead letter queue for permanent failures
   
3. Task queue jobs:
   - analyze_video (user onboarding) - HIGH priority, 5min timeout
   - analyze_food_photo (meal logging) - MEDIUM priority
   - generate_ai_meal_plan - MEDIUM priority, 3min timeout
   - generate_ai_workout_program - MEDIUM priority, 3min timeout
   - weekly_analysis_report (every Monday 9am) - LOW priority
   - send_email_notification - HIGH priority, 1min timeout
   - process_workout_video (transcoding) - MEDIUM priority, long timeout
   - send_ios_push_notification - HIGH priority, 30s timeout
   - export_user_data (for GDPR) - LOW priority, 10min timeout
   
4. Database updates for job tracking:
   - Add job_status table: task_id, user_id, job_type, status, 
     progress_percent, error_message, created_at, completed_at
   - Track progress for long-running jobs
   
5. iOS Push Notification pipeline:
   - Move notification dispatch to async APNs queue via Celery
   - Decouple push dispatches from core FastAPI endpoints
   - Handle APNs tokens and batch notification delivery asynchronously
   - Retry failed push dispatches (max 3 times)
   
6. Frontend integration:
   - WebSocket for real-time job progress updates (optional)
   - Polling endpoint: GET /api/jobs/{task_id} (status, progress, result)
   - Optimistic UI: Show progress bar during job execution
   
7. Monitoring & observability:
   - Flower dashboard for Celery monitoring
   - Task execution metrics (duration, success rate, failures)
   - Alert on task failures (email to admin)
   - Dead letter queue inspection & replay
   
8. Production deployment:
   - Celery worker scaling (auto-scale based on queue length)
   - Worker health checks (liveness probe)
   - Graceful shutdown (finish in-flight tasks)
   - Log aggregation for worker logs

DELIVERABLES:
- celery_config.py: Celery app setup, broker/backend config
- tasks.py: All task definitions with retry/timeout logic
- job_service.py: Job status tracking, progress updates
- main.py: Updated endpoints to use Celery (no blocking)
- apns_service.py: APNs push notification handler via task queue
- models.py: JobStatus table
- docker-compose.yml: Redis + Celery worker services
- flower_config.py: Flower dashboard setup
- Test suite: Mock Celery tasks, retry logic tests
- Monitoring & alerting setup
- Production deployment guide (worker scaling)

CONSTRAINTS:
- Idempotent tasks (safe to retry)
- No circular task dependencies
- Task results expire after 24 hours (save persistent results to DB)
- Celery worker separate from FastAPI process

TONE: Architecture-focused, operational excellence
PROMPT 6: API Versioning, Pagination & Rate Limiting
You are implementing production-grade API design patterns.

CURRENT STATE:
- No API versioning
- Endpoints: GET /api/workout, /api/nutrition, etc. (hardcoded)
- No pagination (returns all records)
- No rate limiting
- No request/response logging

REQUIREMENTS:
1. API versioning:
   - URL path versioning: /api/v1/*, /api/v2/* (future-proof)
   - Support v1 indefinitely (5+ years)
   - Deprecation headers: Deprecation, Sunset, Link
   - Version negotiation in header (fallback to URL version)
   - Documentation: Migration guide v1→v2
   
2. Pagination:
   - Standard: limit, offset (default: limit=50, max=1000)
   - Cursor-based pagination for time-series (created_at cursor)
   - Response format: { data: [...], total: 1234, limit: 50, offset: 0 }
   - Apply to: nutrition logs, workout logs, chat history, invoices
   
3. Rate limiting:
   - Per-user rate limits (based on subscription tier):
     * FREE: 10 requests/min, 100/hour
     * PREMIUM: 100 requests/min, unlimited/hour
     * COACHING: Unlimited
   - Per-IP rate limits: 1000 requests/min (prevent DDoS)
   - Use Redis for distributed rate limiting
   - Return headers: X-RateLimit-Limit, X-RateLimit-Remaining, X-RateLimit-Reset
   - Graceful fallback: 429 Too Many Requests with retry-after
   
4. Request/response design:
   - Consistent error format: { error: { code: "INVALID_INPUT", message: "...", details: {} } }
   - Request IDs: X-Request-ID header (for debugging)
   - Content negotiation: Accept: application/json (ignore others)
   - Compression: gzip for responses > 1KB
   - Cache headers: Vary, Cache-Control, ETag
   
5. Logging & observability:
   - Structured logging (JSON format):
     { timestamp, request_id, user_id, method, path, status, duration_ms, 
       query_params, error_message }
   - Log levels: DEBUG (dev), INFO (normal), WARN (degradation), ERROR (failure)
   - Sample logging: 100% for errors, 5% for normal requests (configurable)
   - Exclude sensitive paths: Don't log password, token, payment data
   - ELK stack integration (for production)
   
6. Response filtering:
   - Allow clients to select fields: ?fields=name,email,created_at
   - Exclude sensitive fields by default (hashed_password, stripe_secret)
   - Role-based field filtering (ADMIN sees more than FREE users)
   
7. Error handling:
   - Standardized HTTP status codes:
     * 200 OK, 201 Created, 204 No Content
     * 400 Bad Request, 401 Unauthorized, 403 Forbidden, 404 Not Found
     * 409 Conflict (duplicate), 422 Unprocessable Entity
     * 429 Too Many Requests, 500 Internal Server Error
   - Never expose stack traces to clients (log internally only)
   - Predictable error codes for client-side handling

DELIVERABLES:
- apiversion.py: FastAPI dependency for version handling
- pagination.py: Pagination logic, cursor support
- ratelimit.py: Rate limiting middleware (Redis-backed)
- logging_config.py: Structured logging setup
- middleware.py: Request ID, response compression, CORS by version
- schemas.py: Updated response models with pagination
- main.py: Refactored endpoints with versioning (/api/v1/*)
- error_handlers.py: Exception handlers with consistent format
- Test suite: Rate limiting tests, pagination tests, version tests
- Documentation: API design guide, versioning strategy

CONSTRAINTS:
- Backward compatibility: Support v1 for 5 years minimum
- Rate limit data (Redis keys) persist correctly under load
- Pagination must be efficient (don't count total records for cursor pagination)
- No performance degradation from logging/tracing

TONE: API design clarity, developer experience focus
PROMPT 7: Monitoring, Error Tracking & Observability
You are implementing production monitoring for a SaaS platform.

CURRENT STATE:
- Basic Python logging
- No error tracking
- No performance monitoring
- No health checks
- No alerting

REQUIREMENTS:
1. Error tracking (Sentry):
   - Setup Sentry project for production
   - Capture all unhandled exceptions
   - Custom error context: user_id, subscription_tier, endpoint
   - Ignore expected errors (404s, client errors)
   - Alert on: spike in errors, specific error type, 401/403 patterns
   - Release tracking (tie errors to code version)
   
2. Performance monitoring (New Relic or DataDog):
   - Track endpoint response times (p50, p95, p99)
   - Database query performance (slow queries alert >1s)
   - Celery task duration & failure rates
   - Gemini API latency (per-user, aggregate)
   - Memory usage per worker process
   - Alert thresholds: Response >500ms, Error rate >1%, CPU >80%
   
3. Health checks:
   - GET /health (liveness): Returns 200 if service running
   - GET /ready (readiness): Returns 200 if DB connected + healthy
   - Checks: DB connectivity, Redis connectivity, Gemini API reachable
   - Include: version, uptime, dependencies status
   - Used by load balancer for auto-recovery
   
4. Metrics collection:
   - Custom metrics:
     * Active users (concurrent)
     * API requests per endpoint per hour
     * Subscription conversions (trial → paid)
     * Payment failures / retry attempts
     * AI generation success rate
     * File upload failures / virus detections
   - Prometheus format export: /metrics endpoint
   - Grafana dashboards: Revenue, API health, user growth
   
5. Logging infrastructure:
   - ELK stack (Elasticsearch, Logstash, Kibana):
     * Centralized log aggregation
     * Full-text search on logs
     * Log retention: 30 days
     * Alert on specific log patterns
   - Alternative: CloudWatch (AWS) or Datadog logs
   
6. Uptime monitoring:
   - Synthetic monitoring: Ping /health every 60s from multiple regions
   - Check critical flows: signup → login → create plan
   - Alert on: Service down >5min, slow response >2s
   
7. Alerting:
   - Channels: Slack, PagerDuty, Email
   - Alert rules:
     * Error rate > 1% for 5min
     * Response time p95 > 2s
     * Database connection pool exhausted
     * Celery queue depth > 1000 jobs
     * Failed Stripe webhook 3+ times
   - Runbooks: What to do when alert fires
   
8. Security monitoring:
   - Failed login attempts > 10 per IP per hour
   - Suspicious file uploads (malware, oversized)
   - Rate limit abuse patterns
   - Unusual data access patterns
   - Unauthenticated requests to protected endpoints

DELIVERABLES:
- sentry_config.py: Sentry setup with DSN, environment config
- metrics.py: Prometheus metrics collection
- health_check.py: Liveness/readiness endpoints
- monitoring_middleware.py: Request timing, error tracking
- alerts.py: Alert rules definition
- grafana_dashboards.json: Pre-built dashboards
- elk_docker_compose.yml: ELK stack setup
- main.py: Integrated monitoring middleware, /health endpoint
- Test suite: Health check tests, metrics export tests
- Runbook.md: Incident response procedures
- Monitoring setup guide

CONSTRAINTS:
- Zero overhead for healthy requests (efficient instrumentation)
- No PII in logs (filter before sending to external services)
- Backward compatibility: Add monitoring to existing endpoints
- Cost optimization: Sample non-critical metrics (5% of normal requests)

TONE: Production reliability, operational discipline
PROMPT 8: Frontend Security & State Management
You are hardening the React frontend for production use.

CURRENT STATE:
- Basic React + Vite setup
- localStorage for token storage (XSS risk)
- No input validation
- No CSP headers
- Axios/fetch without security headers
- No encryption for sensitive data

REQUIREMENTS:
1. Authentication hardening:
   - Move tokens from localStorage to HttpOnly cookies (Secure flag)
   - CSRF protection: Double-submit cookie pattern
   - Authorization header: Always include Bearer token
   - Handle 401 responses: Redirect to login, refresh token
   
2. Input validation & sanitization:
   - Validate all user inputs (email, password, numbers, dates)
   - Sanitize HTML inputs (prevent XSS): DOMPurify library
   - File uploads: Check MIME type + file extension on client
   - Never trust server responses - validate against schema
   
3. Secure HTTP headers:
   - Content-Security-Policy (CSP): Restrict script sources
   - X-Content-Type-Options: nosniff
   - X-Frame-Options: DENY (prevent clickjacking)
   - X-XSS-Protection: 1; mode=block
   - Strict-Transport-Security: max-age=31536000
   - Implement via backend CORS headers
   
4. State management:
   - Replace localStorage with secure state (in-memory + encrypted session storage)
   - Redux/Zustand for centralized state
   - Encrypt sensitive state (subscription_tier, payment info) before storage
   - Clear sensitive state on logout
   - Prevent state leaks in console/devtools
   
5. API client security:
   - Axios wrapper with automatic token refresh
   - Timeout on all requests (30s default)
   - Retry logic for transient failures (exponential backoff)
   - Error handling: Show user-friendly messages (hide backend details)
   - Request interceptor: Inject request ID, timestamp
   
6. Error handling:
   - Catch and log errors (to Sentry)
   - Display user-friendly error messages
   - Don't expose stack traces or API URLs
   - Handle network errors gracefully
   
7. Performance & bundle security:
   - Dependency vulnerability scanning: npm audit, Snyk
   - Code splitting: Lazy-load routes, reduce bundle size
   - Minification: Remove debugging info
   - CSP nonce for inline scripts
   
8. Data sensitivity:
   - Blur password inputs (no copy-paste)
   - Auto-logout after 15min inactivity
   - Disable dev tools in production (optional)
   - Prevent localStorage inspection (encrypt sensitive data)

DELIVERABLES:
- auth_service.js: Token management (cookies, refresh logic)
- api_client.js: Secured Axios wrapper
- validators.js: Input validation functions
- sanitizer.js: XSS prevention utilities
- useAuth.js hook: Authentication state management
- useProtectedRoute.js: Route protection wrapper
- error_handler.js: Global error handling
- security.md: Frontend security practices
- .env.example: CSP, API endpoint config
- Test suite: Input validation tests, auth flow tests
- Dependency scanning setup (Snyk GitHub action)

CONSTRAINTS:
- No hardcoding of sensitive values in code
- SSR compatibility (if adding server-side rendering later)
- Backwards compatibility with existing auth flow
- Performance: Security shouldn't add >100ms to page load

TONE: Security-first, developer UX clarity
PROMPT 9: iOS Native Push Notifications & Reminders Architecture (APNs)
You are implementing an enterprise iOS native notification and reminder system, eliminating external messaging bots completely.

CURRENT STATE:
- All reminders and alerts must strictly originate from and deliver to the native iOS app
- Basic Capacitor / Local Notifications setup (unscalable, single-device dependent)
- No server-driven APNs push delivery pipeline
- No multi-device push token management per user

REQUIREMENTS:
1. APNs (Apple Push Notification service) Backend Architecture:
   - Secure HTTP/2 APNs connection using Apple `.p8` Auth Key, Team ID, and Key ID
   - Environment handling: Sandbox (dev) vs Production APNs gateways
   - Support for APNs payload specs: alert titles, bodies, badges, sound, custom categories, deep link URIs, and thread-IDs for notification grouping

2. Device Token Management:
   - User Device Token Registry: Allow users to log in across multiple iOS devices
   - Endpoints:
     * `POST /api/v1/notifications/devices` (Register APNs token + device metadata)
     * `DELETE /api/v1/notifications/devices/{token}` (Unregister token on logout/uninstall)
   - Token lifecycle management: Automatically handle invalid/expired tokens returned by APNs (BadDeviceToken, Unregistered) by pruning database records

3. Notification Types & Trigger Pipeline:
   - Daily Check-in Prompts (e.g., morning reminder at 9 AM user local time)
   - Scheduled Workout Reminders (e.g., 30 minutes prior to scheduled session)
   - Weekly AI Analysis Alerts (e.g., notification when weekly report is ready)
   - Inactivity / Re-engagement Alerts (e.g., 3 days without logging meals/workouts)
   - System & Billing Alerts (e.g., payment failure, subscription auto-renew warnings)

4. Background & Celery Task Integration:
   - Asynchronous APNs dispatching via Celery worker (`send_ios_push_notification`)
   - Batch notification dispatches for scheduled tasks (APScheduler / Celery Beat)
   - Retry mechanism for transient network or Apple gateway failures (max 3 retries with exponential backoff)

5. In-App & iOS User Settings Control:
   - Database schema for Notification Preferences (user_id, daily_checkin_enabled, workout_reminders_enabled, weekly_report_enabled, quiet_hours_start, quiet_hours_end)
   - API endpoints to fetch and update push settings:
     * `GET /api/v1/notifications/settings`
     * `PUT /api/v1/notifications/settings`
   - Respect user quiet hours and timezone offsets when scheduling push tasks

6. Capacitor / Native iOS Integration:
   - Configure Capacitor Push Notifications Plugin on iOS (App Delegate configuration)
   - Request Notification Permissions gracefully (permission prompt handling)
   - Deep Linking Router: Tapping a push notification routes directly to relevant app screen (e.g., `/workout/active`, `/nutrition/daily`, `/analytics/weekly`)

7. Security & Data Isolation:
   - Payload Encryption / Sanitize sensitive PII (do not send raw personal health metrics inside unencrypted APNs alert strings)
   - Strict user ownership verification for token registration

DELIVERABLES:
- apns_client.py: Apple Push Notification HTTP/2 client wrapper
- notification_service.py: Push business logic, token lookup, preference filtering
- models.py: UserDeviceToken, NotificationSettings, PushNotificationLog tables
- routes/notifications.py: Device token registration & user preference API endpoints
- tasks.py: Celery push dispatch tasks (`send_push_notification_task`, `batch_send_scheduled_reminders`)
- scheduler.py: Celery Beat cron setup for daily/weekly notification triggers
- ios_push_guide.md: Setup guide for Xcode APNs capabilities, entitlements, and Capacitor listener code
- Test suite: APNs mock payload test, device token lifecycle unit tests, quiet hours logic tests

CONSTRAINTS:
- 100% native iOS delivery (No third-party messaging dependencies like Telegram)
- High throughput dispatches must not block API requests
- Device token rot handled automatically without user intervention

TONE: Systems architecture clarity, mobile platform reliability
PROMPT 10: Testing Strategy & CI/CD Pipeline
You are building comprehensive test coverage and automated deployment.

CURRENT STATE:
- Some unit tests (test_auth.py, test_crud.py)
- No integration tests
- No E2E tests
- No CI/CD pipeline
- Manual deployment

REQUIREMENTS:
1. Unit testing (80%+ coverage):
   - FastAPI endpoints: Valid inputs, invalid inputs, auth failures, edge cases
   - Database operations: CRUD, constraints, transactions
   - AI service: Mocked Gemini API responses
   - Auth: Token generation, refresh, expiry
   - Subscriptions: Plan validation, feature access
   - Test framework: pytest + fixtures (conftest.py)
   
2. Integration tests:
   - Full auth flow: Register → Email verification → Login → Refresh
   - Subscription flow: Free trial → Upgrade → Pay → Webhook confirmation
   - User data isolation: User A cannot see User B's data
   - File uploads: Upload → Validation → S3 storage → Confirmation
   - Celery tasks: Trigger task → Check result in DB
   - iOS Push Notifications: Token registration & payload delivery
   
3. End-to-end tests (Playwright):
   - Web app: Login → Create profile → Log workout → View dashboard
   - Mobile app: Same flows on iOS simulator
   - Cross-browser: Chrome, Safari, Firefox
   
4. Performance tests:
   - Load testing: 100 concurrent users, measure response times
   - Database query performance: Ensure indexes working
   - File upload performance: Max throughput, latency
   - API rate limiting: Verify limits enforced
   
5. Security tests:
   - OWASP Top 10: SQL injection, XSS, CSRF tests
   - Authentication: Bypass attempts, token manipulation
   - Authorization: User A accessing User B's endpoints
   - File upload: Malware files, oversized uploads
   - Rate limiting: Brute force attempts
   
6. Test data & fixtures:
   - conftest.py: Database fixtures, user fixtures, sample data
   - Factory pattern: Generate test users, subscriptions, logs
   - Faker library: Random realistic data
   - Seed scripts: Populate test database
   
7. CI/CD pipeline (GitHub Actions):
   - Trigger on: Push to main/dev, PR creation
   - Steps:
     1. Lint: ESLint (frontend), Flake8/Black (backend)
     2. Type check: TypeScript/Pyright
     3. Unit tests: pytest (backend), Jest (frontend)
     4. Integration tests: pytest with real PostgreSQL (Docker)
     5. Security scan: Bandit (Python), npm audit (JavaScript)
     6. SAST: SonarQube quality gate
     7. Build: Docker images, frontend bundle
     8. Deploy to staging: Auto-deploy on main branch
     9. E2E tests on staging: Playwright tests
     10. Manual approval for production
   
8. Deployment process:
   - Blue-green deployment (zero downtime)
   - Database migrations: Run before code switch
   - Rollback procedure: If metrics degrade
   - Health checks: Wait for endpoints to respond
   - Smoke tests: Verify critical flows work
   
9. Test coverage reporting:
   - Coverage badge in README
   - Enforce minimum 80% coverage on new code
   - Track coverage trends over time
   
10. Monitoring tests in production:
   - Synthetic transactions: Test signup flow every 5min
   - Scheduled E2E tests: Run full flow daily

DELIVERABLES:
- conftest.py: Pytest fixtures (db, app, users)
- tests/unit: Unit test suites
- tests/integration: Integration test suites
- tests/e2e: Playwright test suites
- tests/security: Security/penetration tests
- tests/performance: Load testing scripts (Locust)
- .github/workflows/: CI/CD workflow files
- docker-compose.test.yml: Test environment setup
- coverage.xml: Coverage report config
- Test documentation: How to run tests locally
- Performance baseline: Acceptable response times per endpoint

CONSTRAINTS:
- Tests must run in < 5min (optimize for CI speed)
- Database tests use separate test database (isolation)
- No external API calls in unit tests (mock all)
- Test data cleanup (prevent interference between tests)
- Reproducible tests (no flakiness, fixed seeds for randomization)

TONE: Quality assurance focus, automation emphasis
PROMPT 11: Compliance & Data Privacy (GDPR/Privacy)
You are implementing compliance features for a multi-user platform.

CURRENT STATE:
- No GDPR implementation
- No data retention policies
- No user data export
- No clear privacy policy integration
- No consent management

REQUIREMENTS:
1. GDPR compliance:
   - Legal basis: Legitimate interest for service operation, consent for marketing
   - Privacy notice: Link to privacy policy (displayed at signup)
   - Consent collection: Checkbox for data processing + marketing emails
   - Right to access: Download all personal data (JSON)
   - Right to erasure: Delete account + all associated data (except legal holds)
   - Right to rectification: Edit profile data
   - Right to data portability: Export data in machine-readable format
   
2. Data protection:
   - Data retention policy: Delete logs after 30 days, invoices after 7 years (legal requirement)
   - Encryption: HTTPS in transit, encrypted at rest for sensitive data
   - Backups: Encrypted, stored separately, retention policy
   - Access controls: Only authorized staff can access customer data
   - Audit logging: Track who accessed what, when
   
3. User rights endpoints:
   - GET /api/privacy/export (generate and download user data as JSON)
     * Include: profile, workouts, nutrition, invoices, chat history
     * Return as downloadable file (gzip)
     * Track export requests (rate limit to 1/month)
   
   - POST /api/privacy/delete-account (initiate account deletion)
     * 30-day grace period before permanent deletion
     * Cancel deletion: Send confirmation email link
     * After 30 days: Cascade delete user + all data (except invoices for 7y)
     * Async job: Clear from S3, archive in secure storage
   
   - POST /api/privacy/consent (manage consent preferences)
     * Consent for data processing, marketing emails, analytics
     * Store: timestamp, IP, user agent (for auditing)
     * Allow update: User can change consent anytime
   
4. Privacy policy & T&Cs:
   - Versioned privacy policy (track updates)
   - Display on signup: "By signing up, you agree to T&Cs and Privacy Policy"
   - Archive old versions: Allow users to view what they agreed to
   - Notify users of material changes (email + in-app)
   
5. Data minimization:
   - Collect only necessary data (not: random analytics, tracking pixels)
   - Default to privacy-friendly: No tracking, no 3rd party ads
   - Analytics: Anonymized, aggregate only
   
6. Cookie policy:
   - Session cookies (HttpOnly, Secure): Functional only
   - No tracking cookies (no Google Analytics, etc.)
   - Cookie banner: Opt-in for analytics (if any)
   
7. Third-party data:
   - Stripe: Handle payment data per Stripe DPA
   - Gemini API: No user PII sent to Gemini (anonymize)
   - Sub-processors: Document all 3rd parties, DPA agreements
   
8. International compliance:
   - CCPA (California): Right to know, right to delete, right to opt-out
   - CASL (Canada): Consent-based email marketing
   - LGPD (Brazil): Similar to GDPR
   - Country detection: Comply with applicable law per user location
   
9. Breach notification:
   - Incident response plan (document)
   - Notification: Within 72 hours to regulators, immediately to affected users
   - Record: Document breach, response, investigation results
   
10. DPO & documentation:
   - Designate Data Protection Officer (if required)
   - Maintain records: Data inventory, processing activities, retention schedules
   - Privacy impact assessment (DPIA) for new features

DELIVERABLES:
- privacy_service.py: Export, delete, consent operations
- models.py: Add Consent, DataExport, DeletionRequest tables
- main.py: Privacy endpoints (/api/privacy/*)
- privacy_policy.md: Versioned privacy policy template
- tos.md: Terms of service template
- gdpr_checklist.md: Compliance checklist
- data_retention_policy.md: What data kept, for how long
- incident_response_plan.md: Breach notification procedure
- tasks.py: Async delete account job (cascade delete)
- Test suite: Delete account flow, export data validation
- Admin dashboard: Deletion requests pending, GDPR audit log

CONSTRAINTS:
- Account deletion must be cascade (no orphaned records)
- Never restore deleted data without explicit backup procedure
- Data export must include everything user might need
- User must authenticate before delete account confirmation
- 30-day grace period is non-negotiable (allows cancellation)

TONE: Legal compliance focus, user-centric privacy
PROMPT 12: Admin Dashboard & User Management
You are building an admin dashboard for platform management.

CURRENT STATE:
- No admin interface
- No user management tools
- No analytics dashboard
- No moderation capabilities

REQUIREMENTS:
1. Admin roles & access:
   - SUPER_ADMIN: Full access (rare)
   - ADMIN: User management, support, analytics
   - SUPPORT: View user data, reply to support tickets
   - FINANCE: View revenue, refunds, disputes
   - Read-only ANALYTICS: View metrics only
   
2. User management:
   - Search users: By email, name, subscription status, signup date
   - View user profile: All personal data, subscription, activity
   - View user activity: Login history, API requests, last active
   - Edit user: Change subscription (manual intervention), reset password
   - Suspend/reactivate user: Disable access, send notification
   - Send message: Email/Push notification user (e.g., "Payment failed, update card")
   - Impersonate user: View app as if you're them (audit logged)
   
3. Analytics dashboard:
   - KPIs:
     * Total users (active, inactive)
     * MRR (monthly recurring revenue)
     * Churn rate (monthly)
     * Conversion: Free → Trial → Paid
     * ARPU (average revenue per user)
     * LTV (lifetime value) estimate
   
   - Charts:
     * User growth over time (line chart)
     * Revenue by plan (bar chart)
     * Subscription status breakdown (pie chart)
     * Daily active users (heat map)
     * Geographic distribution (map)
   
   - Filters: Date range, subscription tier, cohort
   - Export: CSV, PDF reports
   
4. Support ticket system:
   - Users can submit support requests: /api/support/tickets
   - Admin views queue: Unresolved → In progress → Resolved
   - Reply to tickets: Save as chat history
   - Auto-categorize: Billing, Bug, Feature request (AI-based)
   - SLA tracking: First response <4h, resolution <24h
   
5. Moderation tools:
   - Flag suspicious accounts: Multiple failed logins, payment issues
   - Review content: User-generated notes, memories (for abuse)
   - Report management: Users can report others, admin reviews
   
6. Financial management:
   - Refund processing: Initiate refund via Stripe
   - Charge disputes: View, respond to disputes
   - Failed payment recovery: See users with failed charges, retry schedule
   - Tax report: Generate tax summaries (for accountant)
   
7. System administration:
   - Feature flags: Enable/disable features per user/tier/region
   - Maintenance mode: Disable API, show message ("Maintenance in progress")
   - Database health: Check connection pool, slow queries
   - Worker health: Celery queue depth, task failures
   - Logs: View application logs, search by error, user, date
   
8. Notifications & alerts:
   - Alert subscriptions: Admin can subscribe to alerts
   - Alert types: High error rate, payment failures, low disk space
   - Notification channels: Slack, email, in-app
   
9. Frontend: React app (separate from user app)
   - Route: /admin/* (protected, requires ADMIN role)
   - Responsive design (desktop-first)
   - Dark mode option
   - Real-time updates: WebSocket for live metrics

DELIVERABLES:
- admin_models.py: AdminSession, SupportTicket, ModeratorLog tables
- admin_schemas.py: Validation schemas for admin operations
- admin_crud.py: Database operations for admin features
- admin_routes.py: API endpoints (/api/admin/*)
- admin_service.py: Business logic (analytics, user management)
- admin_frontend/: Separate React app for admin dashboard
- admin_dashboard.jsx: Main dashboard with KPI cards
- user_management.jsx: User search, edit, suspend
- analytics.jsx: Charts, KPI visualization
- support_tickets.jsx: Ticket queue, messaging
- Test suite: Admin access control, analytics accuracy
- Admin documentation: User guide

CONSTRAINTS:
- Admin access must be audit-logged (every action recorded)
- Impersonation must be clearly marked (admin can't masquerade)
- Sensitive data (passwords) must never be viewable
- GDPR compliance: Admin can't export user data for non-business purposes
- Rate limiting: Exclude admins from rate limits

TONE: Administrative clarity, security audit trail
