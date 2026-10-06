# Exercise 4.1 — Multi-Tenant Data Isolation

**1. What is the difference between row-level multi-tenancy and schema-level multi-tenancy?**
- **Row-level multi-tenancy**: All tenants share the same database tables. A column (like `tenant_id`) is added to each table to identify which rows belong to which tenant. It is simpler to manage a single schema, but carries a higher risk of data leakage because developers must remember to filter by `tenant_id` on every query.
- **Schema-level multi-tenancy**: Each tenant has their own separate schema within the same PostgreSQL database. The application dynamically switches the search path to the appropriate schema based on the current tenant. This provides strong data isolation at the database level and eliminates the need for `tenant_id` filters, making accidental data leakage much less likely.

**2. What is the public schema used for in our system?**
In `django-tenants`, the `public` schema is reserved for global, cross-tenant data. This typically includes the core models that map domains/URLs to specific tenants, as well as any shared configuration, global users, or metadata that is not specific to a single tenant.

**3. What happens if you forget to set the correct schema before a database query?**
If the correct schema is not set, the query will run against the default search path (usually the `public` schema). This will either:
- Result in an error (e.g., "relation does not exist") if the tenant-specific tables do not exist in the public schema.
- Or, worse, it could query or write data to the wrong schema (if a previous tenant's schema is still active in a pooled connection), leading to critical cross-tenant data leaks or corruption.

**4. Write a pseudocode example of how django-tenants switches the schema on an incoming request.**
```python
def tenant_middleware(request):
    # 1. Determine the hostname from the HTTP request
    hostname = request.get_host()
    
    # 2. Look up the tenant associated with this domain in the public schema
    tenant = get_tenant_by_domain(hostname)
    
    # 3. If no tenant is found, return 404 or route to public site
    if not tenant:
        return HttpResponseNotFound()
        
    # 4. Switch the database connection's search path to this tenant's schema
    connection.set_schema(tenant.schema_name)
    
    # 5. Attach the tenant to the request object for use in views
    request.tenant = tenant
```
