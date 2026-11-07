"""Test-only exact owner source; real disposable PKI/TLS, no fake grants."""
import hashlib
import importlib
import importlib.util
import os
from pathlib import Path
import sys

IDENTITY_SHA = "84093865e8477ef6562100d41137922785446c9cb4e024c9ba7105593a2b36c1"
FIXTURE_SHA = "b26fe114c778a8b8a95bc3de822dd7c7a4f57dd12277e9fdcbc96cfb5bc4199f"


def load_owner():
    # Trusted test provisioning, never a public request/source-path parameter.
    root = Path(os.environ["A4_COMPONENT_ROOT"])
    identity_path = root/"unified_system/gateway_identity.py"
    fixture_path = root/"tests/test_gateway_identity.py"
    for path, expected in ((identity_path, IDENTITY_SHA), (fixture_path, FIXTURE_SHA)):
        if path.is_symlink() or path.stat().st_nlink != 1 or hashlib.sha256(path.read_bytes()).hexdigest() != expected:
            raise RuntimeError("OWNER_SOURCE_NOT_PROVISIONED")
    owner = importlib.import_module("unified_system.gateway_identity")
    if Path(owner.__file__).resolve() != identity_path.resolve():
        raise RuntimeError("OWNER_CANONICAL_MODULE_MISMATCH")
    name = "a4_pinned_owner_tls_fixture"
    if name not in sys.modules:
        spec = importlib.util.spec_from_file_location(name, fixture_path)
        module = importlib.util.module_from_spec(spec)
        sys.modules[name] = module
        spec.loader.exec_module(module)
    return owner, sys.modules[name]
