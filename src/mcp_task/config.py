import os
from pathlib import Path

import redis
from dotenv import load_dotenv


load_dotenv()

MOBILEACTION_API_KEY = os.environ.get("MOBILEACTION_API_KEY")
MOBILEACTION_BASE_URL = "https://api.mobileaction.co"

# Repo root, three levels up from this file (src/mcp_task/config.py).
_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
LOG_DIR = Path(os.getenv("LOG_DIR", _REPO_ROOT / "logs"))
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

if not MOBILEACTION_API_KEY:
    raise RuntimeError(
        "MOBILEACTION_API_KEY is not set. Add it to a .env file or export it as an "
        "environment variable before starting the server."
    )


REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

redis_client = redis.from_url(REDIS_URL, decode_responses=True)

# iTunes' lookup endpoint comfortably supports a couple hundred comma-joined
# ids per request; this stays well under that so a single batch call never
# risks a rejected/oversized request.
BATCH_LOOKUP_MAX_IDS = int(os.getenv("BATCH_LOOKUP_MAX_IDS", "300"))