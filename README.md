# Safety-Aware Multi-Agent Financial Assistant

This is a small FastAPI service for the Safety-Aware Multi-Agent Financial Assistant. It implements the required spine of the system:

```text
SSE endpoint -> local safety guard -> intent classifier -> router -> portfolio health agent or stub agent
```

<<<<<<< HEAD
The implementation is intentionally simple and readable. The goal was to build a working fresher-friendly MVP that handles the required edge cases without hiding the logic behind too many abstractions.


## What Is Implemented

- Local safety guard with no LLM or network call
- Intent classifier with one OpenAI call when `OPENAI_API_KEY` is set
- Rule-based classifier fallback when the LLM is unavailable
- Follow-up handling for prior user turns
- Portfolio Health agent implemented end to end
- Stub responses for all other classified agents
- In-memory session memory
- Server-Sent Events only response mode
- Pytest coverage for safety, classification, portfolio health, and SSE pipeline

## Setup

Requires Python 3.11+.

```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
```

For Linux/macOS:

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

## Environment Variables

```text
OPENAI_API_KEY   Optional for tests, required for live LLM classification
OPENAI_MODEL     Defaults to gpt-4o-mini
APP_ENV          development | production | test
DATABASE_URL     Optional, unused in this MVP
```

Tests pass without `OPENAI_API_KEY`. In that case the classifier uses the local fallback.

## Run The Service

```bash
uvicorn src.app:app --host 127.0.0.1 --port 8000
```

Example request:

```bash
curl -N -X POST http://127.0.0.1:8000/v1/chat/stream ^
  -H "Content-Type: application/json" ^
  -d "{\"query\":\"how is my portfolio doing\",\"user_id\":\"usr_003\",\"session_id\":\"demo-1\"}"
```

The endpoint returns only SSE events:

```text
event: metadata
event: chunk
event: done
```

Errors are also streamed as SSE:

```text
event: error
event: done
```

## Run Tests

```bash
pytest tests/ -v
```

Current local result:

```text
12 passed
```

## Request Flow

1. `src.app` receives `POST /v1/chat/stream`.
2. `src.safety.check()` runs first and can block the query.
3. If safe, prior user turns are loaded from `src.memory`.
4. `src.classifier.classify()` classifies the query.
5. `src.router.dispatch()` sends portfolio health queries to the real agent.
6. Other agents return a structured "not implemented" response.
7. The response is streamed as SSE chunks.

Safety takes precedence. If the local guard blocks a query, the classifier never runs.

## Design Decisions

**In-memory session memory:** I used a dictionary in `src.memory` because the assignment allows in-memory persistence for the demo. It keeps the project easy to run in CI and avoids database setup. With another week I would move this to SQLite or Postgres with tenant/session indexes.

**StreamingResponse instead of extra SSE abstraction:** FastAPI's `StreamingResponse` is enough for this MVP and keeps the protocol visible. The service still follows the SSE format directly.

**Classifier fallback:** The live path uses OpenAI JSON mode when an API key is present. Tests and no-key environments use a deterministic local fallback so CI never depends on external credentials.

**Portfolio values:** The fixtures do not provide live prices. To avoid hardcoding market data, Portfolio Health uses cost basis as a current-value fallback and labels benchmark/performance fields with notes. This is honest, testable, and easy to replace with `yfinance` or MCP-backed pricing later.

**Safety tradeoff:** The guard favors blocking obvious harmful instructions while allowing educational questions such as "what is insider trading?" The rules are plain keyword checks so they remain fast and explainable.

## Cost And Performance Notes

Development model: `gpt-4o-mini`

Evaluation model: `gpt-4.1`

The normal live path uses one classifier LLM call and no LLM call inside Portfolio Health. Stub agents do not call an LLM. The local safety guard runs before the LLM, so blocked harmful requests cost zero model tokens.

Measured locally with pytest/TestClient on the deterministic fallback path:

```text
pytest tests/ -v
12 passed in under 1 second
```

Expected live latency target:

- First SSE event should arrive quickly because safety and metadata are lightweight.
- End-to-end time is mainly the single classifier call.
- Pipeline timeout is set to 8 seconds in `src.app.PIPELINE_TIMEOUT_SECONDS`.

Cost target reasoning:

- One classification call with short prompt and 500 output-token cap should stay well under $0.05 per query on `gpt-4.1`.
- Safety-blocked queries use no model call.
- Portfolio Health itself is deterministic.

<<<<<<< HEAD
## Defence Video

Video link: TODO - add unlisted YouTube URL before final submission.

## What I Would Improve With Another Week
=======
## What can be Improved
>>>>>>> be2853eeb18091c8b2a69b9062e2e57b9fce2aa4

- Add real market data through `yfinance` or MCP and compute actual returns.
- Persist memory in SQLite/Postgres.
- Add a small classifier evaluation report in CI.
- Add tenant-specific rate limits and model selection.
