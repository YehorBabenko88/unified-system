"""Remove two write-bypass privileges from this explicit LAB process only.

This supports accidental-write ACL protection. It does not make the process a
non-administrator, constrain hostile owner code, or change the parent or host.
No privilege is enabled, and no impersonation or integrity level is changed.
"""
import os

NAMES=('SeRestorePrivilege','SeBackupPrivilege')
LIMIT=65536
MAX_COUNT=256


def _api():
    if os.name!='nt':raise ValueError('LAB_PRIVILEGE_WINDOWS_REQUIRED')
    import ctypes as c
    from ctypes import wintypes as w
    class LUID(c.Structure):
        _fields_=[('LowPart',w.DWORD),('HighPart',w.LONG)]
    class ENTRY(c.Structure):
        _fields_=[('Luid',LUID),('Attributes',w.DWORD)]
    k=c.WinDLL('kernel32',use_last_error=True)
    a=c.WinDLL('advapi32',use_last_error=True)
    k.GetCurrentProcess.argtypes=[];k.GetCurrentProcess.restype=w.HANDLE
    k.GetCurrentThread.argtypes=[];k.GetCurrentThread.restype=w.HANDLE
    k.CloseHandle.argtypes=[w.HANDLE];k.CloseHandle.restype=w.BOOL
    a.OpenProcessToken.argtypes=[w.HANDLE,w.DWORD,c.POINTER(w.HANDLE)];a.OpenProcessToken.restype=w.BOOL
    a.OpenThreadToken.argtypes=[w.HANDLE,w.DWORD,w.BOOL,c.POINTER(w.HANDLE)];a.OpenThreadToken.restype=w.BOOL
    a.LookupPrivilegeValueW.argtypes=[w.LPCWSTR,w.LPCWSTR,c.POINTER(LUID)];a.LookupPrivilegeValueW.restype=w.BOOL
    a.GetTokenInformation.argtypes=[w.HANDLE,c.c_int,c.c_void_p,w.DWORD,c.POINTER(w.DWORD)];a.GetTokenInformation.restype=w.BOOL
    a.AdjustTokenPrivileges.argtypes=[w.HANDLE,w.BOOL,c.c_void_p,w.DWORD,c.c_void_p,c.c_void_p];a.AdjustTokenPrivileges.restype=w.BOOL
    return c,w,k,a,LUID,ENTRY


def _snapshot(c,w,a,token,ENTRY):
    # Fixed bounded buffer: never allocate a size supplied by the token API.
    buffer=c.create_string_buffer(LIMIT);length=w.DWORD()
    if not a.GetTokenInformation(token,3,buffer,LIMIT,c.byref(length)):
        raise ValueError('LAB_PRIVILEGE_QUERY_FAILED')
    if not 4<=length.value<=LIMIT:raise ValueError('LAB_PRIVILEGE_QUERY_BOUNDS')
    count=w.DWORD.from_buffer(buffer).value
    offset=4;size=c.sizeof(ENTRY)
    if count>MAX_COUNT or offset+count*size>length.value:
        raise ValueError('LAB_PRIVILEGE_QUERY_BOUNDS')
    result={}
    for index in range(count):
        entry=ENTRY.from_buffer_copy(buffer,offset+index*size)
        key=(entry.Luid.LowPart,entry.Luid.HighPart)
        if key in result:raise ValueError('LAB_PRIVILEGE_QUERY_BOUNDS')
        result[key]=entry.Attributes
    return result


def _with_primary(reduce):
    c,w,k,a,LUID,ENTRY=_api()
    thread=w.HANDLE()
    if a.OpenThreadToken(k.GetCurrentThread(),8,True,c.byref(thread)):
        k.CloseHandle(thread)
        raise ValueError('LAB_PRIVILEGE_THREAD_TOKEN_REJECTED')
    if c.get_last_error()!=1008:raise ValueError('LAB_PRIVILEGE_THREAD_QUERY_FAILED')
    token=w.HANDLE()
    if not a.OpenProcessToken(k.GetCurrentProcess(),8|(32 if reduce else 0),c.byref(token)):
        raise ValueError('LAB_PRIVILEGE_PROCESS_TOKEN_FAILED')
    try:
        targets={}
        for name in NAMES:
            luid=LUID()
            if not a.LookupPrivilegeValueW(None,name,c.byref(luid)):
                raise ValueError('LAB_PRIVILEGE_LOOKUP_FAILED')
            targets[name]=(luid.LowPart,luid.HighPart)
        before=_snapshot(c,w,a,token,ENTRY)
        present=[key for key in targets.values() if key in before]
        if reduce and present:
            class CHANGES(c.Structure):
                _fields_=[('PrivilegeCount',w.DWORD),('Privileges',ENTRY*len(present))]
            changes=CHANGES();changes.PrivilegeCount=len(present)
            for entry,key in zip(changes.Privileges,present):
                entry.Luid.LowPart,entry.Luid.HighPart=key
                entry.Attributes=4  # SE_PRIVILEGE_REMOVED: irreversible here.
            c.set_last_error(0)
            if not a.AdjustTokenPrivileges(token,False,c.byref(changes),0,None,None) or c.get_last_error()!=0:
                raise ValueError('LAB_PRIVILEGE_REMOVAL_FAILED')
        after=_snapshot(c,w,a,token,ENTRY) if reduce else before
        if reduce and any(key in after for key in targets.values()):
            raise ValueError('LAB_PRIVILEGE_REMOVAL_UNVERIFIED')
        # Ensure no other privilege's attributes were changed by this operation.
        if reduce and {k:v for k,v in before.items() if k not in targets.values()}!=after:
            raise ValueError('LAB_PRIVILEGE_UNEXPECTED_CHANGE')
        return {name:'PRESENT' if key in after else 'ABSENT' for name,key in targets.items()}
    finally:k.CloseHandle(token)


def current_privilege_state():
    """Read only the two relevant statuses; never disclose token handles."""
    return _with_primary(False)


def remove_lab_write_bypass_privileges():
    """Permanently remove only Backup/Restore from this primary token."""
    _with_primary(True)
    return 'LAB_WRITE_BYPASS_PRIVILEGES_ABSENT'
