#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd -- "${SCRIPT_DIR}/.." && pwd)"
ENV_FILE="${1:-${REPO_ROOT}/deploy/scripts/env.ovh.example}"

if [[ ! -f "$ENV_FILE" ]]; then
  echo "Missing env file: $ENV_FILE" >&2
  exit 1
fi

set -a
source "$ENV_FILE"
set +a

: "${SSH_USER:?Set SSH_USER in $ENV_FILE}"
: "${SSH_HOST:?Set SSH_HOST in $ENV_FILE}"
: "${APP_DIR:?Set APP_DIR in $ENV_FILE}"

SSH_PORT="${SSH_PORT:-22}"
SSH_KEY_PATH="${SSH_KEY_PATH:-}"
LOCAL_ENV_FILE="${LOCAL_ENV_FILE:-${REPO_ROOT}/.env}"
SYNC_SCRIPT="${REPO_ROOT}/scripts/sync_to_vps.sh"
REMOTE="${SSH_USER}@${SSH_HOST}"
DEPLOY_WAIT_TIMEOUT="${DEPLOY_WAIT_TIMEOUT:-300}"
ROLLBACK_ON_FAILURE="${ROLLBACK_ON_FAILURE:-true}"
AIRFLOW_BIND_DOMAIN="${AIRFLOW_BIND_DOMAIN:-doctumconsilium.com}"
AIRFLOW_REQUIRE_VPN="${AIRFLOW_REQUIRE_VPN:-true}"

is_vpn_or_private_ipv4() {
  local ip="$1"
  [[ "$ip" =~ ^10\. ]] && return 0
  [[ "$ip" =~ ^192\.168\. ]] && return 0
  [[ "$ip" =~ ^172\.(1[6-9]|2[0-9]|3[0-1])\. ]] && return 0
  [[ "$ip" =~ ^100\.(6[4-9]|[7-9][0-9]|1[01][0-9]|12[0-7])\. ]] && return 0
  return 1
}

resolve_ipv4_from_domain() {
  local domain="$1"
  local resolved=""

  if command -v getent >/dev/null 2>&1; then
    resolved="$(getent ahostsv4 "$domain" | awk 'NR==1{print $1}')"
  fi

  if [[ -z "$resolved" ]] && command -v dig >/dev/null 2>&1; then
    resolved="$(dig +short A "$domain" | head -n 1)"
  fi

  if [[ -z "$resolved" ]] && command -v nslookup >/dev/null 2>&1; then
    resolved="$(nslookup "$domain" 2>/dev/null | awk '/^Address: /{print $2}' | head -n 1)"
  fi

  printf '%s' "$resolved"
}

if [[ -z "${AIRFLOW_BIND_HOST:-}" || "${AIRFLOW_BIND_HOST:-}" == "auto" ]]; then
  resolved_ip="$(resolve_ipv4_from_domain "$AIRFLOW_BIND_DOMAIN")"
  if [[ -n "$resolved_ip" ]]; then
    AIRFLOW_BIND_HOST="$resolved_ip"
    echo "Resolved AIRFLOW_BIND_HOST from DNS ${AIRFLOW_BIND_DOMAIN}: ${AIRFLOW_BIND_HOST}"
  else
    echo "Could not resolve ${AIRFLOW_BIND_DOMAIN} for AIRFLOW_BIND_HOST" >&2
    exit 1
  fi
fi

if [[ "$AIRFLOW_REQUIRE_VPN" == "true" ]]; then
  if ! is_vpn_or_private_ipv4 "$AIRFLOW_BIND_HOST"; then
    echo "AIRFLOW_BIND_HOST=${AIRFLOW_BIND_HOST} is not in VPN/private ranges." >&2
    echo "Set AIRFLOW_BIND_HOST to your VPN IP (for example 100.x.x.x for Tailscale)." >&2
    exit 1
  fi
fi

if [[ -n "$SSH_KEY_PATH" ]]; then
  SSH_KEY_PATH="${SSH_KEY_PATH/#\~/$HOME}"
fi
if [[ "$LOCAL_ENV_FILE" != /* ]]; then
  LOCAL_ENV_FILE="${REPO_ROOT}/${LOCAL_ENV_FILE}"
fi

SSH_ARGS=(-p "$SSH_PORT")
if [[ -n "$SSH_KEY_PATH" ]]; then
  SSH_ARGS+=(-i "$SSH_KEY_PATH")
fi

if [[ ! -x "$SYNC_SCRIPT" ]]; then
  chmod +x "$SYNC_SCRIPT"
fi

sync_args=(
  --host "$SSH_HOST"
  --user "$SSH_USER"
  --port "$SSH_PORT"
  --dest "$APP_DIR"
)
if [[ -n "$SSH_KEY_PATH" ]]; then
  sync_args+=(--key "$SSH_KEY_PATH")
fi
if [[ -n "$LOCAL_ENV_FILE" ]]; then
  sync_args+=(--env-file "$LOCAL_ENV_FILE")
fi

"$SYNC_SCRIPT" "${sync_args[@]}"

ssh "${SSH_ARGS[@]}" "$REMOTE" bash -s -- \
  "$APP_DIR" \
  "${POSTGRES_BIND_HOST:-127.0.0.1}" \
  "${POSTGRES_HOST_PORT:-5432}" \
  "${BACKEND_BIND_HOST:-127.0.0.1}" \
  "${BACKEND_HOST_PORT:-18000}" \
  "${FRONTEND_BIND_HOST:-127.0.0.1}" \
  "${FRONTEND_HOST_PORT:-13000}" \
  "${AIRFLOW_BIND_HOST:-127.0.0.1}" \
  "${AIRFLOW_PORT:-8088}" \
  "${VITE_API_URL:-http://127.0.0.1:18000/api/v1}" \
  "$DEPLOY_WAIT_TIMEOUT" \
  "$ROLLBACK_ON_FAILURE" <<'REMOTE_SCRIPT'
set -euo pipefail

APP_DIR="$1"
POSTGRES_BIND_HOST="$2"
POSTGRES_HOST_PORT="$3"
BACKEND_BIND_HOST="$4"
BACKEND_HOST_PORT="$5"
FRONTEND_BIND_HOST="$6"
FRONTEND_HOST_PORT="$7"
AIRFLOW_BIND_HOST="$8"
AIRFLOW_PORT="$9"
VITE_API_URL="${10}"
DEPLOY_WAIT_TIMEOUT="${11}"
ROLLBACK_ON_FAILURE="${12}"

PRESERVE_ENV_VARS="POSTGRES_BIND_HOST,POSTGRES_HOST_PORT,BACKEND_BIND_HOST,BACKEND_HOST_PORT,FRONTEND_BIND_HOST,FRONTEND_HOST_PORT,AIRFLOW_BIND_HOST,AIRFLOW_PORT,VITE_API_URL"

run_compose() {
  sudo --preserve-env="$PRESERVE_ENV_VARS" docker compose \
    -f docker-compose.yml \
    -f deploy/docker-compose.ovh.yml "$@"
}

backup_image() {
  local source_image="$1"
  local backup_image="$2"
  if sudo docker image inspect "$source_image" >/dev/null 2>&1; then
    sudo docker image tag "$source_image" "$backup_image"
    echo "$backup_image"
  fi
}

restore_image() {
  local backup_image="$1"
  local target_image="$2"
  if [[ -n "$backup_image" ]] && sudo docker image inspect "$backup_image" >/dev/null 2>&1; then
    sudo docker image tag "$backup_image" "$target_image"
  fi
}

if ! command -v docker >/dev/null 2>&1; then
  sudo apt-get update
  sudo apt-get install -y ca-certificates curl gnupg
  sudo install -m 0755 -d /etc/apt/keyrings
  if [[ ! -f /etc/apt/keyrings/docker.gpg ]]; then
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
    sudo chmod a+r /etc/apt/keyrings/docker.gpg
  fi
  . /etc/os-release
  echo \
    "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu ${VERSION_CODENAME} stable" | \
    sudo tee /etc/apt/sources.list.d/docker.list >/dev/null
  sudo apt-get update
  sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
  sudo systemctl enable --now docker
fi

cd "$APP_DIR"

if [[ ! -f .env ]]; then
  echo "Missing remote .env in $APP_DIR" >&2
  exit 1
fi

export POSTGRES_BIND_HOST POSTGRES_HOST_PORT BACKEND_BIND_HOST BACKEND_HOST_PORT
export FRONTEND_BIND_HOST FRONTEND_HOST_PORT AIRFLOW_BIND_HOST AIRFLOW_PORT VITE_API_URL

backup_suffix="$(date +%Y%m%d%H%M%S)"
backend_backup="$(backup_image market-screener/backend:ovh market-screener/backend:backup-${backup_suffix} || true)"
frontend_backup="$(backup_image market-screener/frontend:ovh market-screener/frontend:backup-${backup_suffix} || true)"

if ! run_compose up -d --build --wait --wait-timeout "$DEPLOY_WAIT_TIMEOUT"; then
  echo "Deployment health checks failed." >&2
  if [[ "$ROLLBACK_ON_FAILURE" == "true" ]]; then
    echo "Attempting minimal rollback to previous backend/frontend images..." >&2
    restore_image "$backend_backup" market-screener/backend:ovh
    restore_image "$frontend_backup" market-screener/frontend:ovh
    run_compose up -d --wait --wait-timeout "$DEPLOY_WAIT_TIMEOUT" || true
  fi
  exit 1
fi

run_compose ps
REMOTE_SCRIPT

if [[ "${APACHE_AUTOCONFIG:-false}" == "true" ]]; then
  : "${API_DOMAIN:?Set API_DOMAIN when APACHE_AUTOCONFIG=true}"
  : "${APP_DOMAIN:?Set APP_DOMAIN when APACHE_AUTOCONFIG=true}"
  certbot_email_arg=""
  if [[ "${CERTBOT_AUTOCONFIG:-false}" == "true" ]]; then
    : "${CERTBOT_EMAIL:?Set CERTBOT_EMAIL when CERTBOT_AUTOCONFIG=true}"
    certbot_email_arg="'${CERTBOT_EMAIL}'"
  fi
  ssh -tt "${SSH_ARGS[@]}" "$REMOTE" "cd '$APP_DIR' && sudo chmod +x deploy/scripts/install_apache_site.sh && sudo ./deploy/scripts/install_apache_site.sh '$API_DOMAIN' '$APP_DOMAIN' '${BACKEND_HOST_PORT:-18000}' '${FRONTEND_HOST_PORT:-13000}' ${certbot_email_arg}"
fi

echo "Deployment completed for $REMOTE:$APP_DIR"