import os
import sys
import tempfile
import warnings
from pathlib import Path

warnings.filterwarnings("ignore")
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ["MEDIPREDICT_DB"] = str(Path(tempfile.mkdtemp()) / "test.db")   # never touch the real DB
