# Deployment Guide

## Local Development (Docker Compose)

### Prerequisites
- Docker Engine 24.0+
- Docker Compose 2.20+
- 4GB RAM minimum
- 2GB free disk space

### Startup

```bash
cd market_screener

# First time setup
docker compose up -d --build

# Subsequent runs
docker compose up -d

# Logs
docker compose logs -f backend
```

### Initial Bootstrap (10-20 minutes)

1. **Startup refresh** (5 min): Fetch initial market data
2. **Fundamentals bootstrap** (12-18 min): Enrich PER, ROE, etc.
3. **Ready for use**

### Access Services

| Service | URL | Purpose |
|---------|-----|---------|
| API | http://localhost:8000 | Backend REST API |
| API Docs | http://localhost:8000/docs | Swagger UI |
| Screener UI | http://localhost:3000 | Web interface |
| Airflow | http://localhost:8080 | DAG scheduler |
| PostgreSQL | localhost:5432 | Database (internal) |

### Cleanup

```bash
# Stop services (keep volumes)
docker compose down

# Stop + reset database
docker compose down -v
```

---

## OVH VPS Deployment

### Prerequisites
- Ubuntu 22.04+ VPS
- Docker installed: `curl https://get.docker.com | sh`
- 4GB RAM, 20GB disk minimum
- Port 8080 (Airflow), 3000 (UI), 8000 (API) accessible

### Deployment Script

```bash
# SSH into VPS
ssh user@vps.ovh

# Clone repository
git clone <repo_url> market-screener
cd market-screener

# Deploy
bash deploy/scripts/deploy_remote.sh
```

Script handles:
1. Environment variable setup
2. Docker image pulling
3. Database initialization
4. Service startup
5. Health checks

### Manual Setup (if script unavailable)

```bash
# Create .env from template
cp deploy/scripts/env.ovh.example deploy/scripts/env.ovh

# Edit with actual values
vim deploy/scripts/env.ovh

# Source environment
source deploy/scripts/env.ovh

# Start services
docker compose -f deploy/docker-compose.ovh.yml up -d --build
```

### Monitoring

```bash
# Check service status
docker compose -f deploy/docker-compose.ovh.yml ps

# Follow logs
docker compose -f deploy/docker-compose.ovh.yml logs -f backend

# Set auto-restart
# (Add --restart=always to docker-compose override file)
```

---

## Kubernetes (Future)

Template structure ready in `deploy/k8s/`:

```
deploy/k8s/
├── base/
│   ├── api-deployment.yaml
│   ├── api-service.yaml
│   ├── postgres-deployment.yaml
│   ├── postgres-configmap.yaml
│   └── kustomization.yaml
└── overlays/
    ├── dev/
    ├── staging/
    └── prod/
```

### Future K8s Deployment

```bash
kubectl apply -f deploy/k8s/overlays/prod
```

Planned for Q2 2026.

---

## Zero-Downtime Updates

### Update Backend Code

```bash
# Pull latest code
git pull origin main

# Rebuild image
docker compose build backend

# Replace running container (old connections drain gracefully)
docker compose up -d backend
```

Airflow DAGs continue running. API traffic briefly unavailable (~5 seconds).

### Update Database Schema (if needed)

```bash
# Backup first
docker compose exec postgres pg_dump -U screener_user market_screener \
  > backup_$(date +%s).sql

# Run migrations
docker compose exec backend alembic upgrade head
```

---

## Scaling Considerations

### For 100+ Stocks
- Increase `FUNDAMENTALS_ROUND_LIMIT` from 120 to 200
- Increase maintenance interval from 30 min to 60 min
- Monitor RAM during bootstrap

### For Multiple Regions
- Deploy separate instances (each manages own stock universe)
- Share configuration via centralized config server
- Aggregate results at API gateway level

### For High Availability
- Run 2+ backend replicas behind load balancer
- PostgreSQL with replication (primary + standby)
- Airflow with HA mode (multiple schedulers)

---

## Security Notes

### Current (Development)
- ✗ No authentication
- ✗ No HTTPS
- ✗ Database password in .env
- ✓ Only for internal/trusted networks

### For Production
- [ ] Add API key authentication (OAuth2)
- [ ] Enable HTTPS with letsencrypt
- [ ] Use secrets manager (AWS Secrets Manager, HashiCorp Vault)
- [ ] Network segmentation (VPC, firewall rules)
- [ ] Regular security audits

---

**Version:** 1.0  
**Last Updated:** April 11, 2026
