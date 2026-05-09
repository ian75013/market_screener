# INFRASTRUCTURE

## Purpose
market_screener provides stock screening APIs and scheduled data refresh pipelines.

## Main Components
- Backend API and data ingestion modules
- Airflow DAGs in airflow/
- Compose orchestration and OVH deployment docs

## Local Run
1. Configure .env variables.
2. Start stack:
   - docker compose up -d --build
3. Validate backend and Airflow services are healthy.

## Deployment
- Use OVH pipeline/deployment documentation and compose overrides.
- Validate refresh jobs and API responses after rollout.

## Operations and Validation
- Check scheduler/worker logs and API health endpoints.
- Verify stock data freshness and fundamentals enrichment status.

## Rollback
- Revert compose/env changes to previous revision.
- Restart services and validate API/data health.
