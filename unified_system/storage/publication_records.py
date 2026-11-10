"""Exact local original-intent custody, not a native wire or proof ABI.

Native publication/receipt/access schemas still require A2/A4/A5/A7 co-ACK.
These records intentionally cannot represent COMMITTED or grant any permission.
"""
from dataclasses import dataclass
import hashlib
import json

from .contracts import _UUID, require

MAX_ORIGINAL_BYTES = 16384


def publication_identifier(value):
    require(type(value) is str and _UUID.fullmatch(value) is not None,
            'INVALID_PUBLICATION_IDENTIFIER')
    return value


@dataclass(frozen=True)
class RetainedPublicationIntent:
    """Opaque candidate bytes, not an approved native intent/schema/authority."""
    publication_id: str
    raw_bytes: bytes

    def __post_init__(self):
        publication_identifier(self.publication_id)
        require(type(self.raw_bytes) is bytes and 0 < len(self.raw_bytes) <= MAX_ORIGINAL_BYTES,
                'INVALID_ORIGINAL_PUBLICATION_BYTES')

    @property
    def sha256(self):
        return hashlib.sha256(self.raw_bytes).hexdigest()

    @property
    def authority_verified(self):
        return False


@dataclass(frozen=True)
class PendingPublicationObservation:
    """Local journal observation; never an A2 result/receipt/projection handle."""
    publication_id: str
    original_sha256: str
    local_phase: str

    @property
    def native_outcome(self):
        return 'UNKNOWN'

    @property
    def publication_confirmed(self):
        return False

    @property
    def retry_authorized(self):
        return False

    @property
    def hold_release_authorized(self):
        return False


_BTC_V1_PINS = (
    (1126, 'c548e2ffcd542d5d741682303694b3c6d06507740f158a6e30089b2d5355f648'),
    (2122, '664d34f06721b3d62404ea2f05b6b929a59b9e3eeecc281a71d2ca927c802cda'),
    (2070, 'f4997d7d26211676cd8664e53d7999f8b71f203510f3b9a275b439c403e03940'),
)


def _meta_bytes(value):
    # Meta numerical JSON, deliberately distinct from the storage C3 codec.
    return json.dumps(value, sort_keys=True, separators=(',', ':'),
                      ensure_ascii=True, allow_nan=False).encode('ascii')


@dataclass(frozen=True)
class LocalFixedBtcV1Packet:
    """Fixed historical byte consistency only; never a native capability.

    Construction validates all three exact pins before any JSON decoding. No
    decoded mutable graph is retained/exposed. Hash matches authenticate neither
    the original source nor scientific correctness nor current reader rights.
    """
    request_bytes: bytes
    descriptor_bytes: bytes
    artifact_bytes: bytes

    def __post_init__(self):
        raws = (self.request_bytes, self.descriptor_bytes, self.artifact_bytes)
        for raw, (size, _) in zip(raws, _BTC_V1_PINS):
            require(type(raw) is bytes and len(raw) == size, 'FIXED_PACKET_SIZE_OR_TYPE')
        for raw, (_, sha) in zip(raws, _BTC_V1_PINS):
            require(hashlib.sha256(raw).hexdigest() == sha, 'FIXED_PACKET_HASH')
        # Fixed hashes above close the entire accepted profile: unknown fields,
        # duplicate keys, numerical aliases and reencodings cannot enter it.
        request, descriptor, artifact = map(json.loads, raws)
        payload = request['payload']
        provenance = descriptor['provenance']
        require(descriptor['request_raw_sha256'] == _BTC_V1_PINS[0][1])
        require(descriptor['artifact'] == {
            'byte_count': '2070', 'raw_sha256': _BTC_V1_PINS[2][1],
            'encoding': 'JSON_UTF8_CANONICAL_META_V1_NOT_C3',
            'schema': artifact['schema']})
        require(payload['dataset_id'] == artifact['dataset_id'] == provenance['dataset_id'])
        require(hashlib.sha256(_meta_bytes({'payload': payload,
                'decision_ms': request['decision_ms']})).hexdigest()
                == artifact['request_digest'] == provenance['meta_request_digest'])
        require(payload['units'] == artifact['units'] == provenance['input_units']
                == {'price': 'USDT/BTC', 'volume': 'BTC'})
        require(payload['rows'] == artifact['rows'] and payload['source'] == artifact['source'])
        require(request['experiment'] == descriptor['experiment'])
        for key, value in (
            ('calculated_at_ms', request['analysis_now_ms']),
            ('decision_ms', request['decision_ms']),
            ('snapshot_as_of_ms', payload['as_of_ms']),
            ('window_start_ms', payload['start_ms']), ('window_end_ms', payload['end_ms']),
            ('data_available_at_ms', payload['source']['retrieved_at_ms']),
        ):
            require(type(value) is int and type(artifact[key]) is int
                    and artifact[key] == value and descriptor['clocks'][key] == str(value))
        for obj in (descriptor, artifact):
            for key in ('execution_authority', 'trading_authorized', 'training_authorized'):
                require(obj[key] is False)
        require(artifact['h_b_eligible'] is False
                and artifact['coverage_status'] == 'DECLARED_COMPLETE_UNVERIFIED'
                and artifact['quality_status'] == 'UNKNOWN'
                and artifact['source_authenticity'] == 'NOT_EVALUATED'
                and provenance['dataset_revision'] == 'UNAVAILABLE_A4_BINDING_PENDING'
                and descriptor['production_runtime_admission'] == 'BLOCKED')
        require(descriptor['financial']['status'] == 'UNAVAILABLE_NUMERICAL_PROFILE_NONE'
                and descriptor['financial']['calculation_basis'] == 'NOT_CALCULATED')
        require(all(descriptor['financial'][key] is None for key in
                    ('currency', 'fees', 'gross_pnl', 'net_pnl', 'scale', 'signed_funding', 'slippage')))

    @property
    def dataset_id(self):
        return '58ddbf7b0e23f2aa613941bc84d063a1d384eafdf4200006e99d4ac2da633672'

    @property
    def meta_request_digest(self):
        return '11b8ddeb6149f544349be0e6f3aac2007a9add878248b81030bb5e6cc64ebd72'

    @property
    def payload_sha256(self):
        return hashlib.sha256(_meta_bytes(json.loads(self.request_bytes)['payload'])).hexdigest()

    classification = property(lambda self: 'LOCAL_UNATTESTED')
    committed_revision = property(lambda self: None)
    receipt = property(lambda self: None)
    authority_verified = property(lambda self: False)
    publication_confirmed = property(lambda self: False)
    current_read_authorized = property(lambda self: False)
    replica_verified = property(lambda self: False)
    scientific_correctness_verified = property(lambda self: False)


def decode_fixed_btc_v1(request_bytes, descriptor_bytes, artifact_bytes):
    """Accept only the reviewed c548/664d/f499 packet, with no IO or effects."""
    return LocalFixedBtcV1Packet(request_bytes, descriptor_bytes, artifact_bytes)
