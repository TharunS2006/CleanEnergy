from datetime import datetime, timezone

from sqlalchemy import (
    Boolean, Column, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint,
)

from app.database import Base


def utcnow():
    return datetime.now(timezone.utc)


# --------------------------------------------------------------------------
# People and access
# --------------------------------------------------------------------------
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    email = Column(String, unique=True, index=True, nullable=False)
    name = Column(String, nullable=False, default="")
    password_hash = Column(String, nullable=False)
    is_admin = Column(Boolean, default=False)
    is_demo = Column(Boolean, default=False)
    is_placeholder = Column(Boolean, default=False)  # demo team members; can never sign in
    must_change_password = Column(Boolean, default=False)
    disabled = Column(Boolean, default=False)
    created_at = Column(DateTime, default=utcnow)
    last_login_at = Column(DateTime, nullable=True)


class Workspace(Base):
    """One monitored organisation: its cloud connections and all its data."""
    __tablename__ = "workspaces"

    id = Column(Integer, primary_key=True)
    slug = Column(String, unique=True, index=True, nullable=False)
    name = Column(String, nullable=False)
    kind = Column(String, default="customer")  # customer | demo
    created_at = Column(DateTime, default=utcnow)


class Membership(Base):
    __tablename__ = "memberships"
    __table_args__ = (UniqueConstraint("user_id", "workspace_id"),)

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), index=True)
    workspace_id = Column(Integer, ForeignKey("workspaces.id", ondelete="CASCADE"), index=True)
    role = Column(String, default="viewer")  # owner | viewer


class SessionToken(Base):
    __tablename__ = "sessions"

    id = Column(Integer, primary_key=True)
    token_hash = Column(String, unique=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), index=True)
    created_at = Column(DateTime, default=utcnow)
    expires_at = Column(DateTime)


class CloudConnection(Base):
    """How to reach one cloud account for a workspace.

    auth = env                -> credentials come from the server's settings
           service_principal  -> client secret stored encrypted in `secret`
    """
    __tablename__ = "connections"

    id = Column(Integer, primary_key=True)
    workspace_id = Column(Integer, ForeignKey("workspaces.id", ondelete="CASCADE"), index=True)
    provider = Column(String)          # azure | aws
    label = Column(String, default="")
    auth = Column(String, default="env")
    config = Column(Text, default="{}")  # JSON: subscription_id, tenant_id, client_id...
    secret = Column(Text, nullable=True)
    enabled = Column(Boolean, default=True)
    created_at = Column(DateTime, default=utcnow)


# --------------------------------------------------------------------------
# Cloud data (always scoped to a workspace)
# --------------------------------------------------------------------------
class CostSnapshot(Base):
    """One row per (provider, service, day)."""
    __tablename__ = "cost_snapshots"

    id = Column(Integer, primary_key=True)
    workspace_id = Column(Integer, index=True, nullable=False)
    provider = Column(String, index=True)
    service = Column(String, index=True)
    date = Column(String, index=True)            # YYYY-MM-DD
    amount = Column(Float)
    tagged_amount = Column(Float, nullable=True)  # known only for FOCUS imports
    currency = Column(String, default="USD")
    source = Column(String, index=True)          # live | focus
    dataset = Column(String, nullable=True)
    collected_at = Column(DateTime, default=utcnow)


class ResourceCost(Base):
    """Daily cost per resource (last ~45 days), used for actual-cost impact,
    root cause and before/after verification."""
    __tablename__ = "resource_costs"

    id = Column(Integer, primary_key=True)
    workspace_id = Column(Integer, index=True, nullable=False)
    provider = Column(String)
    resource_id = Column(String, index=True)   # lower-case
    service = Column(String)
    date = Column(String, index=True)
    amount = Column(Float)


class ResourceOwner(Base):
    """Cached answer to 'who created this resource?'."""
    __tablename__ = "resource_owners"
    __table_args__ = (UniqueConstraint("workspace_id", "resource_id"),)

    id = Column(Integer, primary_key=True)
    workspace_id = Column(Integer, index=True, nullable=False)
    resource_id = Column(String, index=True)   # lower-case
    principal = Column(String, nullable=True)
    principal_type = Column(String, nullable=True)  # user | service
    event = Column(String, nullable=True)
    event_at = Column(String, nullable=True)
    source = Column(String, nullable=True)     # activity_log | cloudtrail | tag | example | unknown
    checked_at = Column(DateTime, default=utcnow)


class Finding(Base):
    """The unit of work: one problem, with evidence, impact, owner and status."""
    __tablename__ = "findings"
    __table_args__ = (UniqueConstraint("workspace_id", "fingerprint"),)

    id = Column(Integer, primary_key=True)
    workspace_id = Column(Integer, index=True, nullable=False)
    fingerprint = Column(String, nullable=False)
    kind = Column(String, index=True)          # idle_resource | idle_vm | rightsize_vm | advisor | anomaly | untagged_spend | budget_risk
    provider = Column(String, nullable=True)
    resource_id = Column(String, nullable=True)
    resource_name = Column(String, nullable=True)
    resource_type = Column(String, nullable=True)
    resource_group = Column(String, nullable=True)
    region = Column(String, nullable=True)

    title = Column(String)
    summary = Column(Text)
    evidence = Column(Text, default="{}")      # JSON
    fix = Column(Text, default="[]")           # JSON list of {label, cmd}

    monthly_impact = Column(Float, default=0.0)
    impact_basis = Column(String, default="")
    list_price_impact = Column(Float, nullable=True)
    severity = Column(String, default="low")
    confidence = Column(Float, default=0.5)
    priority_score = Column(Integer, default=0)
    priority = Column(String, default="P4")

    owner = Column(String, nullable=True)      # cloud identity that created the resource
    owner_source = Column(String, nullable=True)
    assignee_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)

    status = Column(String, default="open", index=True)  # open | assigned | in_progress | resolved | verified | dismissed | snoozed
    status_note = Column(Text, nullable=True)
    snoozed_until = Column(DateTime, nullable=True)
    resolved_at = Column(DateTime, nullable=True)
    resolved_by = Column(String, nullable=True)
    verified_at = Column(DateTime, nullable=True)
    realized_monthly = Column(Float, nullable=True)
    verification = Column(Text, nullable=True)  # JSON

    still_detected = Column(Boolean, default=True)
    first_seen = Column(DateTime, default=utcnow)
    last_seen = Column(DateTime, default=utcnow)
    times_seen = Column(Integer, default=1)
    source = Column(String, default="live")    # live | demo
    created_at = Column(DateTime, default=utcnow)
    updated_at = Column(DateTime, default=utcnow)


class FindingEvent(Base):
    __tablename__ = "finding_events"

    id = Column(Integer, primary_key=True)
    finding_id = Column(Integer, ForeignKey("findings.id", ondelete="CASCADE"), index=True)
    workspace_id = Column(Integer, index=True)
    at = Column(DateTime, default=utcnow)
    actor = Column(String)                     # a user's email, or "CloudPulse"
    kind = Column(String)                      # created | status | assigned | comment | verified | reopened | updated
    message = Column(Text)
    data = Column(Text, nullable=True)


class Notification(Base):
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), index=True)
    workspace_id = Column(Integer, index=True)
    finding_id = Column(Integer, nullable=True)
    kind = Column(String)
    message = Column(Text)
    created_at = Column(DateTime, default=utcnow)
    read_at = Column(DateTime, nullable=True)


class AuditLog(Base):
    __tablename__ = "audit_log"

    id = Column(Integer, primary_key=True)
    at = Column(DateTime, default=utcnow, index=True)
    actor_id = Column(Integer, nullable=True)
    actor = Column(String)
    workspace_id = Column(Integer, nullable=True, index=True)
    action = Column(String)
    target = Column(String, nullable=True)
    detail = Column(Text, nullable=True)
    ip = Column(String, nullable=True)


class PriceCache(Base):
    __tablename__ = "price_cache"

    key = Column(String, primary_key=True)
    value = Column(Text)
    fetched_at = Column(DateTime, default=utcnow)


class CollectionRun(Base):
    __tablename__ = "collection_runs"

    id = Column(Integer, primary_key=True)
    workspace_id = Column(Integer, index=True, nullable=False)
    started_at = Column(DateTime, default=utcnow)
    finished_at = Column(DateTime, nullable=True)
    status = Column(String, default="queued")    # queued | running | live | partial | failed | demo | empty
    step = Column(String, nullable=True)         # what it's doing right now
    detail = Column(Text, nullable=True)         # JSON: per-connection outcome
    requested_by = Column(String, nullable=True)


class Setting(Base):
    __tablename__ = "settings"
    __table_args__ = (UniqueConstraint("workspace_id", "key"),)

    id = Column(Integer, primary_key=True)
    workspace_id = Column(Integer, index=True, nullable=False)
    key = Column(String)
    value = Column(Text)
