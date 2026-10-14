import os

APP_NAME = "Ubuntu Server Project API"
APP_VERSION = "0.1.0"
APP_ENV = "development"

SECRET_KEY = os.environ.get("UBUNTU_SERVER_SECRET_KEY")

if not SECRET_KEY:
    raise RuntimeError(
        "Set the UBUNTU_SERVER_SECRET_KEY environment variable before starting the API."
    )

TOKEN_EXPIRE_MINUTES = 30
