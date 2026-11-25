"""Print a compact summary of lan_mtls_probe JSON files (diagnostic only)."""
import json
import pathlib
import sys


def main(directory):
    for path in sorted(pathlib.Path(directory).glob('*.json')):
        try:
            doc = json.loads(path.read_text(encoding='utf-8'))
        except (OSError, ValueError) as exc:
            print('SUMMARY_UNREADABLE', path.name, type(exc).__name__)
            continue
        if type(doc) is not dict or 'iterations' not in doc:
            continue
        print(f"== {path.name} label={doc.get('label')} python={(doc.get('python') or '?').split()[0]} platform={doc.get('platform')}")
        for it in doc.get('iterations', []):
            print(f"  iteration={it['index']} ran={it['ran']} errors={it['errors']} failures={it['failures']} seconds={it['seconds']}")
            for row in it.get('failed', []):
                if 'test_lan' not in row['id'] and 'test_network_budget' not in row['id']:
                    print('    NON_LAN_FAILED', row['id'])
                    continue
                print('    FAILED', row['id'], 'ms=', row['ms'], 'budget_tx=', json.dumps(row.get('budget_tx')))
                print('      error', json.dumps(row.get('error'))[:600])
                for event in row.get('events', []):
                    if event['kind'] in ('CONNECTION_CLOSE', 'MUX_ABORT', 'MUX_SEND_ERROR', 'MUX_SEND_START', 'MUX_SEND_DONE',
                                         'WRITE_FRAME_ERROR', 'FRAGMENT_SEND_ERROR', 'SLOW_BUDGET_TX', 'SLOW_WRITE_FRAME'):
                        print('      ', json.dumps(event, default=str)[:1200])
            mux = it.get('lan_timings', {}).get('test_lan_mux_channel.MuxTlsTests.test_complete_large_messages_real_mtls_and_budget_overhead')
            if mux:
                print('    large_messages_ms', mux['ms'], json.dumps(mux['budget_tx']))
    return 0


if __name__ == '__main__':
    raise SystemExit(main(sys.argv[1]))
