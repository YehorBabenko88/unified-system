"""Closed test-only constructor failure observations; no authority or guard changes."""
import sys
from contextlib import contextmanager

_CODES=frozenset(('TARGET_CONTRACT_REJECTED','ISOLATED_RUNTIME_REQUIRED','RUNTIME_PIN_MISMATCH','ISOLATED_CACHE_REQUIRED','FRESH_ISOLATED_CACHE_REQUIRED','PRIVATE_CACHE_REQUIRED','CACHE_SOURCE_OVERLAP','UNQUALIFIED_IMPORT_HOOK'))
_TYPES=((ValueError,'VALUE_ERROR'),(RuntimeError,'RUNTIME_ERROR'),(OSError,'OS_ERROR'),(FileNotFoundError,'FILE_NOT_FOUND'),(PermissionError,'PERMISSION_ERROR'),(AssertionError,'ASSERTION_ERROR'))

@contextmanager
def observe_constructor(stand_type,journal_type,rejected_type):
    """Observe original calls once; preserve and re-raise their original exception."""
    codes={stand_type.__init__.__code__:'CONSTRUCTOR',stand_type._runtime_custody.__code__:'RUNTIME_CUSTODY',stand_type._records.__code__:'RECORDS',journal_type.initialize.__code__:'JOURNAL_INITIALIZE',journal_type.read.__code__:'JOURNAL_READ'}
    events=[]
    previous=sys.gettrace()
    if previous is not None:raise RuntimeError('STAND_DIAGNOSTIC_TRACE_ALREADY_ACTIVE')
    def trace(frame,event,arg):
        stage=codes.get(frame.f_code)
        if stage is not None and event=='exception' and len(events)<16:
            kind,value,_=arg
            code='OTHER_ERROR'
            if kind is rejected_type:
                args=value.args
                code=args[0] if len(args)==1 and type(args[0]) is str and args[0] in _CODES else 'TARGET_REJECTED'
            else:code=next((label for expected,label in _TYPES if kind is expected),'OTHER_ERROR')
            events.append(stage+':'+code)
        return trace
    sys.settrace(trace)
    try:
        yield
    except rejected_type as error:
        error.add_note('STAND_DIAGNOSTIC='+','.join(events or ['NO_OBSERVED_STAGE']))
        raise
    finally:
        sys.settrace(previous)
