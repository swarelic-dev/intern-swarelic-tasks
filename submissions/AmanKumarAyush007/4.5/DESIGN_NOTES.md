# Design Notes — Option A: Call Queue Dashboard

## Why I chose this option

A call-queue API demonstrates the same practical questions as a call-center backend: how does a tenant identify its own queues, how do waiting calls enter and leave reliably, and how do operators observe congestion? It can also be verified without live telephony credentials or modifying the production platform. The exercise requested a queue model with live counters, four API endpoints and a Celery alert; this implementation chooses those boundaries explicitly.

## Three key design decisions

**1. Explicit tenant authorization.** A `TenantMembership` row connects each API user to the tenants they can access. All views derive their queryset from those memberships and then look up the requested queue. An unauthorized queue returns 404, avoiding information leaks through distinct authorization responses. The membership approach is intentionally a standalone substitute, not a claim about how actual SCAI enforces isolation.

**2. Transactional FIFO admission and removal.** A `QueuedCall` is a durable row rather than an in-memory list, and the oldest waiting entry is served first using creation time and primary key to break ties. A transaction locks the parent `CallQueue` row on PostgreSQL before checking capacity and updating the denormalized depth counter. The count is changed using an `F` expression to avoid lost updates. Duplicate calls are rejected with application validation backed by a database uniqueness constraint.

**3. Background alerts after persistence.** Alerts are dispatched through `transaction.on_commit`, so a rolled-back admission cannot generate a misleading alert. Celery workers query the current queue depth again instead of trusting potentially stale counts sent from the web process. The task currently emits a structured log event and does not require an external notification provider; a production integration would add an idempotent notification delivery policy.

## Trade-offs

The `current_calls` counter is denormalized for efficient queue listings, introducing a consistency responsibility. Transactions and restricted write paths limit drift, but administrative direct edits would require reconciliation. The statistics aggregate historical served and abandoned calls rather than supporting selectable time windows; a later version should expose a bounded query range and cache safe aggregate snapshots. API authentication uses built-in DRF mechanisms in a standalone environment rather than attempting to infer the real organization's identity provider.

## Edge cases handled

A full queue returns HTTP 400 without changing state. An empty dequeue returns HTTP 404, a duplicate call ID returns HTTP 400, missing call identifiers are rejected by the serializer, and users outside a tenant cannot enumerate or mutate its queues. Alert tasks do not crash if a queue is deleted before execution. There is no cross-tenant lookup by global queue ID without membership filtering.

## What I would do with more time

I would add explicit abandonment events and policy-based expiration, allowing real abandonment rates to grow from events rather than always remaining zero for this limited API. I would introduce range-filtered analytics, pagination, service-role permissions, OpenAPI schema generation, metrics/tracing, and an integration test suite against real PostgreSQL and Redis. A WebSocket bridge could push queue changes to a dashboard only after authorization. I would also define retry/backpressure policies for alerts and deploy with credential rotation and proper security review before live call traffic.

## What remains out of scope

This mini service does not integrate with Twilio, the real SCAI rules engine, live call agents, SCAI's existing tenant model, or production credentials. No production schema assumptions are made. These integrations require the actual source and mentor approval. SQLite is acceptable for local checks, but concurrent correctness is only intended for a PostgreSQL deployment using row locks.
