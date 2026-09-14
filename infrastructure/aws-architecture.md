# AWS Architecture — Enterprise AI Assistant

How the Kubernetes/container pieces in this repo map onto AWS production
services. The goal: an ephemeral, credentials-free, auto-scaling AI
backend with **zero production secrets committed to git**.

```
                          ┌──────────────────────────────────────────────┐
   users ──► Route 53 ──► │ AWS ALB  (TLS via ACM, or ALB Ingress)      │
   (api.example.com)      │   └─► EKS Ingress (nginx) — app logic        │
                          │        └─► Service (ClusterIP)               │
                          │             └─► Deployment (FastAPI pods)    │
                          │                  │  HPA (CPU 70%) ─ Karpenter│
                          │                  ▼                          │
                          │   pods ──► RDS PostgreSQL  (app schema)     │
                          │   pods ──► ElastiCache Redis (cache, queue) │
                          │   pods ──► Qdrant on EKS (vector search)    │
                          │   pods ──► S3 (document/upload storage)     │
                          └──────────────────────────────────────────────┘
    Secrets: AWS Secrets Manager ──► External Secrets Operator ──► Secret
    CI/CD:   GitHub Actions ──► GHCR/ECR ──► kubectl set image / ArgoCD
```

| This repo (portable) | AWS production equivalent | Notes |
|---|---|---|
| `infrastructure/kubernetes/ingress.yaml` | **ALB** (Application Load Balancer) or nginx-Ingress in front of it | Either let ALB Ingress Controller route straight to the Service, or keep nginx-Ingress behind the ALB for path/TLS handling. Cert-manager ↔ **ACM**. |
| `infrastructure/kubernetes/deployment.yaml` | **EKS** (managed node group or Fargate) deployment | `runAsNonRoot: true`, `runAsUser: 10001` carries straight over. Resource requests/limits feed the scheduler and the HPA. |
| `infrastructure/kubernetes/hpa.yaml` | **HPA with EKS **cluster-autoscaler / Karpenter**** | CPU-based scale-out per-pod; node autoscaler scales the *cluster*. AI workloads: budget on cold-start (model weight load) via `startupProbe`. |
| `DATABASE_URL` (secret) | **Amazon RDS** (PostgreSQL) endpoint | Repoint `DATABASE_URL` at the RDS writer endpoint; keep the app schema handled by `alembic upgrade head` in the entrypoint. |
| `REDIS_URL` (secret) | **Amazon ElastiCache for Redis** | Add `?ssl_cert_reqs=none`-style TLS/auth options in the URL for ElastiCache's in-transit encryption. |
| Qdrant `StatefulSet` on EKS | **Qdrant Cloud** (managed) or self-hosted on EKS with EBS/EFS | The readiness probe (`/ready`) exercises Qdrant the same way regardless of where it lives. |
| Local `uploads/` storage | **Amazon S3** | The code stores uploaded documents on the local filesystem today; wire S3 via `boto3` and PUT/GET presigned URLs. Pass bucket + credentials through env, never baked into the image. |

## Secrets flow — the anti-pattern and the fix

:no_entry: **NEVER** `GitHub → .env → production credentials`.

:white_check_mark: The supported path:

```
AWS Secrets Manager ──► External Secrets Operator ──► K8s Secret
                                                          │
                                        secretRef ──► FastAPI env (config.py)
```

`infrastructure/kubernetes/secret.yaml` contains only `change-me`
placeholders so the template is reviewable in git. Real values live in
Secrets Manager and are applied with:

```bash
kubectl create secret generic enterprise-ai-secrets \
  --from-env-file=secrets.env --dry-run=client -o yaml | kubectl apply -f -
```

## Bringing up the stack

```bash
# 1. Cluster + namespaces
eksctl create cluster --name enterprise-ai --region us-east-1

# 2. Managed services (RDS, ElastiCache, S3) via the AWS console/CloudFormation
#    then put their endpoints into the EKS Secret.

# 3. External Secrets Operator (delegates to AWS Secrets Manager)
kubectl apply -k "github.com/external-secrets/external-secrets//deploy/crds?ref=v0.9.x"

# 4. The app
kubectl apply -k infrastructure/kubernetes/
```

## Deploying a new version (rolling update)

```bash
kubectl -n enterprise-ai set image deployment/enterprise-ai-api \
  api=ghcr.io/<org>/enterprise-ai-assistant:<git-sha>
kubectl -n enterprise-ai rollout status deployment/enterprise-ai-api
```

The Deployment's RollingUpdate (maxUnavailable 1, maxSurge 1) plus the
`/ready` readiness gate and SIGTERM drain (`--timeout-graceful-shutdown
30`) give zero-downtime upgrades — an in-flight agent request finishes
before the pod is replaced.