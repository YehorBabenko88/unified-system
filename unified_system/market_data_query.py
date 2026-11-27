"""Root-owned bounded object reads; canonical Data alone decodes query domains.

No source loader, financial kernel, provider client or publication path lives here.
Actual issuer/store checks stay in Root; pure Data context is never authority.
"""
from market_data import gateway_query as domain
from .storage.object_store import ObjectStore
from .storage.manifest import decode_manifest

def read_market_data(request_bytes,*,owner_read_capability,expected_identity_authority,pinned_owned_store):
    prepared=domain.prepare_query(request_bytes)
    if owner_read_capability is None or expected_identity_authority is None:return prepared.not_executed()
    try:from .gateway_identity import DisposableIdentityAuthority,GatewayReadCapability
    except ImportError:return prepared.not_executed()
    if (type(expected_identity_authority) is not DisposableIdentityAuthority
            or type(owner_read_capability) is not GatewayReadCapability):
        return prepared.not_executed()
    request=prepared.as_dict()
    binding={'schema':'unified.gateway.read-binding.v1-review2',
        'dataset_id':request['dataset_id'],'dataset_revision':request['dataset_revision'],
        'manifest_sha256':request['knowledge_cut']['manifest_sha256'],
        'schema_sha256':request['data_schema_sha256'],
        'consumer_id':request['consumer_context']['consumer_id'],'view_id':request['consumer_context']['view_id']}
    def current():
        result=DisposableIdentityAuthority.require_issued_read(expected_identity_authority,owner_read_capability,
            tool_name='unified.query_market_data',request_bytes=request_bytes,binding=binding,owned_store=pinned_owned_store)
        if result is not None:raise domain.QueryFormatError('unsupported current-check result')
    remaining=1048576
    def read(key,limit):
        nonlocal remaining
        if remaining<=0:raise domain.QueryFormatError('query input byte bound')
        current()
        if type(pinned_owned_store) is not ObjectStore:raise domain.QueryFormatError('exact owned store required')
        raw=pinned_owned_store.read(key,max_bytes=min(limit,remaining))
        if type(raw) is not bytes or not 0<len(raw)<=min(limit,remaining):raise domain.QueryFormatError('bounded object bytes required')
        remaining-=len(raw)
        return raw
    manifest_raw=read(binding['manifest_sha256'],16384)
    claim=decode_manifest(manifest_raw);root=claim.as_dict();lineage=root['lineage']
    if (claim.sha256!=binding['manifest_sha256'] or root['manifest_revision']!=request['knowledge_cut']['manifest_revision']
            or root['data_schema_sha256']!=domain.DATA_SCHEMA_SHA256 or lineage['dataset_id']!=request['dataset_id']
            or lineage['instrument_id']!=request['instrument_id'] or lineage['data_kind']!='normalized'
            or lineage['source_id']!='synthetic.gateway.ohlcv.1m.v1'):
        raise domain.QueryFormatError('query manifest identity/revision binding')
    context={key:root[key] for key in ('manifest_revision','data_schema_sha256','segments_root_sha256','coverage_root_sha256','dependencies_root_sha256')}
    context.update(manifest_sha256=claim.sha256,dataset_id=lineage['dataset_id'],instrument_id=dict(lineage['instrument_id']),
        lineage_sha256=claim.lineage_sha256,source_class='SYNTHETIC')
    descriptor=context['data_schema_sha256'];index=context['segments_root_sha256']
    objects={descriptor:read(descriptor,4096),index:read(index,16384)}
    reference=domain.decode_query_segment_index(objects[index],context=context)
    objects[reference.sha256]=read(reference.sha256,524288)
    for key,limit in ((context['coverage_root_sha256'],524288),(context['dependencies_root_sha256'],16384)):
        objects[key]=read(key,limit)
    result=domain.project_query(prepared,context=context,manifest_bytes=manifest_raw,objects_by_sha256=objects)
    current() # Seventh check: no disclosure after capability expiry/revocation.
    return result
