"""Windows SSH context regression; no connections or private credentials."""
import unittest
from unified_system.worker_transport import windows_ssh_environment


def context():
    return {'SystemRoot':r'C:\Windows','ProgramData':r'C:\ProgramData',
            'USERPROFILE':r'C:\Users\lab','PATH':r'C:\Windows\System32\OpenSSH',
            'TEMP':r'C:\Users\lab\Temp'}


class WorkerTransportEnvironmentTests(unittest.TestCase):
    def test_windows_openssh_required_programdata_is_not_filtered_out(self):
        result=windows_ssh_environment(context())
        self.assertEqual(result['PROGRAMDATA'],r'C:\ProgramData')

    def test_missing_context_is_rejected_before_any_transport(self):
        for missing in ('SystemRoot','ProgramData','USERPROFILE','PATH'):
            with self.subTest(missing=missing):
                value=context();value.pop(missing)
                with self.assertRaisesRegex(ValueError,'SSH_OS_CONTEXT_MISSING'):
                    windows_ssh_environment(value)

    def test_database_exchange_and_bot_secrets_never_enter_ssh_environment(self):
        value=context();value.update(PGPASSWORD='private',GRID_SHARED_TOKEN='private',
            NODE_CREDENTIAL='private',BYBIT_API_KEY='private',TELEGRAM_BOT_TOKEN='private',
            SSH_ASKPASS='unapproved-program',GIT_SSH_COMMAND='unapproved-program')
        result=windows_ssh_environment(value)
        self.assertEqual(set(result),{'SYSTEMROOT','PROGRAMDATA','USERPROFILE','PATH','TEMP'})
        self.assertNotIn('private',result.values())

    def test_case_aliases_and_invalid_values_are_rejected(self):
        value=context();value['PROGRAMDATA']=r'C:\other'
        with self.assertRaisesRegex(ValueError,'SSH_OS_CONTEXT_AMBIGUOUS'):
            windows_ssh_environment(value)
        for item in (None,False,'','bad\x00path','bad\rpath','bad\npath','x'*32768):
            with self.subTest(type=type(item).__name__):
                value=context();value['ProgramData']=item
                with self.assertRaises(ValueError):windows_ssh_environment(value)

    def test_returned_mapping_is_independent_of_parent(self):
        value=context();before=dict(value);result=windows_ssh_environment(value)
        result['PROGRAMDATA']='changed'
        self.assertEqual(value,before)


if __name__=='__main__':unittest.main()
