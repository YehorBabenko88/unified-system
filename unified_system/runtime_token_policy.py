"""Read-only Windows runtime-token policy proposal, NOT execution authority.

Not wired into the protected Kernel. Expected identities must ultimately come
from its protected owner-approved descriptor, not an environment/JSON ticket.
This audit does not prove network object ACLs, service-account provisioning,
future impersonation by other threads, or absence of delegated network access.
It never repairs/reconfigures a network, changes tokens, or restarts services.

Microsoft primary documentation (reviewed 2026-11-05):
https://learn.microsoft.com/en-us/windows/win32/services/localservice-account
https://learn.microsoft.com/en-us/windows/win32/secauthz/sid-attributes-in-an-access-token
https://learn.microsoft.com/en-us/windows/win32/secauthz/privilege-constants
https://learn.microsoft.com/en-us/windows/win32/api/winsvc/ns-winsvc-service_required_privileges_infow
https://learn.microsoft.com/en-us/windows/win32/secauthz/mandatory-integrity-control
"""
import re
import os

SCHEMA = 'unified.windows-runtime-token-observation.v1'
COMPONENTS = ('unified-system', 'grid', 'strattester', 'math', 'meta_analyse', 'terminan')
FIELDS = frozenset(('schema', 'user_sid', 'token_type', 'elevation_type', 'elevated',
                    'thread_token_present', 'session_id', 'ui_access', 'integrity_sid', 'groups', 'privileges'))
FORBIDDEN_GROUPS = frozenset('S-1-5-32-' + str(rid) for rid in (544, 547, 548, 549, 550, 551, 552, 556, 578)) | {'S-1-5-114'}
ALLOWED_PRIVILEGES = frozenset(('SeChangeNotifyPrivilege',))


class TokenPolicyBlocked(ValueError):
    pass


def need(value, code='RUNTIME_TOKEN_OBSERVATION_REJECTED'):
    if not value:
        raise TokenPolicyBlocked(code)


def canonical_sid(value):
    need(type(value) is str and len(value) <= 184 and re.fullmatch(r'S-1-[0-9]+(?:-[0-9]+){1,15}', value))
    parts = value.split('-')[2:]
    need(all(str(int(part)) == part for part in parts))
    need(int(parts[0]) < 2**48 and all(int(part) < 2**32 for part in parts[1:]))
    return value


def service_sid(value):
    canonical_sid(value)
    return re.fullmatch(r'S-1-5-80-(?:[0-9]+-){4}[0-9]+', value) is not None


def dedicated_account_sid(value):
    canonical_sid(value)
    need(service_sid(value) or (re.fullmatch(r'S-1-5-21-(?:[0-9]+-){3}[0-9]+', value)
                               and int(value.rsplit('-', 1)[1]) >= 1000), 'DEDICATED_RUNTIME_ACCOUNT_REQUIRED')
    return value


def validate_component_accounts(mapping):
    """Validate a proposed inventory, not proof that accounts/services exist."""
    need(type(mapping) is dict and set(mapping) == set(COMPONENTS), 'COMPONENT_ACCOUNT_INVENTORY_REJECTED')
    values = [dedicated_account_sid(mapping[name]) for name in COMPONENTS]
    need(len(set(values)) == len(COMPONENTS), 'COMPONENT_ACCOUNT_REUSE_REJECTED')
    return {name: mapping[name] for name in COMPONENTS}


def sid_from_buffer(raw, base, pointer):
    """Decode an inline SID only after bounds checking; no pointer dereference."""
    need(type(raw) is bytes and len(raw) <= 65536 and type(base) is int and type(pointer) is int)
    offset = pointer - base
    need(0 <= offset <= len(raw) - 8)
    revision = raw[offset]; count = raw[offset + 1]
    need(revision == 1 and 1 <= count <= 15 and offset + 8 + 4 * count <= len(raw))
    authority = int.from_bytes(raw[offset + 2:offset + 8], 'big')
    subs = [int.from_bytes(raw[offset + 8 + 4*i:offset + 12 + 4*i], 'little') for i in range(count)]
    return canonical_sid('S-1-' + str(authority) + ''.join('-' + str(value) for value in subs))


def evaluate_token(observation, *, expected_account_sid, expected_service_sid):
    """Pure policy on supplied facts; fake facts can NEVER authorize execution."""
    dedicated_account_sid(expected_account_sid)
    need(service_sid(expected_service_sid), 'EXPECTED_SERVICE_IDENTITY_REJECTED')
    need(type(observation) is dict and set(observation) == FIELDS and observation['schema'] == SCHEMA)
    user = canonical_sid(observation['user_sid'])
    need(user == expected_account_sid, 'RUNTIME_ACCOUNT_MISMATCH')
    for key in ('token_type', 'elevation_type', 'session_id'):
        need(type(observation[key]) is int)
    for key in ('elevated', 'thread_token_present', 'ui_access'):
        need(type(observation[key]) is bool)
    need(observation['token_type'] == 1 and observation['elevation_type'] == 1
         and observation['elevated'] is False and observation['thread_token_present'] is False
         and observation['ui_access'] is False and observation['session_id'] == 0, 'UNSAFE_RUNTIME_TOKEN')
    # System-service integrity alone is not membership in Administrators. It
    # remains subject to all identity, group, privilege and elevation checks.
    need(observation['integrity_sid'] in ('S-1-16-8192', 'S-1-16-16384'), 'RUNTIME_INTEGRITY_REJECTED')
    groups = observation['groups']; privileges = observation['privileges']
    need(type(groups) is list and 1 <= len(groups) <= 256 and type(privileges) is list and len(privileges) <= 256)
    seen = {}; service_groups = set()
    for row in groups:
        need(type(row) is dict and set(row) == {'sid', 'attributes'})
        sid = canonical_sid(row['sid']); flags = row['attributes']
        need(sid not in seen and type(flags) is int and 0 <= flags <= 0xffffffff and flags & ~0xe000007f == 0
             and not (flags & 4 and flags & 16))
        need(sid not in FORBIDDEN_GROUPS and not (sid.startswith('S-1-5-21-') and sid.rsplit('-', 1)[1] in ('512', '518', '519')),
             'PRIVILEGED_RUNTIME_GROUP_PRESENT')
        seen[sid] = flags
        if service_sid(sid):
            need(flags & 4 and not flags & 16, 'RUNTIME_SERVICE_IDENTITY_REJECTED'); service_groups.add(sid)
    need(seen.get('S-1-5-6', 0) & 4 and not seen.get('S-1-5-6', 0) & 16, 'SERVICE_LOGON_REQUIRED')
    need(service_groups <= {expected_service_sid} and (expected_service_sid in service_groups or user == expected_service_sid),
         'RUNTIME_SERVICE_IDENTITY_REJECTED')
    names = set()
    for row in privileges:
        need(type(row) is dict and set(row) == {'name', 'attributes'})
        name = row['name']; flags = row['attributes']
        need(type(name) is str and name not in names and name in ALLOWED_PRIVILEGES,
             'UNSAFE_RUNTIME_PRIVILEGE_PRESENT')
        need(type(flags) is int and 0 <= flags <= 0xffffffff and flags & ~0x80000007 == 0)
        names.add(name)
    return dict(schema='unified.runtime-token-policy-result.v1', status='TOKEN_POLICY_SATISFIED',
                execution_authority=False, network_configuration_access='NOT_PROVEN',
                account_provisioning='NOT_EVALUATED', account_sid=user, service_sid=expected_service_sid)


def groups_from_buffer(raw, base, pointer_size):
    need(pointer_size in (4, 8) and len(raw) >= pointer_size)
    count = int.from_bytes(raw[:4], 'little'); stride = pointer_size * 2
    end = pointer_size + count * stride
    need(count <= 256 and end <= len(raw))
    rows = []
    for index in range(count):
        offset = pointer_size + index * stride
        pointer = int.from_bytes(raw[offset:offset + pointer_size], 'little')
        need(pointer - base >= end)
        sid = sid_from_buffer(raw, base, pointer)
        rows.append(dict(sid=sid, attributes=int.from_bytes(raw[offset + pointer_size:offset + pointer_size + 4], 'little')))
    return rows


def privileges_from_buffer(raw, name_for_luid):
    need(len(raw) >= 4)
    count = int.from_bytes(raw[:4], 'little')
    need(count <= 256 and 4 + count * 12 <= len(raw))
    return [dict(name=name_for_luid(raw[4 + i*12:12 + i*12]),
                 attributes=int.from_bytes(raw[12 + i*12:16 + i*12], 'little')) for i in range(count)]


def _collect(api):
    """Typed backend seam for offline ABI/failure tests; NOT a grant factory."""
    need(api.thread_token_present() is False, 'RUNTIME_THREAD_TOKEN_PRESENT')
    token = api.open_process(); current = None
    try:
        before, _ = api.query(token, 10)
        need(len(before) == 56, 'RUNTIME_TOKEN_STATISTICS_REJECTED')
        def scalar(kind):
            raw, _ = api.query(token, kind); need(len(raw) == 4)
            return int.from_bytes(raw, 'little')
        def sid(kind):
            raw, base = api.query(token, kind); size = api.pointer_size
            need(len(raw) >= 2*size)
            pointer = int.from_bytes(raw[:size], 'little'); need(pointer - base >= 2*size)
            return sid_from_buffer(raw, base, pointer)
        user = sid(1); raw, base = api.query(token, 2)
        groups = groups_from_buffer(raw, base, api.pointer_size)
        raw, _ = api.query(token, 3); privileges = privileges_from_buffer(raw, api.privilege_name)
        elevation = scalar(20); ui_access = scalar(26)
        need(elevation in (0, 1) and ui_access in (0, 1))
        result = dict(schema=SCHEMA, user_sid=user, groups=groups, privileges=privileges,
                      token_type=scalar(8), elevation_type=scalar(18), elevated=bool(elevation),
                      thread_token_present=False, ui_access=bool(ui_access), session_id=scalar(12), integrity_sid=sid(25))
        after, _ = api.query(token, 10)
        need(before == after and int.from_bytes(before[40:44], 'little') == len(groups)
             and int.from_bytes(before[44:48], 'little') == len(privileges), 'RUNTIME_TOKEN_CHANGED')
        candidate = api.open_process()
        need(candidate != token, 'RUNTIME_TOKEN_HANDLE_REJECTED'); current = candidate
        current_stats, _ = api.query(current, 10)
        need(current_stats == before and api.thread_token_present() is False, 'RUNTIME_TOKEN_CHANGED')
        return result
    finally:
        try:
            if current is not None:
                api.close(current)
        finally:
            api.close(token)


class _WindowsTokenReader:
    """TOKEN_QUERY only. No mutation, impersonation, logon or network API."""
    def __init__(self):
        need(os.name == 'nt', 'RUNTIME_TOKEN_WINDOWS_REQUIRED')
        import ctypes as c
        from ctypes import wintypes as w
        self.c = c; self.w = w; self.pointer_size = c.sizeof(c.c_void_p)
        self.kernel = c.WinDLL('kernel32', use_last_error=True)
        self.advapi = c.WinDLL('advapi32', use_last_error=True)
        self.kernel.GetCurrentProcess.argtypes=[]; self.kernel.GetCurrentProcess.restype=w.HANDLE
        self.kernel.GetCurrentThread.argtypes=[]; self.kernel.GetCurrentThread.restype=w.HANDLE
        self.kernel.CloseHandle.argtypes=[w.HANDLE]; self.kernel.CloseHandle.restype=w.BOOL
        self.advapi.OpenProcessToken.argtypes=[w.HANDLE,w.DWORD,c.POINTER(w.HANDLE)]; self.advapi.OpenProcessToken.restype=w.BOOL
        self.advapi.OpenThreadToken.argtypes=[w.HANDLE,w.DWORD,w.BOOL,c.POINTER(w.HANDLE)]; self.advapi.OpenThreadToken.restype=w.BOOL
        self.advapi.GetTokenInformation.argtypes=[w.HANDLE,c.c_int,c.c_void_p,w.DWORD,c.POINTER(w.DWORD)]; self.advapi.GetTokenInformation.restype=w.BOOL
        self.advapi.LookupPrivilegeNameW.argtypes=[w.LPCWSTR,c.c_void_p,w.LPWSTR,c.POINTER(w.DWORD)]; self.advapi.LookupPrivilegeNameW.restype=w.BOOL

    def close(self, token):
        need(self.kernel.CloseHandle(token), 'RUNTIME_TOKEN_CLOSE_FAILED')

    def thread_token_present(self):
        token = self.w.HANDLE(); self.c.set_last_error(0)
        if self.advapi.OpenThreadToken(self.kernel.GetCurrentThread(), 8, True, self.c.byref(token)):
            self.close(token); return True
        need(self.c.get_last_error() == 1008, 'RUNTIME_THREAD_TOKEN_QUERY_FAILED')
        return False

    def open_process(self):
        token = self.w.HANDLE()
        need(self.advapi.OpenProcessToken(self.kernel.GetCurrentProcess(), 8, self.c.byref(token)), 'RUNTIME_PROCESS_TOKEN_QUERY_FAILED')
        need(bool(token.value), 'RUNTIME_TOKEN_HANDLE_REJECTED')
        return token.value

    def query(self, token, kind):
        # TokenElevation rejects an oversized buffer with ERROR_BAD_LENGTH on
        # actual Windows even though variable-length classes accept one. Fixed
        # scalar/statistics ABI sizes are exact; variable inputs stay bounded.
        sizes = {1:65536, 2:65536, 3:65536, 8:4, 10:56, 12:4, 18:4, 20:4, 25:65536, 26:4}
        need(kind in sizes, 'RUNTIME_TOKEN_CLASS_REJECTED')
        buffer = self.c.create_string_buffer(sizes[kind]); length = self.w.DWORD()
        need(self.advapi.GetTokenInformation(token, kind, buffer, len(buffer), self.c.byref(length)), 'RUNTIME_TOKEN_QUERY_FAILED')
        need(4 <= length.value <= len(buffer), 'RUNTIME_TOKEN_QUERY_BOUNDS')
        return bytes(buffer.raw[:length.value]), self.c.addressof(buffer)

    def privilege_name(self, raw):
        need(type(raw) is bytes and len(raw) == 8)
        luid = self.c.create_string_buffer(raw, 8); text = self.c.create_unicode_buffer(129); length = self.w.DWORD(129)
        need(self.advapi.LookupPrivilegeNameW(None, luid, text, self.c.byref(length)) and 1 <= length.value <= 128,
             'RUNTIME_PRIVILEGE_NAME_QUERY_FAILED')
        value = text.value
        need(len(value) == length.value and re.fullmatch(r'Se[A-Za-z0-9]+Privilege', value), 'RUNTIME_PRIVILEGE_NAME_REJECTED')
        return value


def collect_current_process_token():
    """Momentary read-only observation of this process and calling thread."""
    return _collect(_WindowsTokenReader())


def require_current_runtime_token(*, expected_account_sid, expected_service_sid):
    """Real local token audit; never substitutes for protected Kernel admission."""
    return evaluate_token(collect_current_process_token(), expected_account_sid=expected_account_sid,
                          expected_service_sid=expected_service_sid)
