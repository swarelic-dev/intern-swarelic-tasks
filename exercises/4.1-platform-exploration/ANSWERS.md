# Multi-Tenant Data Isolation in SCAI — Exercise 4.1 Answers

This document details the multi-tenant architecture, data isolation mechanisms, PostgreSQL schema patterns, and the `django-tenants` implementation used within the Swarelic / SCAI platform.

---

## 1. Difference Between Row-Level and Schema-Level Multi-Tenancy

In multi-tenant SaaS applications, tenant isolation can be designed at different layers of the database. The two prominent models are **Row-Level Multi-Tenancy** and **Schema-Level Multi-Tenancy**.

### Architectural Comparison

| Dimension | Row-Level Multi-Tenancy | Schema-Level Multi-Tenancy (SCAI / `django-tenants`) |
| :--- | :--- | :--- |
| **Data Organization** | All tenants share the same database tables. Every table includes a `tenant_id` foreign key. | Each tenant has its own isolated PostgreSQL schema (`tenant_acme`, `tenant_globex`). |
| **Isolation Mechanism** | Application-level filtering (`WHERE tenant_id = ...`) or DB Row-Level Security (RLS). | Kernel-level schema separation enforced by PostgreSQL's `search_path`. |
| **Risk of Data Leakage** | High: A single forgotten query filter or flawed ORM join can expose another tenant's data. | Very Low: Queries cannot access another schema unless explicitly qualified with cross-schema syntax. |
| **Database Migrations** | Single migration runs once across the shared tables; instant and uniform. | Migrations loop over each schema (`migrate_schemas`). Takes longer for many tenants, but enables per-tenant rollouts. |
| **Backup and Restore** | Extremely complex: Restoring one tenant requires manual row filtering and selective ETL dumps. | Simple and clean: Backups and restores use standard tools (`pg_dump -n tenant_x` and `pg_restore`). |
| **Tenant Offboarding** | Requires deleting millions of rows across foreign-key cascades, causing write locks and fragmentation. | Instant and clean: `DROP SCHEMA tenant_x CASCADE;` reclaims space immediately. |
| **Indexing and Performance** | Shared B-Trees and table bloat; index size grows with global table size. | Independent table files, indexes, and query planner statistics per tenant schema. |
| **Tenant Limits** | Effectively unlimited tenants in a single DB (until storage/IOPS limits). | Optimal up to ~5,000–10,000 schemas before PostgreSQL catalog cache overhead becomes measurable. |

### Why Schema-Level Multi-Tenancy Was Chosen for SCAI
SCAI processes highly sensitive voice call recordings, caller PII, transcripts, and enterprise CRM records. Schema-level isolation guarantees:
1. **Zero accidental leaks:** A developer writing `CallLog.objects.all()` inside a tenant request will only ever see call logs belonging to that tenant, without requiring manual `.filter(tenant=request.tenant)` calls on every query.
2. **Regulatory & Compliance ease:** Customers requiring strict data segregation (such as HIPAA or GDPR data removal) can have their entire schema exported or deleted without impacting any other tenant.

---

## 2. What Is the Public Schema Used for in Our System?

In PostgreSQL with `django-tenants`, the database contains one `public` schema and multiple tenant-specific schemas.

The `public` schema serves as the **shared control plane and routing layer** for the platform:
1. **Tenant Directory & Domain Registry:**
   - Stores the `Client` (or `Tenant`) model instances, defining tenant metadata, subscription tiers, status (active, suspended), and schema identifiers (`schema_name`).
   - Stores the `Domain` model instances, mapping hostnames (e.g., `acme.swarelic.ai`, `callcenter1.internal.swarelic.ai`) to specific `Client` records so incoming HTTP requests can be routed to the appropriate tenant schema.
2. **Global Platform Services (`SHARED_APPS`):**
   - In Django settings, apps are split into `SHARED_APPS` and `TENANT_APPS`.
   - `SHARED_APPS` (such as tenant management, billing models, global API keys, audit logging, and core Django authentication/permissions if centralized) live exclusively in the `public` schema.
3. **Migration and System Tracking:**
   - Tracks global schema migrations in `public.django_migrations`.
   - Hosts system extensions and shared lookup dictionaries that are accessible to all schemas.

---

## 3. What Happens If You Forget to Set the Correct Schema Before a Database Query?

When interacting with PostgreSQL, queries without explicit schema qualification rely on the current connection's `search_path`. If application code executes a query without setting the tenant schema, several severe failure modes occur:

### Scenario A: Relation Does Not Exist (Tenant App Error)
If the connection's `search_path` is left at the default `"$user", public`, any query targeting a model defined in `TENANT_APPS` (e.g., `CallLog`, `AgentSession`, `RulesConfig`) will search only the `public` schema. Because those tables only exist within tenant schemas, PostgreSQL immediately raises:
```text
django.db.utils.ProgrammingError: relation "calls_calllog" does not exist
LINE 1: SELECT "calls_calllog"."id" FROM "calls_calllog" ...
```
This causes an immediate HTTP 500 error or crashed background worker task.

### Scenario B: Catastrophic Cross-Tenant Data Leak (Connection Pool Pollution)
In modern production architectures, database connections are managed via connection pooling (e.g., `pgbouncer` in session/transaction mode, or Django persistent connections with `CONN_MAX_AGE > 0`).

1. Worker thread / connection handles Request A for Tenant Acme: executes `SET search_path TO tenant_acme, public;`.
2. Request A completes and returns the connection back to the connection pool.
3. Worker thread takes the next connection to handle Request B for Tenant Beta, but the code forgets to switch or reset the schema.
4. Request B executes `SELECT * FROM calls_calllog;`.
5. Because the connection's `search_path` is still `tenant_acme`, **Tenant Beta receives Tenant Acme's confidential phone call records and transcripts!**
This is a catastrophic cross-tenant data leak and compliance violation.

### Scenario C: Celery / Asynchronous Task Failures
Background tasks processing webhooks, transcripts, or batch analytics do not run within an HTTP request cycle. If the Celery task does not explicitly wrap execution in `schema_context(tenant.schema_name)`, it either crashes because tables are missing from `public`, or writes records into whichever tenant schema was last used by that Celery worker process.

---

## 4. Pseudocode: How `django-tenants` Switches Schema on Incoming Requests

The following pseudocode demonstrates how `django-tenants` (via `TenantMainMiddleware` and database connection hooks) intercepts each incoming request, resolves the tenant, sets the PostgreSQL `search_path`, and ensures clean connection restoration.

```python
import re
from django.db import connection
from django.http import Http404, HttpResponseServerError
from my_platform.tenants.models import Client, Domain


class SCAITenantMiddleware:
    """
    Middleware that inspects incoming HTTP requests, identifies the target
    tenant via the request hostname, switches the PostgreSQL search_path,
    and guarantees connection safety upon request completion.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # 1. Extract hostname from HTTP headers (e.g. 'acme.swarelic.ai' or '10.0.0.1:8000')
        raw_host = request.get_host()
        hostname = raw_host.split(":")[0].lower()

        # 2. Query the shared public schema to resolve the tenant domain
        # NOTE: At this stage, search_path must point to 'public' to query the Domain table
        connection.set_schema_to_public()

        try:
            domain_record = Domain.objects.select_related("tenant").get(domain=hostname)
            tenant = domain_record.tenant
        except Domain.DoesNotExist:
            # Handle special root/admin domains or return 404
            if hostname in ["swarelic.ai", "admin.swarelic.ai", "localhost"]:
                tenant = Client.objects.get(schema_name="public")
            else:
                raise Http404(f"Tenant domain '{hostname}' not registered.")

        # 3. Verify tenant is active and eligible for service
        if not tenant.is_active:
            raise Http404("Tenant account is suspended or inactive.")

        # 4. Attach tenant and domain context to the request object
        request.tenant = tenant
        request.domain = domain_record

        # 5. Switch PostgreSQL connection schema to the tenant's isolated schema
        # Under the hood: executes 'SET search_path TO "tenant_schema", "public"'
        previous_tenant = connection.tenant
        connection.set_tenant(tenant)

        try:
            # 6. Process the request down the middleware chain & execute view logic
            response = self.get_response(request)
            return response
        finally:
            # 7. CRITICAL CLEANUP: Reset connection to public schema before returning
            # This prevents connection pool pollution across persistent connections
            connection.set_schema_to_public()
            if previous_tenant is not None and previous_tenant.schema_name != "public":
                connection.set_tenant(previous_tenant)
```

### Key Safety Highlights in the Workflow
1. **Host Header Resolution:** `request.get_host()` safely normalizes host headers and maps subdomains/domains to unique `Client` records.
2. **Atomic Schema Switch:** `connection.set_tenant(tenant)` issues `SET search_path TO "tenant_name", public` at the database level before any view queries run.
3. **Guaranteed `finally` Cleanup:** Re-setting the schema in the `finally` block guarantees that subsequent requests reusing that pooled connection will never inherit a stale tenant context.
