#!/usr/bin/env bash
# Creates a read-only identity (service principal) that CloudPulse uses to
# read this subscription, and prints the four values CloudPulse needs.
#
# Roles granted, on this subscription only:
#   Reader                  - list resources and read the Activity Log
#   Cost Management Reader  - read spend
# It cannot create, change or delete anything.
#
# Use it when CloudPulse runs on your laptop or on a host outside Azure.
# (On Azure App Service, 04-deploy-app.sh uses a managed identity instead,
# which needs no secret at all.)
#
# Usage:  bash scripts/azure/03-reader-identity.sh

source "$(dirname "$0")/_common.sh"
show_account
NAME="${SP_NAME:-cloudpulse-reader}"
bold "This creates (or refreshes the secret of) a read-only identity called '$NAME'."
confirm "Go ahead?"

register_providers Microsoft.CostManagement
SCOPE="/subscriptions/$SUB_ID"
OUT="$(az ad sp create-for-rbac --name "$NAME" --role Reader --scopes "$SCOPE" --years 1 \
  --query "[appId, password]" -o tsv 2>/tmp/cloudpulse-sp.err)" || {
  cat /tmp/cloudpulse-sp.err >&2
  die "Azure refused to create the identity. If your directory blocks app registrations, run CloudPulse on your laptop with 'az login' and AZURE_USE_CLI=true instead."
}
# tsv prints the two values tab-separated (one line) or one per line, depending on CLI version.
OUT="$(printf '%s' "$OUT" | tr '\n' '\t')"
APP_ID="$(printf '%s' "$OUT" | cut -f1)"
SECRET="$(printf '%s' "$OUT" | cut -f2)"
[ -n "$APP_ID" ] && [ -n "$SECRET" ] || die "Azure didn't return the identity details."
OBJ_ID="$(az ad sp show --id "$APP_ID" --query id -o tsv)"
assign_role "$OBJ_ID" "Cost Management Reader" "$SCOPE"

bold "Paste these into CloudPulse"
cat <<EOF

  Option A: Admin → Workspaces & users → Connect Azure
    Subscription ID : $SUB_ID
    Tenant ID       : $TENANT_ID
    Client (app) ID : $APP_ID
    Client secret   : $SECRET

  Option B: backend/.env on your laptop
    AZURE_SUBSCRIPTION_ID=$SUB_ID
    AZURE_TENANT_ID=$TENANT_ID
    AZURE_CLIENT_ID=$APP_ID
    AZURE_CLIENT_SECRET=$SECRET

EOF
warn "The secret is a password. Don't paste it into chats, screenshots or git."
warn "It expires in one year. Run this script again to get a new one."
