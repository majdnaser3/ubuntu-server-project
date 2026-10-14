from pwdlib import PasswordHash
from app.database import get_connection
from datetime import datetime, timedelta, timezone
import jwt
from app.config import SECRET_KEY, TOKEN_EXPIRE_MINUTES

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

def authenticate_user(username: str, password: str):
    connection = get_connection()

    try:
        user = connection.execute(
            "SELECT id, username, password_hash FROM users WHERE username = ?",
            (username,),
        ).fetchone()
    finally:
        connection.close()

    if user is None:
        return None

    if not password_hash.verify(password, user["password_hash"]):
        return None

    return {
        "id": user["id"],
        "username": user["username"],
    }


def create_access_token(user_id: int, username: str):
    expires_at = datetime.now(timezone.utc) + timedelta(
        minutes=TOKEN_EXPIRE_MINUTES
    )

    payload = {
        "sub": str(user_id),
        "username": username,
        "exp": expires_at,
    }

    return jwt.encode(payload, SECRET_KEY, algorithm="HS256")
