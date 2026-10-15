import uuid
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
STORAGE_DIR = PROJECT_ROOT / "storage"


async def save_file(
    user_id: int,
    uploaded_file,
    max_size_bytes: int,
) -> tuple[str, int]:
    user_directory = STORAGE_DIR / str(user_id)
    user_directory.mkdir(parents=True, exist_ok=True)

    storage_filename = uuid.uuid4().hex
    file_path = user_directory / storage_filename
    total_size = 0

    try:
        with file_path.open("xb") as output:
            while True:
                chunk = await uploaded_file.read(1024 * 1024)

                if not chunk:
                    break

                total_size += len(chunk)

                if total_size > max_size_bytes:
                    raise ValueError("File exceeds the upload limit")

                output.write(chunk)

        return storage_filename, total_size

    except Exception:
        file_path.unlink(missing_ok=True)
        raise