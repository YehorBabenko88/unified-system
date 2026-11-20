"""Exact-source owned Terminan process proof; never physical or six-module admission."""
import argparse
import hashlib
import http.client
import json
import os
from pathlib import Path
import shutil
import socket
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]


def isolated_host(execute):
    if execute is not True:
        raise ValueError('explicit isolated cloud execution flag required')
    if socket.gethostname().split('.')[0].upper() in ('ADMINIT', 'LS5', 'PC4'):
        raise ValueError('office execution prohibited')
    hosted = (os.environ.get('GITHUB_ACTIONS') == 'true'
              and os.environ.get('RUNNER_ENVIRONMENT') == 'github-hosted')
    if os.name == 'nt':
        if not hosted or os.environ.get('RUNNER_OS') != 'Windows' or not os.environ.get('RUNNER_TEMP'):
            raise ValueError('disposable hosted Windows runner required')
        return Path(os.environ['RUNNER_TEMP']).resolve(strict=True)
    if not sys.platform.startswith('linux'):
        raise ValueError('unsupported isolated execution host')
    if not (hosted and os.environ.get('RUNNER_OS') == 'Linux'
            or Path('/etc/codex/network-policy.json').is_file()):
        raise ValueError('managed cloud or disposable hosted Linux fixture required')
    return Path(os.environ['RUNNER_TEMP']).resolve(strict=True) if hosted else Path(tempfile.gettempdir()).resolve()



SOURCE_REASONS=frozenset(('BYTECODE_ORIGIN_OUTSIDE_ISOLATED_CACHE','CONFIG_INCLUDE_OR_FILTER',
    'EXTERNAL_GIT_DIRECTORY','EXTERNAL_OBJECTS_OR_ATTRIBUTES','EXTERNAL_PROMISOR_OBJECTS',
    'EXTERNAL_SOURCE_NAMESPACE','EXTERNAL_WORKTREE_CONFIG','EXTERNAL_WORKTREE_OR_ATTRIBUTES',
    'GIT_CHECK_FAILED','GIT_ENV_OVERRIDE','GIT_INPUT_LIMIT','GIT_PIN_PAIR_REQUIRED',
    'GIT_RESOURCE_LIMIT','GIT_RUNTIME_PIN','IMPORT_ORIGIN_MISSING','IMPORT_ORIGIN_OUTSIDE_TREE',
    'IMPORT_ORIGIN_UNTRACKED','INDEX_DIRTY','ISOLATED_CACHE_NOT_ACTIVE','ISOLATED_CACHE_REQUIRED',
    'LINKED_SOURCE_METADATA','LOCAL_CONFIG_INVALID','METADATA_LIMIT','NON_REGULAR_SOURCE',
    'OBJECT_BYTES','OBJECT_IDENTITY','PRECHECK_REQUIRED','REPLACE_REFS_FORBIDDEN',
    'SOURCE_CHANGED_DURING_RUN','SOURCE_PATH_ESCAPE','SOURCE_PIN_MISMATCH',
    'TRACKED_BYTES_MISMATCH','UNSAFE_FSMONITOR','UNTRACKED_SOURCE'))


def source_failure_reason(exc):
    if type(exc).__name__ != 'SourceQualificationError':return 'OTHER'
    prefix=str(exc).split(':',1)[0]
    return prefix if prefix in SOURCE_REASONS else 'OTHER'


def failure_annotation(report):
    """Public fixed enums only; never project exception messages or paths."""
    stages={'EXECUTION_SCOPE','SOURCE_PRECHECK','ROOT_SOURCE_PRECHECK','TERMINAN_SOURCE_PRECHECK','OWNED_START_AND_AUTHENTICATED_READINESS',
            'ACTUAL_RUNTIME_DISPLAY','UNAUTHENTICATED_HEALTH_DENIAL','OWNED_STOP',
            'SOURCE_POSTCHECK','PRIVATE_CLEANUP'}
    kinds={'AssertionError','ValueError','OSError','PermissionError','FileNotFoundError',
           'TimeoutError','RuntimeError','JSONDecodeError','ProcessLookupError','SourceQualificationError'}
    stage=report.get('failure_stage');kind=report.get('error_class')
    return ('::error::TERMINAN_RUNTIME phase='+ (stage if stage in stages else 'OTHER')
            +' exception='+(kind if kind in kinds else 'OTHER')
            +' reason='+(report.get('source_reason') if report.get('source_reason') in SOURCE_REASONS else 'OTHER'))


def main(argv=None):
    sys.path.insert(0,str(ROOT))
    from integration.four_owner.runtime_gate import main as qualify_gate
    return qualify_gate(argv,kind='managed-runtime')

if __name__=='__main__':raise SystemExit(main())
