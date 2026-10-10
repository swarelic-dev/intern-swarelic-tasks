# Exercise 4.5 — Call Queue Dashboard (Option A)

Standalone tenant-aware Django REST API. Tenant membership is explicit: a queue is invisible (404) to users who lack access to its tenant. Calls are admitted/served through transactions, retaining historical queue entries. FIFO is stable by enqueue time and primary key. Queue alerts are dispatched after commit to a Celery worker and are logged instead of sent to a third-party service.

## Local setup (PowerShell)

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python manage.py check
python manage.py migrate
python manage.py test queues.tests -v 2
```

To run asynchronous alerts start Redis with `docker compose up -d redis`, then in separate terminals run `celery -A project worker --loglevel=info` and `python manage.py runserver`. Before authenticating, provision `User`, `Tenant`, `TenantMembership` and `CallQueue` with a Django shell or Django fixtures. API uses DRF basic/session auth for this standalone local exercise; deploy behind TLS with production SSO/JWT.

## HTTP routes

- `GET /api/v1/queues/`: list authorized queues
- `GET /api/v1/queues/{id}/stats/`: wait times, abandonment rate and current depth
- `POST /api/v1/queues/{id}/enqueue/` with `{"call_id": "call-123"}`
- `POST /api/v1/queues/{id}/dequeue/`: serve the oldest call

## Deployment notes

Production concurrency requires PostgreSQL (configure `DATABASE_URL`); SQLite does not provide equivalent row-level locking. Replace the logging alert stub with your monitoring/notification transport. Configure TLS, hostnames, secrets management and authenticated service accounts externally. This service is not connected to live SCAI telephony.
