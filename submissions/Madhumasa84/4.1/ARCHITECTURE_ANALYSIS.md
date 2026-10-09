# Architecture Analysis — Madhusudhanan

> Exercise 4.1 | Submitted: 2026-10-09

---

## Section 1: Codebase Map

The Swarelic Call AI (SCAI) platform is structured into modular domains that handle telephony integration, real-time voice synthesis and recognition, business rules evaluation, multi-tenant database isolation, agent state orchestration, REST APIs, and asynchronous job queuing.

| Directory | Purpose | Key Files | Depends On |
| :--- | :--- | :--- | :--- |
| `scaibp/voice/` | End-to-end real-time voice pipeline including STT, LLM orchestration, VAD, and TTS | `pipeline.py`, `transcriber.py`, `consumer.py` | `scaibp/rules/`, `scaibp/tenants/` |
| `scaibp/rules/` | Standalone and database-driven business rule evaluation engine for routing calls | `engine.py`, `loader.py`, `models.py` | `scaibp/tenants/` |
| `scaibp/tenants/` | Multi-tenant schema isolation, domain resolution, and client metadata tracking | `models.py`, `middleware.py`, `routing.py` | PostgreSQL `django-tenants` |
| `scaibp/agents/` | Agent session management, call routing queues, and state machine lifecycle | `state_machine.py`, `session.py`, `models.py` | `scaibp/tenants/`, `scaibp/voice/` |
| `scaibp/api/` | RESTful API endpoints for client integrations, reporting, and dashboard CRUD | `views.py`, `serializers.py`, `urls.py` | `scaibp/agents/`, `scaibp/rules/` |
| `scaibp/telephony/` | Webhook ingestion and media stream gateway for Twilio and SIP providers | `twilio_handler.py`, `webrtc.py`, `views.py` | `scaibp/voice/` |
| `scaibp/tasks/` | Celery asynchronous worker tasks for audio persistence, transcription, and CRM sync | `celery.py`, `tasks.py`, `webhooks.py` | `scaibp/tenants/`, `scaibp/voice/` |
| `scaibp/analytics/` | Real-time call analytics, latency metrics, agent KPI tracking, and dashboards | `metrics.py`, `aggregators.py`, `views.py` | `scaibp/agents/`, `scaibp/voice/` |

### Detailed Module Analysis

### `scaibp/voice/` — Voice Pipeline
The `scaibp/voice/` directory contains the core real-time streaming audio engine of the SCAI platform. It interfaces with external telephony streams (such as Twilio Media Streams or WebRTC endpoints), converts binary audio into text via Speech-to-Text (STT) services, coordinates conversation context with Google Gemini and OpenAI LLM models, and returns synthesized audio using low-latency Text-to-Speech (TTS). It relies on Python async event loops and WebSockets to sustain sub-second round-trip latency.

### `scaibp/rules/` — Rules Engine
This module contains the decision engine that controls call flow progression. Rules are configured as sets of conditions (evaluating fields like caller tags, call counts, hour of day, and speech intent) paired with actionable triggers (such as queue routing, voicemail redirection, supervisor escalation, or hangup). The engine evaluates rules based on strict priority rankings and operates independently from presentation logic to facilitate rapid testing and iteration.

### `scaibp/tenants/` — Multi-Tenant Architecture
This module implements tenant separation using PostgreSQL schemas via the `django-tenants` library. It contains models representing clients and their associated domain names, middleware that intercepts requests to bind the appropriate database schema via `search_path`, and database utility routines to guarantee complete data isolation between corporate clients.

### `scaibp/agents/` — Agent Lifecycle & Call Queuing
The `scaibp/agents/` module coordinates human and AI agent presence. It tracks agent statuses (such as OFFLINE, ONLINE, AVAILABLE, RINGING, ON_CALL, WRAPPING_UP, BREAK) using a finite state machine. It prevents invalid transitions, calculates key contact center metrics (average handling time, wrap-up duration, availability percentage), and routes prioritized incoming calls to eligible agents.

### `scaibp/telephony/` — Telephony Gateway
This component handles inbound and outbound telephone calls by serving webhooks for Twilio Voice and SIP providers. When an inbound call arrives, it generates TwiML instructions directing Twilio to establish a bi-directional WebSocket connection to the Voice Pipeline. It normalizes provider-specific payloads into standardized event models.

### `scaibp/api/` — Client & Admin REST API
Built using Django REST Framework (DRF), this module provides secure endpoints for configuring business rules, viewing historical call logs, managing agent accounts, and retrieving call transcripts. It leverages JWT authentication and enforces tenant schema separation across all endpoints.

### `scaibp/tasks/` — Asynchronous Background Jobs
This module utilizes Celery backed by Redis to manage long-running background processes. When phone calls terminate, tasks in this module asynchronously compress call audio, store raw recordings in S3-compatible cloud storage, generate post-call summaries, and push webhook payloads into external CRMs (Salesforce, HubSpot).

### `scaibp/analytics/` — Telemetry & KPI Engine
This module ingests telemetry generated by active calls, rules engine invocations, and agent sessions. It aggregates metrics such as latency distributions (STT, LLM, TTS turnaround times), call volumes, drop-off rates, and agent utilization, surfacing data through internal APIs and Prometheus metrics endpoints.

---

## Section 2: Call Flow Trace

The lifecycle of an incoming call follows a coordinated path across telephony, voice processing, rules evaluation, agent dispatch, and post-call persistence.

### Step 1: Telephony Webhook Ingestion
**File:** `scaibp/telephony/twilio_handler.py` (lines 45–95)

**What happens here:**
An external customer dials a tenant's phone number. Twilio dispatches an HTTP POST webhook to `/telephony/incoming-call/`. The handler validates the Twilio HMAC signature, resolves the receiving tenant number against the tenant database in `scaibp/tenants/`, and responds with a TwiML payload instructing Twilio to open a bi-directional media stream over WebSockets to `/ws/voice/{call_sid}/`.

**Data passed forward:**
```python
{
    "call_sid": "CA1029384756abcdef",
    "caller_number": "+14155550199",
    "called_number": "+18005550100",
    "timestamp": "2026-10-09T16:00:00Z",
    "stream_url": "wss://api.swarelic.ai/ws/voice/CA1029384756abcdef"
}
```

### Step 2: WebSocket Connection & Voice Pipeline Initialization
**File:** `scaibp/voice/consumer.py` (lines 30–85)

**What happens here:**
Twilio connects to the `VoiceCallConsumer` WebSocket endpoint. The consumer initializes a streaming session instance in `scaibp/voice/pipeline.py` (lines 60–120). Audio chunks arriving in G.711 mulaw format (8kHz) are queued into an audio buffer, and Voice Activity Detection (VAD) monitors caller speech boundaries.

**Data passed forward:**
```python
{
    "event": "media",
    "stream_sid": "MZ1234567890",
    "call_sid": "CA1029384756abcdef",
    "payload": "base64_encoded_audio_data_chunk..."
}
```

### Step 3: Speech-to-Text Transcription Event
**File:** `scaibp/voice/transcriber.py` (lines 110–165)

**What happens here:**
Once the VAD detects caller speech completion or a continuous speech stream, raw audio frames are processed by the STT engine. A finalized text transcript is returned with confidence scoring and timestamp metadata.

**Data passed forward:**
```python
{
    "call_sid": "CA1029384756abcdef",
    "transcript": "I need to speak with someone about an urgent billing issue on my account.",
    "confidence": 0.96,
    "speaker": "caller"
}
```

### Step 4: Rules Engine Evaluation
**File:** `scaibp/rules/engine.py` (lines 80–145)

**What happens here:**
The voice pipeline assembles a structured context event including caller metadata, historical call frequency, caller tags, current time of day, and the detected transcription intent. The `RulesEngine.evaluate(context)` function evaluates rules sorted by priority (lowest integer first). The first rule satisfying all conditions matches, producing an action.

**Data passed forward:**
```python
{
    "action": "route",
    "data": {
        "target": "billing_urgent_queue",
        "priority": 1,
        "caller_tag": "VIP"
    }
}
```

### Step 5: Agent Assignment & Call Bridging
**File:** `scaibp/agents/session.py` (lines 75–130)

**What happens here:**
The routing dispatcher inspects available agents subscribed to the `billing_urgent_queue`. The agent state machine transitions the selected agent from `AVAILABLE` to `RINGING`. When the agent answers via the browser UI, the state transitions to `ON_CALL`, bridging the human representative into the audio stream alongside the real-time AI assistant.

**Data passed forward:**
```python
{
    "agent_id": "agent_alice_402",
    "call_sid": "CA1029384756abcdef",
    "state": "ON_CALL",
    "queue": "billing_urgent_queue"
}
```

### Step 6: Call Completion and Data Persistence
**File:** `scaibp/tasks/tasks.py` (lines 40–105)

**What happens here:**
Upon caller or agent disconnect, the WebSocket closes. The state machine transitions the agent to `WRAPPING_UP`. An asynchronous Celery task `persist_call_summary` writes the complete transcript, call duration, and audio recording URI into the tenant's isolated PostgreSQL database schema table `calls_calllog`. A webhook dispatches call metadata to the tenant's configured external CRM.

---

## Section 3: Rules Engine Deep Dive

### 1. How are rules stored?
Rules in the SCAI platform are modeled both as persistent database records (using Django ORM in `scaibp/rules/models.py`) and as serialized JSON representations in caching tiers (`Redis`). This enables administrators to manage rules via the Admin API while the real-time voice pipeline evaluates cached rules without incurring database roundtrips.

### 2. What does a rule look like in data?
```python
{
    "id": "rule-billing-escalation-004",
    "name": "High Priority Billing Escalation",
    "priority": 10,
    "conditions": [
        {"field": "intent", "operator": "eq", "value": "billing"},
        {"field": "caller_tag", "operator": "in", "value": ["VIP", "ENTERPRISE"]},
        {"field": "hour_of_day", "operator": "lt", "value": 18}
    ],
    "action": {
        "type": "escalate",
        "data": {
            "target": "senior_tier_queue",
            "notify_manager": True
        }
    }
}
```

### 3. How are conditions evaluated?
Conditions are represented by the `Condition` dataclass in `scaibp/rules/engine.py`. Each condition defines a `field`, `operator` (such as `eq`, `ne`, `gt`, `gte`, `lt`, `lte`, `in`, `not_in`, `contains`, `startswith`), and `value`. During evaluation, `Condition.evaluate(context)` extracts the field from the runtime context dict. If the field is missing, it returns `False`. Otherwise, it applies the specified operator check. Rules employ short-circuit Boolean AND logic: if any condition fails, the rule match terminates immediately.

### 4. What happens when multiple rules match?
Rules are sorted upon engine instantiation by `priority` in ascending order (where priority 1 takes precedence over priority 10). When `RulesEngine.evaluate(context)` is invoked, it evaluates rules sequentially and immediately returns the action associated with the **first matching rule**. Subsequent matching rules are ignored for routing, though an auxiliary method `evaluate_all(context)` is available for testing and audit logs.

### 5. What action types exist?
The platform defines standard action types in `VALID_ACTION_TYPES`:
- `route`: Directs the caller to a specific agent queue or department.
- `voicemail`: Redirects the call to a voicemail recording box.
- `escalate`: Immediately escalates call priority and notifies a supervisor.
- `hangup`: Terminates the telephony connection.
- `play_message`: Streams a pre-recorded audio prompt or TTS text before further routing.

### 6. How would you add a new action type?
To introduce a new action type (e.g., `send_sms_link`):
1. Add `'send_sms_link'` to `VALID_ACTION_TYPES` in `scaibp/rules/engine.py` (line 18).
2. Update the `ActionType` choices enum in `scaibp/rules/models.py` (line 32) and create database migrations.
3. In `scaibp/rules/loader.py`, validate payload schemas required for SMS delivery (such as `phone_number` and `template_id`).
4. Implement the execution handler in the call coordinator (`scaibp/voice/pipeline.py`), dispatching a Celery task to send the SMS message via the telephony gateway.
5. Add unit and integration tests covering the new action type in `tests/test_engine.py`.

---

## Section 4: Multi-Tenancy Model

### 1. Database isolation mechanism
SCAI enforces strict tenant isolation using PostgreSQL schema-level multi-tenancy backed by `django-tenants`. Instead of shared tables filtered with a `tenant_id` foreign key, each tenant is provisioned with its own dedicated PostgreSQL schema (e.g., `tenant_acme`, `tenant_globex`). The active schema is switched at the database connection level by setting PostgreSQL's `search_path`.

### 2. Where is tenant context stored in a request?
Incoming requests pass through `SCAITenantMiddleware` (`scaibp/tenants/middleware.py`). The middleware inspects the incoming request hostname (`request.get_host()`), queries the domain registry in the `public` schema, and attaches the resolved `Tenant` model instance to `request.tenant`. The connection's `search_path` is immediately set via `connection.set_tenant(tenant)`.

### 3. Tenant-specific configuration
Each tenant schema maintains its own configuration tables for business rules, agent queues, routing options, and operating schedules. High-volume settings are cached in Redis under tenant-scoped namespace keys (e.g., `tenant:{tenant_id}:rules`).

### 4. Risk of bypass
If schema switching is bypassed (such as due to improper connection pool reuse or unhandled exceptions in background workers), queries could execute against the default `public` schema or retain the previous request's schema. This risk is mitigated by:
- Wrapping all middleware request handling in `try...finally` blocks that reset `search_path` to `public`.
- Rejecting queries without an active tenant context.
- Running comprehensive automated integration tests verifying cross-schema isolation.

---

## Section 5: Improvement Opportunities

### Opportunity 1: Streaming Voice Pipeline Interruption (Barge-in Support)
**Current implementation:**
The current voice pipeline processes audio in sequential discrete blocks: when the AI receptionist or TTS is speaking, incoming user audio is buffered until the playback block completes.

**Problem:**
If a human caller interrupts the AI to correct information or request an immediate transfer, the AI continues speaking until the TTS playback buffer empties, creating an unnatural customer experience.

**Proposed improvement:**
Implement low-latency Voice Activity Detection (VAD) with instant barge-in cancellation. When incoming energy levels indicate user speech during TTS playback, the WebSocket immediately dispatches an interruption signal to Twilio to flush the audio buffer and cancel pending TTS frames.

**Effort estimate:** Medium (requires asynchronous stream coordination in `scaibp/voice/consumer.py`).

---

### Opportunity 2: Pre-Compiled Rules Engine with Abstract Syntax Trees (AST)
**Current implementation:**
`RulesEngine.evaluate()` iterates sequentially through rules, evaluating each condition using string-based operator lookups during call execution.

**Problem:**
As tenants scale to hundreds of complex routing rules, linear iteration on every incoming utterance increases evaluation latency.

**Proposed improvement:**
Compile rules into an indexed evaluation graph (or Python bytecode/callable closures) upon tenant rule updates. Rules can be indexed by candidate fields (`intent`, `caller_tag`) using hash lookups, reducing evaluation time to $O(1)$ for non-matching branches.

**Effort estimate:** Medium (enhance `scaibp/rules/engine.py` with indexed rule trees).

---

### Opportunity 3: Tenant Schema Connection Pool Management in PgBouncer
**Current implementation:**
PostgreSQL connection pooling relies on standard session-mode pooling, where `SET search_path` modifies the session state.

**Problem:**
In high-concurrency environments, session pooling limits maximum open database connections. Switching to transaction-level pooling causes `SET search_path` statements to leak across transactions if connections are reused.

**Proposed improvement:**
Deploy a customized PgBouncer setup using query-level schema qualification or implement explicit connection checkout decorators that invoke `DISCARD TEMP; RESET search_path;` on connection release.

**Effort estimate:** Large (requires DevOps infrastructure coordination and database proxy tuning).

---

## Section 6: Questions

1. In `scaibp/voice/consumer.py` (lines 62–78), what is the buffer threshold before raw G.711 mulaw audio packets are passed to the STT transcriber, and how is packet jitter handled over high-latency connections?
2. In `scaibp/rules/engine.py` (lines 92–104), does the rules engine support nested condition groups (e.g., boolean `OR` conditions within `AND` groups), and what is the recommended architecture for expressing compound boolean logic?
3. In `scaibp/tenants/middleware.py` (lines 38–54), how are incoming webhook requests from third-party services that do not include tenant subdomains in their Host headers mapped to the correct tenant schema?
4. In `scaibp/agents/state_machine.py` (lines 88–112), what mechanism cleans up agent sessions when a client browser disconnects unexpectedly without issuing a formal `LOGOUT` event?
5. In `scaibp/tasks/tasks.py` (lines 85–110), how are failed CRM webhook deliveries retried, and is there an exponential backoff policy configured with dead-letter queue handling?
