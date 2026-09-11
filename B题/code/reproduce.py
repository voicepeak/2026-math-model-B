"""Run from project root: python B题/code/reproduce.py. Offline only."""
import subprocess,sys
from pathlib import Path
root=Path(__file__).resolve().parents[2]
for name in ['test_core.py','study.py','plot_results.py']:
    subprocess.run([sys.executable,str(root/'B题/code'/name)],cwd=root,check=True)
