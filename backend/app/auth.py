from pwdlib import PasswordHash

from app.database import get_connection


password_hash = PasswordHash.recommended()


def register_user(username: str, password: str):
    hashed_password = password_hash.hash(password)

    connection = get_connection()

    try:
        cursor = connection.execute(
            """
            INSERT INTO users (username, password_hash)
            VALUES (?, ?)
            """,
            (username, hashed_password),
        )

        connection.commit()

        return cursor.lastrowid

    finally:
        connection.close()