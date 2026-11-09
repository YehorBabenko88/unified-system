"""Read-only clock metadata/counter DATA, never physical-age qualification."""
from dataclasses import dataclass
import hashlib
import json
import math
from pathlib import Path
import re
import struct
import sys
import time
import uuid

_INCARNATION=str(uuid.uuid4())

def _canonical(value):
    return json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False).encode('ascii')

def observe_clock_source_v1():
    executable=Path(sys.executable).resolve()
    runtime=dict(implementation=sys.implementation.name,python_version=sys.version,
        cache_tag=sys.implementation.cache_tag,pointer_bits=struct.calcsize('P')*8,
        executable_path_declared=str(executable),executable_sha256_observed=hashlib.sha256(executable.read_bytes()).hexdigest(),
        helper_source_sha256_observed=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        binding_status='OBSERVED_FILES_NOT_LOADED_IMAGE_CUSTODY')
    clocks={}
    for name in ('monotonic','perf_counter'):
        info=time.get_clock_info(name)
        if not math.isfinite(info.resolution) or info.resolution<=0:raise ValueError('CLOCK_RESOLUTION_UNAVAILABLE')
        clocks[name]=dict(implementation=info.implementation,monotonic=info.monotonic,
            adjustable=info.adjustable,resolution_seconds_api_repr=repr(info.resolution))
    binding=hashlib.sha256(_canonical(dict(runtime=runtime,clocks=clocks))).hexdigest()
    return dict(schema='a5.local-clock-source-observation.v1',runtime=runtime,clocks=clocks,
        runtime_source_binding_sha256=binding,observation_incarnation_id=_INCARNATION,
        quantization_uncertainty_ns=None,physical_elapsed_upper_bound_ns=None,
        measurement_age_upper_bound_ns=None,operational_max_age_ns=None,
        admission_supported=False,resources_reserved=False,admitted_fields=[])

@dataclass(frozen=True)
class CounterSpanV1:
    state: str
    reason: str
    counter_delta_ns: int | None=None
    physical_elapsed_upper_bound_ns: int | None=None
    measurement_age_upper_bound_ns: int | None=None
    operational_max_age_ns: int | None=None
    admission_supported: bool=False
    resources_reserved: bool=False

def _valid_source(value):
    if type(value) is not dict or set(value)!={'runtime_source_binding_sha256','observation_incarnation_id','clock_name'}:return False
    digest=value['runtime_source_binding_sha256'];inc=value['observation_incarnation_id']
    return (type(digest) is str and re.fullmatch('[0-9a-f]{64}',digest) is not None
        and type(inc) is str and re.fullmatch('[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}',inc) is not None
        and type(value['clock_name']) is str and value['clock_name'] in ('monotonic','perf_counter'))

def counter_span_v1(start_ns,end_ns,*,start_source,end_source):
    """Untrusted source descriptions are checked, not authenticated or admitted."""
    if not _valid_source(start_source) or not _valid_source(end_source):
        return CounterSpanV1('UNSUPPORTED','CLOSED_LOCAL_CLOCK_SOURCE_REQUIRED')
    if start_source!=end_source:return CounterSpanV1('FOREIGN_CLOCK_SOURCE','RUNTIME_INCARNATION_OR_CLOCK_MISMATCH')
    if type(start_ns) is not int or type(end_ns) is not int or min(start_ns,end_ns)<0:
        return CounterSpanV1('UNSUPPORTED','NONNEGATIVE_INTEGER_COUNTER_REQUIRED')
    if end_ns<start_ns:return CounterSpanV1('CLOCK_UNCERTAIN','COUNTER_ROLLBACK')
    return CounterSpanV1('COUNTER_DELTA_ONLY_NOT_PHYSICAL_TIME','RESOLUTION_IS_NOT_A_PHYSICAL_ERROR_BOUND',end_ns-start_ns)

if __name__=='__main__':
    if sys.argv[1:]!=['--observe-only']:raise SystemExit('explicit --observe-only required')
    sys.stdout.buffer.write(_canonical(observe_clock_source_v1())+b'\n')
