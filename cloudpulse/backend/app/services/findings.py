"""The findings engine: signal -> finding -> owner -> action -> verification.

Lifecycle
    open ──assign──▶ assigned ──start──▶ in_progress ──resolve──▶ resolved ──(sync)──▶ verified
      │                 │                     │                      │
      └──── dismiss / snooze from any active state ────┘            └─ still detected ─▶ reopened
    A finding that stops being detected is resolved automatically.
    A verified finding that comes back is reopened, and its saving is withdrawn.
"""
from __future__ import annotations

import hashlib
import json
from datetime import date, datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.models import Finding, FindingEvent, Membership, Notification, ResourceCost, User
from app.services import analytics as A

ACTIVE = ("open", "assigned", "in_progress")
RESOURCE_KINDS = ("idle_resource", "idle_vm", "rightsize_vm", "advisor")
WORKSPACE_KINDS = ("anomaly", "budget_risk", "untagged_spend")
GOVERNANCE_KINDS = ("untagged_spend", "budget_risk")
SAVINGS_KINDS = RESOURCE_KINDS   # only these count towards savings totals; anomalies are investigations
REOPEN_GRACE = timedelta(minutes=30)
ZERO_SAVING_WAIT_DAYS = 14
KIND_LABELS = {
    "idle_resource": "Idle resource", "idle_vm": "Idle VM", "rightsize_vm": "Oversized VM",
    "advisor": "Advisor", "anomaly": "Spend anomaly", "budget_risk": "Budget risk",
    "untagged_spend": "Untagged spend",
}
ACTOR = "CloudPulse"


def utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _naive(dt):
    return dt.replace(tzinfo=None) if dt is not None and dt.tzinfo else dt


# ==========================================================================
# helpers
# ==========================================================================
def fingerprint(signal: dict) -> str:
    kind = signal["kind"]
    if kind == "anomaly":
        key = f"anomaly:{signal['evidence']['date']}"
    elif kind == "budget_risk":
        key = f"budget_risk:{signal['evidence']['forecast']['month']}"
    elif kind == "untagged_spend":
        key = "untagged_spend"
    else:
        key = f"{kind}:{(signal.get('resource_id') or '').lower()}:{signal.get('fingerprint_extra') or ''}"
    return hashlib.sha256(key.encode()).hexdigest()[:32]


def record(db: Session, f: Finding, actor: str, kind: str, message: str, data: dict | None = None, at=None):
    db.add(FindingEvent(finding_id=f.id, workspace_id=f.workspace_id, actor=actor, kind=kind,
                        message=message, data=json.dumps(data) if data else None, at=at or utcnow()))


def notify(db: Session, user_ids, f: Finding, kind: str, message: str, skip_user_id: int | None = None):
    for uid in {u for u in user_ids if u and u != skip_user_id}:
        db.add(Notification(user_id=uid, workspace_id=f.workspace_id, finding_id=f.id, kind=kind, message=message))


def workspace_owner_ids(db: Session, ws_id: int) -> list[int]:
    return [m.user_id for m in db.query(Membership).filter_by(workspace_id=ws_id, role="owner")]


def user_for_principal(db: Session, ws_id: int, principal: str | None) -> User | None:
    """The cloud identity that created a resource is matched to a CloudPulse
    user with the same email, if that user belongs to the workspace."""
    if not principal or "@" not in principal:
        return None
    u = db.query(User).filter(User.email == principal.strip().lower(), User.disabled.is_(False)).first()
    if u and db.query(Membership).filter_by(user_id=u.id, workspace_id=ws_id).first():
        return u
    return None


def severity_for(signal_or_finding_kind: str, impact: float, evidence: dict) -> str:
    if signal_or_finding_kind == "budget_risk":
        over = evidence.get("overrun_ratio", 1)
        return "critical" if over >= 1.2 else "high"
    if signal_or_finding_kind == "anomaly":
        excess = evidence.get("excess", 0)
        if excess >= 500:
            return "critical"
        if evidence.get("z", 0) >= 8 or excess >= 100:
            return "high"
        return "medium" if excess >= 20 else "low"
    return A.severity_for_impact(impact)


def rescore(f: Finding, now: datetime):
    ev = json.loads(f.evidence or "{}")
    f.severity = severity_for(f.kind, f.monthly_impact or 0, ev)
    # A fixed finding stops ageing on the day it was fixed, so its score stays put.
    end = _naive(f.resolved_at) if f.status in ("resolved", "verified") and f.resolved_at else now
    days_open = max(0.0, (end - _naive(f.first_seen)).total_seconds() / 86400) if f.first_seen else 0
    p = A.priority(f.monthly_impact or 0, f.severity, f.confidence or 0.5, days_open, f.kind)
    f.priority_score, f.priority = p["score"], p["band"]
    return p


# ==========================================================================
# signals -> findings
# ==========================================================================
def upsert_signals(db: Session, ws_id: int, signals: list[dict], scope: dict, now: datetime | None = None,
                   source: str = "live") -> dict:
    """Create or update findings from this sync's signals.

    scope = {"kinds": [...], "provider": "azure" | None, "id_prefix": "/subscriptions/<id>" | None}
    Only findings inside the scope are considered "not detected any more"
    when they're missing from `signals`, so a failed or partial scan never
    closes findings it didn't look at.
    """
    now = now or utcnow()
    seen, stats = set(), {"new": 0, "updated": 0, "reopened": 0, "auto_resolved": 0}
    owners_to_notify = workspace_owner_ids(db, ws_id)

    for s in signals:
        if s.get("extra_cost_ids"):
            s.setdefault("evidence", {})["extra_cost_ids"] = s["extra_cost_ids"]
        fp = fingerprint(s)
        seen.add(fp)
        f = db.query(Finding).filter_by(workspace_id=ws_id, fingerprint=fp).first()
        fields = dict(
            kind=s["kind"], provider=s.get("provider"), resource_id=s.get("resource_id"),
            resource_name=s.get("resource_name"), resource_type=s.get("resource_type"),
            resource_group=s.get("resource_group"), region=s.get("region"),
            title=s["title"], summary=s.get("summary", ""), evidence=json.dumps(s.get("evidence", {}), default=str),
            fix=json.dumps(s.get("fix", [])), monthly_impact=round(float(s.get("monthly_impact") or 0), 2),
            impact_basis=s.get("impact_basis", ""), list_price_impact=s.get("list_price_impact"),
            confidence=float(s.get("confidence", 0.5)), source=source,
        )
        if f is None:
            f = Finding(workspace_id=ws_id, fingerprint=fp, first_seen=now, last_seen=now, created_at=now,
                        updated_at=now, owner=s.get("owner"), owner_source=s.get("owner_source"), **fields)
            db.add(f)
            db.flush()
            rescore(f, now)
            record(db, f, ACTOR, "created", f"Detected: {f.title}",
                   {"impact": f.monthly_impact, "priority": f.priority}, at=now)
            u = user_for_principal(db, ws_id, f.owner)
            if u:
                f.assignee_id, f.status = u.id, "assigned"
                record(db, f, ACTOR, "assigned", f"Assigned to {u.email}, who created the resource", at=now)
                notify(db, [u.id], f, "assigned", f"You were assigned: {f.title}")
            if f.priority == "P1":
                notify(db, owners_to_notify, f, "new_p1", f"New P1 finding: {f.title}")
            stats["new"] += 1
            continue

        for k, v in fields.items():
            setattr(f, k, v)
        if s.get("owner") and not f.owner:
            f.owner, f.owner_source = s.get("owner"), s.get("owner_source")
        f.last_seen, f.updated_at, f.still_detected = now, now, True
        f.times_seen = (f.times_seen or 0) + 1
        stats["updated"] += 1

        historical = f.kind == "anomaly"  # an anomaly day stays in the history; it can't "come back"
        if f.status == "snoozed" and f.snoozed_until and _naive(f.snoozed_until) <= now:
            f.status = "assigned" if f.assignee_id else "open"
            f.snoozed_until = None
            record(db, f, ACTOR, "status", "Snooze ended; the finding is active again", at=now)
            notify(db, [f.assignee_id], f, "reopened", f"Snooze ended: {f.title}")
        elif not historical and f.status == "resolved" and f.resolved_at and now - _naive(f.resolved_at) > REOPEN_GRACE:
            f.status = "assigned" if f.assignee_id else "open"
            f.status_note = "Still detected after being marked resolved."
            f.resolved_at = None
            record(db, f, ACTOR, "reopened", "Reopened: the problem is still there on the latest sync", at=now)
            notify(db, [f.assignee_id], f, "reopened", f"Reopened, still detected: {f.title}")
            stats["reopened"] += 1
        elif not historical and f.status == "verified":
            withdrawn = f.realized_monthly
            f.status = "assigned" if f.assignee_id else "open"
            f.status_note = "Came back after it was verified."
            f.verified_at = None
            f.realized_monthly = None
            f.resolved_at = None
            record(db, f, ACTOR, "reopened", "Reopened: the problem came back, so its verified saving was withdrawn",
                   {"withdrawn_monthly": withdrawn}, at=now)
            notify(db, [f.assignee_id], f, "reopened", f"Came back: {f.title}")
            stats["reopened"] += 1
        rescore(f, now)

    # Not detected this time, inside scope.
    q = db.query(Finding).filter(Finding.workspace_id == ws_id, Finding.kind.in_(scope["kinds"]),
                                 Finding.source == source)
    if scope.get("provider"):
        q = q.filter(Finding.provider == scope["provider"])
    for f in q.all():
        if f.fingerprint in seen:
            continue
        if scope.get("id_prefix") and not (f.resource_id or "").lower().startswith(scope["id_prefix"].lower()):
            continue
        f.still_detected = False
        if f.status in ACTIVE or f.status == "snoozed":
            f.status = "resolved"
            f.resolved_at, f.resolved_by = now, ACTOR
            f.status_note = "No longer detected on the latest sync."
            f.updated_at = now
            record(db, f, ACTOR, "status", "Resolved automatically: no longer detected", at=now)
            notify(db, [f.assignee_id], f, "resolved", f"No longer detected: {f.title}")
            stats["auto_resolved"] += 1
    db.commit()
    return stats


# ==========================================================================
# verification
# ==========================================================================
def _resource_daily(db: Session, ws_id: int, ids: list[str]) -> tuple[dict[str, float], bool]:
    ids = [i.lower() for i in ids if i]
    if not ids:
        return {}, False
    daily: dict[str, float] = {}
    rows = db.query(ResourceCost.date, ResourceCost.amount).filter(
        ResourceCost.workspace_id == ws_id, ResourceCost.resource_id.in_(ids)).all()
    for d, amt in rows:
        daily[d] = daily.get(d, 0.0) + amt
    return daily, bool(rows)


def verify(db: Session, ws_id: int, ctx: dict, now: datetime | None = None, only_ids: list[int] | None = None) -> int:
    """Check every resolved finding.

    ctx: last_cost_day (date|None), recent_daily (list of (date, amount) for the
    last billed days), untagged_share (float|None), budget_ok (bool|None)
    """
    now = now or utcnow()
    count = 0
    q = db.query(Finding).filter_by(workspace_id=ws_id, status="resolved")
    if only_ids is not None:
        q = q.filter(Finding.id.in_(only_ids))
    for f in q.all():
        ev = json.loads(f.evidence or "{}")
        result = None
        if f.kind in RESOURCE_KINDS:
            if f.still_detected:
                continue  # either within the reopen grace period, or will be reopened
            ids = [f.resource_id] + ev.get("extra_cost_ids", [])
            daily, has_history = _resource_daily(db, ws_id, ids)
            change_day = _naive(f.resolved_at).date()
            if not has_history:
                result = {"method": "Resource gone; it had no billed cost history, so the estimate is used",
                          "realized_monthly": round(f.monthly_impact or 0, 2)}
            else:
                ba = A.before_after(daily, change_day, ctx.get("last_cost_day"))
                if ba is None:
                    f.verification = json.dumps({"state": "waiting",
                                                 "message": "Confirmed on the latest sync. Waiting for 3 days of cost data after the fix.",
                                                 "expected_by": (change_day + timedelta(days=A.VERIFY_MIN_AFTER + 1)).isoformat()})
                    continue
                if ba["realized_monthly"] <= 0 and (now.date() - change_day).days < ZERO_SAVING_WAIT_DAYS:
                    f.verification = json.dumps({"state": "waiting", **ba,
                                                 "message": "Fix confirmed, but the cost hasn't dropped yet."})
                    continue
                result = {"method": "Average daily cost, 7 days before vs. after the fix", **ba}
        elif f.kind == "anomaly":
            recent = ctx.get("recent_daily") or []
            if len(recent) < 3 or date.fromisoformat(recent[-3][0]) <= date.fromisoformat(ev["date"]):
                f.verification = json.dumps({"state": "waiting", "message": "Waiting for 3 billed days after the spike."})
                continue
            limit = ev["expected"] + 0.5 * ev["excess"]
            last3 = [a for _, a in recent[-3:]]
            if not all(a <= limit for a in last3):
                f.verification = json.dumps({"state": "waiting", "limit": round(limit, 2),
                                             "last_days": [round(a, 2) for a in last3],
                                             "message": "Spend is still above normal."})
                continue
            saved = max(0.0, ev["amount"] - A.mean(last3)) * A.DAYS_PER_MONTH if ev.get("ongoing") else 0.0
            result = {"method": "Last 3 billed days back within half the spike",
                      "limit": round(limit, 2), "last_days": [round(a, 2) for a in last3],
                      "realized_monthly": round(saved, 2),
                      "note": "Recurring cost avoided" if ev.get("ongoing") else "One-off spike: nothing recurring to save"}
        elif f.kind == "untagged_spend":
            share = ctx.get("untagged_share")
            if share is None or share >= 0.10:
                continue
            result = {"method": f"Untagged share now {share:.1%} (below 10%)", "realized_monthly": 0.0}
        elif f.kind == "budget_risk":
            if ctx.get("budget_ok") is not True:
                continue
            result = {"method": "Forecast back under budget", "realized_monthly": 0.0}
        if result is None:
            continue
        f.status = "verified"
        f.verified_at = now
        f.realized_monthly = round(float(result.get("realized_monthly") or 0), 2)
        f.verification = json.dumps({"state": "verified", **result})
        f.updated_at = now
        record(db, f, ACTOR, "verified",
               f"Verified. Saving: ${f.realized_monthly:,.2f} a month" if f.realized_monthly else "Verified",
               {"realized_monthly": f.realized_monthly}, at=now)
        notify(db, [f.assignee_id], f, "verified", f"Verified: {f.title}")
        count += 1
    db.commit()
    return count


def rescore_active(db: Session, ws_id: int, now: datetime | None = None):
    now = now or utcnow()
    for f in db.query(Finding).filter(Finding.workspace_id == ws_id, Finding.status.in_(ACTIVE)).all():
        rescore(f, now)
    db.commit()


# ==========================================================================
# people acting on findings
# ==========================================================================
class ActionError(Exception):
    pass


ACTIONS = {
    "assign": ("open", "assigned", "in_progress", "snoozed", "resolved"),
    "start": ("open", "assigned"),
    "resolve": ("open", "assigned", "in_progress", "snoozed"),
    "dismiss": ("open", "assigned", "in_progress", "snoozed", "resolved"),
    "snooze": ("open", "assigned", "in_progress"),
    "reopen": ("resolved", "dismissed", "snoozed", "verified"),
}


def allowed_actions(f: Finding, user: User, role: str, is_demo_ws: bool) -> list[str]:
    if is_demo_ws or user.is_demo:
        return []
    manager = user.is_admin or role == "owner"
    mine = f.assignee_id == user.id
    out = []
    for action, states in ACTIONS.items():
        if f.status not in states:
            continue
        if manager or (mine and action in ("start", "resolve")):
            out.append(action)
    if manager or mine:
        out.append("comment")
    return out


def act(db: Session, f: Finding, user: User, role: str, action: str, note: str = "",
        assignee_id: int | None = None, snooze_days: int | None = None, is_demo_ws: bool = False,
        now: datetime | None = None) -> Finding:
    now = now or utcnow()
    if action not in allowed_actions(f, user, role, is_demo_ws):
        raise ActionError("You can't do that to this finding right now.")
    note = (note or "").strip()[:2000]
    who = user.email
    prev = f.status

    if action == "comment":
        if not note:
            raise ActionError("Write a comment first.")
        record(db, f, who, "comment", note, at=now)
        notify(db, [f.assignee_id], f, "comment", f"{who} commented on: {f.title}", skip_user_id=user.id)
    elif action == "assign":
        target = db.get(User, assignee_id) if assignee_id else None
        if target is None or target.disabled or not (
                target.is_admin or db.query(Membership).filter_by(user_id=target.id, workspace_id=f.workspace_id).first()):
            raise ActionError("Pick someone who belongs to this workspace.")
        f.assignee_id = target.id
        if f.status in ("open", "resolved", "snoozed"):
            f.status = "assigned"
            f.resolved_at = None
            f.snoozed_until = None
        record(db, f, who, "assigned", f"Assigned to {target.email}" + (f": {note}" if note else ""), at=now)
        notify(db, [target.id], f, "assigned", f"{who} assigned you: {f.title}", skip_user_id=user.id)
    elif action == "start":
        f.status = "in_progress"
        if not f.assignee_id:
            f.assignee_id = user.id
        record(db, f, who, "status", "Started working on it" + (f": {note}" if note else ""), at=now)
    elif action == "resolve":
        f.status = "resolved"
        f.resolved_at, f.resolved_by = now, who
        f.status_note = note or None
        record(db, f, who, "status", "Marked as fixed" + (f": {note}" if note else "") +
               ". CloudPulse will check on the next syncs.", at=now)
        notify(db, [f.assignee_id], f, "resolved", f"{who} marked as fixed: {f.title}", skip_user_id=user.id)
    elif action == "dismiss":
        if len(note) < 3:
            raise ActionError("Say why it's being dismissed, so others know.")
        f.status, f.status_note = "dismissed", note
        record(db, f, who, "status", f"Dismissed: {note}", at=now)
        notify(db, [f.assignee_id], f, "dismissed", f"{who} dismissed: {f.title}", skip_user_id=user.id)
    elif action == "snooze":
        days = int(snooze_days or 0)
        if not 1 <= days <= 90:
            raise ActionError("Snooze for 1 to 90 days.")
        f.status = "snoozed"
        f.snoozed_until = now + timedelta(days=days)
        f.status_note = note or None
        record(db, f, who, "status", f"Snoozed for {days} day(s)" + (f": {note}" if note else ""), at=now)
    elif action == "reopen":
        if prev == "verified":
            record(db, f, who, "reopened", "Reopened; its verified saving was withdrawn",
                   {"withdrawn_monthly": f.realized_monthly}, at=now)
            f.realized_monthly, f.verified_at = None, None
        else:
            record(db, f, who, "reopened", "Reopened" + (f": {note}" if note else ""), at=now)
        f.status = "assigned" if f.assignee_id else "open"
        f.resolved_at = None
        f.snoozed_until = None
        f.status_note = note or None
    f.updated_at = now
    rescore(f, now)
    db.commit()
    return f


# ==========================================================================
# savings ledger
# ==========================================================================
def ledger(db: Session, ws_id: int, today: date) -> dict:
    rows = db.query(Finding).filter_by(workspace_id=ws_id).all()
    savings_kinds = [f for f in rows if f.kind in SAVINGS_KINDS]
    active = [f for f in savings_kinds if f.status in ACTIVE]
    verified = [f for f in savings_kinds if f.status == "verified"]
    by_month: dict[str, float] = {}
    for f in verified:
        m = _naive(f.verified_at).strftime("%Y-%m")
        by_month[m] = round(by_month.get(m, 0) + (f.realized_monthly or 0), 2)
    compared = [f for f in verified if (f.monthly_impact or 0) > 0 and f.realized_monthly is not None]
    est = sum(f.monthly_impact for f in compared)
    real = sum(f.realized_monthly for f in compared)
    return {
        "open_estimated_monthly": round(sum(f.monthly_impact or 0 for f in active), 2),
        "resolved_pending": sum(1 for f in savings_kinds if f.status == "resolved"),
        "verified_monthly": round(sum(f.realized_monthly or 0 for f in verified), 2),
        "verified_count": len(verified),
        "saved_to_date": round(sum(A.saved_to_date(f.realized_monthly or 0, _naive(f.verified_at).date(), today)
                                   for f in verified), 2),
        "accuracy": round(real / est, 4) if est else None,
        "by_month": [{"month": k, "realized_monthly": v} for k, v in sorted(by_month.items())],
    }
