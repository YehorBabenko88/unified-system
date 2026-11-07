"""Opt-in, bounded local measurements. No import/runtime automatic execution.

CPU score is not a millicore entitlement. Loopback is not LAN capacity; temporary
file fsync throughput is not a guarantee about Storage devices or replica budgets.
Only own temporary files and 127.0.0.1 ephemeral sockets are touched.
"""
import ctypes
import hashlib
import os
from pathlib import Path
import platform
import socket
import tempfile
import threading
import time
import uuid


def _bound(value, maximum):
    if type(value) is not int or not 0 < value <= maximum:
        raise ValueError('explicit bounded positive integer required')


def _rate(byte_count, elapsed):
    return dict(bytes=str(byte_count), elapsed_ns=str(elapsed),
                bytes_per_second_floor=str(byte_count * 1000000000 // max(1, elapsed)))


def _memory():
    if os.name != 'nt': return dict(status='UNAVAILABLE', source='WINDOWS_ONLY')
    class Memory(ctypes.Structure):
        _fields_ = [('length', ctypes.c_uint32), ('load', ctypes.c_uint32),
                    ('total_physical', ctypes.c_uint64), ('available_physical', ctypes.c_uint64),
                    ('total_page', ctypes.c_uint64), ('available_page', ctypes.c_uint64),
                    ('total_virtual', ctypes.c_uint64), ('available_virtual', ctypes.c_uint64),
                    ('available_extended', ctypes.c_uint64)]
    value = Memory(); value.length = ctypes.sizeof(value)
    if not ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(value)):
        raise OSError('GlobalMemoryStatusEx failed')
    return dict(status='MEASURED', source='GlobalMemoryStatusEx',
                total_physical_bytes=str(value.total_physical), available_physical_bytes=str(value.available_physical),
                memory_load_percent=str(value.load))


def _loopback(size):
    started = time.monotonic_ns(); deadline = time.monotonic() + 2
    errors, received = [], []
    def remaining():
        value = deadline - time.monotonic()
        if value <= 0: raise TimeoutError('loopback deadline')
        return value
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as listener:
        listener.bind(('127.0.0.1', 0)); listener.listen(1); listener.settimeout(remaining())
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sender:
            sender.settimeout(remaining()); sender.connect(listener.getsockname())
            connection, peer = listener.accept()
            with connection:
                if peer[0] != '127.0.0.1': raise OSError('non-loopback peer')
                def receive():
                    try:
                        total = 0
                        while total < size:
                            connection.settimeout(remaining())
                            chunk = connection.recv(min(65536, size - total))
                            if not chunk: raise OSError('incomplete loopback transfer')
                            total += len(chunk)
                        received.append(total)
                    except Exception as error: errors.append(error)
                reader = threading.Thread(target=receive, daemon=True); reader.start()
                try:
                    sender.settimeout(remaining()); sender.sendall(b'x' * size)
                    reader.join(timeout=remaining())
                    if reader.is_alive(): raise TimeoutError('loopback receive deadline')
                    if errors: raise errors[0]
                    if received != [size]: raise OSError('loopback byte mismatch')
                finally:
                    # Own socket closure also interrupts the bounded receiver.
                    if reader.is_alive(): connection.shutdown(socket.SHUT_RDWR)
    return _rate(size, time.monotonic_ns() - started)


def measure_local(*, allow_local_measurement=False, cpu_duration_ms=100,
                  scratch_bytes=1024 * 1024, loopback_bytes=65536):
    if allow_local_measurement is not True:
        raise ValueError('local benchmark requires explicit opt-in')
    _bound(cpu_duration_ms, 2000); _bound(scratch_bytes, 8 * 1024 * 1024); _bound(loopback_bytes, 1024 * 1024)
    block = b'x' * 1048576
    started = time.monotonic_ns(); deadline = started + cpu_duration_ms * 1000000; count = 0
    while time.monotonic_ns() < deadline:
        hashlib.sha256(block).digest(); count += len(block)
    cpu = _rate(count, time.monotonic_ns() - started)
    # TemporaryDirectory chooses a new private path; no caller-provided path or
    # existing product data can be used or removed by this measurement.
    with tempfile.TemporaryDirectory(prefix='agent5-benchmark-') as directory:
        started = time.monotonic_ns()
        with (Path(directory) / 'scratch.bin').open('xb') as stream:
            remaining = scratch_bytes
            while remaining:
                chunk = block[:min(remaining, len(block))]
                stream.write(chunk); remaining -= len(chunk)
            stream.flush(); os.fsync(stream.fileno())
        disk = _rate(scratch_bytes, time.monotonic_ns() - started)
    network = _loopback(loopback_bytes)
    return dict(schema='unified.scheduler.local-benchmark.v1', run_id=str(uuid.uuid4()),
                provenance=dict(scope='LOCAL_PROCESS_TEMPFILE_LOOPBACK_NOT_FLEET_CAPACITY',
                                platform=platform.system(), python=platform.python_version(), pid=str(os.getpid())),
                cpu=dict(profile='SHA256_1M_SINGLE_PROCESS_BYTES_PER_SECOND', **cpu),
                scratch=dict(profile='PRIVATE_TEMPFILE_WRITE_FLUSH_FSYNC', **disk),
                network=dict(profile='IPV4_LOOPBACK_EPHEMERAL_NOT_LAN', **network), memory=_memory())
