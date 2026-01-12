# HORNET Deployment Guide

## Prerequisites

- Docker & Docker Compose
- Kubernetes cluster (for production)
- PostgreSQL 16 with pgvector
- Redis 7.x
- API keys: Anthropic, OpenAI

## Quick Start (Docker)

```bash
# Clone repository
git clone https://github.com/hornet/hornet.git
cd hornet

# Configure environment
cp .env.example .env
# Edit .env with your API keys

# Start services
docker-compose up -d

# Run migrations
docker-compose exec api alembic upgrade head

# Access dashboard
open http://localhost:8000/dashboard
```

## Production (Kubernetes)

```bash
# Create namespace
kubectl apply -f k8s/namespace.yaml

# Create secrets
kubectl create secret generic hornet-secrets \
  --from-literal=ANTHROPIC_API_KEY=your_key \
  --from-literal=OPENAI_API_KEY=your_key \
  --from-literal=SECRET_KEY=your_secret \
  -n hornet

# Deploy with Helm
helm install hornet ./helm/hornet \
  -f helm/hornet/values.yaml \
  --set secrets.anthropicApiKey=$ANTHROPIC_API_KEY \
  -n hornet

# Or raw manifests
kubectl apply -f k8s/
```

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| ANTHROPIC_API_KEY | Yes | Claude API key |
| OPENAI_API_KEY | Yes | For embeddings |
| SECRET_KEY | Yes | Encryption key |
| DATABASE_URL | Yes | PostgreSQL connection |
| REDIS_URL | Yes | Redis connection |
| LOG_LEVEL | No | INFO, DEBUG, etc |

## Scaling

```yaml
# HPA for API pods
minReplicas: 3
maxReplicas: 10
targetCPUUtilization: 70

# HPA for workers
minReplicas: 5
maxReplicas: 20
```

## Monitoring

- Prometheus metrics: `/metrics`
- Health checks: `/api/v1/health`
- Grafana dashboards included
