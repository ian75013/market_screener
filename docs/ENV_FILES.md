# Environment Files - Market Screener

## Authoritative Files

### Local development

- `.env`
  - local/runtime configuration used by base `docker compose`

### OVH production

- `deploy/scripts/env.ovh`
  - authoritative production file
  - used both as deploy-control env and runtime env copied to the VPS
  - includes Airflow scheduling, startup refresh, fundamentals enrichment, domains and host ports

- `deploy/scripts/env.ovh.example`
  - versioned template for `deploy/scripts/env.ovh`

## Variables by role

### Deploy-control variables in `deploy/scripts/env.ovh`

- `SSH_USER`, `SSH_HOST`, `SSH_PORT`, `SSH_KEY_PATH`
- `APP_DIR`, `LOCAL_ENV_FILE`, `GIT_REPO`, `GIT_BRANCH`
- `APACHE_AUTOCONFIG`, `CERTBOT_AUTOCONFIG`, `CERTBOT_EMAIL`
- `DEPLOY_WAIT_TIMEOUT`, `ROLLBACK_ON_FAILURE`
- `AUTO_PORT_REMAP`

### Runtime variables in `deploy/scripts/env.ovh`

- container bind ports: `POSTGRES_*`, `BACKEND_*`, `FRONTEND_*`, `AIRFLOW_*`
- frontend routing: `VITE_API_URL`
- Airflow schedule: `AIRFLOW_INTRADAY_*`, `AIRFLOW_NIGHTLY_*`
- startup refresh: `STARTUP_*`
- fundamentals enrichment: `FUNDAMENTALS_*`

## Production Rule

If you change Market Screener production behavior, change `deploy/scripts/env.ovh` first.
That file is the exact source used by the OVH deploy pipeline.