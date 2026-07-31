from pathlib import Path
from fastmcp import Client

client = Client(Path(__file__).parent / "server.py")

