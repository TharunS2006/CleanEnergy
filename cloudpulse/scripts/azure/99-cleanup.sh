#!/usr/bin/env bash
# Removes what the other scripts created.
#
#   bash scripts/azure/99-cleanup.sh         # demo workload + planted waste
#   bash scripts/azure/99-cleanup.sh --all   # also the deployed app and the reader identity

source "$(dirname "$0")/_common.sh"
show_account
ALL=0
[ "${1:-}" = "--all" ] && ALL=1

groups=("$WORKLOAD_RG" "$LEAK_RG")
[ "$ALL" = "1" ] && groups+=("$APP_RG")

bold "This deletes these resource groups and everything in them:"
for g in "${groups[@]}"; do
  if az group exists -n "$g" | grep -q true; then info "- $g"; else info "- $g (not found, skipped)"; fi
done
[ "$ALL" = "1" ] && info "- the 'cloudpulse-reader' identity, if it exists"
confirm "Delete them?"

for g in "${groups[@]}"; do
  if az group exists -n "$g" | grep -q true; then
    az group delete -n "$g" --yes --no-wait
    info "Deleting $g (continues in the background)"
  fi
done

if [ "$ALL" = "1" ]; then
  for id in $(az ad app list --display-name "${SP_NAME:-cloudpulse-reader}" --query "[].appId" -o tsv); do
    az ad app delete --id "$id"
    info "Deleted identity $id"
  done
fi

bold "Done"
info "Deletion takes a few minutes. On its next sync, CloudPulse moves the removed resources to 'Recently cleaned up'."
