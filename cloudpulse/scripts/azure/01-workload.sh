#!/usr/bin/env bash
# Creates a small, realistic "company" workload so CloudPulse has real,
# multi-service spend to show: a VM, a web app, a SQL database and storage.
#
# Cost: roughly $2 a day from your credit (about $60 a month).
# Delete it with: bash scripts/azure/99-cleanup.sh
#
# Usage:  bash scripts/azure/01-workload.sh
#         LOCATION=southindia bash scripts/azure/01-workload.sh

source "$(dirname "$0")/_common.sh"
show_account

bold "This creates resource group '$WORKLOAD_RG' with:"
info "- a Linux VM (2 vCPU, B-series)           ~ \$1.00 / day"
info "- an App Service plan (B1) with a web app ~ \$0.45 / day"
info "- an Azure SQL database (Basic)           ~ \$0.17 / day"
info "- a storage account with some sample data ~ \$0.05 / day"
confirm "Go ahead?"

pick_location
register_providers Microsoft.Compute Microsoft.Network Microsoft.Storage Microsoft.Web Microsoft.Sql

bold "Resource group"
az group create -n "$WORKLOAD_RG" -l "$LOCATION" --tags purpose=cloudpulse-demo -o none
info "$WORKLOAD_RG ready"

bold "Storage account with sample data"
STORAGE="cpstore${SUFFIX}"
az storage account create -g "$WORKLOAD_RG" -n "$STORAGE" -l "$LOCATION" --sku Standard_LRS \
  --kind StorageV2 --min-tls-version TLS1_2 --allow-blob-public-access false \
  --tags team=data owner="$ME" -o none
KEY="$(az storage account keys list -g "$WORKLOAD_RG" -n "$STORAGE" --query '[0].value' -o tsv)"
az storage container create --account-name "$STORAGE" --account-key "$KEY" -n exports -o none
head -c 52428800 /dev/urandom > /tmp/cloudpulse-sample.bin
for i in 1 2 3; do
  az storage blob upload --account-name "$STORAGE" --account-key "$KEY" -c exports \
    -n "daily-export-$i.bin" -f /tmp/cloudpulse-sample.bin --overwrite -o none
done
rm -f /tmp/cloudpulse-sample.bin
info "$STORAGE with 150 MB of sample exports"

bold "App Service plan and web app"
PLAN="shop-plan-${SUFFIX}"
WEB="shop-web-${SUFFIX}"
az appservice plan create -g "$WORKLOAD_RG" -n "$PLAN" -l "$LOCATION" --sku B1 --is-linux \
  --tags team=web -o none
az webapp create -g "$WORKLOAD_RG" -p "$PLAN" -n "$WEB" --runtime "NODE:20-lts" -o none
az webapp update -g "$WORKLOAD_RG" -n "$WEB" --https-only true -o none
info "https://$WEB.azurewebsites.net"

bold "Azure SQL database"
SQL="shop-sql-${SUFFIX}"
SQL_PASSWORD="Cp$(openssl rand -hex 12)!9"
az sql server create -g "$WORKLOAD_RG" -n "$SQL" -l "$LOCATION" \
  --admin-user cpadmin --admin-password "$SQL_PASSWORD" --minimal-tls-version 1.2 -o none
az sql db create -g "$WORKLOAD_RG" -s "$SQL" -n orders --service-objective Basic \
  --backup-storage-redundancy Local -o none
unset SQL_PASSWORD
info "$SQL/orders (the admin password isn't needed for the demo and isn't kept)"

bold "Virtual machine"
if create_vm_any_size "$WORKLOAD_RG" "shop-api-vm" Standard_B2s Standard_B2als_v2 Standard_B2ats_v2 Standard_D2s_v3 Standard_D2as_v5; then
  az vm update -g "$WORKLOAD_RG" -n shop-api-vm --set tags.baseSize="$VM_SIZE" -o none
  info "shop-api-vm running as $VM_SIZE"
else
  warn "No VM size was available in $LOCATION. Everything else is in place; try LOCATION=<other region>."
fi

bold "Done"
info "Azure publishes cost data 8 to 24 hours after usage, so spend appears in CloudPulse tomorrow."
info "Next: bash scripts/azure/02-leaks.sh"
