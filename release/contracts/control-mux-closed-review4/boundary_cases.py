"""Bounded deterministic canonical fixtures; no endpoint/provider functionality."""
import hashlib
import json
from pathlib import Path


def materialize(vector):
    if 'raw' in vector:return vector['raw']
    recipe=vector['recipe'];kind=recipe['kind'];n=int(recipe['n'])
    if kind=='depth':
        assert 1<=n<=13
        return '{"k":'*n+'"x"'+'}'*n
    if kind=='array':
        assert 0<=n<=1001
        return '['+','.join(['"x"']*n)+']'
    if kind=='string':
        assert 0<=n<=16385
        return '{"x":"'+'a'*n+'"}'
    if kind=='key_length':
        assert 1<=n<=129
        return '{"'+'k'*n+'":"x"}'
    if kind=='members':
        assert 0<=n<=65
        value={'k'+str(i).zfill(2):'x' for i in range(n)}
    elif kind=='nodes':
        assert n in (1,2)
        value=[{'k'+str(i).zfill(2):'' for i in range(64)} for _ in range(254)]
        for i in range(n):value[0]['k'+str(i).zfill(2)]=['']
        # root1 +254*(object1+64keynodes+64values) +n =32767+n.
    elif kind=='bytes':
        assert n in (0,1)
        value=['a'*16384 for _ in range(127)]+['a'*(15999+n)]
        # 127*16384+15999 +256quotes+127commas+2brackets =2097152.
    else:raise ValueError('unknown bounded recipe')
    return json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=True)


if __name__=='__main__':
    root=Path(__file__).parent
    base=json.loads((root/'canonical-cross-language-vectors.json').read_bytes())
    rows=[v for v in base['vectors'] if 'recipe' not in v and v.get('id') not in ('A1_DEPTH12_CHANGE','A6_NODECOUNT_CHANGE')]
    # Include the original exact A1 frame alongside generic codec boundary cases.
    original=(root/'A1-DEPTH12-RAW.json').read_bytes().decode('ascii')
    rows.append(dict(id='A1_DEPTH12_CHANGE',raw=original,accept=True,
        sha256_ascii=hashlib.sha256(original.encode()).hexdigest()))
    node_frame=(root/'A6-NODECOUNT-RAW.json').read_bytes().decode('ascii')
    assert hashlib.sha256(node_frame.encode()).hexdigest()=='59aa160e69e0516eaaa673e67890ebea5f3bc8f2680bb9878ca920590b040cf6'
    rows.append(dict(id='A6_NODECOUNT_CHANGE',raw=node_frame,accept=False))
    specifications=[('depth','12',True),('depth','13',False),('array','1000',True),('array','1001',False),
        ('string','16384',True),('string','16385',False),('key_length','128',True),('key_length','129',False),
        ('members','64',True),('members','65',False),('nodes','1',True),('nodes','2',False),
        ('bytes','0',True),('bytes','1',False)]
    for kind,n,accept in specifications:
        v=dict(id=kind+'_'+n,recipe=dict(kind=kind,n=n),accept=accept)
        if accept:v['sha256_ascii']=hashlib.sha256(materialize(v).encode('ascii')).hexdigest()
        rows.append(v)
    def forbidden_primitive(x):
        if type(x) in (int,float):return True
        if type(x) is str:return any(not 32<=ord(c)<=126 for c in x)
        if type(x) is dict:return any(forbidden_primitive(k) or forbidden_primitive(v) for k,v in x.items())
        if type(x) is list:return any(forbidden_primitive(v) for v in x)
        return False
    for v in rows:
        raw=materialize(v)
        value=json.loads(raw)
        v['writer_accept']=v['accept'] if 'recipe' in v or v.get('id') in ('A1_DEPTH12_CHANGE','A6_NODECOUNT_CHANGE') else not forbidden_primitive(value)
        if v['writer_accept']:
            canonical=json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=True).encode()
            v['writer_sha256_ascii']=hashlib.sha256(canonical).hexdigest()
    out=dict(scope='COMMON_CODEC_CONTAINER_DEPTH_AND_COUNTER_BOUNDARIES_MODEL_ONLY',vectors=rows)
    (root/'canonical-cross-language-vectors.json').write_bytes((json.dumps(out,sort_keys=True,separators=(',',':'))+'\n').encode())
    print(json.dumps(dict(vectors=len(rows))))
