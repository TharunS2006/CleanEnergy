#!/usr/bin/env bash
# Leaves some things running on purpose, the way people really do, so
# CloudPulse's Waste and Owners pages have real findings:
#   - a disk attached to nothing
#   - a static public IP attached to nothing
#   - a snapshot whose disk has been deleted
#   - a VM shut down with "stop" (still billed) instead of "deallocate"
# None of them carries an owner tag. CloudPulse finds the creator from the
# Activity Log.
#
# Cost: about $0.30 a day, mostly the stopped VM.
# Usage:  bash scripts/azure/02-leaks.sh          (all four)
#         SKIP_VM=1 bash scripts/azure/02-leaks.sh (no VM)

source "$(dirname "$0")/_common.sh"
show_account
bold "This creates resource group '$LEAK_RG' with four idle resources."
confirm "Go ahead?"

pick_location
register_providers Microsoft.Compute Microsoft.Network

az group create -n "$LEAK_RG" -l "$LOCATION" --tags purpose=cloudpulse-demo -o none

bold "1. Disk attached to nothing"
az disk create -g "$LEAK_RG" -n leftover-disk --size-gb 4 --sku Standard_LRS -o none
info "leftover-disk (4 GB)"

bold "2. Public IP attached to nothing"
az network public-ip create -g "$LEAK_RG" -n unused-ip --sku Standard --allocation-method Static -o none
info "unused-ip ($(az network public-ip show -g "$LEAK_RG" -n unused-ip --query ipAddress -o tsv))"

bold "3. Snapshot of a disk that no longer exists"
az disk create -g "$LEAK_RG" -n temp-disk --size-gb 1 --sku Standard_LRS -o none
az snapshot create -g "$LEAK_RG" -n old-backup-snap --source temp-disk -o none
az disk delete -g "$LEAK_RG" -n temp-disk --yes -o none
info "old-backup-snap (its disk is gone)"

if [ "${SKIP_VM:-0}" != "1" ]; then
  bold "4. VM stopped the wrong way"
  if create_vm_any_size "$LEAK_RG" forgotten-vm Standard_B1s Standard_B1ls Standard_B2ats_v2 Standard_B2s; then
    az vm stop -g "$LEAK_RG" -n forgotten-vm -o none
    info "forgotten-vm ($VM_SIZE) is stopped but not deallocated, so compute keeps billing"
  else
    warn "No small VM size was available; skipped this one."
  fi
fi

bold "Done"
info "New resources can take a few minutes to appear in the Activity Log."
info "Then press Sync in CloudPulse. Everything here will be listed under Waste with you as the creator."
info "Remove it all later with: bash scripts/azure/99-cleanup.sh"
