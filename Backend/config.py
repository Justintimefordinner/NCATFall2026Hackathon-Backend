"""Settings. Imports nothing from the project."""
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

PIN = os.environ.get("MES_PIN", "1234")
CONFIDENCE_THRESHOLD = float(os.environ.get("MES_CONFIDENCE", "0.6"))
DATA_PATH = os.environ.get(
    "MES_DATA", os.path.join(BASE_DIR, "data", "op10.json"))
IMG_DIR = os.path.join(BASE_DIR, "data", "img")
FRONTEND_DIST = os.environ.get(
    "MES_FRONTEND_DIST",
    os.path.join(BASE_DIR, "..", "Frontend", "dist")
)
HOST = "0.0.0.0"
PORT = int(os.environ.get("MES_PORT", "5000"))

LOG_CAP = 200          # entries kept in memory
LOG_SENT = 50          # entries pushed to clients
