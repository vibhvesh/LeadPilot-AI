#!/bin/sh
# Selects HTTP or automatic HTTPS before Caddy starts.
# TLS_MODE=auto uses HTTPS when LEADPILOT_DOMAIN is a public hostname,
# and plain HTTP for an empty domain, localhost, or an IP address.
set -eu

mode="${TLS_MODE:-auto}"
domain="${LEADPILOT_DOMAIN:-}"
email="${ACME_EMAIL:-}"
src_dir="/opt/leadpilot-proxy"

strip_quotes() {
  value=$1
  case $value in
    \"*\") value=${value#\"}; value=${value%\"} ;;
    \'*\') value=${value#\'}; value=${value%\'} ;;
  esac
  printf '%s' "$value"
}

mode=$(strip_quotes "$mode")
domain=$(strip_quotes "$domain")
email=$(strip_quotes "$email")
mode=$(printf '%s' "$mode" | tr '[:upper:]' '[:lower:]')

is_ip() {
  printf '%s\n' "$1" | grep -Eq '^([0-9]{1,3}\.){3}[0-9]{1,3}$|^[0-9A-Fa-f:]+$'
}

case $mode in
  http|off|disabled|ip|plain) mode=http ;;
  https|on|tls|acme) mode=https ;;
  auto|"") mode=auto ;;
  *)
    echo "leadpilot-proxy: TLS_MODE must be auto, http, or https (got ${mode})" >&2
    exit 1
    ;;
esac

if [ "$mode" = "auto" ]; then
  if [ -z "$domain" ] || [ "$domain" = "localhost" ] || is_ip "$domain"; then
    mode=http
  else
    mode=https
  fi
fi

if [ "$mode" = "https" ]; then
  if [ -z "$domain" ]; then
    echo "leadpilot-proxy: set LEADPILOT_DOMAIN or use TLS_MODE=http" >&2
    exit 1
  fi
  if is_ip "$domain" || [ "$domain" = "localhost" ]; then
    echo "leadpilot-proxy: ${domain} cannot use a public certificate. Set TLS_MODE=http." >&2
    exit 1
  fi
  if ! printf '%s\n' "$domain" | grep -Eq '^[A-Za-z0-9]([A-Za-z0-9-]{0,61}[A-Za-z0-9])?(\.[A-Za-z0-9]([A-Za-z0-9-]{0,61}[A-Za-z0-9])?)+$'; then
    echo "leadpilot-proxy: LEADPILOT_DOMAIN must be a hostname such as leads.example.com" >&2
    exit 1
  fi
  if [ -n "$email" ] && ! printf '%s\n' "$email" | grep -Eq '^[^@[:space:]]+@[^@[:space:]]+\.[^@[:space:]]+$'; then
    echo "leadpilot-proxy: ACME_EMAIL is not a usable email address" >&2
    exit 1
  fi
  if [ -n "$email" ]; then
    cp "${src_dir}/Caddyfile.https" /tmp/Caddyfile
  else
    grep -v -F 'email {$ACME_EMAIL}' "${src_dir}/Caddyfile.https" > /tmp/Caddyfile
  fi
  echo "leadpilot-proxy: HTTPS for ${domain}"
else
  cp "${src_dir}/Caddyfile.http" /tmp/Caddyfile
  echo "leadpilot-proxy: HTTP only on port 80"
fi

caddy validate --config /tmp/Caddyfile --adapter caddyfile
exec caddy run --config /tmp/Caddyfile --adapter caddyfile
