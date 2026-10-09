#!/usr/bin/env bash
# Deploys CloudPulse to Azure App Service (Linux, Python) in this subscription.
#
# - The app signs in to Azure with its own managed identity: no keys or
#   secrets are stored anywhere. It gets Reader + Cost Management Reader on
#   this subscription only.
# - A customer workspace for this subscription is created automatically.
# - You choose the admin email and password; the script asks for them.
# - Data is kept in SQLite under /home, which App Service keeps across restarts.
#
# Cost: App Service plan B1, about $13 a month (needed for a custom domain
# with a free HTTPS certificate).
#
# Run it from the unzipped cloudpulse folder (the one with backend/ in it):
#   bash scripts/azure/04-deploy-app.sh
# Run it again after changing the code to redeploy; settings are kept.

source "$(dirname "$0")/_common.sh"
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
[ -f "$ROOT/backend/app/main.py" ] || die "Run this from the cloudpulse folder (couldn't find backend/app/main.py)."

show_account
APP="${APP_NAME:-cloudpulse-${SUFFIX}}"
PLAN="${APP}-plan"
bold "This deploys CloudPulse as https://$APP.azurewebsites.net in resource group '$APP_RG'."
confirm "Go ahead?"

pick_location
register_providers Microsoft.Web Microsoft.CostManagement

EXISTS=0
az webapp show -g "$APP_RG" -n "$APP" -o none 2>/dev/null && EXISTS=1

if [ "$EXISTS" = "0" ]; then
  bold "Admin account"
  read -r -p "  Admin email: " ADMIN_EMAIL
  [ -n "$ADMIN_EMAIL" ] || die "An admin email is required."
  while true; do
    read -r -s -p "  Admin password (10+ chars, upper, lower, number): " ADMIN_PASSWORD; echo
    read -r -s -p "  Repeat it: " AGAIN; echo
    if [ "$ADMIN_PASSWORD" != "$AGAIN" ]; then warn "They don't match. Try again."; continue; fi
    if [ "${#ADMIN_PASSWORD}" -lt 10 ] || ! [[ "$ADMIN_PASSWORD" =~ [A-Z] ]] || ! [[ "$ADMIN_PASSWORD" =~ [a-z] ]] || ! [[ "$ADMIN_PASSWORD" =~ [0-9] ]]; then
      warn "Use at least 10 characters with upper and lower case letters and a number."; continue
    fi
    break
  done
  read -r -p "  Name for this subscription's workspace [${SUB_NAME}]: " WS_NAME
  WS_NAME="${WS_NAME:-$SUB_NAME}"

  bold "App Service"
  az group create -n "$APP_RG" -l "$LOCATION" --tags purpose=cloudpulse-app -o none
  az appservice plan create -g "$APP_RG" -n "$PLAN" -l "$LOCATION" --sku B1 --is-linux -o none
  RUNTIME="PYTHON:3.12"
  az webapp list-runtimes --os-type linux -o tsv 2>/dev/null | grep -q "PYTHON:3.12" || RUNTIME="PYTHON:3.11"
  az webapp create -g "$APP_RG" -p "$PLAN" -n "$APP" --runtime "$RUNTIME" -o none
  info "$APP created ($RUNTIME)"

  bold "Managed identity and read-only access"
  PRINCIPAL="$(az webapp identity assign -g "$APP_RG" -n "$APP" --query principalId -o tsv)"
  assign_role "$PRINCIPAL" "Reader" "/subscriptions/$SUB_ID"
  assign_role "$PRINCIPAL" "Cost Management Reader" "/subscriptions/$SUB_ID"

  bold "Settings"
  az webapp config appsettings set -g "$APP_RG" -n "$APP" -o none --settings \
    AZURE_SUBSCRIPTION_ID="$SUB_ID" \
    AZURE_USE_MANAGED_IDENTITY=true \
    WORKSPACE_NAME="$WS_NAME" \
    ADMIN_EMAIL="$ADMIN_EMAIL" \
    ADMIN_PASSWORD="$ADMIN_PASSWORD" \
    APP_SECRET_KEY="$(openssl rand -base64 36 | tr -d '\n')" \
    DATABASE_URL="sqlite:////home/data/cloudpulse.db" \
    COOKIE_SECURE=true \
    COLLECT_INTERVAL_MINUTES=180 \
    FORWARDED_ALLOW_IPS="*" \
    SCM_DO_BUILD_DURING_DEPLOYMENT=true \
    WEBSITES_CONTAINER_START_TIME_LIMIT=600
  unset ADMIN_PASSWORD AGAIN
  az webapp config set -g "$APP_RG" -n "$APP" -o none \
    --startup-file "python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --proxy-headers" \
    --always-on true --ftps-state Disabled --min-tls-version 1.2 --http20-enabled true
  az webapp update -g "$APP_RG" -n "$APP" --https-only true -o none
  info "Settings saved"
else
  bold "Updating the existing app $APP (settings unchanged)"
fi

bold "Uploading code"
PKG="$(mktemp -d)/cloudpulse.zip"
( cd "$ROOT/backend" && zip -qr "$PKG" . -x 'venv/*' '.env' '*.db' '*/__pycache__/*' '__pycache__/*' )
info "Package: $(du -h "$PKG" | cut -f1)"
az webapp deploy -g "$APP_RG" -n "$APP" --src-path "$PKG" --type zip --async false -o none \
  || warn "The upload reported a problem. Check Deployment Center in the portal, then run this again."
rm -f "$PKG"

bold "Checking it's up (the first start installs packages and can take a few minutes)"
URL="https://$APP.azurewebsites.net"
for _ in $(seq 1 40); do
  if [ "$(curl -s -o /dev/null -w '%{http_code}' "$URL/api/health")" = "200" ]; then
    info "CloudPulse is running."
    break
  fi
  sleep 10
done

bold "Done"
info "Open:        $URL"
info "Sign in as:  the admin email and password you just chose"
info "Logs:        az webapp log tail -g $APP_RG -n $APP"
info "Your domain: bash scripts/azure/06-custom-domain.sh app.yourdomain.in"
