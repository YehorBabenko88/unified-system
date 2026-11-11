"""Version2 discovery facade; exact original3 cases, no unbound exports."""
import hashlib
import os
from pathlib import Path
import stat

FACADE_SCHEMA = 'preparation.observer-admission.discovery-facade.v2'
_FIXTURE = 'tests/fixtures/preparation_observer_admission.py'
_FIXTURE_BYTES = 5616
_FIXTURE_SHA256 = '15c5ced54f3c569bd1d8fdc7a752a1e7147efae80c91853b2f1ba0cddc4c80a1'
_QUALIFIER = 'tools/ci/qualify_preparation_integrity.py'
_QUALIFIER_BYTES = 31264
_QUALIFIER_SHA256 = 'dd6fa2bb62bec980dd556b3b90f98045d293d61439c2ae84004e72533cfc8ac4'


def _ordinary_directory(path):
    info = path.lstat()
    if (not stat.S_ISDIR(info.st_mode) or path.is_symlink()
            or getattr(info, 'st_file_attributes', 0) & 1024
            or getattr(info, 'st_reparse_tag', 0)):
        raise RuntimeError('OBSERVER_FACADE_DIRECTORY_REJECTED')
    return info


def _directory_identity(info):
    return (info.st_dev, info.st_ino, info.st_mode,
            getattr(info, 'st_file_attributes', 0), getattr(info, 'st_reparse_tag', 0))


def _ordinary_file(path, size):
    info = path.lstat()
    if (not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or info.st_size != size
            or path.is_symlink() or getattr(info, 'st_file_attributes', 0) & 1024
            or getattr(info, 'st_reparse_tag', 0)):
        raise RuntimeError('OBSERVER_FACADE_FILE_REJECTED')
    return info


def _same_api(info):
    return (info.st_dev, info.st_ino, info.st_mode, info.st_nlink, info.st_size,
            info.st_mtime_ns, info.st_ctime_ns, getattr(info, 'st_file_attributes', 0),
            getattr(info, 'st_reparse_tag', 0))


def _cross_api(info):
    return (info.st_dev, info.st_ino, stat.S_IFMT(info.st_mode), info.st_nlink,
            info.st_size, info.st_mtime_ns)


def _read_source(root, relative, size, sha256):
    path = root / relative
    # Inspect root/ancestors first, before any descendant file byte read.
    directories = [(parent, _ordinary_directory(parent)) for parent in reversed(path.parents)]
    before = _ordinary_file(path, size)
    with path.open('rb') as stream:
        opened = os.fstat(stream.fileno())
        if _cross_api(opened) != _cross_api(before):
            raise RuntimeError('OBSERVER_FACADE_OPEN_CHANGED')
        raw = stream.read(size + 1)
        after = os.fstat(stream.fileno())
    final = _ordinary_file(path, size)
    if (len(raw) != size or _same_api(before) != _same_api(final)
            or _same_api(opened) != _same_api(after) or _cross_api(after) != _cross_api(final)
            or hashlib.sha256(raw).hexdigest() != sha256):
        raise RuntimeError('OBSERVER_FACADE_SOURCE_CHANGED')
    for parent, info in directories:
        if _directory_identity(info) != _directory_identity(_ordinary_directory(parent)):
            raise RuntimeError('OBSERVER_FACADE_PARENT_CHANGED')
    return raw


def load_tests(loader, standard_tests, pattern):
    if standard_tests.countTestCases() != 0:
        raise RuntimeError('OBSERVER_FACADE_UNEXPECTED_EXPORTED_CASES')
    facade = Path(__file__).absolute()
    root = facade.parents[1]
    if facade != root / 'tests/test_preparation_observer_admission.py':
        raise RuntimeError('OBSERVER_FACADE_PATH_REJECTED')
    fixture = _read_source(root, _FIXTURE, _FIXTURE_BYTES, _FIXTURE_SHA256)
    qualifier = _read_source(root, _QUALIFIER, _QUALIFIER_BYTES, _QUALIFIER_SHA256)
    namespace = dict(__name__='test_preparation_observer_admission', __file__=str(root / _FIXTURE))
    exec(compile(fixture, str(root / _FIXTURE), 'exec'), namespace)
    suite = namespace['make_suite'](qualifier, expected_source_sha256=_QUALIFIER_SHA256)
    expected = ['test_preparation_observer_admission.PreparationObserverAdmissionControls.' + name
                for name in ('test_actual_observer_controls_accepts_normal_twelve_successes',
                             'test_actual_observer_controls_rejects_expected_failure',
                             'test_actual_observer_controls_rejects_unexpected_success')]
    if [case.id() for case in suite] != expected:
        raise RuntimeError('OBSERVER_FACADE_EXACT3_REQUIRED')
    return suite
