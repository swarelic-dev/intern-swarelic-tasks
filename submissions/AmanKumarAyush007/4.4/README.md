# Exercise 4.4 — Production-style SCAI REST client

The client uses requests.Session pooling, credential caching and refresh, typed configuration, bounded retries on GET only, a single 401 recovery attempt, and explicit 400/401/403/404/5xx errors. The exercise specifies `/api/auth/token/` and `/api/v1/call-logs/`; confirm these against the actual server before integration.

```powershell
python -m pip install -r requirements.txt
python -m pytest tests -v
```

Example (never commit credentials):

```python
import os
from scai_client import SCAIClient, SCAIClientConfig
with SCAIClient(SCAIClientConfig(
    base_url=os.environ["SCAI_BASE_URL"],
    username=os.environ["SCAI_USERNAME"],
    password=os.environ["SCAI_PASSWORD"],
)) as client:
    logs = client.list_call_logs(page=1)
```

No real HTTP requests occur in tests.
