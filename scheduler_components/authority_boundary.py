"""Closed wire-v2 draft3 boundary. No backend/client, flags or live endpoints.

This is an isolated deny boundary, not an implementation of authority operations.
Opening it requires a new reviewed adapter; caller payload cannot open a gate.
"""
CONTRACT_SHA256 = '5cc8e6a3557a9d71b6d1ccdf9939be49133deee9219b19029ffd4cf3d3bfa278'
MUTATIONS = frozenset({'GrantAssignment', 'RenewAssignment', 'DrainAssignment',
    'SupersedeAssignment', 'CancelAssignment', 'CompleteAssignment',
    'PublishSegment', 'AdoptCommittedSegment', 'ReleaseReservation'})

class ClosedAuthorityBoundary:
    def execute(self, operation, payload=None):
        if not isinstance(operation, str):
            return 'UNSUPPORTED_OPERATION'
        if operation in MUTATIONS:
            return 'SAFETY_GATE_CLOSED'
        if operation == 'ReadReceipt':
            return 'UNKNOWN'
        if operation == 'Rejoin':
            return 'RECONCILIATION_REQUIRED'
        return 'UNSUPPORTED_OPERATION'
