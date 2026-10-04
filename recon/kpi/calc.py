"""The KPI file of one period, shaped as docs/contracts/kpi.md. Pure functions, no file or database access."""
from . import periods
from .catalog import AREAS, DEFINITIONS, KPIS, PILLAR, PILLARS
from .facts import facts
from .kpis import CALC

# Reasons in the contract's order of precedence.
ORDER = ("missing_days", "missing_internal_days", "no_buyer_ids", "no_prior_period", "no_internal_data",
         "no_marketplace_data", "zero_denominator", "period_too_short")


def _status(res):
    """(status, reason, note): the worst status, its first reason in contract order, the notes that go with it."""
    if not res.problems:
        return "ok", None, res.note
    status = "no_data" if any(s == "no_data" for s, _, _ in res.problems) else "partial"
    mine = sorted((p for p in res.problems if p[0] == status), key=lambda p: ORDER.index(p[1]))
    notes = [note for _, _, note in mine]
    if status == "partial" and res.note:
        notes.append(res.note)
    return status, mine[0][1], " ".join(dict.fromkeys(notes))


def _delta(kpi, value, status, prior_value, prior_status):
    blank = {"value": None, "pct": None}
    if kpi.kind == "ranking":
        return {**blank, "reason": "not_applicable"}
    if value is None:
        return {**blank, "reason": "current_no_data"}
    if prior_value is None:
        return {**blank, "reason": "no_prior_period"}
    change = value - prior_value
    if isinstance(change, float):
        change = round(change, 4 if kpi.unit == "ratio" else 1)
    relative = kpi.unit != "ratio" and prior_value > 0
    return {
        "value": change,
        "pct": round(100 * (value - prior_value) / prior_value, 1) if relative else None,
        "reason": "partial_period" if "partial" in (status, prior_status) else None,
    }


def _shape(kpi, res, prior, simulated):
    status, reason, note = _status(res)
    prior_status = _status(prior)[0]
    ranking = kpi.kind == "ranking"
    value = None if ranking or status == "no_data" else res.value
    # A prior value computed on another basis (per order against per unit) is not comparable.
    comparable = not ranking and prior_status != "no_data" and prior.basis == res.basis
    prior_value = prior.value if comparable else None
    return {
        "id": kpi.id,
        "area": kpi.area,
        "pillar": PILLAR[kpi.id],
        "name": kpi.name,
        "kind": kpi.kind,
        "unit": kpi.unit,
        "per": res.per or kpi.per,
        "value": value,
        "rows": (res.value if status != "no_data" else []) if ranking else None,
        "parts": res.parts,
        "status": status,
        "reason": reason,
        "note": note,
        "basis": res.basis,
        "covers": res.covers,
        "prior_value": prior_value,
        "delta": _delta(kpi, value, status, prior_value, prior_status),
        "good_direction": kpi.good_direction,
        "source": kpi.source,
        "simulated": simulated and kpi.source != "files",
        "definition": res.definition or kpi.definition,
        "inputs": res.inputs,
    }


def _internal_data(internal):
    if internal.source is None:
        return None
    label = "Simulated internal data" if internal.source == "mock" else "Goodwill internal data"
    return {"source": internal.source, "label": label, "as_of": internal.as_of}


def build(win, data, prior_data, before_data, generated_at=None):
    """The KPI file for the window `win`.

    `prior_data` is what is stored for `periods.prior_window(win)`, and `before_data` for the
    window before that one (it gives revenue growth its own prior value).
    """
    prior_win = periods.prior_window(win)
    f = facts(win, data)
    pf = facts(prior_win, prior_data)
    bf = facts(periods.prior_window(prior_win), before_data)
    simulated = f.internal.source == "mock"
    return {
        "schema_version": 1,
        "generated_at": generated_at,
        "currency": "USD",
        "period": {
            "type": win.period.type,
            "id": win.period.id,
            "label": periods.label(win),
            "start": win.start.isoformat(),
            "end": win.period.end.isoformat(),
            "through": win.through.isoformat(),
            "days": win.days,
            "complete": win.complete,
        },
        "prior_period": {
            "id": prior_win.period.id,
            "label": periods.comparison_label(prior_win),
            "start": prior_win.start.isoformat(),
            "through": prior_win.through.isoformat(),
            "days": prior_win.days,
            "available": bool(prior_data.pulse),
        },
        "coverage": f.coverage,
        "internal_data": _internal_data(f.internal),
        "areas": [{"id": area, "name": name} for area, name in AREAS],
        "pillars": [{"id": pillar, "name": name} for pillar, name in PILLARS],
        "kpis": [_shape(kpi, CALC[kpi.id](f, pf), CALC[kpi.id](pf, bf), simulated) for kpi in KPIS],
        "definitions": DEFINITIONS,
    }
