#!/usr/bin/env bash
# Puts CloudPulse on your own domain with a free HTTPS certificate.
#
#   bash scripts/azure/06-custom-domain.sh app.yourdomain.in
#
# Use a subdomain such as app. or www. (Azure's free certificate for a bare
# domain like yourdomain.in needs extra DNS steps; point the bare domain to
# the subdomain with your registrar's "forwarding" option instead.)

source "$(dirname "$0")/_common.sh"
HOST="${1:-}"
[ -n "$HOST" ] || die "Give the address to use, e.g. bash scripts/azure/06-custom-domain.sh app.cloudpulse.in"
APP="${APP_NAME:-cloudpulse-${SUFFIX}}"
az webapp show -g "$APP_RG" -n "$APP" -o none 2>/dev/null || die "CloudPulse isn't deployed yet. Run 04-deploy-app.sh first."

SUB_LABEL="${HOST%%.*}"
ZONE="${HOST#*.}"
VERIFY="$(az webapp show -g "$APP_RG" -n "$APP" --query customDomainVerificationId -o tsv)"

bold "Step 1: add these two DNS records at your domain registrar (for $ZONE)"
cat <<EOF

  Type   Name                    Value
  CNAME  $SUB_LABEL                     $APP.azurewebsites.net
  TXT    asuid.$SUB_LABEL               $VERIFY

  (Some registrars want the full name, e.g. $HOST and asuid.$HOST.)
  Changes usually take 5 to 30 minutes to be visible.

EOF
confirm "Have you added both records?"

bold "Step 2: waiting for DNS"
for _ in $(seq 1 30); do
  if nslookup -type=CNAME "$HOST" 2>/dev/null | grep -qi "azurewebsites.net"; then
    info "DNS is visible."
    break
  fi
  info "Not visible yet, checking again in 20 seconds…"
  sleep 20
done

bold "Step 3: attaching $HOST"
az webapp config hostname add -g "$APP_RG" --webapp-name "$APP" --hostname "$HOST" -o none \
  || die "Azure couldn't verify the domain yet. Wait a few minutes and run this again."

bold "Step 4: free HTTPS certificate"
THUMB="$(az webapp config ssl create -g "$APP_RG" -n "$APP" --hostname "$HOST" --query thumbprint -o tsv)" \
  || die "Certificate creation failed. It sometimes needs a few more minutes after DNS changes; run this again."
az webapp config ssl bind -g "$APP_RG" -n "$APP" --certificate-thumbprint "$THUMB" --ssl-type SNI -o none

bold "Done"
info "CloudPulse is now at https://$HOST"
