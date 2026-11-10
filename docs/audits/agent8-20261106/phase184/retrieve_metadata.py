"""One bounded metadata-only retrieval; never imports or runs fetched content."""
import datetime
import hashlib
import http.client
import json
from pathlib import Path
import re
import ssl
import time
from urllib.parse import urljoin, urlsplit

OUT = Path(__file__).resolve().parent
ITEMS = [
    ('checksums.txt', 'https://releases.hashicorp.com/consul/1.22.2/consul_1.22.2_SHA256SUMS'),
    ('signature-keyid.bin', 'https://releases.hashicorp.com/consul/1.22.2/consul_1.22.2_SHA256SUMS.72D7468F.sig'),
    ('signature-generic.bin', 'https://releases.hashicorp.com/consul/1.22.2/consul_1.22.2_SHA256SUMS.sig'),
    ('publisher-key.txt', 'https://www.hashicorp.com/.well-known/pgp-key.txt'),
    ('security.html', 'https://www.hashicorp.com/en/trust/security'),
    ('key-update-bulletin.html', 'https://discuss.hashicorp.com/t/hcsec-2026-03-hashicorp-gpg-key-72d7468f-update/77237'),
]
DOMAINS = frozenset(('releases.hashicorp.com', 'www.hashicorp.com', 'discuss.hashicorp.com'))
MAX_BYTES = 6 * 1024 * 1024
RATE = 32 * 1024
MAX_GETS = 6  # Conservatively includes every redirect request, not just initial URLs.


def utc():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def main():
    assert not (OUT / 'RETRIEVAL.json').exists(), 'NO_RETRY_OR_OVERWRITE'
    context = ssl.create_default_context()
    report = dict(schema='a2.consul.metadata-retrieval.v1', started_utc=utc(),
        scope='METADATA_ONLY_NO_SIGNATURE_VERIFICATION', tls='ssl.create_default_context; certificate+hostname verification; no override',
        limits=dict(get_requests=6, aggregate_body_bytes=MAX_BYTES, body_bytes_per_second=RATE,
                    per_response_seconds=30, redirects_per_item=2, parallel_connections=1),
        redirects_count_as_gets=True, items=[], requests_made=0, received_body_bytes=0,
        signature_verified=False, publisher_authenticated=False, archive_downloaded=False)
    try:
        for filename, original in ITEMS:
            item = dict(original_url=original, filename=filename, started_utc=utc(), chain=[], status='NOT_ATTEMPTED')
            report['items'].append(item)
            current = original
            try:
                for hop in range(3):
                    if report['requests_made'] >= MAX_GETS:
                        item['status'] = 'GET_BUDGET_EXHAUSTED_NO_FALLBACK'
                        break
                    u = urlsplit(current)
                    if (u.scheme != 'https' or u.hostname not in DOMAINS or u.port not in (None, 443)
                            or u.username is not None or u.password is not None or u.fragment):
                        raise ValueError('REDIRECT_NOT_APPROVED_HTTPS_ORIGIN')
                    started = time.monotonic()
                    deadline = started + 30
                    conn = http.client.HTTPSConnection(u.hostname, port=443, timeout=30, context=context)
                    response = None
                    data = bytearray()
                    row = dict(url=current, request_utc=utc())
                    item['chain'].append(row)
                    try:
                        report['requests_made'] += 1
                        conn.request('GET', u.path + (('?' + u.query) if u.query else ''),
                                     headers={'User-Agent': 'A2-bounded-metadata-review/1', 'Accept-Encoding': 'identity', 'Connection': 'close'})
                        remaining = deadline - time.monotonic()
                        if remaining <= 0:
                            raise TimeoutError('RESPONSE_DEADLINE')
                        if conn.sock:
                            conn.sock.settimeout(remaining)
                        response = conn.getresponse()
                        row.update(http_status=response.status, response_utc=utc(),
                                   content_type=response.getheader('Content-Type'),
                                   content_length=response.getheader('Content-Length'))
                        if response.status in (301, 302, 303, 307, 308):
                            location = response.getheader('Location')
                            if not location or hop == 2:
                                raise ValueError('REDIRECT_LIMIT_OR_MISSING_LOCATION')
                            current = urljoin(current, location)
                            row['redirect_to'] = current
                            continue
                        # Read at most remaining global body bytes, including HTTP errors.
                        while True:
                            chunk_budget = min(4096, MAX_BYTES - report['received_body_bytes'])
                            if chunk_budget <= 0:
                                raise ValueError('BODY_BUDGET_EXHAUSTED')
                            # Pace BEFORE reading, so no initial unthrottled body burst.
                            delay = chunk_budget / RATE
                            if time.monotonic() + delay >= deadline:
                                raise TimeoutError('RESPONSE_DEADLINE')
                            time.sleep(delay)
                            remaining = deadline - time.monotonic()
                            sock = getattr(getattr(getattr(response, 'fp', None), 'raw', None), '_sock', None)
                            if sock is not None:
                                sock.settimeout(remaining)
                            elif conn.sock is not None:
                                conn.sock.settimeout(remaining)
                            else:
                                raise ValueError('RESPONSE_SOCKET_DEADLINE_UNAVAILABLE')
                            chunk = response.read1(chunk_budget)
                            if not chunk:
                                break
                            data.extend(chunk)
                            report['received_body_bytes'] += len(chunk)
                        item['status'] = 'RETAINED_HTTP_200' if response.status == 200 else 'RETAINED_HTTP_ERROR_NO_RETRY'
                        break
                    finally:
                        if data:
                            target = OUT / (filename if item['status'].startswith('RETAINED_') else filename + '.partial')
                            with target.open('xb') as stream:
                                stream.write(data)
                            row.update(retained_filename=target.name, bytes=len(data), sha256=hashlib.sha256(data).hexdigest())
                        row['elapsed_seconds'] = round(time.monotonic() - started, 6)
                        if response is not None:
                            response.close()
                        conn.close()
            except Exception as exc:
                item.update(status='FAILED_NO_RETRY_OR_FALLBACK', error_type=type(exc).__name__, error=str(exc)[:300])
            item['finished_utc'] = utc()
            print(json.dumps(dict(item=filename, status=item['status'], requests_made=report['requests_made'],
                                  received_body_bytes=report['received_body_bytes'])), flush=True)
        checksums = OUT / 'checksums.txt'
        comparisons = []
        if checksums.exists() and report['items'][0]['status'] == 'RETAINED_HTTP_200':
            text = checksums.read_text(encoding='ascii')
            expected = {
                'consul_1.22.2_windows_amd64.zip': '7b8a3bb723017d1be87decf3a7bb12661c36e43eba8283b8c04eca60501493ec',
                'consul_1.22.2_linux_amd64.zip': 'e9ad339128e396238f053269bf8f76aeba1b5fada6f6cb60ab19fe70e133acde',
            }
            for name, known in expected.items():
                matches = re.findall(r'^([0-9a-f]{64})[ \t]+\*?' + re.escape(name) + r'\r?$', text, re.MULTILINE)
                comparisons.append(dict(archive=name, checksum_entries=matches, expected_existing_sha256=known,
                                        exact_unique_match=matches == [known]))
        report['checksum_comparisons_not_signature_verification'] = comparisons
        report['root_reported_publisher_reference_not_verified_here'] = dict(
            primary_fingerprint='C874011F0AB405110D02105534365D9472D7468F', updated_expiry='2030-03-01')
    finally:
        report['finished_utc'] = utc()
        with (OUT / 'RETRIEVAL.json').open('x', encoding='utf-8', newline='\n') as stream:
            json.dump(report, stream, sort_keys=True, indent=2)
            stream.write('\n')


if __name__ == '__main__':
    main()
