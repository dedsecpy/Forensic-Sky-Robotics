"""CLI wrapper for offline clip analysis."""
import bootstrap  # noqa: F401
import runpy
from pathlib import Path
import sys

# Preserve `python analyze.py clip.mp4` usage from the project root.
sys.argv[0] = str(Path(__file__).resolve().parent / 'evaluation' / 'analyze.py')
runpy.run_path(str(Path(__file__).resolve().parent / 'evaluation' / 'analyze.py'), run_name='__main__')
