import os

APP_NAME = "Ubuntu Server Project API"
APP_VERSION = "0.1.0"
APP_ENV = "development"

SECRET_KEY = os.environ.get("UBUNTU_SERVER_SECRET_KEY")
SETUP_TOKEN = os.environ.get("UBUNTU_SERVER_SETUP_TOKEN")

if not SECRET_KEY:
    raise RuntimeError(
        "Set the UBUNTU_SERVER_SECRET_KEY environment variable before starting the API."
    )

TOKEN_EXPIRE_MINUTES = 30

MAX_UPLOAD_SIZE_MB = int(
    os.environ.get("UBUNTU_SERVER_MAX_UPLOAD_MB", "500")
)
