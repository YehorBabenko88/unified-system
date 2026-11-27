"""Pure format/cardinality arithmetic; no application imports/native execution."""
from pathlib import Path
import collections
import hashlib
import json
import sys

if __name__=='__main__':
    here=Path(__file__).resolve().parent
    a2=Path(sys.argv[1])
    source=a2/'HA-LOGICAL-CODEC-PLAN-REVIEW3-20261110'
    seal=(source/'SHA256.json').read_bytes()
    assert hashlib.sha256(seal).hexdigest()=='b4237bf61d6c862368bcdb27ba4dbd919ca1e43e4221a9053c82efd749fa63e7'
    files=json.loads(seal)['files'];measurement=json.loads((here/'measurements.json').read_bytes())
    for phase in ('queue','cancel'):
        name=phase+'.FORMAT-ONLY.native-plan.json';raw=(source/name).read_bytes()
        assert hashlib.sha256(raw).hexdigest()==files[name]['sha256']
        operations=json.loads(raw);keys=set();absent=set()
        for operation in operations:
            record=operation['KV'];keys.add(record['Key'])
            if record['Verb']=='check-not-exists':absent.add(record['Key'])
        m=measurement['phases'][phase]
        assert len(operations)==m['operations']
        assert len(keys)==m['total_unique_keys']
        assert len(absent)==m['expected_absent_rows']
        assert len(keys)-len(absent)==m['expected_present_rows']
        assert (len(keys)-len(absent))*16384+len(keys)*1024+4096==m['expected_shape_payload_allowance']
    assert 19*(16384+512+512)==330752
    assert 330752+4096==334848<=360448
    assert 334848+2*(32768+512)+4096==405504
    assert 360448+2*(32768+512)+4096==431104<=458752
    assert 37030+4106+4102==45238 and 5286+4102==9388
    assert 45238+9388==54626
    assert 2*(65536+32768+32928+2048+1024+4096+16384)+65536==375104<=524288
    print('PURE_SYNTHETIC_SELECTOR_AND_BYTE_ARITHMETIC_ONLY; no native validity/ABI/priority qualification')
