import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
LOGS_DIR = DATA_DIR / "logs"
METRICS_DIR = DATA_DIR / "metrics"
GROUND_TRUTHS_DIR = BASE_DIR / "ground_truths"

LOGS_DIR.mkdir(parents=True, exist_ok=True)
METRICS_DIR.mkdir(parents=True, exist_ok=True)
GROUND_TRUTHS_DIR.mkdir(parents=True, exist_ok=True)

# Supabase & DB settings
SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "sb_publishable_slewOyII3s2T85VGBw77Zw_KGjV3V2J")
DATABASE_URL = os.getenv("DATABASE_URL", "")

# Service Ports
PAYMENT_SERVICE_PORT = int(os.getenv("PAYMENT_SERVICE_PORT", "8001"))
ORDER_SERVICE_PORT = int(os.getenv("ORDER_SERVICE_PORT", "8002"))
