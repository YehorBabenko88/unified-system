"""Canonical four-owner all source scope; no retired source aliases."""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parent))
from qualify_four_owner import main as qualify

def main(argv=None):return qualify(argv,suite='all')
if __name__=='__main__':raise SystemExit(main())
