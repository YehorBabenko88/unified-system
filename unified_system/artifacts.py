"""Offline artifact verifier: checks bytes against a supplied digest, not publisher trust."""
import hashlib
import os
import re
from pathlib import Path
from .contracts import ContractError

_SHA=re.compile(r"[0-9a-f]{64}\Z")

def verify_artifact(path, expected_sha256, *, max_bytes=512*1024*1024):
    if type(expected_sha256) is not str or not _SHA.fullmatch(expected_sha256):
        raise ContractError("invalid expected digest")
    if type(max_bytes) is not int or not 1 <= max_bytes <= 2**40:
        raise ContractError("invalid size limit")
    path=Path(path)
    if path.is_symlink() or not path.is_file():
        raise ContractError("artifact must be a regular file, not a symlink")
    flags=os.O_RDONLY | getattr(os,"O_BINARY",0) | getattr(os,"O_NOFOLLOW",0)
    fd=os.open(path,flags)
    try:
        stat=os.fstat(fd)
        if not __import__("stat").S_ISREG(stat.st_mode) or stat.st_size>max_bytes:
            raise ContractError("artifact type or size invalid")
        digest=hashlib.sha256()
        total=0
        with os.fdopen(fd,"rb",closefd=False) as stream:
            while True:
                chunk=stream.read(min(1024*1024,max_bytes-total+1))
                if not chunk:break
                total+=len(chunk)
                if total>max_bytes:
                    raise ContractError("artifact exceeds limit")
                digest.update(chunk)
        if digest.hexdigest()!=expected_sha256:
            raise ContractError("artifact digest mismatch")
        return {"status":"BYTES_VERIFIED_ONLY","sha256":expected_sha256,"bytes":total}
    finally:
        os.close(fd)
