"""Root discovery registration for the exact current-source binding controls."""
from tests.collector.test_qualification_current_sources import load_tests
from pathlib import Path as _Path

if load_tests.__code__.co_filename != str(_Path(__file__).parent/'collector/test_qualification_current_sources.py'):
    raise RuntimeError('CURRENT_SOURCE_TEST_MODULE_REQUIRED')