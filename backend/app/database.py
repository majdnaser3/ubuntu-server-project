
import sqlite3
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data"
DATABASE_PATH = DATA_DIR / "server.db"


def get_connection():
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row

    return connection


def initialize_database():
    connection = get_connection()

    try:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                is_admin INTEGER NOT NULL DEFAULT 0,
                storage_quota_bytes INTEGER NOT NULL DEFAULT 10000000000,
                max_upload_size_bytes INTEGER NOT NULL DEFAULT 524288000
            )
            """
        )

        # Migrate existing databases to support administrator roles.
        user_columns = {
            row["name"]
            for row in connection.execute(
                "PRAGMA table_info(users)"
            ).fetchall()
        }

        if "is_admin" not in user_columns:
            connection.execute(
                """
                ALTER TABLE users
                ADD COLUMN is_admin INTEGER NOT NULL DEFAULT 0
                """
            )

        # Migrate existing databases to support individual storage quotas.
        user_columns = {
            row["name"]
            for row in connection.execute(
                "PRAGMA table_info(users)"
            ).fetchall()
        }

        if "storage_quota_bytes" not in user_columns:
            connection.execute(
                """
                ALTER TABLE users
                ADD COLUMN storage_quota_bytes INTEGER NOT NULL
                DEFAULT 10000000000
                """
            )

        # Migrate existing databases to support individual upload limits.
        user_columns = {
            row["name"]
            for row in connection.execute(
                "PRAGMA table_info(users)"
            ).fetchall()
        }

        if "max_upload_size_bytes" not in user_columns:
            connection.execute(
                """
                ALTER TABLE users
                ADD COLUMN max_upload_size_bytes INTEGER NOT NULL
                DEFAULT 524288000
                """
            )

        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS files (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                original_filename TEXT NOT NULL,
                storage_filename TEXT NOT NULL UNIQUE,
                content_type TEXT,
                size_bytes INTEGER NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
            """
        )

        connection.commit()

    finally:
        connection.close()
