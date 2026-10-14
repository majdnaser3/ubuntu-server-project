import jwt

from pathlib import Path
from sqlite3 import IntegrityError

from fastapi import (
    FastAPI,
    HTTPException,
    UploadFile,
    File,
    Depends,
)
from fastapi.responses import FileResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field

from app.config import (
    APP_NAME,
    APP_VERSION,
    SECRET_KEY,
)
from app.database import (
    initialize_database,
    get_connection,
)
from app.auth import (
    register_user,
    authenticate_user,
    create_access_token,
)
from app.file_storage import (
    STORAGE_DIR,
    save_file,
)

app = FastAPI(
    title=APP_NAME,
    description="A private, multi-user personal cloud and file storage API.",
    version=APP_VERSION,
)

@app.on_event("startup")
def startup():
    initialize_database()

@app.get("/health")
def health_check():
    return {
        "status": "ok",
        "service": "ubuntu-server-project-api",
    }

class RegisterRequest(BaseModel):
    username: str = Field(min_length=3, max_length=50)
    password: str = Field(min_length=8, max_length=128)

class LoginRequest(BaseModel):
    username: str
    password: str

security = HTTPBearer()


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
):
    try:
        payload = jwt.decode(
            credentials.credentials,
            SECRET_KEY,
            algorithms=["HS256"],
        )
        user_id = int(payload["sub"])
    except (jwt.InvalidTokenError, KeyError, ValueError):
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired token",
        )

    connection = get_connection()
    try:
        user = connection.execute(
            "SELECT id, username FROM users WHERE id = ?",
            (user_id,),
        ).fetchone()
    finally:
        connection.close()

    if user is None:
        raise HTTPException(status_code=401, detail="User not found")

    return {"id": user["id"], "username": user["username"]}

@app.post("/register", status_code=201)
def create_account(request: RegisterRequest):
    username = request.username.strip()

    if len(username) < 3:
        raise HTTPException(
            status_code=422,
            detail="Username must contain at least 3 characters",
        )

    try:
        user_id = register_user(username, request.password)
    except IntegrityError:
        raise HTTPException(
            status_code=409,
            detail="Username already exists",
        )

    return {
        "id": user_id,
        "username": username,
        "message": "Account created successfully",
    }

@app.post("/login")
def login(request: LoginRequest):
    user = authenticate_user(
        request.username.strip(),
        request.password,
    )

    if user is None:
        raise HTTPException(
            status_code=401,
            detail="Incorrect username or password",
        )

    token = create_access_token(
        user["id"],
        user["username"],
    )

    return {
        "access_token": token,
        "token_type": "bearer",
    }

@app.post("/files/upload", status_code=201)
async def upload_file(
    uploaded_file: UploadFile = File(...),
    user: dict = Depends(get_current_user),
):
    original_filename = Path(uploaded_file.filename or "").name

    if not original_filename:
        raise HTTPException(status_code=400, detail="Filename is required")

    content = await uploaded_file.read()

    if not content:
        raise HTTPException(status_code=400, detail="Empty files are not allowed")

    storage_filename = save_file(
        user["id"],
        original_filename,
        content,
    )

    connection = get_connection()
    try:
        cursor = connection.execute(
            """
            INSERT INTO files (
                user_id, original_filename, storage_filename,
                content_type, size_bytes
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                user["id"],
                original_filename,
                storage_filename,
                uploaded_file.content_type,
                len(content),
            ),
        )
        connection.commit()
        file_id = cursor.lastrowid
    finally:
        connection.close()

    await uploaded_file.close()

    return {
        "id": file_id,
        "filename": original_filename,
        "size_bytes": len(content),
        "message": "File uploaded successfully",
    }

@app.get("/files")
def list_files(user: dict = Depends(get_current_user)):
    connection = get_connection()

    try:
        rows = connection.execute(
            """
            SELECT id, original_filename, content_type,
                   size_bytes, created_at
            FROM files
            WHERE user_id = ?
            ORDER BY created_at DESC
            """,
            (user["id"],),
        ).fetchall()

        return [dict(row) for row in rows]

    finally:
        connection.close()

@app.get("/files/{file_id}/download")
def download_file(
    file_id: int,
    user: dict = Depends(get_current_user),
):
    connection = get_connection()

    try:
        row = connection.execute(
            """
            SELECT original_filename, storage_filename
            FROM files
            WHERE id = ? AND user_id = ?
            """,
            (file_id, user["id"]),
        ).fetchone()
    finally:
        connection.close()

    if row is None:
        raise HTTPException(status_code=404, detail="File not found")

    file_path = STORAGE_DIR / str(user["id"]) / row["storage_filename"]

    if not file_path.is_file():
        raise HTTPException(status_code=404, detail="File missing from storage")

    return FileResponse(
        path=file_path,
        filename=row["original_filename"],
    )

@app.delete("/files/{file_id}")
def delete_file(
    file_id: int,
    user: dict = Depends(get_current_user),
):
    connection = get_connection()

    try:
        row = connection.execute(
            """
            SELECT storage_filename
            FROM files
            WHERE id = ? AND user_id = ?
            """,
            (file_id, user["id"]),
        ).fetchone()

        if row is None:
            raise HTTPException(status_code=404, detail="File not found")

        file_path = STORAGE_DIR / str(user["id"]) / row["storage_filename"]

        if file_path.is_file():
            file_path.unlink()

        connection.execute(
            "DELETE FROM files WHERE id = ? AND user_id = ?",
            (file_id, user["id"]),
        )
        connection.commit()

        return {"message": "File deleted successfully"}

    finally:
        connection.close()
