import json
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone

from fastapi import APIRouter, Depends, File, HTTPException, Query, Request, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy import func
from sqlalchemy.orm import Session

from app import jobs
from app.audit import audit
from app.database import get_db
from app.deps import Access, csrf_guard, current_user, editable, workspace_access
from app.models import (
    CloudConnection, CollectionRun, CostSnapshot, Finding, FindingEvent, Membership, Notification,
    ResourceCost, Setting, User,
)
from app.services import analytics as A
from app.services import demo_data, findings as F
from app.services.collection_orchestrator import import_focus_file
from app.services.connections import describe

router = APIRouter(prefix="/api", dependencies=[Depends(csrf_guard)])

PROVIDER_LABELS = {"aws": "AWS", "azure": "Azure", "gcp": "Google Cloud", "oci": "Oracle Cloud"}
TYPE_LABELS = {
    "volume": "EBS volume", "elastic_ip": "Elastic IP", "instance": "EC2 instance", "disk": "Managed disk",
    "public_ip": "Public IP", "vm": "Virtual machine", "snapshot": "Snapshot", "service": "Service",
    "resource": "Resource", "budget": "Budget", "governance": "Governance", "subscription": "Subscription",
}
STATUS_GROUPS = {
    "active": F.ACTIVE, "resolved": ("resolved",), "verified": ("verified",),
    "closed": ("dismissed", "snoozed"), "all": None,
}


def plabel(p):
    return PROVIDER_LABELS.get(p, p or "")


def iso(dt):
    if dt is None:
        return None
    return (dt.replace(tzinfo=None) if dt.tzinfo else dt).isoformat() + "Z"


def clock(access: Access) -> datetime:
    """The demo lives in September 2024; everything else in the present."""
    if access.workspace.kind == "demo":
        return demo_data.DEMO_CLOCK
    return datetime.now(timezone.utc).replace(tzinfo=None)


# ==========================================================================
# sync, imports, budget
# ==========================================================================
@router.post("/collect")
def collect(request: Request, access: Access = Depends(editable), db: Session = Depends(get_db)):
    run = jobs.enqueue(db, access.workspace, access.user.email)
    audit(db, request, access.user, "sync_requested", access.workspace.slug, workspace_id=access.workspace.id)
    return _run_json(run)


@router.get("/sync")
def sync_status(access: Access = Depends(workspace_access), db: Session = Depends(get_db),
                run_id: int | None = None):
    q = db.query(CollectionRun).filter(CollectionRun.workspace_id == access.workspace.id)
    run = q.filter(CollectionRun.id == run_id).first() if run_id else q.order_by(CollectionRun.id.desc()).first()
    return _run_json(run) if run else {"status": None}


def _run_json(run: CollectionRun) -> dict:
    return {"run_id": run.id, "status": run.status, "step": run.step, "started_at": iso(run.started_at),
            "finished_at": iso(run.finished_at), "detail": json.loads(run.detail or "{}"),
            "requested_by": run.requested_by}


@router.post("/focus")
async def upload_focus(request: Request, file: UploadFile = File(...), access: Access = Depends(editable),
                       db: Session = Depends(get_db)):
    content = await file.read()
    if len(content) > 50 * 1024 * 1024:
        raise HTTPException(413, "File is larger than 50 MB.")
    try:
        n = import_focus_file(db, access.workspace, content, file.filename or "upload.csv")
    except (ValueError, UnicodeDecodeError) as e:
        raise HTTPException(400, str(e)) from e
    audit(db, request, access.user, "bill_imported", file.filename, {"rows": n}, workspace_id=access.workspace.id)
    return {"rows": n, "dataset": file.filename}


class BudgetIn(BaseModel):
    amount: float = Field(ge=0, le=10_000_000)


def _budget(db: Session, ws_id: int):
    return db.query(Setting).filter_by(workspace_id=ws_id, key="budget_monthly").first()


@router.get("/budget")
def get_budget(access: Access = Depends(workspace_access), db: Session = Depends(get_db)):
    row = _budget(db, access.workspace.id)
    return {"amount": float(row.value) if row else None}


@router.post("/budget")
def set_budget(body: BudgetIn, request: Request, access: Access = Depends(editable), db: Session = Depends(get_db)):
    row = _budget(db, access.workspace.id)
    if body.amount == 0:
        if row:
            db.delete(row)
    else:
        if row is None:
            row = Setting(workspace_id=access.workspace.id, key="budget_monthly")
            db.add(row)
        row.value = str(body.amount)
    db.commit()
    audit(db, request, access.user, "budget_set", None, {"amount": body.amount}, workspace_id=access.workspace.id)
    if body.amount:
        jobs.enqueue(db, access.workspace, access.user.email)  # re-check budget risk now
    return {"amount": body.amount or None}


@router.get("/health")
def health():
    return {"ok": True}


# ==========================================================================
# shared time window
# ==========================================================================
def _books(db: Session, ws_id: int) -> list[str]:
    present = {s for (s,) in db.query(CostSnapshot.source).filter(CostSnapshot.workspace_id == ws_id).distinct()}
    return [b for b in ("live", "focus") if b in present]


class Window:
    def __init__(self, db: Session, access: Access, book: str, provider: str, days: int):
        ws_id = access.workspace.id
        self.ws_id, self.access = ws_id, access
        self.books = _books(db, ws_id)
        self.book = (self.books[0] if self.books else "live") if book == "auto" else book
        base = db.query(CostSnapshot).filter(CostSnapshot.workspace_id == ws_id, CostSnapshot.source == self.book)
        self.providers = sorted({p for (p,) in base.with_entities(CostSnapshot.provider).distinct()})
        if provider != "all":
            base = base.filter(CostSnapshot.provider == provider)
        self.base, self.provider = base, provider
        last = base.with_entities(func.max(CostSnapshot.date)).scalar()
        today = clock(access).date()
        self.end = min(date.fromisoformat(last), today) if last else today
        self.days = days
        self.start = self.end - timedelta(days=days - 1)
        self.prev_start = self.start - timedelta(days=days)
        self.rows = base.filter(CostSnapshot.date >= self.start.isoformat(),
                                CostSnapshot.date <= self.end.isoformat()).all()
        self.prev_total = base.filter(CostSnapshot.date >= self.prev_start.isoformat(),
                                      CostSnapshot.date < self.start.isoformat()) \
            .with_entities(func.sum(CostSnapshot.amount)).scalar() or 0.0
        ds = base.with_entities(CostSnapshot.dataset).filter(CostSnapshot.dataset.isnot(None)).first()
        self.dataset = ds[0] if ds else None
        currencies = {r.currency for r in self.rows}
        self.currency = currencies.pop() if len(currencies) == 1 else "USD"

    def daily_all(self, days: int = 60) -> dict[str, float]:
        start = self.end - timedelta(days=days - 1)
        rows = self.base.filter(CostSnapshot.date >= start.isoformat(), CostSnapshot.date <= self.end.isoformat()) \
            .with_entities(CostSnapshot.date, func.sum(CostSnapshot.amount)).group_by(CostSnapshot.date).all()
        return dict(rows)

    def meta(self):
        return {"book": self.book, "books": self.books, "dataset": self.dataset, "provider": self.provider,
                "providers": [{"id": p, "label": plabel(p)} for p in self.providers],
                "window": {"start": self.start.isoformat(), "end": self.end.isoformat(), "days": self.days},
                "currency": self.currency, "can_edit": self.access.can_edit,
                "workspace_kind": self.access.workspace.kind}


def _change(now: float, before: float):
    return None if before <= 0 else round((now - before) / before, 4)


def _forecast(db: Session, w: Window) -> dict:
    budget = _budget(db, w.ws_id)
    amount = float(budget.value) if budget else None
    fc = A.month_forecast(w.daily_all(60), w.end, clock(w.access).date(), amount)
    fc["budget"] = amount
    if amount:
        fc["used"] = round(fc["month_to_date"] / amount, 4)
        fc["forecast_ratio"] = round(fc["forecast"] / amount, 4)
    return fc


# ==========================================================================
# overview
# ==========================================================================
@router.get("/overview")
def overview(access: Access = Depends(workspace_access), db: Session = Depends(get_db),
             book: str = Query("auto", pattern="^(auto|live|focus)$"), provider: str = Query("all"),
             days: int = Query(30, ge=7, le=90)):
    w = Window(db, access, book, provider, days)
    daily, by_service = defaultdict(float), defaultdict(float)
    tagged, tag_known = 0.0, 0.0
    for r in w.rows:
        daily[r.date] += r.amount
        by_service[(r.provider, r.service)] += r.amount
        if r.tagged_amount is not None:
            tagged += r.tagged_amount
            tag_known += r.amount
    series = [{"date": d, "amount": round(daily.get(d, 0.0), 2)} for d in A.daterange(w.start, days)]
    total = sum(daily.values())
    billed = [s for s in series if s["amount"] > 0]
    ranked = sorted(by_service.items(), key=lambda kv: kv[1], reverse=True)
    rows = db.query(Finding).filter_by(workspace_id=access.workspace.id).all()
    anomaly_dates = [json.loads(f.evidence).get("date") for f in rows if f.kind == "anomaly"]
    return {
        **w.meta(),
        "total": round(total, 2), "previous_total": round(w.prev_total, 2),
        "change": _change(total, w.prev_total),
        "daily_average": round(total / len(billed), 2) if billed else 0,
        "peak": max(series, key=lambda s: s["amount"]) if series else None,
        "series": series,
        "by_provider": A.stacked(w.rows, w.start, days, key=lambda r: r.provider, top_n=3),
        "services": [{"provider": p, "provider_label": plabel(p), "service": s, "amount": round(a, 2),
                      "share": round(a / total, 4) if total else 0} for (p, s), a in ranked[:6]],
        "service_count": len(ranked),
        "forecast": {k: v for k, v in _forecast(db, w).items() if k != "path"},
        "untagged": {"share": round(1 - tagged / tag_known, 4), "amount": round(tag_known - tagged, 2)} if tag_known else None,
        "anomaly_dates": [d for d in anomaly_dates if d],
        "pipeline": _pipeline(rows),
        "top_findings": [_finding_row(db, f, now=clock(access)) for f in sorted(
            (f for f in rows if f.status in F.ACTIVE), key=lambda f: -f.priority_score)[:5]],
        "savings": F.ledger(db, access.workspace.id, clock(access).date()),
        "owners": _owners(db, access)[:5],
        "connections": _connections(db, access.workspace.id),
    }


def _pipeline(rows: list[Finding]) -> dict:
    stages = [("open", ("open",)), ("assigned", ("assigned", "in_progress")), ("resolved", ("resolved",)),
              ("verified", ("verified",))]
    out = []
    for name, sts in stages:
        sel = [f for f in rows if f.status in sts and f.kind in F.SAVINGS_KINDS]
        amount = sum((f.realized_monthly or 0) if name == "verified" else (f.monthly_impact or 0) for f in sel)
        out.append({"stage": name, "count": len(sel), "monthly": round(amount, 2)})
    return {"stages": out, "dismissed": sum(1 for f in rows if f.status == "dismissed"),
            "snoozed": sum(1 for f in rows if f.status == "snoozed"),
            "governance_open": sum(1 for f in rows if f.kind in F.GOVERNANCE_KINDS and f.status in F.ACTIVE),
            "anomalies_open": sum(1 for f in rows if f.kind == "anomaly" and f.status in F.ACTIVE + ("resolved",))}


# ==========================================================================
# explorer and month
# ==========================================================================
@router.get("/explorer")
def explorer(access: Access = Depends(workspace_access), db: Session = Depends(get_db),
             book: str = Query("auto", pattern="^(auto|live|focus)$"), provider: str = Query("all"),
             days: int = Query(30, ge=7, le=90), group: str = Query("service", pattern="^(service|provider)$")):
    w = Window(db, access, book, provider, days)
    key = (lambda r: r.service) if group == "service" else (lambda r: plabel(r.provider))
    prev_rows = w.base.filter(CostSnapshot.date >= w.prev_start.isoformat(),
                              CostSnapshot.date < w.start.isoformat()).all() if w.prev_total else []
    now_t, prev_t, owner = defaultdict(float), defaultdict(float), {}
    for r in w.rows:
        now_t[key(r)] += r.amount
        owner[key(r)] = plabel(r.provider)
    for r in prev_rows:
        prev_t[key(r)] += r.amount
    total = sum(now_t.values())
    table = [{"key": k, "provider_label": owner.get(k, ""), "amount": round(v, 2),
              "share": round(v / total, 4) if total else 0, "previous": round(prev_t.get(k, 0.0), 2),
              "change": _change(v, prev_t.get(k, 0.0))}
             for k, v in sorted(now_t.items(), key=lambda kv: kv[1], reverse=True)]
    return {**w.meta(), "group": group, "total": round(total, 2), "previous_total": round(w.prev_total, 2),
            "stack": A.stacked(w.rows, w.start, days, key=key, top_n=5), "table": table,
            "connections": _connections(db, access.workspace.id)}


@router.get("/month")
def month(access: Access = Depends(workspace_access), db: Session = Depends(get_db),
          book: str = Query("auto", pattern="^(auto|live|focus)$"), provider: str = Query("all")):
    w = Window(db, access, book, provider, 7)
    fc = _forecast(db, w)
    return {**w.meta(), "forecast": fc, "budget": fc["budget"],
            "connections": _connections(db, access.workspace.id)}


# ==========================================================================
# findings
# ==========================================================================
def _user_names(db: Session, ids) -> dict[int, dict]:
    ids = {i for i in ids if i}
    if not ids:
        return {}
    return {u.id: {"id": u.id, "email": u.email, "name": u.name or u.email}
            for u in db.query(User).filter(User.id.in_(ids)).all()}


def _finding_row(db: Session, f: Finding, users: dict | None = None, now: datetime | None = None) -> dict:
    users = users if users is not None else _user_names(db, [f.assignee_id])
    now = now or datetime.now(timezone.utc).replace(tzinfo=None)
    first = f.first_seen.replace(tzinfo=None) if f.first_seen and f.first_seen.tzinfo else f.first_seen
    return {
        "id": f.id, "kind": f.kind, "kind_label": F.KIND_LABELS.get(f.kind, f.kind),
        "title": f.title, "summary": f.summary,
        "provider": f.provider, "provider_label": plabel(f.provider),
        "resource_id": f.resource_id, "resource_name": f.resource_name,
        "resource_type": f.resource_type, "type_label": TYPE_LABELS.get(f.resource_type, f.resource_type or ""),
        "resource_group": f.resource_group, "region": f.region,
        "monthly_impact": f.monthly_impact, "impact_basis": f.impact_basis,
        "severity": f.severity, "confidence": f.confidence,
        "priority": f.priority, "priority_score": f.priority_score,
        "owner": f.owner, "owner_source": f.owner_source,
        "assignee": users.get(f.assignee_id),
        "status": f.status, "status_note": f.status_note,
        "snoozed_until": iso(f.snoozed_until), "resolved_at": iso(f.resolved_at), "verified_at": iso(f.verified_at),
        "realized_monthly": f.realized_monthly,
        "first_seen": iso(f.first_seen), "last_seen": iso(f.last_seen), "still_detected": f.still_detected,
        "age_days": (now - first).days if first else None,
        "source": f.source, "governance": f.kind in F.GOVERNANCE_KINDS,
    }


@router.get("/findings")
def list_findings(access: Access = Depends(workspace_access), db: Session = Depends(get_db),
                  status: str = Query("active", pattern="^(active|resolved|verified|closed|all)$"),
                  kind: str = Query("all"), priority: str = Query("all"), mine: bool = False, q: str = ""):
    rows = db.query(Finding).filter_by(workspace_id=access.workspace.id).all()
    counts = {k: sum(1 for f in rows if v is None or f.status in v) for k, v in STATUS_GROUPS.items()}
    sel = [f for f in rows if STATUS_GROUPS[status] is None or f.status in STATUS_GROUPS[status]]
    kinds = defaultdict(int)
    for f in sel:
        kinds[f.kind] += 1
    if kind != "all":
        sel = [f for f in sel if f.kind == kind]
    prios = defaultdict(int)
    for f in sel:
        prios[f.priority] += 1
    if priority != "all":
        sel = [f for f in sel if f.priority == priority]
    if mine:
        sel = [f for f in sel if f.assignee_id == access.user.id]
    if q:
        ql = q.lower()
        sel = [f for f in sel if any(ql in (v or "").lower() for v in
                                     (f.title, f.resource_name, f.owner, f.summary, f.resource_group))]
    sel.sort(key=lambda f: (-(f.priority_score or 0), -(f.monthly_impact or 0)))
    users = _user_names(db, [f.assignee_id for f in sel])
    return {
        "items": [_finding_row(db, f, users, clock(access)) for f in sel],
        "counts": counts, "kinds": [{"id": k, "label": F.KIND_LABELS.get(k, k), "count": n} for k, n in kinds.items()],
        "priorities": dict(prios),
        "mine_count": sum(1 for f in rows if f.assignee_id == access.user.id and f.status in F.ACTIVE),
        "can_edit": access.can_edit, "workspace_kind": access.workspace.kind,
        "connections": _connections(db, access.workspace.id),
    }


def _get_finding(db: Session, access: Access, finding_id: int) -> Finding:
    f = db.get(Finding, finding_id)
    if not f or f.workspace_id != access.workspace.id:
        raise HTTPException(404, "Finding not found.")
    return f


@router.get("/findings/{finding_id}")
def finding_detail(finding_id: int, access: Access = Depends(workspace_access), db: Session = Depends(get_db)):
    f = _get_finding(db, access, finding_id)
    now = clock(access)
    prio = F.rescore(f, now)   # same numbers as the list row, with the working shown
    events = db.query(FindingEvent).filter_by(finding_id=f.id).order_by(FindingEvent.at.asc(), FindingEvent.id.asc()).all()
    members = (db.query(User, Membership.role).join(Membership, Membership.user_id == User.id)
               .filter(Membership.workspace_id == f.workspace_id, User.disabled.is_(False)).all())
    ev = json.loads(f.evidence or "{}")
    ids = [(f.resource_id or "").lower()] + ev.get("extra_cost_ids", [])
    cost_rows = db.query(ResourceCost.date, func.sum(ResourceCost.amount)).filter(
        ResourceCost.workspace_id == f.workspace_id, ResourceCost.resource_id.in_([i for i in ids if i])
    ).group_by(ResourceCost.date).order_by(ResourceCost.date).all() if f.resource_id else []
    return {
        **_finding_row(db, f, now=now),
        "evidence": ev, "fix": json.loads(f.fix or "[]"),
        "list_price_impact": f.list_price_impact,
        "verification": json.loads(f.verification) if f.verification else None,
        "priority_breakdown": prio,
        "events": [{"at": iso(e.at), "actor": e.actor, "kind": e.kind, "message": e.message,
                    "data": json.loads(e.data) if e.data else None} for e in events],
        "cost_history": [{"date": d, "amount": round(a, 4)} for d, a in cost_rows],
        "actions": F.allowed_actions(f, access.user, access.role, access.workspace.kind == "demo"),
        "assignable": [{"id": u.id, "email": u.email, "name": u.name or u.email, "role": r}
                       for u, r in members if not u.is_demo],
    }


class ActionIn(BaseModel):
    action: str = Field(pattern="^(assign|start|resolve|dismiss|snooze|reopen|comment)$")
    note: str = Field(default="", max_length=2000)
    assignee_id: int | None = None
    snooze_days: int | None = Field(default=None, ge=1, le=90)


@router.post("/findings/{finding_id}/action")
def finding_action(finding_id: int, body: ActionIn, request: Request,
                   access: Access = Depends(workspace_access), db: Session = Depends(get_db)):
    f = _get_finding(db, access, finding_id)
    before = f.status
    try:
        F.act(db, f, access.user, access.role, body.action, body.note, body.assignee_id, body.snooze_days,
              is_demo_ws=access.workspace.kind == "demo")
    except F.ActionError as e:
        raise HTTPException(400, str(e)) from e
    audit(db, request, access.user, f"finding_{body.action}", f"#{f.id} {f.title}",
          {"from": before, "to": f.status, "note": body.note[:200] if body.note else None},
          workspace_id=access.workspace.id)
    return finding_detail(finding_id, access, db)


# ==========================================================================
# savings and owners
# ==========================================================================
@router.get("/savings")
def savings(access: Access = Depends(workspace_access), db: Session = Depends(get_db)):
    today = clock(access).date()
    rows = db.query(Finding).filter_by(workspace_id=access.workspace.id).all()
    verified = sorted((f for f in rows if f.status == "verified" and f.kind in F.SAVINGS_KINDS),
                      key=lambda f: f.verified_at, reverse=True)
    users = _user_names(db, [f.assignee_id for f in rows])
    items = []
    for f in verified:
        v = json.loads(f.verification or "{}")
        row = _finding_row(db, f, users, clock(access))
        row.update(method=v.get("method"), before_daily=v.get("before_daily"), after_daily=v.get("after_daily"),
                   saved_to_date=A.saved_to_date(f.realized_monthly or 0,
                                                 (f.verified_at.replace(tzinfo=None)).date(), today),
                   accuracy=round(f.realized_monthly / f.monthly_impact, 4) if f.monthly_impact else None)
        items.append(row)
    pending = [_finding_row(db, f, users, clock(access)) | {"verification": json.loads(f.verification) if f.verification else None}
               for f in rows if f.status == "resolved" and f.kind in F.SAVINGS_KINDS]
    return {"ledger": F.ledger(db, access.workspace.id, today), "verified": items, "pending": pending,
            "by_person": _people_savings(rows, users), "connections": _connections(db, access.workspace.id)}


def _people_savings(rows, users):
    out = defaultdict(lambda: {"verified_monthly": 0.0, "verified": 0})
    for f in rows:
        if f.status == "verified" and f.kind in F.SAVINGS_KINDS:
            key = users.get(f.assignee_id, {}).get("email") or f.owner or "Unassigned"
            out[key]["verified_monthly"] += f.realized_monthly or 0
            out[key]["verified"] += 1
    return sorted(({"who": k, "verified_monthly": round(v["verified_monthly"], 2), "verified": v["verified"]}
                   for k, v in out.items()), key=lambda x: -x["verified_monthly"])


def _owners(db: Session, access: Access) -> list[dict]:
    rows = db.query(Finding).filter_by(workspace_id=access.workspace.id).all()
    users = _user_names(db, [f.assignee_id for f in rows])
    people = defaultdict(lambda: {"open": 0, "open_monthly": 0.0, "verified": 0, "verified_monthly": 0.0,
                                  "resolve_days": [], "kinds": defaultdict(int), "findings": [],
                                  "assignee": None, "source": None})
    for f in rows:
        if f.kind not in F.SAVINGS_KINDS:
            continue
        who = f.owner or (users.get(f.assignee_id, {}).get("email")) or ""
        p = people[who]
        p["source"] = p["source"] or (f.owner_source if f.owner else "assigned")
        if f.assignee_id and not p["assignee"]:
            p["assignee"] = users.get(f.assignee_id)
        if f.status in F.ACTIVE:
            p["open"] += 1
            p["open_monthly"] += f.monthly_impact or 0
            p["kinds"][F.KIND_LABELS.get(f.kind, f.kind)] += 1
            p["findings"].append({"id": f.id, "title": f.resource_name or f.title, "kind": F.KIND_LABELS.get(f.kind),
                                  "monthly": f.monthly_impact, "priority": f.priority, "status": f.status})
        elif f.status == "verified":
            p["verified"] += 1
            p["verified_monthly"] += f.realized_monthly or 0
            if f.resolved_at and f.first_seen:
                p["resolve_days"].append((f.resolved_at - f.first_seen).total_seconds() / 86400)
    out = []
    for who, p in people.items():
        out.append({
            "owner": who or None, "source": p["source"], "assignee": p["assignee"],
            "open": p["open"], "open_monthly": round(p["open_monthly"], 2),
            "verified": p["verified"], "verified_monthly": round(p["verified_monthly"], 2),
            "median_days_to_fix": round(A.median(p["resolve_days"]), 1) if p["resolve_days"] else None,
            "kinds": dict(p["kinds"]),
            "findings": sorted(p["findings"], key=lambda x: -(x["monthly"] or 0))[:8],
        })
    return sorted(out, key=lambda x: (x["owner"] is None, -(x["open_monthly"] + x["verified_monthly"])))


@router.get("/owners")
def owners_view(access: Access = Depends(workspace_access), db: Session = Depends(get_db)):
    return {"owners": _owners(db, access), "connections": _connections(db, access.workspace.id)}


# ==========================================================================
# notifications
# ==========================================================================
@router.get("/notifications")
def notifications(user: User = Depends(current_user), db: Session = Depends(get_db), limit: int = 30):
    from app.models import Workspace

    rows = db.query(Notification).filter_by(user_id=user.id).order_by(Notification.id.desc()).limit(limit).all()
    names = {w.id: (w.slug, w.name) for w in db.query(Workspace).all()}
    return {"unread": db.query(Notification).filter(Notification.user_id == user.id,
                                                    Notification.read_at.is_(None)).count(),
            "items": [{"id": n.id, "kind": n.kind, "message": n.message, "at": iso(n.created_at),
                       "read": n.read_at is not None, "finding_id": n.finding_id,
                       "workspace": names.get(n.workspace_id, (None, None))[0],
                       "workspace_name": names.get(n.workspace_id, (None, None))[1]} for n in rows]}


class ReadIn(BaseModel):
    ids: list[int] | None = None


@router.post("/notifications/read")
def mark_read(body: ReadIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    q = db.query(Notification).filter(Notification.user_id == user.id, Notification.read_at.is_(None))
    if body.ids:
        q = q.filter(Notification.id.in_(body.ids))
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    for n in q.all():
        n.read_at = now
    db.commit()
    return {"ok": True}


# ==========================================================================
# connections
# ==========================================================================
def _connections(db: Session, ws_id: int) -> dict:
    conns = db.query(CloudConnection).filter_by(workspace_id=ws_id).all()
    done = db.query(CollectionRun).filter(CollectionRun.workspace_id == ws_id, CollectionRun.finished_at.isnot(None)) \
        .order_by(CollectionRun.id.desc()).first()
    active = jobs.active_run(db, ws_id)
    detail = json.loads(done.detail or "{}") if done else {}
    items = []
    for c in conns:
        d = describe(c)
        d["status"] = detail.get(str(c.id), {"state": "not_synced"})
        items.append(d)
    return {
        "last_run": iso(done.finished_at) if done else None,
        "status": done.status if done else None,
        "running": _run_json(active) if active else None,
        "items": items,
        "connected": [c["provider"] for c in items if c["status"].get("state") == "connected"],
    }


@router.get("/connections")
def connections(access: Access = Depends(workspace_access), db: Session = Depends(get_db)):
    ws_id = access.workspace.id
    books = {}
    for b in _books(db, ws_id):
        q = db.query(CostSnapshot).filter(CostSnapshot.workspace_id == ws_id, CostSnapshot.source == b)
        first, last = q.with_entities(func.min(CostSnapshot.date), func.max(CostSnapshot.date)).one()
        ds = q.with_entities(CostSnapshot.dataset).filter(CostSnapshot.dataset.isnot(None)).first()
        books[b] = {"from": first, "to": last, "rows": q.count(), "dataset": ds[0] if ds else None}
    return {**_connections(db, ws_id), "books": books, "can_edit": access.can_edit,
            "is_admin": access.user.is_admin, "workspace_kind": access.workspace.kind}
