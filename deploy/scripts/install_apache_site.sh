#!/usr/bin/env bash
set -euo pipefail

if [ "$(id -u)" -ne 0 ]; then
  echo "Run this script as root (sudo)."
  exit 1
fi

if [ "$#" -lt 4 ] || [ "$#" -gt 5 ]; then
  echo "Usage: $0 API_DOMAIN APP_DOMAIN API_HOST_PORT APP_HOST_PORT [CERTBOT_EMAIL]"
  exit 1
fi

API_DOMAIN="$1"
APP_DOMAIN="$2"
API_HOST_PORT="$3"
APP_HOST_PORT="$4"
CERTBOT_EMAIL="${5:-}"

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd -- "${SCRIPT_DIR}/../.." && pwd)"
TEMPLATE_FILE="${REPO_ROOT}/deploy/reverse-proxy/apache/market-screener.prod.example.conf"
TARGET_FILE="/etc/apache2/sites-available/market-screener.conf"

if [ ! -f "${TEMPLATE_FILE}" ]; then
  echo "Template not found: ${TEMPLATE_FILE}"
  exit 1
fi

if ! command -v apache2ctl >/dev/null 2>&1; then
  apt-get update
  apt-get install -y apache2
fi

tmpfile=$(mktemp)
trap 'rm -f "${tmpfile}"' EXIT

sed \
  -e "s|__API_DOMAIN__|${API_DOMAIN}|g" \
  -e "s|__APP_DOMAIN__|${APP_DOMAIN}|g" \
  -e "s|__API_HOST_PORT__|${API_HOST_PORT}|g" \
  -e "s|__APP_HOST_PORT__|${APP_HOST_PORT}|g" \
  "${TEMPLATE_FILE}" > "${tmpfile}"

cp "${tmpfile}" "${TARGET_FILE}"

a2enmod proxy proxy_http headers rewrite >/dev/null
a2dissite 000-default >/dev/null 2>&1 || true
a2ensite market-screener.conf >/dev/null

apache2ctl configtest
systemctl enable apache2
systemctl reload apache2 || systemctl restart apache2

if [ -n "${CERTBOT_EMAIL}" ]; then
  if ! command -v certbot >/dev/null 2>&1; then
    apt-get update
    apt-get install -y certbot python3-certbot-apache
  fi

  certbot --apache \
    --non-interactive \
    --agree-tos \
    --redirect \
    --email "${CERTBOT_EMAIL}" \
    -d "${API_DOMAIN}" \
    -d "${APP_DOMAIN}"
fi

echo "Apache site installed: ${TARGET_FILE}"
echo "API domain: ${API_DOMAIN} -> 127.0.0.1:${API_HOST_PORT}"
echo "App domain: ${APP_DOMAIN} -> 127.0.0.1:${APP_HOST_PORT}"
if [ -n "${CERTBOT_EMAIL}" ]; then
  echo "HTTPS enabled via Certbot for: ${API_DOMAIN}, ${APP_DOMAIN}"
fi