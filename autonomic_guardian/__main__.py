"""Operator-invoked offline observer; persistent operation requires separate install approval."""
from __future__ import annotations

import argparse
import json
import sys
import time
from .core import EvidenceError, evaluate, load_snapshot, record_scan, verify_history


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Seven offline, proposal-only LAB diagnostic agents")
    parser.add_argument("--snapshot", required=True, help="approved JSON observation snapshot")
    parser.add_argument("--journal", required=True, help="separate owned SQLite journal")
    parser.add_argument("--loop", action="store_true", help="repeat until interrupted; does not install a service")
    parser.add_argument("--interval", type=int, default=30)
    args = parser.parse_args(argv)
    if args.loop and not 10 <= args.interval <= 3600:
        parser.error("--interval must be 10..3600")
    try:
        while True:
            snapshot, digest = load_snapshot(args.snapshot)
            report = evaluate(snapshot, source_sha256=digest)
            report["journal_sequence"] = record_scan(args.journal, report)
            report["journal_chain_ok"] = verify_history(args.journal)
            print(json.dumps(report, ensure_ascii=True, sort_keys=True), flush=True)
            if not args.loop:
                return 0 if report["journal_chain_ok"] else 2
            time.sleep(args.interval)
    except (EvidenceError, OSError, ValueError) as exc:
        print(f"GUARDIAN_BLOCKED: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
