"""Turns a stored CloudConnection into something the collectors can use."""
import json
import os
from dataclasses import dataclass, field
from typing import Callable

from app.config import settings
from app.security import decrypt

AZURE_AUTH_LABELS = {
    "managed_identity": "App Service managed identity",
    "cli": "Azure CLI login on this machine",
    "service_principal": "Service principal",
}


@dataclass
class AzureTarget:
    subscription_id: str
    auth: str
    _factory: Callable = field(repr=False)
    _cred: object = field(default=None, repr=False)

    def credential(self):
        if self._cred is None:
            self._cred = self._factory()
        return self._cred


@dataclass
class AwsTarget:
    region: str
    _session_factory: Callable = field(repr=False)
    _session: object = field(default=None, repr=False)

    def client(self, name: str, region: str | None = None):
        from botocore.config import Config

        if self._session is None:
            self._session = self._session_factory()
        cfg = Config(connect_timeout=5, read_timeout=15, retries={"max_attempts": 2})
        return self._session.client(name, region_name=region or self.region, config=cfg)


def env_azure_auth() -> str | None:
    """Which Azure sign-in the server's own settings provide, if any."""
    if not settings.AZURE_SUBSCRIPTION_ID:
        return None
    if settings.AZURE_CLIENT_ID and settings.AZURE_CLIENT_SECRET and settings.AZURE_TENANT_ID:
        return "service_principal"
    if settings.AZURE_USE_MANAGED_IDENTITY:
        return "managed_identity"
    if settings.AZURE_USE_CLI:
        return "cli"
    return None


def azure_env_problems() -> list[str]:
    """Why the server's Azure settings aren't usable (empty list when they are)."""
    if env_azure_auth():
        return []
    out = []
    if not settings.AZURE_SUBSCRIPTION_ID:
        out.append("AZURE_SUBSCRIPTION_ID is empty (is backend/.env present, and are you running from the backend folder?)")
    have = {"AZURE_TENANT_ID": settings.AZURE_TENANT_ID, "AZURE_CLIENT_ID": settings.AZURE_CLIENT_ID,
            "AZURE_CLIENT_SECRET": settings.AZURE_CLIENT_SECRET}
    missing = [k for k, v in have.items() if not v]
    if missing and len(missing) < 3:
        out.append("Service principal is incomplete; missing " + ", ".join(missing))
    if not settings.AZURE_USE_CLI and not settings.AZURE_USE_MANAGED_IDENTITY and len(missing) == 3:
        out.append("No sign-in method set: fill AZURE_TENANT_ID / AZURE_CLIENT_ID / AZURE_CLIENT_SECRET, "
                   "or set AZURE_USE_CLI=true (after `az login`)")
    return out or ["Azure settings are incomplete"]


def env_aws_configured() -> bool:
    return bool(os.getenv("AWS_ACCESS_KEY_ID") and os.getenv("AWS_SECRET_ACCESS_KEY"))


def _azure_factory(auth: str, tenant: str, client_id: str, secret: str | None):
    def make():
        if auth == "service_principal":
            from azure.identity import ClientSecretCredential
            if not secret:
                raise RuntimeError("The stored client secret can't be read. Re-enter it in Admin.")
            return ClientSecretCredential(tenant, client_id, secret)
        if auth == "managed_identity":
            from azure.identity import ManagedIdentityCredential
            return ManagedIdentityCredential(client_id=client_id or None)
        from azure.identity import AzureCliCredential
        return AzureCliCredential(process_timeout=20)
    return make


def build_target(conn):
    cfg = json.loads(conn.config or "{}")
    if conn.provider == "azure":
        if conn.auth == "env":
            auth = env_azure_auth() or "cli"
            return AzureTarget(
                subscription_id=settings.AZURE_SUBSCRIPTION_ID, auth=auth,
                _factory=_azure_factory(auth, settings.AZURE_TENANT_ID, settings.AZURE_CLIENT_ID,
                                        settings.AZURE_CLIENT_SECRET),
            )
        return AzureTarget(
            subscription_id=cfg.get("subscription_id", ""), auth=conn.auth,
            _factory=_azure_factory(conn.auth, cfg.get("tenant_id", ""), cfg.get("client_id", ""),
                                    decrypt(conn.secret)),
        )

    if conn.provider == "aws":
        import boto3

        region = cfg.get("region") or settings.AWS_REGION
        if conn.auth == "env":
            return AwsTarget(region=region, _session_factory=lambda: boto3.Session(region_name=region))
        key_id = cfg.get("access_key_id", "")
        secret = decrypt(conn.secret)
        return AwsTarget(region=region, _session_factory=lambda: boto3.Session(
            aws_access_key_id=key_id, aws_secret_access_key=secret, region_name=region))
    raise ValueError(f"Unknown provider {conn.provider}")


def describe(conn) -> dict:
    """Safe, secret-free summary for the UI."""
    cfg = json.loads(conn.config or "{}")
    out = {"id": conn.id, "provider": conn.provider, "label": conn.label, "enabled": conn.enabled}
    if conn.provider == "azure":
        if conn.auth == "env":
            auth = env_azure_auth()
            out.update(subscription_id=settings.AZURE_SUBSCRIPTION_ID,
                       auth=AZURE_AUTH_LABELS.get(auth, "Not configured") + " (server settings)")
        else:
            out.update(subscription_id=cfg.get("subscription_id"),
                       auth=AZURE_AUTH_LABELS.get(conn.auth, conn.auth),
                       client_id=cfg.get("client_id"), tenant_id=cfg.get("tenant_id"),
                       secret_readable=decrypt(conn.secret) is not None if conn.auth == "service_principal" else None)
    else:
        out.update(region=cfg.get("region") or settings.AWS_REGION,
                   auth="Access key (server settings)" if conn.auth == "env" else "Access key")
    return out
