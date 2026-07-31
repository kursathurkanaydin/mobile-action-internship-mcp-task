import os

from dotenv import load_dotenv

load_dotenv()

MOBILEACTION_API_KEY = os.environ.get("MOBILEACTION_API_KEY")
MOBILEACTION_BASE_URL = "https://api.mobileaction.co"

if not MOBILEACTION_API_KEY:
    raise RuntimeError(
        "MOBILEACTION_API_KEY is not set. Add it to a .env file or export it as an "
        "environment variable before starting the server."
    )
