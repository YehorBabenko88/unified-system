import unittest,tempfile
from pathlib import Path

class BootstrapPathTests(unittest.TestCase):
    def test_source_git_selection_pins_executable_without_rewriting_target_source(self):
        from tools.physical_dev.bootstrap import source_git_argv
        root=Path('C:/sources/stratt');git=Path('C:/tooling/git/cmd/git.exe')
        argv=['git','--no-replace-objects','-C',str(root),'show','a'*40+':strattester/research/gateway_adapter.py']
        self.assertEqual(source_git_argv(argv,git,{root}),[str(git),*argv[1:]])
        for bad in [argv[:4]+['status',argv[5]],['C:/foreign/git.exe',*argv[1:]],['git',*argv[1:3],'C:/foreign',*argv[4:]]]:
            with self.assertRaises(RuntimeError):source_git_argv(bad,git,{root})

    def test_own_sqlite_readonly_uri_preserves_exact_state_boundary(self):
        from tools.physical_dev.bootstrap import validate_state_path
        with tempfile.TemporaryDirectory(prefix='pure-smoke-state-') as tmp:
            root=Path(tmp).resolve();db=root/'own.sqlite'
            self.assertIsNone(validate_state_path(db,root))
            self.assertIsNone(validate_state_path(db.as_uri()+'?mode=ro',root))
            for bad in [(root.parent/'foreign.sqlite'),db.as_uri()+'?mode=rw',db.as_uri()+'?mode=ro&cache=shared','file://foreign/own.sqlite?mode=ro',root/'../escape.sqlite']:
                with self.subTest(path=str(bad)),self.assertRaises(RuntimeError):validate_state_path(bad,root)

if __name__=='__main__':unittest.main()
