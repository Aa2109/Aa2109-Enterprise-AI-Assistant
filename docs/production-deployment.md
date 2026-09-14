# Production Deployment — PR-29

How the Enterprise AI Assistant runs in production, from a single
Docker image up to a managed AWS / Kubernetes deployment. Read this
alongside the manifests in `infrastructure/`.

---

## 1. The shape of a production deployment

Docker makes the app reproducible; Kubernetes makes it operational.
Each hop answers a specific production problem:

```
        Dockerfile              builds the artifact (locked deps, non-root, no dev tools)
            │
            ▼
        Image (ghcr.io/…:sha-…)  immutable, versioned — never :latest
            │
            ▼
      Kubernetes Deployment      desired state: N replicas, rollout strategy
            │
            ▼
             Pods                ephemeral units running 1 uvicorn each
            │
            ▼
             Service             stable DNS + load balancing across pods
            │
            ▼
             Ingress (ALB)       TLS termination, host/path routing
            │
            ▼
            Edge / users
```

Behind the pods sit the state stores: PostgreSQL (RDS), Redis
(ElastiCache), Qdrant, and object storage (S3/uploaded documents).

## 2. The AI request path

A normal backend is `request → DB → response`. Yours is a chain of
fallible, expensive, slow steps — which is why upstream PR-28
(timeouts, retries, circuit breakers, token budgets, concurrency)
is not optional at deploy time:

```
User → ALB → FastAPI → auth/guardrails → Supervisor
      → [rag | research | data] agents → LLM / RAG / tools
      → reliability controls (timeouts, retries, budget, slots)
      → Response
```

Implications for deployment:

- **Latency is high and variable** — an agent run can take seconds to
  over a minute, so proxy/load-balancer timeouts must be generous
  (the Ingress sets 180 s read/send timeouts for this reason).
- **Requests are expensive** — a request routed to a pod that is not
  healthy *wastes* that cost. Hence readiness gates on `/ready`, not
  just liveness.
- **Cold start is real** — model weights load at import, so the
  Deployment uses a `startupProbe` to tolerate a several-minute warm
  up before readiness applies.
- **Everything AI must stay config-driven** — `MAX_AGENT_STEPS`,
  `MAX_TOOL_CALLS`, `TOKEN_BUDGET`, `TIMEOUTS`, `AGENT_CONCURRENCY`,
  `REDIS_CACHE_TTL` all come from the ConfigMap, never hard-coded.

## 3. Health checks (liveness vs readiness)

|          | `/health`                    | `/ready`                                   |
|----------|------------------------------|--------------------------------------------|
| Question | is the *process* alive?      | can it *serve traffic* now?                |
| Checks   | nothing (deliberately)       | Postgres, Redis, Qdrant round-trip         |
| Returns  | 200 always when not wedged   | 200 all green / 503 any dependency down    |
| Used by  | `livenessProbe`              | `readinessProbe`, Compose healthcheck, LB   |
| Action   | restart the pod              | stop routing traffic (do **not** restart)  |

The asymmetry matters: if Redis blips for 10 seconds, a restart makes
things *worse* (cold start, loss of in-flight work). Removing the pod
from the Service until it recovers is correct.

## 4. Graceful shutdown

Rolling deploys, HPA scale-down and node drains all terminate pods.
In-flight agent requests must be allowed to finish, not vanish:

```
SIGTERM
  → uvicorn stops accepting new connections
  → drains in-flight requests (--timeout-graceful-shutdown 30)
  → lifespan shutdown: close HTTP client pools
  → close Redis connection
  → dispose SQLAlchemy pool
  → exit 0
```

## 5. Config vs secrets

```
                  FastAPI pod
                       │
        ┌──────────────┴───────────────┐
        ▼                              ▼
   ConfigMap                      Secret
   non-sensitive                  credentials
   (timeouts, limits, hostnames)  (DB URL, JWT, API keys)
```

- **ConfigMap** — `ENVIRONMENT`, `MAX_AGENT_STEPS`, timeouts, Qdrant
  service DNS, `KNOWLEDGE_VERSION`.
- **Secret** — `DATABASE_URL`, `JWT_SECRET_KEY`, `OPENAI/GOOGLE/Tavily`
  keys. The committed `secret.yaml` ships **placeholder** values only.
- Kubernetes Secrets are base64, not encryption. For anything real, use
  **AWS Secrets Manager + the External Secrets Operator**, which inject
  credentials at runtime from KMS — they never land in git or in plain
  etcd.
- The repo never contains `.env` (gitignored). `.env.example` and
  `.env.prod.example` document the shape only.

## 6. Resource limits & autoscaling

AI workloads are the worst case for noisy neighbors. Without limits one
agent request can balloon and exhaust the node. Requests guarantee
scheduling (and set the HPA baseline); limits cap damage:

```yaml
resources:
  requests: { cpu: "250m", memory: "512Mi" }
  limits:   { cpu: "1",     memory: "1Gi" }
```

The HPA scales pod count on average CPU utilization (70% of request)
between 2 and 6 replicas, with stabilization windows to avoid thrashing
after spikes. Custom AI metrics (queue depth, token burn) can replace
CPU later — CPU is the correct first step.

## 7. Rolling deployment

```
V1 ── Pod A, Pod B          (2 healthy pods)
deploy V2
V1 ── Pod A, Pod B, Pod C   (V2 surge — new pod joins first)
     → readiness on V2 pod passes → traffic admitted
V2 ── Pod A, B, C           (old pods drain + terminate one at a time)
V2 ── Pod B, C              (settled at 2 replicas)
```

`maxSurge: 1` / `maxUnavailable: 1` means there is always a health
instance serving. Users never see a full outage, which is the whole
point of `Deployment` + `readinessProbe` + graceful shutdown.

## 8. AWS mapping

```
                     AWS
                      │
               ┌──────▼──────┐
               │     ALB     │   Application Load Balancer (TLS)
               └──────┬──────┘
                      ▼
                    EKS
                      │
          ┌───────────┼───────────┐
          ▼           ▼           ▼
       API Pod     API Pod     API Pod   (Deployment + HPA)
          └───────────┼───────────┘
                      ▼
   ┌─────────────┼─────────────┐
   ▼             ▼             ▼
   RDS         ElastiCache    Qdrant (or self-managed)
 PostgreSQL      Redis
                      ▼
                  S3 (docs)
                      ▼
              AI providers (OpenAI/Gemini/Tavily…)
```

| On-prem/compose | AWS managed |
|---|---|
| PostgreSQL | Amazon RDS |
| Redis | ElastiCache |
| MinIO/local uploads | Amazon S3 |
| Docker registry | Amazon ECR |
| Load balancer | ALB via the Ingress controller |
| Secret storage | AWS Secrets Manager |

## 9. Image lifecycle

Immutable tags only — CI stamps the git SHA so a running pod is
always traceable to a commit:

```
enterprise-ai-assistant:1.0.0          # promoted release
enterprise-ai-assistant:gita81f3c2     # per-commit build (what CI pushes)
```

`kubectl set image deployment/enterprise-ai-api api=<...>` then
`kubectl rollout status` performs the rolling update.

## 10. Manual verification checklist

**Docker**
- [ ] `docker build -t enterprise-ai-assistant:1.0.0 ./backend` builds
- [ ] Container starts; `curl localhost:8000/health` → 200
- [ ] `curl localhost:8000/ready` → 200 (all deps up) / 503 (dep down)
- [ ] Down a dependency (e.g. stop Redis) → `/ready` 503, `/health` 200

**Compose (prod)**
- [ ] `docker compose -f infrastructure/docker/docker-compose.prod.yml --env-file infrastructure/docker/.env.prod up -d --build`
- [ ] Backend waits for healthy Postgres/Redis/Qdrant, then starts

**Kubernetes**
- [ ] `kubectl apply -k infrastructure/kubernetes/`
- [ ] `kubectl get pods -n enterprise-ai` → all Running + Ready
- [ ] `kubectl get svc -n enterprise-ai` → Service routes to pods
- [ ] `kubectl describe pod` shows startup/readiness/liveness probes passing
- [ ] Kill a pod (`kubectl delete pod …`) → ReplicaSet recreates it
- [ ] `kubectl get hpa -n enterprise-ai` → reports target/current CPU
- [ ] `kubectl set image deployment/enterprise-ai-api api=new:tag` → rolling update, zero-downtime

**Configuration**
- [ ] `git grep -lE 'sk-|password|secret_key' infra` finds only placeholders
- [ ] Secret contains credentials; ConfigMap contains no credentials
- [ ] Env vars in ConfigMap/Secret override config defaults

## 11. Interview notes

- **Why Kubernetes?** "To manage containerized FastAPI instances —
  service discovery, health checks, rolling deployments and horizontal
  scaling."
- **Why not just Docker Compose?** "Compose is great for local and small
  deployments, but Kubernetes adds orchestration, self-healing, rolling
  deployments, service discovery and autoscaling."
- **Liveness vs readiness?** "Liveness decides whether to restart the
  container; readiness decides whether it gets traffic."
- **Why ConfigMap/Secret?** "ConfigMap holds non-sensitive config;
  Secret holds credentials like API keys and DB passwords."
- **Why readiness probes for AI?** "AI requests are long and expensive.
  I refuse to route traffic to a pod that has started but isn't ready."
- **Why resource limits?** "AI workloads consume significant CPU and
  memory; requests+limits give predictable scheduling and stop one
  workload exhausting the node."
- **Why rolling deployment?** "New versions join gradually while
  healthy old instances keep serving — downtime-free release."