# Connect a real Azure subscription

CloudPulse only reads your cloud (Reader + Cost Management Reader). Run these
steps in Azure Cloud Shell, or any shell with the Azure CLI.

## 1. Create a read-only identity

The bundled script creates the service principal, grants both roles and prints
the four values you need:

```bash
bash scripts/azure/03-reader-identity.sh
```

By hand:

```bash
SUB=$(az account show --query id -o tsv)
az ad sp create-for-rbac --name CloudPulse --role Reader --scopes /subscriptions/$SUB
# -> appId (client id), password (client secret), tenant
az role assignment create --assignee <appId> --role "Cost Management Reader" \
  --scope /subscriptions/$SUB
```

## 2. Configure

```bash
cd backend
cp .env.example .env
```

Set these in `backend/.env` (the names the app actually reads):

```
ADMIN_EMAIL=admin@cloudpulse.local
ADMIN_PASSWORD=<choose one, or leave empty and read the generated one in the log>
APP_SECRET_KEY=<python -c "import secrets; print(secrets.token_urlsafe(32))">
WORKSPACE_NAME=My Azure subscription
AZURE_SUBSCRIPTION_ID=...
AZURE_TENANT_ID=...
AZURE_CLIENT_ID=...
AZURE_CLIENT_SECRET=...
```

Alternatives to a client secret: `AZURE_USE_CLI=true` (after `az login`, laptop
only) or `AZURE_USE_MANAGED_IDENTITY=true` (Azure App Service).

Demo mode is a separate, read-only workspace on the sign-in page
(`DEMO_ENABLED=true`). There is no real/demo switch to flip: the workspace
created from your Azure settings is a real workspace.

## 3. Run

```bash
docker compose up --build      # from the cloudpulse/ folder
# or
cd backend && pip install -r requirements.txt && uvicorn app.main:app
```

Open http://localhost:8000 and sign in as the admin. The first sync starts
automatically; check **Data sources** for progress.

## 4. What to expect

* Waste findings (idle/oversized VMs, unattached disks, unused public IPs,
  orphaned snapshots) and owners appear within minutes.
* Cost charts, anomalies and the budget forecast need Azure billing data, which
  arrives 8 to 24 hours after usage. Anomalies need about a week of history.
* Savings are verified only after 7 days of billed cost before and after a fix.

## Troubleshooting

| Symptom | Fix |
|---|---|
| No resources after sync | Check the four `AZURE_*` values and that the principal has **Reader** |
| Sync fails with 403 on costs | Grant **Cost Management Reader** at subscription scope |
| Saved connection stops working after restart | Set a fixed `APP_SECRET_KEY` |
| Text looks faint | Hard-refresh the browser (cached old `app.css`) |

## Still seeing the demo ("Demo data", $2,829.99 from Sept 2024)?

That is the built-in sample bill, not your Azure account. Your real data only
appears in a separate workspace, created when the app starts with complete Azure
settings. To fix it:

1. From `cloudpulse/backend`, run `python -m app.manage check-azure`. It tells you
   exactly what is missing (empty subscription ID, incomplete service principal,
   bad secret, no Reader role) or prints `Connected: <subscription name>`.
2. Make sure `backend/.env` exists (copy `.env.example`) and you start the server
   from the `backend` folder. With Docker, the file is read via `env_file`.
3. Restart the server. The startup log says "Created workspace ... from server
   settings", or prints why no real workspace exists.
4. In the app, use the workspace switcher (top of the sidebar) to pick your
   workspace instead of "Demo company". Or skip `.env` entirely and use
   **Workspaces & users -> New workspace -> Connect Azure** as the admin.
5. Press **Sync**. Resources and owners appear in minutes; costs after 8 to 24 hours.
