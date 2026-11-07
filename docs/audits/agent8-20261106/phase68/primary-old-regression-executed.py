import pathlib,sys,types,subprocess,unittest
root=pathlib.Path.cwd();sys.path[:0]=[str(root),str(root/'tests')]
from unified_system import lan_mux_channel as mux
old=subprocess.check_output(['git','--no-replace-objects','show','acf4f89d70e00e0b9a2b1bd3400abe07bb720ba1:unified_system/lan_mux_channel.py'])
exec(compile(old,'<A8-primary-acf4-in-memory-only>','exec'),mux.__dict__)
import test_lan_mux_channel as tests
suite=unittest.TestSuite([tests.MuxTlsTests('test_hash_terminal_cause_survives_reader_receive_interleaving')]);result=unittest.TextTestRunner(verbosity=2).run(suite)
assert result.testsRun==1 and len(result.failures)==1 and not result.errors and not result.skipped
assert 'MUX_CLOSED' in result.failures[0][1] and 'MUX_MESSAGE_HASH_REJECTED' in result.failures[0][1]
