"""Optional notification transport; never receives raw source diagnostics."""
import json
import re

from .model import EVENT_KINDS, STATES, label, need


def closed_message(message):
    need(type(message) is str and 0 < len(message) <= 512, 'CLOSED_NOTIFICATION_REQUIRED')
    parts = message.split(' | ')
    need(len(parts) == 4 and parts[0].startswith('Unified Observer: ') and
         parts[0][18:] in EVENT_KINDS and parts[2] in STATES and
         re.fullmatch(r'source [a-f0-9]{7}', parts[3]), 'CLOSED_NOTIFICATION_REQUIRED')
    label(parts[1])


class MockNotificationTransport:
    mode = 'MOCK'
    def __init__(self, result='SENT'):
        need(result in ('SENT', 'NOT_SENT', 'UNKNOWN'), 'DELIVERY_STATE')
        self.result, self.messages = result, []

    def send(self, message):
        closed_message(message)
        self.messages.append(message)
        return self.result


class TelegramTestTransport:
    """Opt-in test bot only; no credential auto-discovery or production fallback.

    API: https://core.telegram.org/bots/api#sendmessage. Ambiguous errors are
    UNKNOWN, never a reason to resend automatically. No token/URL/error logging.
    """
    mode = 'TELEGRAM_TEST'
    def __init__(self, token, chat_id, *, test_credentials_confirmed=False,
                 network_admitted=False, request=None):
        need(test_credentials_confirmed is True and network_admitted is True, 'TELEGRAM_TEST_ADMISSION_REQUIRED')
        need(type(token) is str and re.fullmatch(r'[0-9]{3,20}:[A-Za-z0-9_-]{20,128}', token), 'TEST_TOKEN_FORMAT')
        need(type(chat_id) is str and re.fullmatch(r'-?[0-9]{1,24}', chat_id), 'TEST_CHAT_ID')
        self._token, self._chat, self._request = token, chat_id, request

    def __repr__(self): return '<Observer TelegramTestTransport: credentials redacted>'

    def send(self, message):
        closed_message(message)
        payload = json.dumps({'chat_id':self._chat, 'text':message,
                              'disable_web_page_preview':True}).encode()
        try:
            if self._request is not None:
                raw = self._request(payload)
            else:
                import ssl
                import urllib.request
                class NoRedirect(urllib.request.HTTPRedirectHandler):
                    def redirect_request(self, *args, **kwargs): return None
                opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect(),
                    urllib.request.HTTPSHandler(context=ssl.create_default_context()))
                request = urllib.request.Request('https://api.telegram.org/bot' + self._token + '/sendMessage',
                    data=payload, method='POST', headers={'Content-Type':'application/json'})
                with opener.open(request, timeout=3) as response:
                    raw = response.read(16385)
            need(type(raw) is bytes and len(raw) <= 16384, 'TELEGRAM_RESPONSE_BOUND')
            data = json.loads(raw)
            if type(data) is dict and data.get('ok') is True:
                return 'SENT'
            # A valid explicit provider refusal did not acknowledge delivery.
            if type(data) is dict and data.get('ok') is False:
                return 'NOT_SENT'
        except Exception:
            pass
        return 'UNKNOWN'
