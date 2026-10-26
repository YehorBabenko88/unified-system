"""Crash-recoverable local SQLite journal, offline and non-authorizing."""
import json
import sqlite3
from pathlib import Path
from .contracts import ContractError, canonical

_ALLOWED = frozenset(("INSTALLED","INFRA_READY","HANDOFF_VERIFIED","OBSERVING","DEGRADED","BLOCKED"))

class Journal:
    def __init__(self, path):
        self.path = Path(path)

    def initialize(self):
        with sqlite3.connect(self.path, timeout=5) as db:
            db.execute("CREATE TABLE IF NOT EXISTS transitions (sequence INTEGER PRIMARY KEY, state TEXT NOT NULL, receipt TEXT, previous_hash TEXT NOT NULL, digest TEXT NOT NULL)")
            db.commit()

    def read(self):
        if not self.path.is_file():
            return []
        with sqlite3.connect(f"file:{self.path.resolve().as_posix()}?mode=ro", uri=True, timeout=5) as db:
            rows=db.execute("SELECT sequence,state,receipt,previous_hash,digest FROM transitions ORDER BY sequence LIMIT 100001").fetchall()
        if len(rows)>100000:
            raise ContractError("journal capacity exceeded")
        import hashlib
        previous="0"*64
        output=[]
        for index,(sequence,state,receipt,previous_hash,digest) in enumerate(rows,1):
            if type(sequence) is not int or sequence != index or state not in _ALLOWED or previous_hash != previous:
                raise ContractError("journal chain broken")
            try:
                parsed=json.loads(receipt) if receipt is not None else None
                body={"sequence":sequence,"state":state,"receipt":parsed,"previous_hash":previous}
                actual=hashlib.sha256(canonical(body)).hexdigest()
            except (ValueError,TypeError) as exc:
                raise ContractError("invalid journal record") from exc
            if actual != digest:
                raise ContractError("journal digest mismatch")
            previous=digest
            output.append(body)
        return output

    def append(self, state, receipt=None):
        if state not in _ALLOWED:
            raise ContractError("invalid transition")
        records=self.read()
        if len(records)>=100000:
            raise ContractError("journal capacity exceeded")
        import hashlib
        previous="0"*64 if not records else hashlib.sha256(canonical(records[-1])).hexdigest()
        body={"sequence":len(records)+1,"state":state,"receipt":receipt,"previous_hash":previous}
        digest=hashlib.sha256(canonical(body)).hexdigest()
        # Single-writer only: the caller must own exclusive lifecycle authority.
        with sqlite3.connect(self.path, timeout=5) as db:
            db.execute("BEGIN IMMEDIATE")
            current=db.execute("SELECT COUNT(*), COALESCE(MAX(digest), '') FROM transitions").fetchone()
            if current[0]!=len(records) or (records and current[1]!=previous):
                raise ContractError("concurrent journal change")
            db.execute("INSERT INTO transitions VALUES (?,?,?,?,?)",(body["sequence"],state,None if receipt is None else canonical(receipt).decode("ascii"),previous,digest))
            db.commit()
        return body
