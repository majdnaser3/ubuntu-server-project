import jwt

from pathlib import Path
from sqlite3 import IntegrityError

from fastapi import (
    FastAPI,
    HTTPException,
    UploadFile,
    File,
    Depends,
    Request,
)
from fastapi.staticfiles import StaticFiles

from fastapi.responses import FileResponse, JSONResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field

from app.config import (
    APP_NAME,
    APP_VERSION,
    SECRET_KEY,
    MAX_UPLOAD_SIZE_MB,
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


@app.middleware("http")
async def check_request_before_processing(request: Request, call_next):
    path = request.url.path

    # Protect all file-management endpoints.
    if path == "/files" or path.startswith("/files/"):
        authorization = request.headers.get("authorization", "")
        parts = authorization.split()

        if len(parts) != 2 or parts[0].lower() != "bearer":
            return JSONResponse(
                status_code=401,
                content={"detail": "Authentication required"},
                headers={"WWW-Authenticate": "Bearer"},
            )

        try:
            payload = jwt.decode(
                parts[1],
                SECRET_KEY,
                algorithms=["HS256"],
            )
            user_id = int(payload["sub"])
        except (jwt.InvalidTokenError, KeyError, ValueError):
            return JSONResponse(
                status_code=401,
                content={"detail": "Invalid or expired token"},
                headers={"WWW-Authenticate": "Bearer"},
            )

        connection = get_connection()
        try:
            user = connection.execute(
                "SELECT id FROM users WHERE id = ?",
                (user_id,),
            ).fetchone()
        finally:
            connection.close()

        if user is None:
            return JSONResponse(
                status_code=401,
                content={"detail": "User not found"},
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Reject clearly oversized upload requests before endpoint processing.
        if request.method == "POST" and path == "/files/upload":
            content_length = request.headers.get("content-length")

            if content_length is not None:
                try:
                    request_size = int(content_length)
                except ValueError:
                    return JSONResponse(
                        status_code=400,
                        content={"detail": "Invalid Content-Length header"},
                    )

                max_request_size = (
                    MAX_UPLOAD_SIZE_MB * 1024 * 1024
                    + 1024 * 1024
                )

                if request_size > max_request_size:
                    return JSONResponse(
                        status_code=413,
                        content={
                            "detail": (
                                f"Upload exceeds the "
                                f"{MAX_UPLOAD_SIZE_MB} MB limit"
                            )
                        },
                    )

    return await call_next(request)


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
        await uploaded_file.close()
        raise HTTPException(
            status_code=400,
            detail="Filename is required",
        )

    max_size_bytes = MAX_UPLOAD_SIZE_MB * 1024 * 1024

    try:
        storage_filename, file_size = await save_file(
            user["id"],
            uploaded_file,
            max_size_bytes,
        )

        if file_size == 0:
            file_path = (
                STORAGE_DIR / str(user["id"]) / storage_filename
            )
            file_path.unlink(missing_ok=True)

            raise HTTPException(
                status_code=400,
                detail="Empty files are not allowed",
            )

        connection = get_connection()

        try:
            cursor = connection.execute(
                """
                INSERT INTO files (
                    user_id,
                    original_filename,
                    storage_filename,
                    content_type,
                    size_bytes
                )
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    user["id"],
                    original_filename,
                    storage_filename,
                    uploaded_file.content_type,
                    file_size,
                ),
            )

            connection.commit()
            file_id = cursor.lastrowid

        except Exception:
            file_path = (
                STORAGE_DIR / str(user["id"]) / storage_filename
            )
            file_path.unlink(missing_ok=True)
            raise

        finally:
            connection.close()

    except ValueError as error:
        if "upload limit" in str(error):
            raise HTTPException(
                status_code=413,
                detail=f"File exceeds the {MAX_UPLOAD_SIZE_MB} MB upload limit",
            )
        raise

    finally:
        await uploaded_file.close()

    return {
        "id": file_id,
        "filename": original_filename,
        "size_bytes": file_size,
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

FRONTEND_DIR = Path(__file__).resolve().parents[2] / "frontend"
app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")
