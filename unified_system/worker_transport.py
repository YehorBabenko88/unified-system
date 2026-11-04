"""Minimal Windows SSH client context, without application credentials.

This does not authorize a connection or enrollment. Callers must separately
admit source/plan, preserve host-key checks and obtain the physical-phase grant.
"""
from collections.abc import Mapping
import os

_NAMES=frozenset(('SYSTEMROOT','WINDIR','PROGRAMDATA','USERPROFILE','PATH',
                  'HOMEDRIVE','HOMEPATH','TEMP','TMP'))
_REQUIRED=frozenset(('SYSTEMROOT','PROGRAMDATA','USERPROFILE','PATH'))


def windows_ssh_environment(source=None):
    """Retain public OS context required by Windows OpenSSH; never copy secrets.

    Actual Windows OpenSSH exits255 before diagnostics if PROGRAMDATA is absent.
    Reject that condition before launching the client rather than inheriting the
    entire environment (which could contain fleet, database or exchange secrets).
    """
    source=os.environ if source is None else source
    if not isinstance(source,Mapping):raise ValueError('SSH_OS_CONTEXT_INVALID')
    result={}
    for name,value in source.items():
        if type(name) is not str:raise ValueError('SSH_OS_CONTEXT_INVALID')
        name=name.upper()
        if name not in _NAMES:continue
        if name in result:raise ValueError('SSH_OS_CONTEXT_AMBIGUOUS')
        if type(value) is not str or not 1<=len(value)<=32767 or any(c in value for c in ('\0','\r','\n')):
            raise ValueError('SSH_OS_CONTEXT_INVALID')
        result[name]=value
    if not _REQUIRED<=result.keys():raise ValueError('SSH_OS_CONTEXT_MISSING')
    return result
