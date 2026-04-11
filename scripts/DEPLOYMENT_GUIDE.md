# Market Screener - OVH VPS Deployment Guide

This project includes deployment scripts for a Docker-based OVH VPS setup.

## Files

- `scripts/sync_to_vps.sh`: synchronize the repository and `.env` to the VPS
- `scripts/deploy_market_screener_ovh.sh`: full remote deployment helper
- `deploy/docker-compose.ovh.yml`: production OVH/VPS compose override
- `deploy/scripts/env.ovh.example`: deployment variables example
- `deploy/scripts/install_apache_site.sh`: Apache reverse proxy installer

## Recommended Flow

1. Copy the deployment env template:

```bash
cp deploy/scripts/env.ovh.example deploy/scripts/env.ovh
```

2. Edit `deploy/scripts/env.ovh` with your OVH values:

```bash
SSH_USER=ubuntu
SSH_HOST=<your-vps-ip-or-dns>
SSH_KEY_PATH=~/.ssh/ovh.key
APP_DIR=/opt/market_screener
LOCAL_ENV_FILE=.env

API_DOMAIN=api.market.screener.doctumconsilium.com
APP_DOMAIN=market.screener.doctumconsilium.com
VITE_API_URL=https://api.market.screener.doctumconsilium.com/api/v1

AIRFLOW_BIND_DOMAIN=doctumconsilium.com
AIRFLOW_BIND_HOST=10.8.0.1
AIRFLOW_REQUIRE_VPN=true
AIRFLOW_PORT=8088
APACHE_AUTOCONFIG=true
CERTBOT_AUTOCONFIG=true
CERTBOT_EMAIL=admin@doctumconsilium.com
DEPLOY_WAIT_TIMEOUT=300
ROLLBACK_ON_FAILURE=true
```

3. Run the deployment:

```bash
./scripts/deploy_market_screener_ovh.sh deploy/scripts/env.ovh
```

## Sync Only

```bash
./scripts/sync_to_vps.sh \
  --host <your-vps-ip-or-dns> \
  --user ubuntu \
  --key ~/.ssh/ovh.key \
  --dest /opt/market_screener \
  --env-file .env
```

## What The Deploy Script Does

- Syncs the repository to the remote VPS
- Transfers the selected `.env` file securely
- Installs Docker Engine and Docker Compose plugin if missing
- Starts the stack with:

```bash
docker compose -f docker-compose.yml -f deploy/docker-compose.ovh.yml up -d --build
```

- Optionally installs an Apache reverse proxy for the app and API domains
- Optionally provisions HTTPS certificates with Certbot for Apache
- Waits for service healthchecks before considering the deployment successful
- Performs a minimal rollback to previous backend/frontend images if the new deploy fails health checks

## Port Exposure Model On OVH

- PostgreSQL: bound to `127.0.0.1` by default
- Backend API: bound to `127.0.0.1` by default
- Frontend: bound to `127.0.0.1` by default
- Airflow: bound to `AIRFLOW_BIND_HOST`, which can be your VPN IP

This means the public entry points should normally be handled by Apache/Nginx/Caddy on the host.

## HTTPS Autoconfig With Certbot

If `APACHE_AUTOCONFIG=true` and `CERTBOT_AUTOCONFIG=true`, the deployment script will:

- install Apache if missing
- install Certbot with the Apache plugin if missing
- configure HTTP reverse proxy vhosts
- request certificates for `API_DOMAIN` and `APP_DOMAIN`
- enable HTTPS redirect automatically

Requirements:

- DNS for `API_DOMAIN` and `APP_DOMAIN` must already point to the VPS
- ports 80 and 443 must be open on the OVH firewall/security group
- Apache must be the public entry point on the VPS

## Minimal Rollback

The deployment script tags the current backend and frontend images before rebuilding.

If `docker compose up --build --wait` fails health checks and `ROLLBACK_ON_FAILURE=true`, the script retags the previous images and attempts to restore the last working application revision.

## Airflow On VPN

Set `AIRFLOW_BIND_HOST` to the VPN IP of the host.

Example:

```bash
AIRFLOW_BIND_HOST=10.8.0.1
AIRFLOW_PORT=8088
```

You can also let the deploy script infer the IP from DNS:

```bash
AIRFLOW_BIND_DOMAIN=doctumconsilium.com
AIRFLOW_BIND_HOST=auto
```

The script resolves the IPv4 from DNS and uses it as bind host for Airflow.

Important: with `AIRFLOW_REQUIRE_VPN=true`, deployment fails if the resolved/bound IP is not in private/VPN ranges (`10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`, `100.64.0.0/10`).

With that configuration, Airflow is reachable only through the VPN network.