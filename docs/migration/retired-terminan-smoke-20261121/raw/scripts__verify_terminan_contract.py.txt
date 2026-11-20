"""Source-only Terminan consumer checks, no listener or live network."""
import importlib.util
import pathlib
import sys
import types

def load_consumer(path):
    # Terminan's real consumer imports source adapter modules. Import the actual
    # package with its own checkout on sys.path, never fake its implementation.
    root=path.resolve()
    sys.path.insert(0,str(root))
    try:
        from terminan.consumer import present_source
        return present_source
    finally:
        sys.path.pop(0)

def main(root):
    consumer=load_consumer(pathlib.Path(root))
    unavailable=consumer({"version":1,"authority":"SYNTHETIC_ONLY","state":"UNKNOWN","coverage":{}})
    assert unavailable["state"]=="UNAVAILABLE"
    stale=consumer({"version":1,"authority":"HISTORICAL_ONLY","state":"STALE","coverage":{"verified":False}})
    assert stale["state"]=="STALE" and stale["coverage_verified"] is False
    gap=consumer({"version":1,"authority":"HISTORICAL_ONLY","state":"PARTIAL","coverage":{"verified":False}})
    assert gap["state"]=="GAP"
    print("TERMINAN_PINNED_CONSUMER_SOURCE_SMOKE_PASS")

if __name__=="__main__":
    if len(sys.argv)!=2:raise SystemExit("expected checkout")
    main(sys.argv[1])
