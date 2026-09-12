# Architecture Decisions

This document records the *why* behind the major engineering decisions in the **Enterprise AI Assistant**. Use it as an interview revision sheet: every entry explains a choice in terms of the concrete problem it solves and the trade-off it accepts.

---

## 1. Why LangGraph?

**Used for** stateful, multi-step agent orchestration with a controlled loop.

A single function-based pipeline is simpler and would cover a fixed sequence of steps — but this system has genuinely stateful requirements:

- a **loop** (supervisor → specialist → supervisor, possibly several specialists per request),
- **conditional routing** (which specialist to run next depends on results so far),
- **shared mutable state** between steps (agent results, retrieved chunks, token budget, citations),
- a **checkpoint/thread** per request so each user request owns its execution state.

LangGraph provides this as a first-class primitive (state schemas, conditional edges, checkpoints). **Trade-off:** an extra abstraction over a plain function pipeline; justified because the workflow is genuinely stateful and multi-step.

## 2. Why a supervisor + multi-agent architecture?

Different tasks need **different tools, prompts, authorization boundaries, and failure semantics**:

- RAG agent — reads the internal vector store, retryable, cites documents.
- Research agent — calls a public web search API, treats all content as untrusted.
- Data agent — queries PostgreSQL but must be read-only and permission-gated.

Separating them means each has its own timeout budget, circuit breaker, and permission check, and each is independently testable. A single "everything" agent would mix trusted internal retrieval with untrusted web content and make authorization boundaries hard to reason about.

**Trade-off:** more orchestration surface. That is why specialization is limited to three capabilities (see §3).

## 3. Why not multi-agent everywhere?

Multiple agents add **latency, token consumption, and orchestration complexity**. Each LLM routing call costs tokens and wall-clock time. The rule applied here: **an agent earns its place only when specialization provides value** — a distinct tool, a distinct permission boundary, or distinct failure handling. Generic conversational turns don't spawn a specialist; they go straight to the responder. The supervisor is also bounded (`MAX_AGENT_STEPS`, token budget) so a "lots of agents" design can't become a runaway.

## 4. Why Qdrant for RAG, PostgreSQL as system of record?

**Qdrant** is optimized for vector similarity search — the core of semantic retrieval over document chunks — and stores embeddings efficiently with an API that fits the pipeline.

**PostgreSQL** remains the system of record for everything structured: users, conversations, messages, documents, memory metadata. It is durable, transactional, and already the source of truth.

The split is explicit: Qdrant is a *retrieval index* for vectors (rebuildable from documents); PostgreSQL is *authoritative data*. Knowledge-versioning invalidates cached answers when the index changes, which is only safe because the index is derived data.

**Trade-off:** operating two datastores. Worth it because neither alone does both jobs well.

## 5. Why Redis (and why a graceful fallback)?

Redis provides a **low-latency response cache**. But it is an optional dependency: when Redis is unavailable, the app degrades to a bounded in-memory TTL cache rather than failing. PostgreSQL remains the durable source of truth; the cache only holds derived, short-lived responses.

**Trade-off:** a best-effort cache can serve stale data. This is controlled by (a) caching only stable, document-grounded answers, (b) embedding the `KNOWLEDGE_VERSION` in keys so a re-index invalidates, and (c) short TTLs.

## 6. Why permission-scoped cache keys?

A response generated for one authorization scope must never be served to another. If two users — an admin and a user — ask the identical question and the admin's answer is cached, a naive cache would leak privileged information to the lower-privileged caller.

Cache keys therefore embed the caller's **role + permission set + knowledge version**. A cache hit only occurs for equivalent scopes.

## 7. Why retries?

External and internal dependencies fail transiently (a database connection blip, an HTTP 429, a timeout). A retry with **exponential backoff and jitter** absorbs those without manual intervention.

Crucially, retries are **selective**: only retryable failures (timeouts, connection errors, 429/5xx) retry. A 4xx (the request itself is wrong) is never retried — retrying it would be wasted work.

**Trade-off:** retries add worst-case latency. Bounded by max attempts and backoff caps.

## 8. Why a circuit breaker?

Retries alone can cause a **retry storm**: if a dependency is genuinely down, every request retries it, multiplying load exactly when the service is unhealthy. A circuit breaker trips after `CIRCUIT_FAIL_MAX` consecutive failures, then fails fast (immediate, cheap `success=False` result) until `CIRCUIT_RECOVERY_TIMEOUT_SECONDS` elapses, where it half-opens to test recovery.

Each dependency (`qdrant`, `web_search`, `database`) has its own breaker so one outage doesn't degrade everything.

## 9. Why graceful degradation?

When one agent fails, the rest of the request should still be useful. A failed research agent must not turn an otherwise-answerable question into a 500. Each specialist records a **structured, non-sensitive `success=False` `AgentResult`** and the responder synthesizes a **partial answer** from whatever succeeded, while honestly reporting what was unavailable.

**Trade-off:** partial answers are weaker than complete ones — but a 500 is worse. The SynthesisPolicy ensures the partial answer never fabricates the failed portion.

## 10. Why a standardized `AgentResult` contract?

Every specialist returns the same six fields — `agent`, `success`, `content`, `sources`, `metadata`, `error` — so the supervisor and responder never need to understand a specialist's internals. This makes specialists **replaceable**: a "deep research" agent can substitute for the research agent behind the same contract, and specialists can be added without redesigning the orchestration. It also gives tests a single shape to validate.

## 11. Why a no-fabrication / deterministic responder?

LLMs must not "round out" a partial result into a complete-sounding answer. The responder enforces hard rules via a testable `SynthesisPolicy`:

- **Only successful evidence** is used. A research failure is described as "external research was unavailable", never invented.
- **RAG with no evidence** yields a deterministic "no relevant document" message — the assistant explicitly refuses to fabricate internal knowledge. No LLM call.
- **Failure text is sanitized** — raw exceptions, stack traces, hosts, and credentials never reach the user or the prompt.
- **Permission denials are deterministic** — the responder answers "You are not authorized..." without an LLM, so the model can never be persuaded to assert access it doesn't have.

The nondeterministic LLM path is used only when real evidence exists; the deterministic paths close the hallucination doors.

## 12. Why timeouts per dependency class?

A single global timeout makes every path as slow as the worst dependency. Each dependency gets its own budget — LLM 60s, RAG 5s, database 5s, web search 10s, Redis 2s — so a slow web search doesn't blow the whole request budget, and a hung vector store fails fast.

## 13. Why a per-request token budget?

Agentic loops multiply LLM calls (supervisor → agents → responder). Without a ceiling, a single user request could produce a runaway bill. The supervisor and responder **charge** every LLM call against `MAX_TOTAL_TOKENS` and stop the loop when the budget is exceeded, returning a graceful "processing budget reached" answer.

**Trade-off:** a hard cap may truncate complex multi-agent requests — deliberately, cost safety wins.

## 14. Why OpenTelemetry + structured logging + metrics?

To answer "why did this request take 12 seconds?" from evidence, not guesswork.

- **One `request_id`** (middleware-generated) flows through logs, traces, metrics, audit events, and graph state — the whole request is one lifecycle.
- **Traces** on every node (`agent.rag`, `agent.research`, `supervisor.route`, `agent.responder`, `memory.*`) show agent and tool spans in order.
- **Metrics** capture request/agent/tool latency, LLM + token usage, agent failures, timeouts, cache hits/misses, and circuit-breaker events.

Structured logs (`structlog`) make events machine-parseable; a `security_event` stream keeps audit separate from application logs.

## 15. Why "memory is not authorization"?

Memory should personalize and recall context, but never **grant** anything. A stored memory ("user is an admin") must not let a later request skip RBAC. The `MemoryPolicy` therefore blocks secrets, authorization claims, and instruction-like content from being stored, and the responder treats memory as context only — never as a system instruction, permission, or tool approval.

## 16. Why keep the graph free of the legacy planner nodes?

The older planner/tool-executor flow served single-step routing before specialists existed. The supervisor + specialist path now owns execution; keeping both live would mean two ways to produce one answer, which is exactly the kind of complexity that makes the system hard to reason about. The legacy node files remain only as reference; the compiled graph wires the supervisor path alone.