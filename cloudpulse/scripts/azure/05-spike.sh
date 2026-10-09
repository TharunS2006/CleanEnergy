#!/usr/bin/env bash
# Stages a real cost spike so CloudPulse's Anomalies page has something to
# find. It scales the workload VM and web app up for a day, then back down.
#
# Needs a few days of normal spend first (the check compares a day with the
# 7 days before it), so run 01-workload.sh at least a week earlier.
#
#   bash scripts/azure/05-spike.sh up     # about +$7 for the day
#   bash scripts/azure/05-spike.sh down   # run this ~24 hours later
#
# The spike shows up in CloudPulse once Azure publishes that day's costs
# (8 to 24 hours after it happens).

source "$(dirname "$0")/_common.sh"
MODE="${1:-}"
[ "$MODE" = "up" ] || [ "$MODE" = "down" ] || die "Say 'up' or 'down'. Example: bash scripts/azure/05-spike.sh up"
show_account

VM=shop-api-vm
PLAN="shop-plan-${SUFFIX}"
az vm show -g "$WORKLOAD_RG" -n "$VM" -o none 2>/dev/null || die "No workload VM found. Run 01-workload.sh first."

if [ "$MODE" = "up" ]; then
  BIG="${SPIKE_SIZE:-Standard_D4s_v3}"
  bold "Scaling up: $VM → $BIG, $PLAN → P1v3"
  confirm "This costs roughly \$7 extra per day until you run 'down'. Continue?"
  az vm resize -g "$WORKLOAD_RG" -n "$VM" --size "$BIG" -o none \
    || die "Azure refused $BIG here. Try SPIKE_SIZE=Standard_D4as_v5 bash scripts/azure/05-spike.sh up"
  az appservice plan update -g "$WORKLOAD_RG" -n "$PLAN" --sku P1V3 -o none \
    || warn "The web app plan couldn't move to P1v3; the VM spike alone is enough."
  info "Scaled up at $(date -u '+%Y-%m-%d %H:%M UTC'). Run 'down' in about 24 hours."
else
  BASE="$(az vm show -g "$WORKLOAD_RG" -n "$VM" --query tags.baseSize -o tsv)"
  BASE="${BASE:-Standard_B2s}"
  bold "Scaling back down: $VM → $BASE, $PLAN → B1"
  az vm resize -g "$WORKLOAD_RG" -n "$VM" --size "$BASE" -o none
  az appservice plan update -g "$WORKLOAD_RG" -n "$PLAN" --sku B1 -o none || true
  info "Back to normal. The spike day will appear under Anomalies once Azure publishes it."
fi
