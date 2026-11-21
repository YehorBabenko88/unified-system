"""Inert design arithmetic only. Samples are not valid/native-issued commands."""
import base64
import json
from pathlib import Path

def canonical(value):
    return json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=True,allow_nan=False).encode('ascii')

if __name__=='__main__':
    root=Path(__file__).resolve().parent
    sizes=json.loads((root/'measurements.json').read_bytes())
    request=json.loads((root/'MAXIMUM-FORMAT-NOT-SENDABLE.request.json').read_bytes())
    event=json.loads((root/'MAXIMUM-FORMAT-NOT-ISSUED.custody.json').read_bytes())
    history=json.loads((root/'PUBLIC-BODY-MAX-FORMAT-NOT-AUTHORIZED.json').read_bytes())
    assert len(base64.b64decode(request['original_base64'],validate=True))==16384
    assert len(request['original_base64'])==21848
    assert len(canonical(request))==sizes['proposed_request_json_max']==22055
    assert 8+len(canonical(request))==sizes['proposed_request_prefixed_max']==22063
    assert len(canonical(history))==841 and 841+8==849
    assert len(canonical(event))==sizes['proposed_custody_event_syntactic_bound']==22947
    wrapped=canonical(dict(sequence=64,state='OBSERVING',receipt=event,previous_hash='f'*64))
    assert len(wrapped)==sizes['current_journal_canonical_body_for_proposed_event']==23076
    assert len(wrapped)-len(canonical(event))==129
    assert 32768+160==32928 and 1024+160==1184
    assert 6+4096+32928==37030 and 6+4096+1184==5286
    assert 37030+5286+4106+2*4102==54626
    assert 16*(16384+512+512)==278528<=307200
    assert 64*(21848+512+1024)+1024==1497600<=1572864
    assert 64*(512*6+128)+1024==205824<=1572864
    print('PURE_FORMAT_ARITHMETIC_ONLY; no runtime/native validity or owner ACK')
