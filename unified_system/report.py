"""Offline report rendering for synthetic-only adapter snapshots."""
import json
from .adapters import compose_dashboard
from .contracts import ContractError, canonical

def build_report(*, strattester=None, grid=None):
    report=compose_dashboard(strattester,grid)
    if any(source["status"] in ("STALE","UNAVAILABLE") for source in report["sources"].values()):
        report["overall"]="DEGRADED"
    else:
        report["overall"]="SYNTHETIC_READY"
    return report

def report_bytes(**kwargs):
    try:
        return canonical(build_report(**kwargs))+b"\n"
    except (TypeError,ValueError,OverflowError) as exc:
        if isinstance(exc,ContractError):
            raise
        raise ContractError("invalid report") from exc
