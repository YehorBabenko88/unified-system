"""Explicit, LAB-only canonical Grid v2 source selector, never an admission grant.

The protected capsule and native service grant still authenticate every file.
This module only prevents a Strattester-v1 to Grid-v2 implicit code switch.
"""
import re

LEGACY_ENTRY = "market_data.cli"
V2_ENTRY = "market_data_v2.read_api"
GRID_REPOSITORY = "YehorBabenko88/bybit-cluster-grid"
APPROVED_GRID_COMMIT = "f57781a947af138a2099bebe553b89c3c5ee726e"
V2_SOURCE_VERSION = "0.2.0-dev0"
V2_WHEEL_VERSION = "0.2.0.dev0"
V2_FILES = (
    "sources/market_data/market_data_v2/__init__.py",
    "sources/market_data/market_data_v2/qualified_read_contract.py",
    "sources/market_data/market_data_v2/read_api.py",
)
_SHA256 = re.compile(r"[0-9a-f]{64}\Z")


class MarketDataEntryRejected(ValueError):
    pass


def _pinned_file(files, path):
    pin = files.get(path)
    return (type(pin) is dict and set(pin) == {"sha256", "bytes"}
            and type(pin["sha256"]) is str
            and _SHA256.fullmatch(pin["sha256"]) is not None
            and type(pin["bytes"]) is int and 0 < pin["bytes"] <= 64 * 1024 * 1024)


def entry_for_manifest(manifest):
    """Select only one entry based on an exact source-and-wheel cohort.

    Old Strattester-backed manifests retain their old fixed entrypoint.
    Explicit Grid v2 source requires a matching full commit, source version,
    all three pinned addon files and one pinned wheel lock, or is rejected.
    This selector never starts a process, authenticates a publisher or proves
    exclusive Grid/PostgreSQL writer ownership.
    """
    if type(manifest) is not dict:
        raise MarketDataEntryRejected("MARKET_ENTRY_SOURCE_REJECTED")
    sources = manifest.get("sources")
    files = manifest.get("files")
    if type(sources) is not dict or type(files) is not dict:
        raise MarketDataEntryRejected("MARKET_ENTRY_SOURCE_REJECTED")
    source = sources.get("market_data")
    if type(source) is not dict:
        raise MarketDataEntryRejected("MARKET_ENTRY_SOURCE_REJECTED")
    if source.get("repository") != GRID_REPOSITORY:
        return LEGACY_ENTRY
    deps = manifest.get("dependencies")
    if (manifest.get("schema") != "unified.lab-release.v1"
            or manifest.get("mode") != "LAB_SIMULATION"):
        raise MarketDataEntryRejected("GRID_V2_LAB_SCOPE_REQUIRED")
    if (source.get("commit") != APPROVED_GRID_COMMIT
            or source.get("version") != V2_SOURCE_VERSION
            or source.get("root") != "sources/market_data"
            or type(deps) is not list
            or not all(_pinned_file(files, path) for path in V2_FILES)):
        raise MarketDataEntryRejected("GRID_V2_SOURCE_NOT_ADMITTED")
    wheels = [d for d in deps if type(d) is dict and d.get("name") == "market-data"]
    if (len(wheels) != 1 or wheels[0].get("version") != V2_WHEEL_VERSION
            or type(wheels[0].get("lock_path")) is not str
            or not _pinned_file(files, wheels[0]["lock_path"])):
        raise MarketDataEntryRejected("GRID_V2_WHEEL_NOT_ADMITTED")
    return V2_ENTRY
