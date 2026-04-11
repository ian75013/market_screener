#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage: sync_to_vps.sh --host HOST --user USER --dest REMOTE_DIR [options]

Options:
  --port PORT           SSH port (default: 22)
  --key PATH            SSH private key path
  --env-file PATH       Local .env file to copy to remote repo root
  --host HOST           Remote host
  --user USER           Remote SSH user
  --dest REMOTE_DIR     Remote deployment directory
EOF
}

SSH_PORT=22
SSH_KEY_PATH=""
ENV_FILE=""
SSH_HOST=""
SSH_USER=""
REMOTE_DIR=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --port) SSH_PORT="$2"; shift 2 ;;
    --key) SSH_KEY_PATH="$2"; shift 2 ;;
    --env-file) ENV_FILE="$2"; shift 2 ;;
    --host) SSH_HOST="$2"; shift 2 ;;
    --user) SSH_USER="$2"; shift 2 ;;
    --dest) REMOTE_DIR="$2"; shift 2 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown argument: $1" >&2; usage; exit 1 ;;
  esac
done

if [[ -z "$SSH_HOST" || -z "$SSH_USER" || -z "$REMOTE_DIR" ]]; then
  usage
  exit 1
fi

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd -- "${SCRIPT_DIR}/.." && pwd)"
REMOTE="${SSH_USER}@${SSH_HOST}"

SSH_ARGS=(-p "$SSH_PORT")
RSYNC_RSH=(ssh -p "$SSH_PORT")
SCP_ARGS=(-P "$SSH_PORT")
if [[ -n "$SSH_KEY_PATH" ]]; then
  SSH_KEY_PATH="${SSH_KEY_PATH/#\~/$HOME}"
  SSH_ARGS+=(-i "$SSH_KEY_PATH")
  RSYNC_RSH+=(-i "$SSH_KEY_PATH")
  SCP_ARGS+=(-i "$SSH_KEY_PATH")
fi

ssh "${SSH_ARGS[@]}" "$REMOTE" "mkdir -p '$REMOTE_DIR'"

rsync -az --delete \
  --exclude '.git' \
  --exclude 'frontend/node_modules' \
  --exclude 'frontend/dist' \
  --exclude '__pycache__' \
  --exclude '.pytest_cache' \
  --exclude '.mypy_cache' \
  --exclude 'postgres_data' \
  --exclude 'airflow_logs' \
  --exclude '.env' \
  -e "${RSYNC_RSH[*]}" \
  "$REPO_ROOT/" "$REMOTE:$REMOTE_DIR/"

if [[ -n "$ENV_FILE" ]]; then
  scp "${SCP_ARGS[@]}" "$ENV_FILE" "$REMOTE:$REMOTE_DIR/.env"
  ssh "${SSH_ARGS[@]}" "$REMOTE" "chmod 600 '$REMOTE_DIR/.env'"
fi

echo "Sync complete: $REMOTE:$REMOTE_DIR"