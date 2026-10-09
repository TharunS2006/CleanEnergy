import os
import secrets

from dotenv import load_dotenv

load_dotenv()


def _flag(name: str, default: str = "false") -> bool:
    return os.getenv(name, default).strip().lower() in ("1", "true", "yes")


def _str(name: str, default: str = "") -> str:
    return os.getenv(name, default).strip()


class Settings:
    DATABASE_URL: str = _str("DATABASE_URL", "sqlite:///./cloudpulse.db")

    # Used to sign nothing and encrypt stored cloud secrets. Set it in
    # production; a random key is generated for a local run (stored secrets
    # then won't survive a restart, which is fine for development).
    APP_SECRET_KEY: str = _str("APP_SECRET_KEY") or secrets.token_urlsafe(32)
    APP_SECRET_KEY_IS_RANDOM: bool = not _str("APP_SECRET_KEY")

    # Cookies are marked Secure when served over HTTPS (App Service, Render).
    COOKIE_SECURE: bool = _flag("COOKIE_SECURE", "false")
    SESSION_HOURS: int = int(_str("SESSION_HOURS", "12"))

    # ---- first-run accounts --------------------------------------------
    ADMIN_EMAIL: str = _str("ADMIN_EMAIL", "admin@cloudpulse.local").lower()
    ADMIN_PASSWORD: str = _str("ADMIN_PASSWORD")      # empty -> generated and printed once
    DEMO_ENABLED: bool = _flag("DEMO_ENABLED", "true")
    DEMO_EMAIL: str = _str("DEMO_EMAIL", "demo@cloudpulse.in").lower()

    # ---- the customer workspace created from environment settings -----
    WORKSPACE_NAME: str = _str("WORKSPACE_NAME", "My cloud")

    # Azure: service principal, `az login` on this machine, or the App
    # Service managed identity.
    AZURE_SUBSCRIPTION_ID: str = _str("AZURE_SUBSCRIPTION_ID")
    AZURE_TENANT_ID: str = _str("AZURE_TENANT_ID")
    AZURE_CLIENT_ID: str = _str("AZURE_CLIENT_ID")
    AZURE_CLIENT_SECRET: str = _str("AZURE_CLIENT_SECRET")
    AZURE_USE_CLI: bool = _flag("AZURE_USE_CLI")
    AZURE_USE_MANAGED_IDENTITY: bool = _flag("AZURE_USE_MANAGED_IDENTITY")

    # AWS: boto3 reads AWS_ACCESS_KEY_ID / AWS_SECRET_ACCESS_KEY itself.
    AWS_REGION: str = _str("AWS_DEFAULT_REGION", "us-east-1")

    # Minutes between automatic syncs. AWS Cost Explorer bills $0.01 per request.
    COLLECT_INTERVAL_MINUTES: int = int(_str("COLLECT_INTERVAL_MINUTES", "360"))


settings = Settings()
