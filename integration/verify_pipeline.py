"""Canonical mandatory pipeline gate; historical positive cases remain obligations."""
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from integration.four_owner.runtime_gate import main as qualify_gate

def main(argv=None):return qualify_gate(argv,kind='pipeline')
if __name__=='__main__':raise SystemExit(main())
