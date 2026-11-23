"""Launch the desktop demo (evaluation/demo.py)."""
import bootstrap  # noqa: F401
import runpy
from pathlib import Path

runpy.run_path(str(Path(__file__).resolve().parent / 'evaluation' / 'demo.py'), run_name='__main__')
