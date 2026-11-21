"""Read-only dry-run installation planner; never installs or executes anything."""
from .lockfile import validate_lock
from .module_catalog import MODULE_IDS

def plan(lock, installed=()):
    wanted=validate_lock(lock)
    installed=frozenset(installed)
    if not installed <= MODULE_IDS:
        raise ValueError("unknown installed module")
    return {"mode":"DRY_RUN_ONLY","would_install":sorted(set(wanted)-installed),"already_present":sorted(set(wanted)&installed),"would_remove":[],"mutations_performed":False,"physical_acceptance":"NOT_RUN"}
