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
import hashlib
import json
import stat
import re
import secrets
import signal
import socket
import subprocess
import time
import uuid
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
             and not self.root.is_symlink(), 'LAB_PG_ROOT_UNOWNED')
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

    # ------------------------------------------------------------------
    def _verify_owned(self):
        try:
            info = self.root.lstat()
            need(stat.S_ISDIR(info.st_mode) and not self.root.is_symlink()
                 and (info.st_dev, info.st_ino) == self._root_identity,
                 'LAB_PG_ROOT_CHANGED')
            need(not self._marker.is_symlink() and self._marker.read_text(encoding='ascii') == self._nonce,
                 'LAB_PG_OWNERSHIP_LOST')
            if os.name != 'nt':
                need(info.st_uid == os.getuid() and not (info.st_mode & 0o077), 'LAB_PG_ROOT_UNSAFE')
            if self.data.exists():
                data_info = self.data.lstat()
                need(stat.S_ISDIR(data_info.st_mode) and not self.data.is_symlink(), 'LAB_PG_DATA_FOREIGN')
                if os.name != 'nt':
                    need(data_info.st_uid == os.getuid(), 'LAB_PG_DATA_FOREIGN')
        except (OSError, ValueError) as error:
            raise LabAdmissionRejected('LAB_PG_OWNERSHIP_LOST') from error

    def _verify_postmaster(self):
        self._verify_owned()
        pidfile = self.data / 'postmaster.pid'
        need(pidfile.is_file() and not pidfile.is_symlink(), 'LAB_PG_PID_UNVERIFIED')
        try:
            lines = pidfile.read_text().splitlines()
            pid = int(lines[0])
            data_path = Path(lines[1]).resolve(strict=True)
            port = int(lines[3])
            need(pid > 1 and data_path == self.data.resolve(strict=True)
                 and port == self.port, 'LAB_PG_PID_UNVERIFIED')
            # pid alone is unsafe: pid reuse can target an unrelated service.
            if self._owned_pid is not None:
                need(pid == self._owned_pid, 'LAB_PG_PID_CHANGED')
            return pid
        except (OSError, ValueError, IndexError) as error:
            raise LabAdmissionRejected('LAB_PG_PID_UNVERIFIED') from error

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
        pwfile.write_text(self.passwords['lab_owner'])
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
            self._verify_postmaster()
            need(not self.started, 'LAB_PG_ALREADY_STARTED')
        result = subprocess.run([str(self.tools['pg_ctl']), '-D', str(self.data), '-l', str(self.log),
                                 '-o', self._options(), '-w', '-t', '120', 'start'],
                                capture_output=True, timeout=180, env=self._env('lab_owner'))
        need(result.returncode == 0, 'LAB_PG_START_FAILED')
        self.started = True
        self._owned_pid = self._verify_postmaster()
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
        """Create the LAB database, roles and the given schema (as lab_writer)."""
        self.sql(f"CREATE DATABASE {self.database}", database='postgres')
        self.sql(f"CREATE ROLE lab_writer LOGIN PASSWORD '{self.passwords['lab_writer']}'")
        self.sql(f"CREATE ROLE lab_reader LOGIN PASSWORD '{self.passwords['lab_reader']}'")
        self.sql("ALTER ROLE lab_reader SET default_transaction_read_only = on")
        self.sql(f"GRANT CONNECT ON DATABASE {self.database} TO lab_writer, lab_reader")
        self.sql("REVOKE CREATE ON SCHEMA public FROM PUBLIC")
        self.sql("GRANT USAGE ON SCHEMA public TO lab_writer")
        self.sql("GRANT USAGE ON SCHEMA public TO lab_reader")
        self.sql("ALTER DEFAULT PRIVILEGES FOR ROLE lab_writer IN SCHEMA public GRANT SELECT ON TABLES TO lab_reader")
        # DDL is owner-controlled. Writer may INSERT into selected tables,
        # never CREATE/ALTER/DROP protected schema objects.
        for statement in schema_statements:
            self.sql(statement, role='lab_owner')
        self.sql("GRANT INSERT, SELECT ON TABLE provenance_minutes TO lab_writer")
        self.sql("GRANT SELECT ON TABLE provenance_minutes TO lab_reader")
        return self

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
            subprocess.run([str(self.tools['pg_ctl']), 'kill', 'KILL', str(pid)], capture_output=True, timeout=30)
        else:
            os.kill(pid, signal.SIGKILL)
        deadline = time.monotonic() + 60
        while time.monotonic() < deadline:
            try:
                with socket.create_connection(('127.0.0.1', self.port), timeout=0.5):
                    pass
            except OSError:
                break
            time.sleep(0.2)
        # Backends exit once the postmaster is gone; give them a bounded moment.
        time.sleep(2)
        self.started = False
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
            self._verify_postmaster()
            subprocess.run([str(self.tools['pg_ctl']), '-D', str(self.data), '-m', 'fast', '-w', '-t', '60', 'stop'],
                           capture_output=True, timeout=120, env=self._env('lab_owner'))
        need(not (self.data / 'postmaster.pid').exists(), 'LAB_PG_STOP_FAILED')
        self.started = False
