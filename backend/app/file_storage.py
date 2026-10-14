import uuid
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
STORAGE_DIR = PROJECT_ROOT / "storage"


def save_file(user_id: int, original_filename: str, content: bytes) -> str:
    user_directory = STORAGE_DIR / str(user_id)
    user_directory.mkdir(parents=True, exist_ok=True)

    storage_filename = uuid.uuid4().hex
    file_path = user_directory / storage_filename
    file_path.write_bytes(content)

    return storage_filename
