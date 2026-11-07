"""Pinned Review4 C3 codec. Encoding/schema validity does not establish authority."""
import hashlib
import json
from pathlib import Path
import jsonschema

ROOT=Path(__file__).resolve().parents[2]/'release/contracts/control-mux-closed-review4'
PINS={
 'control-mux-closed.schema.json':'335cda8e5d451fd9ab90586b6f6a4d6fbaf5f52eabb5a11762d9100ed92fefdf',
 'codec-bounds.json':'be9a0eb518ab14683cbb8e002e18f05e03d948b8c5d1537d635736bde8789203',
 'operation-result-matrix.json':'104039ed4383ad9bd34c25aaa5e73cf7bc1606f7d789a82a1962ebe40e65d6cd'}
def _pinned(name):
    raw=(ROOT/name).read_bytes()
    if hashlib.sha256(raw).hexdigest()!=PINS[name]:raise RuntimeError('CONTRACT_PIN_MISMATCH')
    return json.loads(raw)
schema=_pinned('control-mux-closed.schema.json')
bounds=_pinned('codec-bounds.json')
matrix=_pinned('operation-result-matrix.json')
PROFILE_SHA=PINS['control-mux-closed.schema.json']
jsonschema.Draft202012Validator.check_schema(schema)

def encode(value):
    nodes=0;size=0;chunks=[]
    def count():
        nonlocal nodes
        nodes+=1
        if nodes>int(bounds['max_nodes']):raise ValueError('NODE_CAP')
    def emit(text):
        nonlocal size
        raw=text.encode('ascii');size+=len(raw)
        if size>int(bounds['max_raw_ascii_bytes']):raise ValueError('BYTE_CAP')
        chunks.append(raw)
    def write(x,parent_depth=0):
        count()
        if x is None:emit('null');return
        if type(x) is bool:emit('true' if x else 'false');return
        if type(x) is str:
            if len(x)>int(bounds['max_value_ascii_characters']) or any(not 32<=ord(c)<=126 for c in x):raise ValueError('STRING_CAP')
            emit(json.dumps(x,ensure_ascii=True));return
        if type(x) not in (dict,list):raise ValueError('UNSUPPORTED_OR_NUMERIC')
        depth=parent_depth+1
        if depth>int(bounds['max_container_depth']):raise ValueError('DEPTH_CAP')
        if type(x) is list:
            if len(x)>int(bounds['max_array_entries']):raise ValueError('ARRAY_CAP')
            emit('[')
            for i,v in enumerate(x):
                if i:emit(',')
                write(v,depth)
            emit(']');return
        if len(x)>int(bounds['max_object_members']):raise ValueError('MEMBER_CAP')
        for key in x:
            if type(key) is not str or not int(bounds['min_key_ascii_bytes'])<=len(key)<=int(bounds['max_key_ascii_bytes']) or any(not 32<=ord(c)<=126 for c in key):raise ValueError('KEY_CAP')
        emit('{')
        for i,key in enumerate(sorted(x)):
            count()
            if i:emit(',')
            emit(json.dumps(key,ensure_ascii=True));emit(':');write(x[key],depth)
        emit('}')
    write(value)
    return b''.join(chunks)


def decode(raw):
    if type(raw) is not bytes or not 0<len(raw)<=int(bounds['max_raw_ascii_bytes']):raise ValueError('BYTE_CAP')
    # Bound depth BEFORE recursive JSON parsing; escaped strings are not delimiters.
    depth=0;quoted=False;escaped=False
    for b in raw:
        if quoted:
            if escaped:escaped=False
            elif b==92:escaped=True
            elif b==34:quoted=False
        elif b==34:quoted=True
        elif b in (91,123):
            depth+=1
            if depth>int(bounds['max_container_depth']):raise ValueError('DEPTH_CAP')
        elif b in (93,125):
            depth-=1
            if depth<0:raise ValueError('INVALID_JSON')
    def unique(pairs):
        out={}
        for k,v in pairs:
            if k in out:raise ValueError('DUPLICATE_KEY')
            out[k]=v
        return out
    def invalid(_):raise ValueError('NONFINITE')
    value=json.loads(raw.decode('ascii'),object_pairs_hook=unique,parse_constant=invalid,
                     parse_int=invalid,parse_float=invalid)
    if encode(value)!=raw:raise ValueError('NONCANONICAL')
    return value


def validate(definition, value):
    """Validate a named closed shape and all C3 limits; returns detached data."""
    detached=decode(encode(value))
    if type(definition) is not str or definition not in schema['$defs']:
        raise ValueError('UNKNOWN_DEFINITION')
    target=dict(schema)
    target.pop('oneOf',None)
    target['$ref']='#/$defs/'+definition
    errors=list(jsonschema.Draft202012Validator(target).iter_errors(detached))
    if errors:raise ValueError('SCHEMA_REJECTION')
    return detached
