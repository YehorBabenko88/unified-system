"""Unavailable async boundary until an exact actual native producer is bound.

Not an implemented Consul adapter. No caller-supplied backend callback, readiness
boolean or local metadata fallback can promote this fixture to authority.
"""
from .contracts import StorageBlocked


class PublicationAdapter:
    def __init__(self):
        pass

    async def commit_storage(self, intent_bytes):
        raise StorageBlocked("ACTUAL_PUBLICATION_BACKEND_UNAVAILABLE")

    async def reconcile_storage(self, original_intent_bytes):
        raise StorageBlocked("ACTUAL_PUBLICATION_BACKEND_UNAVAILABLE")
