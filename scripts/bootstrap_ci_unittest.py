"""Launch unchanged retained discovery with real isolated startup flags."""
from pathlib import Path
import subprocess
import sys
import sysconfig
import tempfile

BOOTSTRAP = "import runpy,sys; script=sys.argv[1]; sys.path.append(sys.argv[2]); sys.argv=[script]; runpy.run_path(script,run_name='__main__')"

def build_command(executable, script, dependencies, cache):
    script, dependencies, cache = Path(script), Path(dependencies), Path(cache)
    root = Path(__file__).resolve().parents[1]
    if not all(p.is_absolute() for p in (script, dependencies, cache)):
        raise ValueError('absolute paths required')
    if not script.is_file() or script.is_symlink() or not dependencies.is_dir() or dependencies.is_symlink():
        raise ValueError('ordinary source and dependency paths required')
    if dependencies.resolve().is_relative_to(root) or cache.exists() or cache.is_symlink() or cache.resolve().is_relative_to(root):
        raise ValueError('external dependencies and fresh external cache required')
    return [str(executable), '-I', '-S', '-B', '-X', 'pycache_prefix='+str(cache), '-c', BOOTSTRAP, str(script), str(dependencies)]

def run_suite(dependencies):
    script = Path(__file__).resolve().with_name('ci_unittest.py')
    with tempfile.TemporaryDirectory(prefix='root-unittest-bootstrap-') as directory:
        cache = Path(directory).resolve() / 'cache'
        command = build_command(sys.executable, script, Path(dependencies).resolve(), cache)
        return subprocess.run(command, check=False).returncode

if __name__ == '__main__':
    raise SystemExit(run_suite(sysconfig.get_path('purelib')))
