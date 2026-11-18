"""Offline-first, proposal-only autonomic monitoring for Unified LAB."""
from .core import EvidenceError, evaluate, load_snapshot, record_scan, verify_history

__all__ = ["EvidenceError", "evaluate", "load_snapshot", "record_scan", "verify_history"]
