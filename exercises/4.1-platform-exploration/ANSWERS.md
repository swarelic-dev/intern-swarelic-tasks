# Exercise 4.1 — Multi-Tenant Data Isolation

## Q1: What is the difference between row-level and schema-level multi-tenancy?

### Row-Level Multi-Tenancy
All tenants share the **same database tables**. Every table has a `tenant_id` column, and application
code must include `WHERE tenant_id = <current_tenant>` on every single query.

| Aspect | Row-Level |
|---|---|
| Isolation | Weak — enforced only in application code |
| Risk | High — one missing WHERE clause leaks cross-tenant data |
| Complexity | Simple schema; complex query logic |
| Performance | Indexes must include `tenant_id`; large tables can slow down |
| Typical use | Low-security SaaS apps with many small tenants |

### Schema-Level Multi-Tenancy
Each tenant gets their **own PostgreSQL schema** (a namespace like `tenant_acme`, `tenant_globex`)
inside a single database. The application switches `search_path` to the correct schema per request,
so all queries automatically hit only that tenant's tables.

| Aspect | Schema-Level |
|---|---|
| Isolation | Strong — enforced at the database level |
| Risk | Low — forgetting to switch schema gives an error rather than leaking data |
| Complexity | More complex migrations (must run per schema) |
| Performance | Smaller per-tenant tables; cleaner query plans |
| Typical use | High-security SaaS apps (SCAI) with strict data isolation requirements |

---

## Q2: What is the `public` schema used for in our system?

In a `django-tenants` system the **`public` schema** is the shared, global namespace. It contains:

- **`Domain` / `Tenant` models** — the mapping from hostname → schema name. These must be globally
  accessible so the middleware can identify the tenant *before* switching schemas.
- **Global user accounts** — super-admins or platform-level users who are not scoped to any single
  tenant.
- **Shared configuration tables** — feature flags, platform-wide settings, subscription plans.

Everything tenant-specific (contacts, calls, appointments, rules) lives in the **tenant schema**, not
in `public`.

---

## Q3: What happens if you forget to set the correct schema before a query?

The query runs against whatever schema is currently active on the database connection (usually
`public`, or the *previous* tenant's schema if connections are pooled).

**Possible outcomes:**

1. **`relation does not exist` error** — the tenant tables don't exist in `public`, so the query
   simply fails. This is the *safe* failure mode.
2. **Silent cross-tenant data leak** — if using a connection pool (e.g., PgBouncer), the previous
   tenant's schema may still be active. You read or write another tenant's data with no error. This
   is a critical security vulnerability.
3. **Corrupted data** — an INSERT into the wrong schema creates records that are invisible to the
   intended tenant but pollute another tenant's database.

This is why `django-tenants` implements `TenantMiddleware` — it guarantees the schema is set on
**every** request before any view or ORM code runs.

---

## Q4: Pseudocode — how `django-tenants` switches schema on an incoming request

```python
class TenantMiddleware:
    """
    Runs before every view. Identifies the tenant from the request hostname
    and switches the PostgreSQL search_path to that tenant's schema.
    """

    def __call__(self, request):
        # 1. Extract the hostname from the incoming HTTP request
        #    e.g. "acme.scai.io" or "globex.scai.io"
        hostname = get_hostname_from_request(request)

        # 2. Query the PUBLIC schema to find the matching tenant
        #    The Domain table is always in 'public', so no schema switch needed yet
        try:
            tenant = Domain.objects.get(domain=hostname).tenant
        except Domain.DoesNotExist:
            return HttpResponseNotFound("Unknown tenant domain")

        # 3. Switch the database connection's search_path to this tenant's schema
        #    All subsequent ORM queries in this request will automatically
        #    target tables inside e.g. "tenant_acme.*"
        connection.set_schema(tenant.schema_name)

        # 4. Attach the tenant object to the request so views can access it
        request.tenant = tenant

        # 5. Hand off to the next middleware or the view function
        response = self.get_response(request)

        # 6. (Optional) Reset to public schema to avoid leaking state
        #    to the next request if the connection is reused from a pool
        connection.set_schema_to_public()

        return response
```

**Key insight:** Step 6 is critical in pooled-connection environments. Without it, a connection
returned to the pool still has a tenant's `search_path` set, and the next request that picks up
that connection will start in the wrong schema.
