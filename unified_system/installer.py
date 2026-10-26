"""Read-only dry-run installation planner; never installs or executes anything."""
from .lockfile import validate_lock

def plan(lock, installed=()):
    wanted=validate_lock(lock)
    installed=frozenset(installed)
    if not installed <= {"grid","strattester","terminan"}:
        raise ValueError("unknown installed module")
    return {"mode":"DRY_RUN_ONLY","would_install":sorted(set(wanted)-installed),"already_present":sorted(set(wanted)&installed),"would_remove":[],"mutations_performed":False,"physical_acceptance":"NOT_RUN"}
