#!/usr/bin/env bash
# Shared helpers for the CloudPulse Azure scripts. Sourced, not run.
# Designed for Azure Cloud Shell (Bash); also works anywhere the Azure CLI
# is installed and signed in.

set -euo pipefail

bold() { printf '\n\033[1m%s\033[0m\n' "$*"; }
info() { printf '  %s\n' "$*"; }
warn() { printf '\033[33m  ! %s\033[0m\n' "$*"; }
die()  { printf '\033[31m  x %s\033[0m\n' "$*" >&2; exit 1; }

command -v az >/dev/null 2>&1 || die "The Azure CLI isn't available. Open Azure Cloud Shell (Bash) and run this there."
az account show >/dev/null 2>&1 || die "You're not signed in to Azure. Run: az login"

SUB_ID="$(az account show --query id -o tsv)"
SUB_NAME="$(az account show --query name -o tsv)"
TENANT_ID="$(az account show --query tenantId -o tsv)"
ME="$(az account show --query user.name -o tsv)"
# Short, stable suffix so globally unique names don't clash with anyone else's.
SUFFIX="$(printf '%s' "$SUB_ID" | sha1sum | cut -c1-6)"

WORKLOAD_RG="${WORKLOAD_RG:-cloudpulse-workload}"
LEAK_RG="${LEAK_RG:-cloudpulse-demo}"
APP_RG="${APP_RG:-cloudpulse-app}"
export SUB_ID SUB_NAME TENANT_ID ME SUFFIX WORKLOAD_RG LEAK_RG APP_RG

show_account() {
  bold "Azure account"
  info "Subscription: $SUB_NAME ($SUB_ID)"
  info "Signed in as: $ME"
}

confirm() {
  [ "${YES:-0}" = "1" ] && return 0
  local answer
  read -r -p "  $1 [y/N] " answer
  case "$answer" in y|Y|yes|YES) return 0 ;; *) echo "  Stopped. Nothing else was changed."; exit 0 ;; esac
}

# Azure for Students only allows some regions. Read the allowed list from the
# subscription's policy and pick the first preferred region on it.
pick_location() {
  if [ -n "${LOCATION:-}" ]; then
    export LOCATION
    return
  fi
  local allowed pref
  allowed="$(az policy assignment list --query "[].parameters.listOfAllowedLocations.value[]" -o tsv 2>/dev/null | sort -u || true)"
  for pref in centralindia southindia westindia southeastasia eastasia eastus2 eastus westeurope; do
    if [ -z "$allowed" ] || printf '%s\n' "$allowed" | grep -qx "$pref"; then
      LOCATION="$pref"
      break
    fi
  done
  if [ -z "${LOCATION:-}" ]; then
    LOCATION="$(printf '%s\n' "$allowed" | head -n1)"
  fi
  [ -n "${LOCATION:-}" ] || die "Couldn't work out an allowed region. Run again with LOCATION=<region> in front."
  export LOCATION
  if [ -n "$allowed" ]; then
    info "Region: $LOCATION (your subscription allows: $(printf '%s' "$allowed" | tr '\n' ' '))"
  else
    info "Region: $LOCATION"
  fi
}

register_providers() {
  local ns state
  for ns in "$@"; do
    state="$(az provider show --namespace "$ns" --query registrationState -o tsv 2>/dev/null || echo Unknown)"
    if [ "$state" != "Registered" ]; then
      info "Registering $ns (first time only, can take a minute)…"
      az provider register --namespace "$ns" --wait >/dev/null
    fi
  done
}

# Create a VM, trying sizes in order until the region has one available.
create_vm_any_size() {
  local rg="$1" name="$2"; shift 2
  local size
  for size in "$@"; do
    info "Trying VM size $size…"
    if az vm create -g "$rg" -n "$name" --image Ubuntu2204 --size "$size" \
        --admin-username azureuser --generate-ssh-keys \
        --nsg-rule NONE --public-ip-address "" \
        --tags purpose=cloudpulse-demo -o none 2>/tmp/cloudpulse-vm-error.txt; then
      VM_SIZE="$size"
      export VM_SIZE
      return 0
    fi
    warn "$(head -c 300 /tmp/cloudpulse-vm-error.txt | tr '\n' ' ')"
  done
  return 1
}

# Role assignments can fail for a few seconds after an identity is created.
assign_role() {
  local assignee="$1" role="$2" scope="$3" type="${4:-ServicePrincipal}"
  for _ in 1 2 3 4 5 6 7 8 9 10; do
    if az role assignment create --assignee-object-id "$assignee" --assignee-principal-type "$type" \
        --role "$role" --scope "$scope" -o none 2>/dev/null; then
      info "Granted \"$role\""
      return 0
    fi
    sleep 6
  done
  die "Couldn't grant \"$role\". You need Owner or User Access Administrator on the subscription."
}
