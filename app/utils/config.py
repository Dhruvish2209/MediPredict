"""Central configuration: paths, env vars, thresholds."""
import os
from pathlib import Path

try:  # optional: load .env if python-dotenv is installed
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parents[2] / ".env")
except Exception:  # pragma: no cover
    pass

ROOT = Path(__file__).resolve().parents[2]
APP_DIR = ROOT / "app"
MODELS_DIR = ROOT / "models"
REPORTS_DIR = ROOT / "reports"
ASSETS_DIR = APP_DIR / "assets"
REFERENCE_DIR = ASSETS_DIR / "reference"
KNOWLEDGE_DIR = ASSETS_DIR / "knowledge"

# The DB path can be overridden (used by tests and for deployments with a mounted volume)
DB_PATH = Path(os.getenv("MEDIPREDICT_DB", ROOT / "database" / "medipredict.db"))

# Doctor registration stays closed until a private code is configured.
DOCTOR_INVITE_CODE = os.getenv("DOCTOR_INVITE_CODE", "")

# Brute-force protection
MAX_FAILED_LOGINS = 5
LOCKOUT_MINUTES = 10

# Risk banding for the disease models (percent)
RISK_MEDIUM_FROM = 30.0
RISK_HIGH_FROM = 60.0

APP_NAME = "MediPredict"
APP_TAGLINE = "Explainable AI for early health-risk screening"
