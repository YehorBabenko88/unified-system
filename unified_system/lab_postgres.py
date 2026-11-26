"""LAB_SIMULATION temporary PostgreSQL (Workstream C2, MASTER #111).

A dedicated, throw-away cluster owned by the LAB supervisor:
- binaries from an explicit absolute directory, major version checked (>= 18
  for market_data's READ_ONLY health contract);
- data directory inside the supervisor-owned temporary root only; never an
  existing cluster, never the default port, never system services;
- loopback TCP only (listen_addresses=127.0.0.1, no Unix socket on Windows,
  a private socket directory elsewhere), SCRAM authentication;
- two roles: ``lab_writer`` (single market-data writer) and ``lab_reader``
  (default_transaction_read_only=on) with random passwords;
- crash simulation (SIGKILL / TerminateProcess of the postmaster), restart
  with WAL crash recovery, and integrity checks; fast stop.
Stdlib only. Passwords are never logged or returned except inside DSNs that
are handed to admitted children.
"""
import os
import stat
import re
import secrets
import signal
import socket
import subprocess
import time
from pathlib import Path

from .lab_simulation_admission import LabAdmissionRejected, need

IDENT = re.compile(r'[a-z_][a-z0-9_]{0,62}')


def _free_port():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('127.0.0.1', 0))
        return s.getsockname()[1]


class LabPostgres:
    def __init__(self, bin_dir, owned_root, *, min_major=18, database='lab'):
        self.bin = Path(bin_dir)
        self.root = Path(owned_root)
        # A caller-provided directory is not an ownership proof.  Require a
        # private, newly created root, and keep a stable filesystem identity.
        self._root_stat = self.root.lstat() if self.root.exists() else None
        need(self.bin.is_absolute() and self.root.is_absolute() and self.root.is_dir(), 'LAB_PG_PATH_REJECTED')
        suffix = '.exe' if os.name == 'nt' else ''
        self.tools = {n: self.bin / (n + suffix) for n in ('postgres', 'initdb', 'pg_ctl', 'psql')}
        need(all(p.is_file() for p in self.tools.values()), 'LAB_PG_BINARIES_MISSING')
        version = subprocess.run([str(self.tools['postgres']), '--version'], capture_output=True, text=True,
                                 timeout=30).stdout
        match = re.search(r'\(PostgreSQL\) ([0-9]+)', version)
        need(match is not None, 'LAB_PG_VERSION_UNKNOWN')
        self.major = int(match[1])
        need(self.major >= min_major, 'LAB_PG_VERSION_TOO_OLD')
        need(IDENT.fullmatch(database) is not None, 'LAB_PG_NAME_REJECTED')
        self.database = database
        need(self._root_stat is not None and stat.S_ISDIR(self._root_stat.st_mode)
             and not self.root.is_symlink()
             and not (getattr(self._root_stat, 'st_file_attributes', 0) & 0x400),
             'LAB_PG_ROOT_UNOWNED')
        if os.name != 'nt':
            need(self._root_stat.st_uid == os.getuid()
                 and not (self._root_stat.st_mode & 0o077), 'LAB_PG_ROOT_UNSAFE')
        self._root_identity = (self._root_stat.st_dev, self._root_stat.st_ino)
        self._nonce = secrets.token_hex(24)
        self._marker = self.root / '.lab-postgres-owner'
        need(not self._marker.exists() and not self._marker.is_symlink(), 'LAB_PG_ROOT_USED')
        with self._marker.open('x', encoding='ascii') as marker:
            marker.write(self._nonce)
        if os.name != 'nt':
            self._marker.chmod(0o600)
        self.data = self.root / 'pgdata'
        self.socket_dir = self.root / 'pgsock'
        self.log = self.root / 'postgres.log'
        self.port = None
        self.passwords = {}
        self.started = False
        self._owned_pid = None
        self._owned_start_time = None
        self._owned_pidfile_inode = None
        self._crashed = False

    # ------------------------------------------------------------------
    def _verify_owned(self):
        try:
            info = self.root.lstat()
            need(stat.S_ISDIR(info.st_mode) and not self.root.is_symlink()
                 and not (getattr(info, 'st_file_attributes', 0) & 0x400)
                 and (info.st_dev, info.st_ino) == self._root_identity,
                 'LAB_PG_ROOT_CHANGED')
            need(not self._marker.is_symlink() and self._marker.read_text(encoding='ascii') == self._nonce,
                 'LAB_PG_OWNERSHIP_LOST')
            if os.name != 'nt':
                need(info.st_uid == os.getuid() and not (info.st_mode & 0o077), 'LAB_PG_ROOT_UNSAFE')
            if self.data.exists():
                data_info = self.data.lstat()
                need(stat.S_ISDIR(data_info.st_mode) and not self.data.is_symlink()
                     and not (getattr(data_info, 'st_file_attributes', 0) & 0x400),
                     'LAB_PG_DATA_FOREIGN')
                if os.name != 'nt':
                    need(data_info.st_uid == os.getuid(), 'LAB_PG_DATA_FOREIGN')
        except (OSError, ValueError) as error:
            raise LabAdmissionRejected('LAB_PG_OWNERSHIP_LOST') from error

    def _os_process_identity(self, pid, recorded_start):
        """Fail closed unless the PID still identifies our postgres executable
        and the OS process creation time matches postmaster.pid."""
        need(recorded_start > 0, 'LAB_PG_PID_UNVERIFIED')
        try:
            if os.name == 'nt':
                import ctypes
                from ctypes import wintypes
                kernel = ctypes.WinDLL('kernel32', use_last_error=True)
                kernel.OpenProcess.argtypes = (wintypes.DWORD, wintypes.BOOL, wintypes.DWORD)
                kernel.OpenProcess.restype = wintypes.HANDLE
                kernel.QueryFullProcessImageNameW.argtypes = (
                    wintypes.HANDLE, wintypes.DWORD, wintypes.LPWSTR, ctypes.POINTER(wintypes.DWORD))
                kernel.QueryFullProcessImageNameW.restype = wintypes.BOOL
                kernel.GetProcessTimes.argtypes = (
                    wintypes.HANDLE, ctypes.POINTER(wintypes.FILETIME), ctypes.POINTER(wintypes.FILETIME),
                    ctypes.POINTER(wintypes.FILETIME), ctypes.POINTER(wintypes.FILETIME))
                kernel.GetProcessTimes.restype = wintypes.BOOL
                handle = kernel.OpenProcess(0x1000, False, pid)  # QUERY_LIMITED_INFORMATION
                need(bool(handle), 'LAB_PG_PID_UNVERIFIED')
                try:
                    path_buf = ctypes.create_unicode_buffer(32768)
                    size = wintypes.DWORD(len(path_buf))
                    need(bool(kernel.QueryFullProcessImageNameW(handle, 0, path_buf, ctypes.byref(size))),
                         'LAB_PG_PID_UNVERIFIED')
                    need(os.path.normcase(os.path.realpath(path_buf.value)) ==
                         os.path.normcase(os.path.realpath(str(self.tools['postgres']))),
                         'LAB_PG_PID_FOREIGN')
                    created = wintypes.FILETIME()
                    ended, kernel_time, user_time = wintypes.FILETIME(), wintypes.FILETIME(), wintypes.FILETIME()
                    need(bool(kernel.GetProcessTimes(handle, ctypes.byref(created), ctypes.byref(ended),
                                                     ctypes.byref(kernel_time), ctypes.byref(user_time))),
                         'LAB_PG_PID_UNVERIFIED')
                    ticks = (created.dwHighDateTime << 32) | created.dwLowDateTime
                    started_at = (ticks - 116444736000000000) / 10000000
                finally:
                    kernel.CloseHandle(handle)
            else:
                proc = Path('/proc') / str(pid)
                need(proc.is_dir(), 'LAB_PG_PID_UNVERIFIED')
                need((proc / 'exe').resolve(strict=True) ==
                     self.tools['postgres'].resolve(strict=True), 'LAB_PG_PID_FOREIGN')
                stat_fields = (proc / 'stat').read_text().rsplit(')', 1)[1].strip().split()
                start_ticks = int(stat_fields[19])  # /proc/PID/stat field 22
                btime_line = next(line for line in Path('/proc/stat').read_text().splitlines()
                                  if line.startswith('btime '))
                started_at = int(btime_line.split()[1]) + start_ticks / os.sysconf('SC_CLK_TCK')
                args = (proc / 'cmdline').read_bytes().split(bytes([0]))
                need(any(args[i] == b'-D' and i + 1 < len(args) and
                         Path(os.fsdecode(args[i + 1])).resolve() == self.data.resolve()
                         for i in range(len(args))), 'LAB_PG_PID_FOREIGN')
                status = (proc / 'status').read_text().splitlines()
                uid = next(line for line in status if line.startswith('Uid:')).split()[1]
                need(int(uid) == os.getuid(), 'LAB_PG_PID_FOREIGN')
            need(abs(started_at - recorded_start) <= 5, 'LAB_PG_PID_START_MISMATCH')
        except (OSError, ValueError, IndexError, StopIteration) as error:
            raise LabAdmissionRejected('LAB_PG_PID_UNVERIFIED') from error

    def _verify_postmaster(self):
        self._verify_owned()
        pidfile = self.data / 'postmaster.pid'
        need(pidfile.is_file() and not pidfile.is_symlink()
             and not (getattr(pidfile.lstat(), 'st_file_attributes', 0) & 0x400),
             'LAB_PG_PID_UNVERIFIED')
        try:
            lines = pidfile.read_text().splitlines()
            pid = int(lines[0])
            data_path = Path(lines[1]).resolve(strict=True)
            port = int(lines[3])
            recorded_start = int(lines[2])
            need(pid > 1 and data_path == self.data.resolve(strict=True)
                 and port == self.port, 'LAB_PG_PID_UNVERIFIED')
            self._os_process_identity(pid, recorded_start)
            # pid alone is unsafe: pid reuse can target an unrelated service.
            if self.started:
                need(pid == self._owned_pid, 'LAB_PG_PID_CHANGED')
            return pid
        except (OSError, ValueError, IndexError) as error:
            raise LabAdmissionRejected('LAB_PG_PID_UNVERIFIED') from error

    @staticmethod
    def _pid_is_live(pid):
        """Treat access denial as live; never infer a foreign PID is safe."""
        if os.name == 'nt':
            import ctypes
            from ctypes import wintypes
            kernel = ctypes.WinDLL('kernel32', use_last_error=True)
            kernel.OpenProcess.argtypes = (wintypes.DWORD, wintypes.BOOL, wintypes.DWORD)
            kernel.OpenProcess.restype = wintypes.HANDLE
            handle = kernel.OpenProcess(0x1000, False, pid)
            if handle:
                kernel.CloseHandle(handle)
                return True
            need(ctypes.get_last_error() in (87, 1168), 'LAB_PG_PID_ACCESS_DENIED')
            return False
        try:
            os.kill(pid, 0)
            return True
        except ProcessLookupError:
            return False
        except PermissionError:
            return True

    def _verify_stale_after_crash(self):
        """Only the exact stale file from *our* confirmed crash may be reused."""
        self._verify_owned()
        need(self._crashed and not self.started and self._owned_pid is not None,
             'LAB_PG_STALE_UNVERIFIED')
        pidfile = self.data / 'postmaster.pid'
        need(pidfile.is_file() and not pidfile.is_symlink()
             and not (getattr(pidfile.lstat(), 'st_file_attributes', 0) & 0x400),
             'LAB_PG_STALE_UNVERIFIED')
        info = pidfile.lstat()
        need((info.st_dev, info.st_ino) == self._owned_pidfile_inode, 'LAB_PG_PIDFILE_CHANGED')
        try:
            lines = pidfile.read_text().splitlines()
            pid, started, port = int(lines[0]), int(lines[2]), int(lines[3])
            data = Path(lines[1]).resolve(strict=True)
        except (IndexError, OSError, ValueError) as error:
            raise LabAdmissionRejected('LAB_PG_STALE_UNVERIFIED') from error
        need(pid == self._owned_pid and started == self._owned_start_time and
             port == self.port and data == self.data.resolve(strict=True),
             'LAB_PG_STALE_UNVERIFIED')
        need(not self._pid_is_live(pid), 'LAB_PG_STALE_PID_LIVE')

    def _env(self, role):
        # Child-scoped password; never the parent's PG* variables.
        env = {k: v for k, v in os.environ.items()
               if k.upper() in ('SYSTEMROOT', 'WINDIR', 'TEMP', 'TMP', 'PATH', 'LANG', 'LC_ALL', 'HOME')}
        env.update(PGPASSWORD=self.passwords[role], PGCONNECT_TIMEOUT='10')
        return env

    def _options(self):
        options = [f'-c listen_addresses=127.0.0.1', f'-c port={self.port}', '-c fsync=on',
                   '-c full_page_writes=on', '-c max_connections=40']
        if os.name == 'nt':
            options.append("-c unix_socket_directories=''")
        else:
            options.append(f"-c unix_socket_directories='{self.socket_dir}'")
        return ' '.join(options)

    def initialize(self):
        self._verify_owned()
        need(not self.data.exists(), 'LAB_PG_DATA_EXISTS')
        self.socket_dir.mkdir(mode=0o700)
        for role in ('lab_owner', 'lab_writer', 'lab_reader'):
            self.passwords[role] = secrets.token_hex(24)
        pwfile = self.root / 'pg-owner.pw'
        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, 'O_NOFOLLOW', 0)
        fd = os.open(pwfile, flags, 0o600)
        with os.fdopen(fd, 'w', encoding='ascii') as secret_file:
            secret_file.write(self.passwords['lab_owner'])
        if os.name != 'nt':
            need(pwfile.stat().st_mode & 0o077 == 0, 'LAB_PG_SECRET_PERMISSIONS')
        try:
            subprocess.run([str(self.tools['initdb']), '-D', str(self.data), '-U', 'lab_owner', '-E', 'UTF8',
                            '--auth=scram-sha-256', '--pwfile', str(pwfile), '--no-instructions', '--locale=C'],
                           check=True, capture_output=True, timeout=300, env=self._env('lab_owner'))
        finally:
            pwfile.unlink()
        # Loopback-only host-based access; nothing else is accepted.
        (self.data / 'pg_hba.conf').write_text(
            'host all all 127.0.0.1/32 scram-sha-256\n'
            + ('' if os.name == 'nt' else 'local all all scram-sha-256\n'))
        self.port = _free_port()
        need(self.port != 5432, 'LAB_PG_PORT_REJECTED')
        return self

    def start(self):
        self._verify_owned()
        need(self.port is not None and self.port != 5432, 'LAB_PG_PORT_REJECTED')
        # Refuse foreign/stale pid files; only a previously crashed owned
        # postmaster is eligible for WAL recovery via pg_ctl.
        if (self.data / 'postmaster.pid').exists():
            need(not self.started, 'LAB_PG_ALREADY_STARTED')
            self._verify_stale_after_crash()
        result = subprocess.run([str(self.tools['pg_ctl']), '-D', str(self.data), '-l', str(self.log),
                                 '-o', self._options(), '-w', '-t', '120', 'start'],
                                capture_output=True, timeout=180, env=self._env('lab_owner'))
        need(result.returncode == 0, 'LAB_PG_START_FAILED')
        pid = self._verify_postmaster()
        self._owned_pid = pid
        lines = (self.data / 'postmaster.pid').read_text().splitlines()
        self._owned_start_time = int(lines[2])
        info = (self.data / 'postmaster.pid').lstat()
        self._owned_pidfile_inode = (info.st_dev, info.st_ino)
        self.started = True
        self._crashed = False
        return self

    def sql(self, statement, *, role='lab_owner', database=None):
        result = subprocess.run([str(self.tools['psql']), '-X', '-q', '-A', '-t', '-v', 'ON_ERROR_STOP=1',
                                 '-h', '127.0.0.1', '-p', str(self.port), '-U', role,
                                 '-d', database or self.database, '-c', statement],
                                capture_output=True, text=True, timeout=120, env=self._env(role))
        if result.returncode != 0:
            lines = result.stderr.strip().splitlines() or ['?']
            error = next((line for line in lines if 'ERROR:' in line), lines[-1])
            raise LabAdmissionRejected('LAB_PG_SQL_FAILED:' + error[:200])
        return result.stdout.strip()

    def provision(self, schema_statements):
        """Apply vetted schema as owner; expose only explicit minimal table grants."""
        self.sql(f"CREATE DATABASE {self.database}", database='postgres')
        self.sql(f"CREATE ROLE lab_writer LOGIN PASSWORD '{self.passwords['lab_writer']}'")
        self.sql(f"CREATE ROLE lab_reader LOGIN PASSWORD '{self.passwords['lab_reader']}'")
        # Remove cluster-default PUBLIC access to the two initdb-created
        # maintenance databases.  This is an isolated LAB cluster only.
        self.sql("REVOKE CONNECT ON DATABASE postgres FROM PUBLIC", database='postgres')
        self.sql("REVOKE CONNECT ON DATABASE template1 FROM PUBLIC", database='postgres')
        self.sql("ALTER ROLE lab_reader SET default_transaction_read_only = on")
        self.sql(f"REVOKE CONNECT, TEMPORARY ON DATABASE {self.database} FROM PUBLIC")
        self.sql(f"GRANT CONNECT ON DATABASE {self.database} TO lab_writer, lab_reader")
        self.sql("REVOKE CREATE ON SCHEMA public FROM PUBLIC")
        self.sql("GRANT USAGE ON SCHEMA public TO lab_writer")
        self.sql("GRANT USAGE ON SCHEMA public TO lab_reader")
        # No default privileges: unrelated or future tables remain private.
        # DDL is owner-controlled. Writer may INSERT into selected tables,
        # never CREATE/ALTER/DROP protected schema objects.
        for statement in schema_statements:
            self.sql(statement, role='lab_owner')
        self.sql("GRANT INSERT ON TABLE provenance_minutes TO lab_writer")
        self.sql("GRANT SELECT ON TABLE provenance_minutes TO lab_reader")
        return self

    def enable_fenced_writer(self):
        """LAB-only: close direct INSERT and establish owner-mediated DB fencing.

        Native production admission is NOT available here. A holder of the
        same SQL role cannot set or claim a generation: only lab_owner can
        call the claim function, after independent Root/OS admission.
        """
        self._verify_owned()
        need(self.started, 'LAB_PG_NOT_STARTED')
        self._verify_postmaster()
        # Owner-only durable high-water state. Empty state is DENIED.
        for query in (
            """CREATE TABLE lab_writer_fence (
                resource text PRIMARY KEY CHECK (resource='grid-market-data-primary'),
                generation bigint NOT NULL CHECK (generation > 0),
                high_water bigint NOT NULL CHECK (high_water > 0),
                session_id uuid NOT NULL, instance_id uuid NOT NULL,
                node_incarnation_id uuid NOT NULL,
                source_sha256 text NOT NULL CHECK (source_sha256 ~ '^[0-9a-f]{64}
        """Owner-only, scoped PostgreSQL custody facts; not provider authenticity.

        This proves catalogue permissions and a configured immutability trigger
        for this isolated cluster. It does not upgrade exchange provenance,
        grant paper authority, or assert protection from the cluster owner.
        """
        self._verify_owned()
        need(self.started, 'LAB_PG_NOT_STARTED')
        self._verify_postmaster()
        # Distinguish plain catalogue grant from a genuinely enforced
        # trigger: inspect its table scope and row-level BEFORE UPDATE/DELETE.
        result = self.sql("""
            SELECT json_build_object(
              'witness_schema', 'lab-postgres-custody.v1',
              'scope', 'ISOLATED_LAB_ONLY',
              'database', current_database(),
              'table', 'public.provenance_minutes',
              'table_owner', pg_get_userbyid(c.relowner),
              'writer_can_insert', has_table_privilege('lab_writer', c.oid, 'INSERT'),
              'writer_can_select', has_table_privilege('lab_writer', c.oid, 'SELECT'),
              'writer_can_update', has_table_privilege('lab_writer', c.oid, 'UPDATE'),
              'writer_can_delete', has_table_privilege('lab_writer', c.oid, 'DELETE'),
              'writer_can_truncate', has_table_privilege('lab_writer', c.oid, 'TRUNCATE'),
              'reader_can_select', has_table_privilege('lab_reader', c.oid, 'SELECT'),
              'reader_can_insert', has_table_privilege('lab_reader', c.oid, 'INSERT'),
              'reader_can_update', has_table_privilege('lab_reader', c.oid, 'UPDATE'),
              'reader_can_delete', has_table_privilege('lab_reader', c.oid, 'DELETE'),
              'reader_can_truncate', has_table_privilege('lab_reader', c.oid, 'TRUNCATE'),
              'writer_can_temp', has_database_privilege('lab_writer', current_database(), 'TEMP'),
              'reader_can_temp', has_database_privilege('lab_reader', current_database(), 'TEMP'),
              'writer_can_schema_create',
                 has_schema_privilege('lab_writer', 'public', 'CREATE'),
              'reader_can_schema_create',
                 has_schema_privilege('lab_reader', 'public', 'CREATE'),
              'reader_role_readonly',
                 (SELECT rolconfig @> ARRAY['default_transaction_read_only=on']
                    FROM pg_roles WHERE rolname='lab_reader'),
              'immutable_trigger_count',
                 (SELECT count(*) FROM pg_trigger t
                   WHERE t.tgrelid = c.oid
                     AND NOT t.tgisinternal AND t.tgenabled = 'O'
                     AND (t.tgtype & 1) = 1
                     AND (t.tgtype & 2) = 2
                     AND (t.tgtype & 16) = 16
                     AND (t.tgtype & 8) = 8
                     AND t.tgfoid = 'reject_provenance_mutation()'::regprocedure)
            )
            FROM pg_class c
            WHERE c.oid='public.provenance_minutes'::regclass
        """)
        import json
        try:
            witness = json.loads(result)
        except (TypeError, ValueError) as error:
            raise LabAdmissionRejected('LAB_PG_CUSTODY_RECEIPT_INVALID') from error
        required = ('writer_can_insert', 'reader_can_select', 'reader_role_readonly')
        forbidden = ('writer_can_select', 'writer_can_update', 'writer_can_delete',
                     'writer_can_truncate', 'reader_can_insert',
                     'reader_can_update', 'reader_can_delete', 'reader_can_truncate',
                     'writer_can_temp', 'reader_can_temp',
                     'writer_can_schema_create', 'reader_can_schema_create')
        need(type(witness) is dict and
             witness.get('witness_schema') == 'lab-postgres-custody.v1'
             and witness.get('scope') == 'ISOLATED_LAB_ONLY'
             and witness.get('database') == self.database
             and witness.get('table') == 'public.provenance_minutes'
             and witness.get('table_owner') == 'lab_owner'
             and all(witness.get(k) is True for k in required)
             and all(witness.get(k) is False for k in forbidden)
             and witness.get('immutable_trigger_count') == 1,
             'LAB_PG_CUSTODY_NOT_VERIFIED')
        # A trigger/catlog receipt is not cryptographic attestation. A
        # privileged owner or server admin can still mutate storage.
        witness['storage_immutability'] = 'ROLE_AND_TRIGGER_GUARDED_LAB_ONLY'
        witness['source_authenticity'] = 'NOT_INDEPENDENTLY_ATTESTED'
        witness['exchange_completeness'] = 'NOT_ATTESTED'
        witness['execution_authority'] = False
        witness['trading_authorized'] = False
        return witness

    def dsn(self, role):
        need(role in ('lab_writer', 'lab_reader'), 'LAB_PG_ROLE_REJECTED')
        return f'postgresql://{role}:{self.passwords[role]}@127.0.0.1:{self.port}/{self.database}'

    # ------------------------------------------------------------------
    def postmaster_pid(self):
        return self._verify_postmaster()

    def crash(self):
        """Simulate a power-loss style abort of the postmaster (no shutdown checkpoint)."""
        need(self.started, 'LAB_PG_NOT_STARTED')
        pid = self.postmaster_pid()
        if os.name == 'nt':
            # Windows process HANDLE is stable even if another process later
            # reuses the numeric PID. Revalidate identity before termination.
            import ctypes
            from ctypes import wintypes
            kernel = ctypes.WinDLL('kernel32', use_last_error=True)
            kernel.OpenProcess.argtypes = (wintypes.DWORD, wintypes.BOOL, wintypes.DWORD)
            kernel.OpenProcess.restype = wintypes.HANDLE
            handle = kernel.OpenProcess(0x1001, False, pid)  # TERMINATE | QUERY_LIMITED_INFORMATION
            need(bool(handle), 'LAB_PG_PID_UNVERIFIED')
            try:
                self._verify_postmaster()
                need(bool(kernel.TerminateProcess(handle, 1)), 'LAB_PG_CRASH_FAILED')
            finally:
                kernel.CloseHandle(handle)
        else:
            need(hasattr(os, 'pidfd_open') and hasattr(signal, 'pidfd_send_signal'),
                 'LAB_PG_PIDFD_UNAVAILABLE')
            pidfd = os.pidfd_open(pid)
            try:
                self._verify_postmaster()
                signal.pidfd_send_signal(pidfd, signal.SIGKILL)
            finally:
                os.close(pidfd)
        deadline = time.monotonic() + 60
        while time.monotonic() < deadline:
            try:
                with socket.create_connection(('127.0.0.1', self.port), timeout=0.5):
                    pass
            except OSError:
                break
            time.sleep(0.2)
        # Do not authorize recovery until the original PID has disappeared.
        while time.monotonic() < deadline and self._pid_is_live(pid):
            time.sleep(0.2)
        need(not self._pid_is_live(pid), 'LAB_PG_CRASH_NOT_CONFIRMED')
        self.started = False
        self._crashed = True
        return pid

    def integrity(self, tables):
        """Row counts, uniqueness of primary keys and B-tree checks (amcheck when available)."""
        report = {}
        has_amcheck = self.sql("SELECT count(*) FROM pg_available_extensions WHERE name='amcheck'") == '1'
        if has_amcheck:
            self.sql('CREATE EXTENSION IF NOT EXISTS amcheck')
        for table in tables:
            need(IDENT.fullmatch(table) is not None, 'LAB_PG_NAME_REJECTED')
            report[table] = dict(rows=int(self.sql(f'SELECT count(*) FROM {table}')))
            if has_amcheck:
                indexes = self.sql(f"SELECT indexrelid::regclass FROM pg_index WHERE indrelid='{table}'::regclass")
                for index in filter(None, indexes.splitlines()):
                    self.sql(f"SELECT bt_index_check('{index}'::regclass, true)")
                report[table]['btree_checked'] = len(list(filter(None, indexes.splitlines())))
        report['amcheck'] = has_amcheck
        return report

    def stop(self):
        self._verify_owned()
        if not self.data.exists():
            return
        if (self.data / 'postmaster.pid').exists():
            if self._crashed:
                self._verify_stale_after_crash()
                self.started = False
                return
            pid = self._verify_postmaster()
            if os.name != 'nt':
                need(hasattr(os, 'pidfd_open') and hasattr(signal, 'pidfd_send_signal'),
                     'LAB_PG_PIDFD_UNAVAILABLE')
                # PostgreSQL postmaster SIGINT = fast shutdown.  Signal the
                # exact kernel process handle, never an unverified numeric PID.
                handle = os.pidfd_open(pid)
                try:
                    self._verify_postmaster()
                    signal.pidfd_send_signal(handle, signal.SIGINT)
                finally:
                    os.close(handle)
                deadline = time.monotonic() + 60
                while (self.data / 'postmaster.pid').exists() and time.monotonic() < deadline:
                    time.sleep(0.2)
            else:
                # Windows native fast-stop remains pg_ctl-managed, with an
                # independently verified postmaster identity before the call.
                subprocess.run([str(self.tools['pg_ctl']), '-D', str(self.data), '-m', 'fast', '-w', '-t', '60', 'stop'],
                               capture_output=True, timeout=120, env=self._env('lab_owner'))
        need(not (self.data / 'postmaster.pid').exists(), 'LAB_PG_STOP_FAILED')
        self.started = False
),
                schema_sha256 text NOT NULL CHECK (schema_sha256 ~ '^[0-9a-f]{64}
        """Owner-only, scoped PostgreSQL custody facts; not provider authenticity.

        This proves catalogue permissions and a configured immutability trigger
        for this isolated cluster. It does not upgrade exchange provenance,
        grant paper authority, or assert protection from the cluster owner.
        """
        self._verify_owned()
        need(self.started, 'LAB_PG_NOT_STARTED')
        self._verify_postmaster()
        # Distinguish plain catalogue grant from a genuinely enforced
        # trigger: inspect its table scope and row-level BEFORE UPDATE/DELETE.
        result = self.sql("""
            SELECT json_build_object(
              'witness_schema', 'lab-postgres-custody.v1',
              'scope', 'ISOLATED_LAB_ONLY',
              'database', current_database(),
              'table', 'public.provenance_minutes',
              'table_owner', pg_get_userbyid(c.relowner),
              'writer_can_insert', has_table_privilege('lab_writer', c.oid, 'INSERT'),
              'writer_can_select', has_table_privilege('lab_writer', c.oid, 'SELECT'),
              'writer_can_update', has_table_privilege('lab_writer', c.oid, 'UPDATE'),
              'writer_can_delete', has_table_privilege('lab_writer', c.oid, 'DELETE'),
              'writer_can_truncate', has_table_privilege('lab_writer', c.oid, 'TRUNCATE'),
              'reader_can_select', has_table_privilege('lab_reader', c.oid, 'SELECT'),
              'reader_can_insert', has_table_privilege('lab_reader', c.oid, 'INSERT'),
              'reader_can_update', has_table_privilege('lab_reader', c.oid, 'UPDATE'),
              'reader_can_delete', has_table_privilege('lab_reader', c.oid, 'DELETE'),
              'reader_can_truncate', has_table_privilege('lab_reader', c.oid, 'TRUNCATE'),
              'writer_can_temp', has_database_privilege('lab_writer', current_database(), 'TEMP'),
              'reader_can_temp', has_database_privilege('lab_reader', current_database(), 'TEMP'),
              'writer_can_schema_create',
                 has_schema_privilege('lab_writer', 'public', 'CREATE'),
              'reader_can_schema_create',
                 has_schema_privilege('lab_reader', 'public', 'CREATE'),
              'reader_role_readonly',
                 (SELECT rolconfig @> ARRAY['default_transaction_read_only=on']
                    FROM pg_roles WHERE rolname='lab_reader'),
              'immutable_trigger_count',
                 (SELECT count(*) FROM pg_trigger t
                   WHERE t.tgrelid = c.oid
                     AND NOT t.tgisinternal AND t.tgenabled = 'O'
                     AND (t.tgtype & 1) = 1
                     AND (t.tgtype & 2) = 2
                     AND (t.tgtype & 16) = 16
                     AND (t.tgtype & 8) = 8
                     AND t.tgfoid = 'reject_provenance_mutation()'::regprocedure)
            )
            FROM pg_class c
            WHERE c.oid='public.provenance_minutes'::regclass
        """)
        import json
        try:
            witness = json.loads(result)
        except (TypeError, ValueError) as error:
            raise LabAdmissionRejected('LAB_PG_CUSTODY_RECEIPT_INVALID') from error
        required = ('writer_can_insert', 'reader_can_select', 'reader_role_readonly')
        forbidden = ('writer_can_select', 'writer_can_update', 'writer_can_delete',
                     'writer_can_truncate', 'reader_can_insert',
                     'reader_can_update', 'reader_can_delete', 'reader_can_truncate',
                     'writer_can_temp', 'reader_can_temp',
                     'writer_can_schema_create', 'reader_can_schema_create')
        need(type(witness) is dict and
             witness.get('witness_schema') == 'lab-postgres-custody.v1'
             and witness.get('scope') == 'ISOLATED_LAB_ONLY'
             and witness.get('database') == self.database
             and witness.get('table') == 'public.provenance_minutes'
             and witness.get('table_owner') == 'lab_owner'
             and all(witness.get(k) is True for k in required)
             and all(witness.get(k) is False for k in forbidden)
             and witness.get('immutable_trigger_count') == 1,
             'LAB_PG_CUSTODY_NOT_VERIFIED')
        # A trigger/catlog receipt is not cryptographic attestation. A
        # privileged owner or server admin can still mutate storage.
        witness['storage_immutability'] = 'ROLE_AND_TRIGGER_GUARDED_LAB_ONLY'
        witness['source_authenticity'] = 'NOT_INDEPENDENTLY_ATTESTED'
        witness['exchange_completeness'] = 'NOT_ATTESTED'
        witness['execution_authority'] = False
        witness['trading_authorized'] = False
        return witness

    def dsn(self, role):
        need(role in ('lab_writer', 'lab_reader'), 'LAB_PG_ROLE_REJECTED')
        return f'postgresql://{role}:{self.passwords[role]}@127.0.0.1:{self.port}/{self.database}'

    # ------------------------------------------------------------------
    def postmaster_pid(self):
        return self._verify_postmaster()

    def crash(self):
        """Simulate a power-loss style abort of the postmaster (no shutdown checkpoint)."""
        need(self.started, 'LAB_PG_NOT_STARTED')
        pid = self.postmaster_pid()
        if os.name == 'nt':
            # Windows process HANDLE is stable even if another process later
            # reuses the numeric PID. Revalidate identity before termination.
            import ctypes
            from ctypes import wintypes
            kernel = ctypes.WinDLL('kernel32', use_last_error=True)
            kernel.OpenProcess.argtypes = (wintypes.DWORD, wintypes.BOOL, wintypes.DWORD)
            kernel.OpenProcess.restype = wintypes.HANDLE
            handle = kernel.OpenProcess(0x1001, False, pid)  # TERMINATE | QUERY_LIMITED_INFORMATION
            need(bool(handle), 'LAB_PG_PID_UNVERIFIED')
            try:
                self._verify_postmaster()
                need(bool(kernel.TerminateProcess(handle, 1)), 'LAB_PG_CRASH_FAILED')
            finally:
                kernel.CloseHandle(handle)
        else:
            need(hasattr(os, 'pidfd_open') and hasattr(signal, 'pidfd_send_signal'),
                 'LAB_PG_PIDFD_UNAVAILABLE')
            pidfd = os.pidfd_open(pid)
            try:
                self._verify_postmaster()
                signal.pidfd_send_signal(pidfd, signal.SIGKILL)
            finally:
                os.close(pidfd)
        deadline = time.monotonic() + 60
        while time.monotonic() < deadline:
            try:
                with socket.create_connection(('127.0.0.1', self.port), timeout=0.5):
                    pass
            except OSError:
                break
            time.sleep(0.2)
        # Do not authorize recovery until the original PID has disappeared.
        while time.monotonic() < deadline and self._pid_is_live(pid):
            time.sleep(0.2)
        need(not self._pid_is_live(pid), 'LAB_PG_CRASH_NOT_CONFIRMED')
        self.started = False
        self._crashed = True
        return pid

    def integrity(self, tables):
        """Row counts, uniqueness of primary keys and B-tree checks (amcheck when available)."""
        report = {}
        has_amcheck = self.sql("SELECT count(*) FROM pg_available_extensions WHERE name='amcheck'") == '1'
        if has_amcheck:
            self.sql('CREATE EXTENSION IF NOT EXISTS amcheck')
        for table in tables:
            need(IDENT.fullmatch(table) is not None, 'LAB_PG_NAME_REJECTED')
            report[table] = dict(rows=int(self.sql(f'SELECT count(*) FROM {table}')))
            if has_amcheck:
                indexes = self.sql(f"SELECT indexrelid::regclass FROM pg_index WHERE indrelid='{table}'::regclass")
                for index in filter(None, indexes.splitlines()):
                    self.sql(f"SELECT bt_index_check('{index}'::regclass, true)")
                report[table]['btree_checked'] = len(list(filter(None, indexes.splitlines())))
        report['amcheck'] = has_amcheck
        return report

    def stop(self):
        self._verify_owned()
        if not self.data.exists():
            return
        if (self.data / 'postmaster.pid').exists():
            if self._crashed:
                self._verify_stale_after_crash()
                self.started = False
                return
            pid = self._verify_postmaster()
            if os.name != 'nt':
                need(hasattr(os, 'pidfd_open') and hasattr(signal, 'pidfd_send_signal'),
                     'LAB_PG_PIDFD_UNAVAILABLE')
                # PostgreSQL postmaster SIGINT = fast shutdown.  Signal the
                # exact kernel process handle, never an unverified numeric PID.
                handle = os.pidfd_open(pid)
                try:
                    self._verify_postmaster()
                    signal.pidfd_send_signal(handle, signal.SIGINT)
                finally:
                    os.close(handle)
                deadline = time.monotonic() + 60
                while (self.data / 'postmaster.pid').exists() and time.monotonic() < deadline:
                    time.sleep(0.2)
            else:
                # Windows native fast-stop remains pg_ctl-managed, with an
                # independently verified postmaster identity before the call.
                subprocess.run([str(self.tools['pg_ctl']), '-D', str(self.data), '-m', 'fast', '-w', '-t', '60', 'stop'],
                               capture_output=True, timeout=120, env=self._env('lab_owner'))
        need(not (self.data / 'postmaster.pid').exists(), 'LAB_PG_STOP_FAILED')
        self.started = False
),
                active boolean NOT NULL DEFAULT false)""",
            "REVOKE ALL ON lab_writer_fence FROM PUBLIC, lab_writer, lab_reader",
            # Fail closed: no shared writer role can insert into the base
            # provenance table, including old legacy clients and stale code.
            "REVOKE INSERT ON provenance_minutes FROM lab_writer",
            "REVOKE ALL ON FUNCTION reject_provenance_mutation() FROM PUBLIC",
        ):
            self.sql(query)
        self.sql("""CREATE FUNCTION lab_fenced_insert(
                p_generation bigint, p_token bigint, p_session uuid,
                p_instance uuid, p_node uuid, p_source text, p_schema text,
                p_fingerprint text, p_content_id text, p_symbol text,
                p_start_ms bigint, p_record jsonb)
            RETURNS void LANGUAGE plpgsql SECURITY DEFINER
            SET search_path = pg_catalog, public AS $
            DECLARE current_fence public.lab_writer_fence%ROWTYPE;
            BEGIN
                IF session_user <> 'lab_writer' OR p_generation IS NULL
                    OR p_token IS NULL OR p_session IS NULL OR p_instance IS NULL
                    OR p_node IS NULL OR p_source IS NULL OR p_schema IS NULL THEN
                    RAISE EXCEPTION 'LAB_FENCE_AUTHORITY_REQUIRED';
                END IF;
                -- Row lock serializes owner revocation/reclaim with writes.
                SELECT * INTO current_fence FROM public.lab_writer_fence
                    WHERE resource='grid-market-data-primary' FOR UPDATE;
                IF NOT FOUND OR current_fence.active IS NOT TRUE
                    OR current_fence.generation IS DISTINCT FROM p_generation
                    OR current_fence.high_water IS DISTINCT FROM p_token
                    OR current_fence.session_id IS DISTINCT FROM p_session
                    OR current_fence.instance_id IS DISTINCT FROM p_instance
                    OR current_fence.node_incarnation_id IS DISTINCT FROM p_node
                    OR current_fence.source_sha256 IS DISTINCT FROM p_source
                    OR current_fence.schema_sha256 IS DISTINCT FROM p_schema THEN
                    RAISE EXCEPTION 'LAB_FENCE_STALE_WRITER';
                END IF;
                INSERT INTO public.provenance_minutes(
                    fingerprint,content_id,symbol,start_ms,record)
                VALUES (p_fingerprint,p_content_id,p_symbol,p_start_ms,p_record);
            END $""")
        self.sql("REVOKE ALL ON FUNCTION lab_fenced_insert(bigint,bigint,uuid,uuid,uuid,text,text,text,text,text,bigint,jsonb) FROM PUBLIC")
        self.sql("GRANT EXECUTE ON FUNCTION lab_fenced_insert(bigint,bigint,uuid,uuid,uuid,text,text,text,text,text,bigint,jsonb) TO lab_writer")
        return self

    def fenced_owner_claim(self, *, generation, token, session_id, instance_id,
                           node_incarnation_id, source_sha256, schema_sha256,
                           previous_quiescence_verified=False):
        """Refuse all claims without private, independently verified handoff.

        The caller must be trusted Root orchestration, never an HTTP client or
        an untrusted Grid worker; this method is LAB-only, not production.
        """
        import uuid
        need(previous_quiescence_verified is True, 'LAB_FENCE_QUIESCENCE_REQUIRED')
        need(type(generation) is int and generation > 0 and
             type(token) is int and 0 < token < 2**63,
             'LAB_FENCE_GENERATION_INVALID')
        ids = (session_id, instance_id, node_incarnation_id)
        try:
            parsed = tuple(uuid.UUID(x) for x in ids)
            need(all(str(u) == x and u.version == 4 for u,x in zip(parsed,ids)),
                 'LAB_FENCE_IDENTITY_INVALID')
        except (TypeError, ValueError, AttributeError) as e:
            raise LabAdmissionRejected('LAB_FENCE_IDENTITY_INVALID') from e
        need(all(type(x) is str and re.fullmatch('[0-9a-f]{64}',x)
                 for x in (source_sha256, schema_sha256)),
             'LAB_FENCE_SHA_INVALID')
        # SQL single-statement CAS, held under row lock; only owner role can
        # update state. Caller-supplied quiescence is a LAB test assertion,
        # NOT verified native process evidence and not production authority.
        q = lambda x: "'" + x + "'"
        result = self.sql(f"""INSERT INTO lab_writer_fence(
            resource,generation,high_water,session_id,instance_id,
            node_incarnation_id,source_sha256,schema_sha256,active)
            VALUES('grid-market-data-primary',{generation},{token},
              {q(session_id)}::uuid,{q(instance_id)}::uuid,
              {q(node_incarnation_id)}::uuid,
              {q(source_sha256)},{q(schema_sha256)},true)
            ON CONFLICT(resource) DO UPDATE SET
                generation=EXCLUDED.generation,
                high_water=EXCLUDED.high_water,
                session_id=EXCLUDED.session_id,
                instance_id=EXCLUDED.instance_id,
                node_incarnation_id=EXCLUDED.node_incarnation_id,
                source_sha256=EXCLUDED.source_sha256,
                schema_sha256=EXCLUDED.schema_sha256,
                active=true
            WHERE lab_writer_fence.active=false
              AND EXCLUDED.high_water > lab_writer_fence.high_water
              AND EXCLUDED.generation > lab_writer_fence.generation
            RETURNING generation""")
        need(result == str(generation), 'LAB_FENCE_CLAIM_REJECTED')
        return True

    def fenced_owner_revoke(self):
        """Owner-only revocation; does not discard durable high-water."""
        return self.sql("""UPDATE lab_writer_fence SET active=false
             WHERE resource='grid-market-data-primary' RETURNING generation""")

    def provenance_storage_witness(self):
        """Owner-only, scoped PostgreSQL custody facts; not provider authenticity.

        This proves catalogue permissions and a configured immutability trigger
        for this isolated cluster. It does not upgrade exchange provenance,
        grant paper authority, or assert protection from the cluster owner.
        """
        self._verify_owned()
        need(self.started, 'LAB_PG_NOT_STARTED')
        self._verify_postmaster()
        # Distinguish plain catalogue grant from a genuinely enforced
        # trigger: inspect its table scope and row-level BEFORE UPDATE/DELETE.
        result = self.sql("""
            SELECT json_build_object(
              'witness_schema', 'lab-postgres-custody.v1',
              'scope', 'ISOLATED_LAB_ONLY',
              'database', current_database(),
              'table', 'public.provenance_minutes',
              'table_owner', pg_get_userbyid(c.relowner),
              'writer_can_insert', has_table_privilege('lab_writer', c.oid, 'INSERT'),
              'writer_can_select', has_table_privilege('lab_writer', c.oid, 'SELECT'),
              'writer_can_update', has_table_privilege('lab_writer', c.oid, 'UPDATE'),
              'writer_can_delete', has_table_privilege('lab_writer', c.oid, 'DELETE'),
              'writer_can_truncate', has_table_privilege('lab_writer', c.oid, 'TRUNCATE'),
              'reader_can_select', has_table_privilege('lab_reader', c.oid, 'SELECT'),
              'reader_can_insert', has_table_privilege('lab_reader', c.oid, 'INSERT'),
              'reader_can_update', has_table_privilege('lab_reader', c.oid, 'UPDATE'),
              'reader_can_delete', has_table_privilege('lab_reader', c.oid, 'DELETE'),
              'reader_can_truncate', has_table_privilege('lab_reader', c.oid, 'TRUNCATE'),
              'writer_can_temp', has_database_privilege('lab_writer', current_database(), 'TEMP'),
              'reader_can_temp', has_database_privilege('lab_reader', current_database(), 'TEMP'),
              'writer_can_schema_create',
                 has_schema_privilege('lab_writer', 'public', 'CREATE'),
              'reader_can_schema_create',
                 has_schema_privilege('lab_reader', 'public', 'CREATE'),
              'reader_role_readonly',
                 (SELECT rolconfig @> ARRAY['default_transaction_read_only=on']
                    FROM pg_roles WHERE rolname='lab_reader'),
              'immutable_trigger_count',
                 (SELECT count(*) FROM pg_trigger t
                   WHERE t.tgrelid = c.oid
                     AND NOT t.tgisinternal AND t.tgenabled = 'O'
                     AND (t.tgtype & 1) = 1
                     AND (t.tgtype & 2) = 2
                     AND (t.tgtype & 16) = 16
                     AND (t.tgtype & 8) = 8
                     AND t.tgfoid = 'reject_provenance_mutation()'::regprocedure)
            )
            FROM pg_class c
            WHERE c.oid='public.provenance_minutes'::regclass
        """)
        import json
        try:
            witness = json.loads(result)
        except (TypeError, ValueError) as error:
            raise LabAdmissionRejected('LAB_PG_CUSTODY_RECEIPT_INVALID') from error
        required = ('writer_can_insert', 'reader_can_select', 'reader_role_readonly')
        forbidden = ('writer_can_select', 'writer_can_update', 'writer_can_delete',
                     'writer_can_truncate', 'reader_can_insert',
                     'reader_can_update', 'reader_can_delete', 'reader_can_truncate',
                     'writer_can_temp', 'reader_can_temp',
                     'writer_can_schema_create', 'reader_can_schema_create')
        need(type(witness) is dict and
             witness.get('witness_schema') == 'lab-postgres-custody.v1'
             and witness.get('scope') == 'ISOLATED_LAB_ONLY'
             and witness.get('database') == self.database
             and witness.get('table') == 'public.provenance_minutes'
             and witness.get('table_owner') == 'lab_owner'
             and all(witness.get(k) is True for k in required)
             and all(witness.get(k) is False for k in forbidden)
             and witness.get('immutable_trigger_count') == 1,
             'LAB_PG_CUSTODY_NOT_VERIFIED')
        # A trigger/catlog receipt is not cryptographic attestation. A
        # privileged owner or server admin can still mutate storage.
        witness['storage_immutability'] = 'ROLE_AND_TRIGGER_GUARDED_LAB_ONLY'
        witness['source_authenticity'] = 'NOT_INDEPENDENTLY_ATTESTED'
        witness['exchange_completeness'] = 'NOT_ATTESTED'
        witness['execution_authority'] = False
        witness['trading_authorized'] = False
        return witness

    def dsn(self, role):
        need(role in ('lab_writer', 'lab_reader'), 'LAB_PG_ROLE_REJECTED')
        return f'postgresql://{role}:{self.passwords[role]}@127.0.0.1:{self.port}/{self.database}'

    # ------------------------------------------------------------------
    def postmaster_pid(self):
        return self._verify_postmaster()

    def crash(self):
        """Simulate a power-loss style abort of the postmaster (no shutdown checkpoint)."""
        need(self.started, 'LAB_PG_NOT_STARTED')
        pid = self.postmaster_pid()
        if os.name == 'nt':
            # Windows process HANDLE is stable even if another process later
            # reuses the numeric PID. Revalidate identity before termination.
            import ctypes
            from ctypes import wintypes
            kernel = ctypes.WinDLL('kernel32', use_last_error=True)
            kernel.OpenProcess.argtypes = (wintypes.DWORD, wintypes.BOOL, wintypes.DWORD)
            kernel.OpenProcess.restype = wintypes.HANDLE
            handle = kernel.OpenProcess(0x1001, False, pid)  # TERMINATE | QUERY_LIMITED_INFORMATION
            need(bool(handle), 'LAB_PG_PID_UNVERIFIED')
            try:
                self._verify_postmaster()
                need(bool(kernel.TerminateProcess(handle, 1)), 'LAB_PG_CRASH_FAILED')
            finally:
                kernel.CloseHandle(handle)
        else:
            need(hasattr(os, 'pidfd_open') and hasattr(signal, 'pidfd_send_signal'),
                 'LAB_PG_PIDFD_UNAVAILABLE')
            pidfd = os.pidfd_open(pid)
            try:
                self._verify_postmaster()
                signal.pidfd_send_signal(pidfd, signal.SIGKILL)
            finally:
                os.close(pidfd)
        deadline = time.monotonic() + 60
        while time.monotonic() < deadline:
            try:
                with socket.create_connection(('127.0.0.1', self.port), timeout=0.5):
                    pass
            except OSError:
                break
            time.sleep(0.2)
        # Do not authorize recovery until the original PID has disappeared.
        while time.monotonic() < deadline and self._pid_is_live(pid):
            time.sleep(0.2)
        need(not self._pid_is_live(pid), 'LAB_PG_CRASH_NOT_CONFIRMED')
        self.started = False
        self._crashed = True
        return pid

    def integrity(self, tables):
        """Row counts, uniqueness of primary keys and B-tree checks (amcheck when available)."""
        report = {}
        has_amcheck = self.sql("SELECT count(*) FROM pg_available_extensions WHERE name='amcheck'") == '1'
        if has_amcheck:
            self.sql('CREATE EXTENSION IF NOT EXISTS amcheck')
        for table in tables:
            need(IDENT.fullmatch(table) is not None, 'LAB_PG_NAME_REJECTED')
            report[table] = dict(rows=int(self.sql(f'SELECT count(*) FROM {table}')))
            if has_amcheck:
                indexes = self.sql(f"SELECT indexrelid::regclass FROM pg_index WHERE indrelid='{table}'::regclass")
                for index in filter(None, indexes.splitlines()):
                    self.sql(f"SELECT bt_index_check('{index}'::regclass, true)")
                report[table]['btree_checked'] = len(list(filter(None, indexes.splitlines())))
        report['amcheck'] = has_amcheck
        return report

    def stop(self):
        self._verify_owned()
        if not self.data.exists():
            return
        if (self.data / 'postmaster.pid').exists():
            if self._crashed:
                self._verify_stale_after_crash()
                self.started = False
                return
            pid = self._verify_postmaster()
            if os.name != 'nt':
                need(hasattr(os, 'pidfd_open') and hasattr(signal, 'pidfd_send_signal'),
                     'LAB_PG_PIDFD_UNAVAILABLE')
                # PostgreSQL postmaster SIGINT = fast shutdown.  Signal the
                # exact kernel process handle, never an unverified numeric PID.
                handle = os.pidfd_open(pid)
                try:
                    self._verify_postmaster()
                    signal.pidfd_send_signal(handle, signal.SIGINT)
                finally:
                    os.close(handle)
                deadline = time.monotonic() + 60
                while (self.data / 'postmaster.pid').exists() and time.monotonic() < deadline:
                    time.sleep(0.2)
            else:
                # Windows native fast-stop remains pg_ctl-managed, with an
                # independently verified postmaster identity before the call.
                subprocess.run([str(self.tools['pg_ctl']), '-D', str(self.data), '-m', 'fast', '-w', '-t', '60', 'stop'],
                               capture_output=True, timeout=120, env=self._env('lab_owner'))
        need(not (self.data / 'postmaster.pid').exists(), 'LAB_PG_STOP_FAILED')
        self.started = False
