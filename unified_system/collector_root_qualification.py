"""Pure outer qualification DATA joins; no acquisition, attestation or grant."""
import copy
import hashlib
from . import collector_operational_review as codec
from . import lab_release as lab
from .collector_profile import decode_collector_profile

SCOPE = 'ORDINARY_SOFTWARE_FOR_C3_ADMISSION'
# Dependency documentation only: NEVER imported from another checkout/ambient path.
A5_CONSUMER_COMMIT = 'c573dde6900b64e3ae6b9678f030f03e26e64fd3'
A5_CONSUMER_SHA256 = 'f349f13d4c5dede717a3d3351fcaf0fdd866492245a39406725c2775622f98e5'


def _pin(value):
    codec.fields(value, 'sha256 bytes')
    codec.digest(value['sha256']); codec.integer(value['bytes'])


def _bytes_pin(raw):
    return dict(sha256=hashlib.sha256(raw).hexdigest(), bytes=len(raw))


def _storage(raw):
    from .storage.raw_capture import RawCaptureProfile
    from .storage.collector_context import CollectorContextProfile
    value = codec.decode(raw)
    codec.fields(value, 'raw_profile lifecycle_headroom_bytes max_lifecycle_records max_context_bytes')
    codec.fields(value['raw_profile'], 'max_observations max_payload_occurrence_bytes max_state_bytes sqlite_headroom_bytes inventory_file_limit')
    for number in value['raw_profile'].values(): codec.integer(number)
    for key in ('lifecycle_headroom_bytes','max_lifecycle_records','max_context_bytes'): codec.integer(value[key])
    CollectorContextProfile(raw_profile=RawCaptureProfile(**value['raw_profile']),
        **{key:value[key] for key in ('lifecycle_headroom_bytes','max_lifecycle_records','max_context_bytes')}).check()
    return value


def parse_root_qualification(release_raw, software_raw, *, authorization_raw, manifest_raw,
                             profile_raw, copied_runtime_inventory_raw, storage_profile_raw):
    """Return detached data, NOT qualified supporting evidence or execution authority.

    Nested measurement validity belongs to A5's separately pinned private consumer.
    Fixed-path rejection cannot establish physical externality under other names.
    This parser performs no file, HTTP, token, native, source or evidence acquisition.
    """
    try:
        for raw in (release_raw,software_raw,authorization_raw,manifest_raw,profile_raw,copied_runtime_inventory_raw,storage_profile_raw):
            codec.need(type(raw) is bytes)
        release = codec.decode(release_raw); software = codec.decode(software_raw)
        codec.fields(release, 'schema scope qualification_id source capsule profile_sha256 copied_runtime_inventory primary_evidence artifact_inventory execution_authority')
        codec.fields(software, 'schema scope qualification_id release test_cohort source_effects_review measurement_evidence collector_max_envelope execution_authority')
        codec.need(release['schema']=='unified.collector.root-release-qualification.v2' and software['schema']=='unified.collector.root-software-qualification.v2')
        for record in (release,software):
            codec.need(record['scope']==SCOPE and record['execution_authority'] is False)
            codec.identifier(record['qualification_id'])
        codec.need(release['qualification_id']==software['qualification_id'])
        for key in ('copied_runtime_inventory','primary_evidence','artifact_inventory'): _pin(release[key])
        for key in ('release','test_cohort','source_effects_review','measurement_evidence'): _pin(software[key])
        codec.need(software['release']==_bytes_pin(release_raw))
        auth = codec.parse_authorization(authorization_raw)
        codec.need(type(manifest_raw) is bytes)
        manifest = lab.parse_manifest(manifest_raw,auth['capsule']['manifest_sha256'])
        codec.need(manifest['schema']==lab.COLLECTOR_SCHEMA and len(manifest_raw)==auth['capsule']['manifest_bytes'])
        fixed = {'qualification/release.json','qualification/software.json'}
        codec.need(not any(name.casefold() in fixed for name in manifest['files']))
        source = release['source']
        codec.fields(source, 'head tree source_manifest_sha256 sources_sha256 overlays_sha256 runtime_sha256 dependencies_sha256 directories_sha256')
        codec.digest(source['head'],40); codec.digest(source['tree'],40)
        for key in source:
            if key.endswith('_sha256'): codec.digest(source[key])
        codec.need(all(source[key]==auth['source'][key] for key in auth['source']))
        codec.need(source['source_manifest_sha256']==manifest['files'][manifest['source_manifest']]['sha256'])
        for key in ('sources','overlays','runtime','dependencies','directories'):
            codec.need(source[key+'_sha256']==_bytes_pin(lab.canonical(manifest[key]))['sha256'])
        capsule = release['capsule']; codec.fields(capsule,'manifest archive')
        _pin(capsule['manifest']); _pin(capsule['archive'])
        codec.need(capsule['manifest']==_bytes_pin(manifest_raw))
        archive = auth['capsule']['archive']
        if archive['kind']=='ARCHIVE':
            codec.need(capsule['archive']=={key:archive[key] for key in ('sha256','bytes')})
        # UNPACKED_MANIFEST_ONLY does not attest the archive, which remains DATA.
        profile = decode_collector_profile(profile_raw,manifest_sha256=source['source_manifest_sha256'])
        codec.need(profile.encoded==profile_raw)
        codec.digest(release['profile_sha256'])
        codec.need(release['profile_sha256']==profile.sha256 and manifest['files'][manifest['collector_profile']]==_bytes_pin(profile_raw))
        codec.need(all(profile.document['limits'][key]==auth['bounds'][key] for key in profile.document['limits']))
        raw = copied_runtime_inventory_raw
        codec.need(type(raw) is bytes and 0<len(raw)<=lab.LIMIT)
        inventory = lab._canonical_document(raw)
        codec.need(type(inventory) is dict and bool(inventory))
        for path,pin in inventory.items():
            lab.relative(path); codec.fields(pin,'sha256 bytes'); codec.digest(pin['sha256']); codec.integer(pin['bytes'],0,lab.FILE_LIMIT)
        codec.need(inventory=={path:pin for path,pin in manifest['files'].items() if path.startswith('runtime/python/')})
        codec.need(release['copied_runtime_inventory']==_bytes_pin(raw))
        storage = _storage(storage_profile_raw)
        envelope = software['collector_max_envelope']
        codec.need(type(envelope) is dict and type(envelope.get('workload')) is dict)
        codec.need(envelope['workload'].get('storage_profile')==storage)
        # Validate exact numeric types of the nested profile independently.
        _storage(codec.encode(envelope['workload']['storage_profile']))
        return copy.deepcopy(dict(release=release,software=software,
            collector_max_envelope_raw=codec.encode(envelope),execution_authority=False,
            supporting_facts='NOT_ATTESTED',
            measured_envelope_validation='REQUIRED_BY_A5_PRIVATE_CONSUMER'))
    except Exception:
        raise ValueError('COLLECTOR_ROOT_QUALIFICATION_REJECTED') from None
