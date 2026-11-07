"""Explicit synthetic subprocess control harness, NOT a production worker.

No imports start it. No command executes user code, provider I/O or publication.
State is process-local: loss/restart requires reconciliation, never assumption of
continued ownership. Native worker control must revalidate authority per effect.
"""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import threading
import queue


class SyntheticWorker:
    def __init__(self, *, response_timeout=2):
        if type(response_timeout) not in (int, float) or not 0 < response_timeout <= 2:
            raise ValueError('bounded fixture response timeout required')
        self.response_timeout = response_timeout
        self.process = subprocess.Popen([sys.executable, '-I', '-u', str(Path(__file__).resolve()), '--synthetic'],
                                        stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
        self.lock = threading.Lock()

    def _call(self, value):
        raw = json.dumps(value, sort_keys=True, separators=(',', ':')).encode('ascii')
        if len(raw) > 1024: raise ValueError('fixture control too large')
        if not self.lock.acquire(timeout=self.response_timeout):
            raise TimeoutError('fixture control busy')
        try:
            replies = queue.Queue(maxsize=1)
            def exchange():
                try:
                    self.process.stdin.write(raw + b'\n'); self.process.stdin.flush()
                    reply = self.process.stdout.readline(1025)
                    replies.put(reply)
                except Exception as error: replies.put(error)
            thread = threading.Thread(target=exchange, daemon=True)
            thread.start()
            try: reply = replies.get(timeout=self.response_timeout)
            except queue.Empty:
                self.close()
                raise TimeoutError('fixture child response deadline') from None
            if isinstance(reply, Exception): raise OSError('fixture pipe failed') from reply
            if not reply or len(reply) > 1024: raise OSError('fixture child unavailable')
            result = json.loads(reply)
            if 'error' in result: raise ValueError(result['error'])
            return None if result['state'] is None else result['state'].encode('ascii')
        finally: self.lock.release()

    def start(self, request_id, raw, grant=b'SYNTHETIC_ONLY'):
        digest = hashlib.sha256(raw + b'\0' + grant).hexdigest()
        return self._call(dict(action='START', request_id=request_id, digest=digest))

    def inspect(self, request_id): return self._call(dict(action='INSPECT', request_id=request_id))
    def pause(self, request_id): return self._call(dict(action='PAUSE', request_id=request_id))

    def close(self):
        if self.process.poll() is None:
            self.process.terminate()
            try: self.process.wait(timeout=2)
            except subprocess.TimeoutExpired: self.process.kill(); self.process.wait(timeout=2)
        self.process.stdin.close(); self.process.stdout.close()

    def __enter__(self): return self
    def __exit__(self, *args): self.close()


def _synthetic_main():
    states, paused = {}, set()
    while True:
        raw = sys.stdin.buffer.readline(1025)
        if not raw: return
        if len(raw) > 1024: return
        try:
            value = json.loads(raw)
            key = value['request_id']; action = value['action']
            if type(key) is not str or not 1 <= len(key) <= 128: raise ValueError('fixture id')
            if action == 'START':
                if len(set(states) | paused) >= 32 and key not in states and key not in paused: raise ValueError('fixture capacity')
                digest = value['digest']
                if key in states and states[key][0] != digest: raise ValueError('fixture intent conflict')
                states.setdefault(key, (digest, 'PAUSED' if key in paused else 'STARTED'))
            elif action == 'PAUSE':
                if len(set(states) | paused) >= 32 and key not in states and key not in paused: raise ValueError('fixture capacity')
                paused.add(key)
                if key in states: states[key] = (states[key][0], 'PAUSED')
            elif action != 'INSPECT': raise ValueError('fixture action')
            result = dict(state=states[key][1] if key in states else None)
        except (ValueError, KeyError, TypeError): result = dict(error='INVALID_FIXTURE_CONTROL')
        print(json.dumps(result, separators=(',', ':')), flush=True)


if __name__ == '__main__' and sys.argv[1:] == ['--synthetic']: _synthetic_main()
