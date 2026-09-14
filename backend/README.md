# Enterprise AI Assistant

An enterprise AI assistant backend built on **FastAPI**, **LangGraph**, and **RAG**. A supervisor-based multi-agent architecture routes each request to specialist agents — internal document retrieval, external web research, and structured data querying — then synthesizes a single, source-attributed answer under explicit safety, reliability, and cost guardrails.

```
                    Enterprise AI Assistant
                              │
                       ┌──────▼──────┐
                       │   FastAPI   │
                       └──────┬──────┘
                              │
                    Auth + Guardrails
                              │
                       ┌──────▼──────┐
                       │  Supervisor │
                       │  (LangGraph)│
                       └──────┬──────┘
                              │
              ┌───────────────┼───────────────┐
              ▼               ▼               ▼
             RAG          Research           Data
              │               │               │
           Qdrant          Web/API         PostgreSQL
              │               │               │
              └───────────────┼───────────────┘
                              ▼
                  Result Validation + Synthesis
                              │
                   Reliability Controls
                              │
                              ▼
                           Response
                              │
                    Observability Layer
```

---

## 1. Problem statement

Enterprises need an assistant that answers **different kinds of questions** together — internal knowledge ("What is our leave policy?"), external knowledge ("What changed in the latest Java release?"), and structured data ("How many orders completed last month?") — with **traceable answers**, **no fabrications**, and **no way for the model to grant itself permissions**. A single chatbot with a few tools neither distinguishes those capabilities nor explains why a request took 12 seconds. This project models the assistant as a **supervisor orchestrating specialized agents** behind guardrails, with reliability and observability built in from the start.

## 2. Architecture

- **FastAPI** exposes HTTP endpoints under `/api/v1` and orchestrates per-request lifecycle: authentication → authorization → input guardrails → agent execution → final synthesis → audit/observability.
- **LangGraph** hosts the **supervisor + specialist** state machine (see §4).
- **PostgreSQL** is the system of record (users, conversations, messages, documents, memory metadata).
- **Qdrant** is the vector store for RAG chunk retrieval and memory recall.
- **Redis** (optional, graceful fallback to in-memory TTL cache) provides response caching.

Dependency direction is explicit: `api/` (HTTP) → `services/` (application logic) → `agents/` (orchestration) → `tools/` (external capability). Cross-cutting concerns live in `core/` (timeout, retry, circuit breaker, concurrency, budget, cache), `security/`, and `observability/`.

## 3. Agent architecture

```
START → memory_retriever → supervisor → [rag | research | data] → supervisor (loop)
      → responder → memory_extractor → END
```

The **supervisor** (an LLM router with a deterministic backstop) selects which specialists to run, bounded by `MAX_AGENT_STEPS` and the per-request token budget. Specialists return a **standardized `AgentResult`**, so the supervisor and responder only depend on six fields:

```python
class AgentResult(BaseModel):
    agent: AgentName   # rag | research | data
    success: bool
    content: str
    sources: list[str]
    metadata: dict
    error: str | None
```

| Scenario | Example | Path |
|---|---|---|
| A. Internal knowledge | "What is our employee leave policy?" | Supervisor → RAG → Qdrant |
| B. External research | "What changed in the latest Java release?" | Supervisor → Research → web search |
| C. Data query | "How many orders completed last month?" | Supervisor → Data → PostgreSQL |
| D. Multi-agent | "Compare our internal architecture with industry practice." | Supervisor → RAG + Research → synthesis |

The contract makes specialists **replaceable**: a future "deep research" agent can swap in behind the same `AgentResult` without redesigning the supervisor.

## 4. RAG pipeline

Document upload → chunking + local embeddings (`all-MiniLM-L6-v2` or provider embeddings) → upsert into the **Qdrant** `documents` collection. At query time:

1. Embed the query.
2. Vector search with a limit (default 5).
3. RAG agent wraps the result in an `AgentResult` with **content** (chunk text, context-capped) and **sources** (human-readable document names).
4. The responder cites those names in the final answer.

The pipeline is read-only and retryable; per-request Qdrant calls have a dedicated 5s timeout and a process-wide circuit breaker.

## 5. Authentication / authorization

- **Authentication:** JWT (HS256, `PyJWT`), password hashing with Argon2.
- **Authorization (RBAC):** three roles with an explicit permission matrix:

| Role | Permissions |
|---|---|
| `USER` | `CHAT`, `RAG_READ` |
| `ANALYST` | `CHAT`, `RAG_READ`, `RESEARCH`, `DATA_READ` |
| `ADMIN` | all of the above + `DATA_WRITE`, `ADMIN` |

- **Tool authorization:** the supervisor drops any specialist the caller lacks permission to run and records a structured `permission_denied` result, so the responder answers deterministically — the LLM can never route into a capability the user doesn't hold. The data agent further enforces **read-only SQL** (`sqlglot` validator).
- **Audit logging:** authentication and tool-authorization events are logged as structured `security_event` records.

## 6. AI guardrails

- **Prompt guard:** user input is validated before any LLM or tool work — injection patterns are rejected at the endpoint and again before the supervisor prompt.
- **Final response validation (`SynthesisPolicy`):** the responder uses **only successful specialist evidence**:
  - A RAG run with no retrievable documents yields a deterministic "no relevant document" message — the assistant does **not** fabricate internal knowledge.
  - Failed / unavailable / unauthorized agents are reported with safe, non-sensitive wording ("external research was unavailable"), never raw exceptions.
  - Citations are collected from successful results and deduplicated.
  - All-failed and permission-denied paths are fully deterministic (no LLM call).
- **Memory is not authority:** stored memories are blocked from becoming instructions, authorization claims, or secrets (see §7).

## 7. Memory

- **Conversation history** lives per conversation in PostgreSQL (`/conversations`) and is loaded into the graph state each request.
- **Long-term memory:** the `memory_retriever` recalls relevant user memories before processing; the `memory_extractor` extracts candidate memories after the answer.
- **Only worthwhile information is stored.** The `MemoryPolicy` discards memories with zero importance, secrets/credentials, authorization claims ("I am admin"), and instruction-like content; the extractor additionally requires evidence text to appear in the user's message. Conversation history ≠ long-term memory.

## 8. Reliability

All config-driven in `app/core/config.py`:

- **Timeouts** per dependency class (LLM 60s, RAG 5s, DB 5s, web 10s, Redis 2s) — never one big timeout for all paths.
- **Retries** with exponential backoff + jitter, only on retryable failures (timeouts, connection errors, 429/5xx — never 4xx).
- **Circuit breakers** (per-dependency: `qdrant`, `web_search`, `database`) prevent retry storms against unhealthy services.
- **Concurrency limit** (`AGENT_CONCURRENCY=3`) via a threading semaphore with fail-fast backpressure (503).
- **Token / cost guard** (`charge_usage`): the supervisor and responder charge every LLM call against a per-request `MAX_TOTAL_TOKENS` budget and stop the loop before it runs away.
- **Agent safety limits:** `MAX_AGENT_STEPS` (supervisor loop) and `MAX_TOOL_CALLS` (specialists).
- **Graceful degradation:** a failed agent is recorded as a structured `success=False` result; the responder still produces a partial answer from whatever succeeded.
- **Response cache** with **permission-scoped keys** (role + permission set + knowledge version), so a cached admin answer can never leak cross-role, and a re-index naturally invalidates entries. Only stable document-grounded answers are cached.

## 9. Observability

One request lifecycle is connected end-to-end by a **`request_id`**:

```
request_received        [req_8f71c9]
supervisor.route        [req_8f71c9]
rag.agent → qdrant      [req_8f71c9]
supervisor.synthesize   [req_8f71c9]
responder→response      [req_8f71c9]
```

- **Logs:** `structlog`/standard structured logging; the `RequestIDMiddleware` stamps every request and the id also flows into graph state (`run_id`).
- **Traces:** OpenTelemetry spans on every node (`agent.rag`, `agent.research`, `agent.data`, `supervisor.route`, `agent.responder`, `memory.*`) — connectors ship for FastAPI and SQLAlchemy.
- **Metrics:** Prometheus counters/histograms for requests, agent failures/timeouts, LLM and token usage, memory extraction, and request duration.

This answers "why did this request take 12 seconds?" from the trace, not by guessing.

## 10. Tech stack

Python 3.12 · FastAPI · LangGraph/LangChain · SQLAlchemy + Alembic · PostgreSQL · Qdrant · Redis · OpenAI / Google Gemini / OpenRouter / Ollama · OpenTelemetry + Prometheus · structlog · PyJWT + Argon2 · pydantic v2.

## 11. Local setup

**Prerequisites:** Docker (PostgreSQL, Qdrant, Redis, MinIO, Jaeger, Prometheus via root `docker-compose.yml`), Python 3.12+.

```bash
# 1. Start infrastructure
docker compose up -d postgres qdrant redis

# 2. Backend
cd backend
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -e .[dev]
cp .env.example .env             # then fill in secrets
alembic upgrade head
uvicorn app.main:app --reload
```

**Tests:** `python -m pytest app/tests` (86 tests covering the agent contract, security/RBAC, reliability, and end-to-end workflows).

## 12. Environment variables

Key configuration lives in `.env` (see `.env.example`). Highlights:

| Variable | Purpose |
|---|---|
| `DATABASE_URL`, `QDRANT_URL`, `REDIS_URL` | Infrastructure connections |
| `LLM_PROVIDER`, `LLM_MODEL`, `LLM_FALLBACK_PROVIDERS/LLM_FALLBACK_MODEL` | Primary + fallback LLM routing |
| `OPENAI_API_KEY` / `GEMINI_API_KEY` / `OPENROUTER_API_KEY` / `OLLAMA_URL` | Provider credentials |
| `TAVILY_API_KEY` | Web research |
| `JWT_SECRET_KEY`, `ACCESS_TOKEN_EXPIRE_MINUTES` | Auth |
| `LLM_TIMEOUT_SECONDS`, `RAG_TIMEOUT_SECONDS`, `DATABASE_TIMEOUT_SECONDS`, `WEB_SEARCH_TIMEOUT_SECONDS` | Per-dependency timeouts |
| `RETRY_MAX_ATTEMPTS`, `CIRCUIT_FAIL_MAX`, `CIRCUIT_RECOVERY_TIMEOUT_SECONDS` | Retry / circuit breaker tuning |
| `MAX_AGENT_STEPS`, `MAX_TOOL_CALLS`, `MAX_TOTAL_TOKENS`, `MAX_CONTEXT_CHARS`, `MAX_QUERY_ROWS` | Agent + cost limits |
| `AGENT_CONCURRENCY` | Backpressure |
| `REDIS_CACHE_TTL_SECONDS`, `KNOWLEDGE_VERSION` | Response cache behavior / invalidation |

## 13. API surface

| Endpoint | Purpose |
|---|---|
| `POST /api/v1/chat/answer` | Main agentic answer (sources + citations + approval status) |
| `POST /api/v1/chat/stream` | Streaming variant |
| `POST /api/v1/documents`, `/search`, `/conversations`, `/memories`, `/approvals`, `/auth`, `/metrics`, `/health` | Document, retrieval, persistence, approval, auth, and ops endpoints |

## 14. Design decisions and known limitations

The "why" behind every major choice — LangGraph, multi-agent supervision, Qdrant vs PostgreSQL, permission-scoped caching, retries/circuit breakers, deterministic no-fabrication paths — is captured in [`docs/architecture-decisions.md`](docs/architecture-decisions.md).

A few honest limitations:

- The LangGraph checkpointer is an in-memory `InMemorySaver`; graph state is not durable across process restarts (conversation persistence lives in PostgreSQL, independent of the graph).
- LLM token counting is an estimate (~4 chars/token), sufficient for a hard budget + cost visibility, not an exact bill.
- Structured data and research answers are dynamic and therefore not cached; only stable document-grounded answers are.
- Concurrency backpressure is process-scoped (single instance). Horizontal scaling and the Kubernetes/AWS deployment (PR-29) are deliberately deferred.
- Web-research quality is bounded by the configured provider (Tavily); a provider outage degrades to a transparent "external research unavailable" partial answer.

## 15. Example workflows

```
User:  "What is our employee leave policy?"
Supervisor → RAG → Qdrant → AgentResult(content=chunk text, sources=[employee_leave_policy.pdf])
Responder:  "Employees receive 20 annual leave days."
              Sources: employee_leave_policy.pdf

User:  "What changed in the latest Java release?"
Supervisor → Research → web_search → AgentResult(content=..., sources=["Java 24 Release Notes — https://openjdk.org/..."])
Responder:  synthesizes with source URL preserved.

User:  "Compare our internal architecture with industry practice."
Supervisor → RAG + Research → SynthesisPolicy → cites BOTH internal documents and external sources.
```