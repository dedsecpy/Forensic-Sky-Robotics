"""Add project module folders to sys.path so imports keep working after reorganization."""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent
for name in ('core', 'training', 'evaluation', 'data_prep', 'legacy'):
    path = ROOT / name
    text = str(path)
    if text not in sys.path:
        sys.path.insert(0, text)
