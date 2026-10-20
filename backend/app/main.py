import jwt
from datetime import datetime, timedelta, timezone
from hmac import compare_digest

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
    SETUP_TOKEN,
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
    password_hash,
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
    if (
    (path == "/files" or path.startswith("/files/"))
    and not (
        request.method == "GET"
        and path.endswith("/download-direct")
    )
    ):
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

class SetupAdminRequest(BaseModel):
    setup_token: str = Field(min_length=1, max_length=256)
    username: str = Field(min_length=3, max_length=50)
    password: str = Field(min_length=8, max_length=128)

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
            "SELECT id, username, is_admin FROM users WHERE id = ?",
            (user_id,),
        ).fetchone()
    finally:
        connection.close()

    if user is None:
        raise HTTPException(status_code=401, detail="User not found")

    return {
        "id": user["id"],
        "username": user["username"],
        "is_admin": bool(user["is_admin"]),
    }


def get_current_admin(
    user: dict = Depends(get_current_user),
):
    if not user["is_admin"]:
        raise HTTPException(
            status_code=403,
            detail="Administrator privileges required",
        )

    return user

@app.get("/admin/status")
def admin_status(user: dict = Depends(get_current_admin)):
    return {
        "status": "ok",
        "message": "Administrator access verified",
        "admin": user["username"],
    }

@app.get("/setup/status")
def setup_status():
    connection = get_connection()
    try:
        admin_exists = connection.execute(
            "SELECT 1 FROM users WHERE is_admin = 1 LIMIT 1"
        ).fetchone() is not None
    finally:
        connection.close()

    return {
        "setup_configured": bool(SETUP_TOKEN),
        "setup_complete": admin_exists,
        "setup_required": bool(SETUP_TOKEN) and not admin_exists,
    }

@app.post("/setup/admin", status_code=201)
def setup_first_admin(request: SetupAdminRequest):
    if not SETUP_TOKEN:
        raise HTTPException(
            status_code=503,
            detail="Administrator setup is not configured",
        )

    if not compare_digest(request.setup_token, SETUP_TOKEN):
        raise HTTPException(
            status_code=403,
            detail="Invalid setup token",
        )

    username = request.username.strip()
    if len(username) < 3:
        raise HTTPException(
            status_code=422,
            detail="Username must contain at least 3 characters",
        )

    hashed_password = password_hash.hash(request.password)
    connection = get_connection()

    try:
        # Serialize simultaneous setup attempts.
        connection.execute("BEGIN IMMEDIATE")

        existing_admin = connection.execute(
            "SELECT id FROM users WHERE is_admin = 1 LIMIT 1"
        ).fetchone()

        if existing_admin is not None:
            connection.rollback()
            raise HTTPException(
                status_code=409,
                detail="Administrator setup is already complete",
            )

        cursor = connection.execute(
            """
            INSERT INTO users (username, password_hash, is_admin)
            VALUES (?, ?, 1)
            """,
            (username, hashed_password),
        )

        connection.commit()

        return {
            "id": cursor.lastrowid,
            "username": username,
            "message": "Administrator created successfully",
        }

    except IntegrityError:
        connection.rollback()
        raise HTTPException(
            status_code=409,
            detail="Username already exists",
        )

    finally:
        connection.close()

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

    connection = get_connection()
    try:
        row = connection.execute(
            "SELECT is_admin FROM users WHERE id = ?",
            (user["id"],),
        ).fetchone()
    finally:
        connection.close()

    return {
        "access_token": token,
        "token_type": "bearer",
        "is_admin": bool(row["is_admin"]) if row else False,
    }



@app.get("/files/storage")
def get_storage_usage(user: dict = Depends(get_current_user)):
    connection = get_connection()
    try:
        user_row = connection.execute(
            """
            SELECT storage_quota_bytes, max_upload_size_bytes
            FROM users
            WHERE id = ?
            """,
            (user["id"],),
        ).fetchone()

        if user_row is None:
            raise HTTPException(status_code=404, detail="User not found")

        usage_row = connection.execute(
            """
            SELECT COALESCE(SUM(size_bytes), 0) AS used_bytes
            FROM files
            WHERE user_id = ?
            """,
            (user["id"],),
        ).fetchone()

        quota_bytes = user_row["storage_quota_bytes"]
        used_bytes = usage_row["used_bytes"]

        return {
            "quota_bytes": quota_bytes,
            "used_bytes": used_bytes,
            "remaining_bytes": max(0, quota_bytes - used_bytes),
            "max_upload_size_bytes": user_row["max_upload_size_bytes"],
            "server_max_upload_size_bytes": MAX_UPLOAD_SIZE_MB * 1024 * 1024,
        }
    finally:
        connection.close()



@app.post("/files/upload", status_code=201)
async def upload_file(
    uploaded_file: UploadFile = File(...),
    user: dict = Depends(get_current_user),
):
    original_filename = Path(uploaded_file.filename or "").name

    if not original_filename:
        await uploaded_file.close()
        raise HTTPException(status_code=400, detail="Filename is required")

    try:
        connection = get_connection()
        try:
            user_row = connection.execute(
                """
                SELECT storage_quota_bytes, max_upload_size_bytes
                FROM users
                WHERE id = ?
                """,
                (user["id"],),
            ).fetchone()

            if user_row is None:
                raise HTTPException(status_code=401, detail="User account not found")

            usage_row = connection.execute(
                """
                SELECT COALESCE(SUM(size_bytes), 0) AS used_bytes
                FROM files
                WHERE user_id = ?
                """,
                (user["id"],),
            ).fetchone()

            quota_bytes = user_row["storage_quota_bytes"]
            user_file_limit = user_row["max_upload_size_bytes"]
            used_bytes = usage_row["used_bytes"]
        finally:
            connection.close()

        remaining_bytes = max(0, quota_bytes - used_bytes)

        if remaining_bytes == 0:
            raise HTTPException(
                status_code=413,
                detail="Your storage quota is full. Delete some files or contact the administrator.",
            )

        server_file_limit = MAX_UPLOAD_SIZE_MB * 1024 * 1024
        effective_limit = min(
            server_file_limit,
            user_file_limit,
            remaining_bytes,
        )

        storage_filename, file_size = await save_file(
            user["id"],
            uploaded_file,
            effective_limit,
        )

        file_path = STORAGE_DIR / str(user["id"]) / storage_filename

        if file_size == 0:
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
            file_path.unlink(missing_ok=True)
            raise
        finally:
            connection.close()

    except ValueError as error:
        if "upload limit" in str(error).lower():
            raise HTTPException(
                status_code=413,
                detail=(
                    "File exceeds your per-file upload limit "
                    "or your remaining storage quota."
                ),
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


@app.post("/files/{file_id}/download-link")
def create_download_link(
    file_id: int,
    user: dict = Depends(get_current_user),
):
    connection = get_connection()

    try:
        row = connection.execute(
            """
            SELECT id
            FROM files
            WHERE id = ? AND user_id = ?
            """,
            (file_id, user["id"]),
        ).fetchone()
    finally:
        connection.close()

    if row is None:
        raise HTTPException(status_code=404, detail="File not found")

    expires_at = datetime.now(timezone.utc) + timedelta(minutes=2)

    token = jwt.encode(
        {
            "sub": str(user["id"]),
            "file_id": file_id,
            "purpose": "download",
            "exp": expires_at,
        },
        SECRET_KEY,
        algorithm="HS256",
    )

    return {
        "download_url": f"/files/{file_id}/download-direct?token={token}"
    }


@app.get("/files/{file_id}/download-direct")
def download_file_direct(file_id: int, token: str):
    try:
        payload = jwt.decode(
            token,
            SECRET_KEY,
            algorithms=["HS256"],
        )

        if (
            payload.get("purpose") != "download"
            or int(payload["file_id"]) != file_id
        ):
            raise HTTPException(
                status_code=401,
                detail="Invalid download link",
            )

        user_id = int(payload["sub"])

    except (jwt.InvalidTokenError, KeyError, ValueError) as error:
        print(f"Download token validation failed: {type(error).__name__}: {error}")
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired download link",
        )

    connection = get_connection()

    try:
        row = connection.execute(
            """
            SELECT original_filename, storage_filename
            FROM files
            WHERE id = ? AND user_id = ?
            """,
            (file_id, user_id),
        ).fetchone()
    finally:
        connection.close()

    if row is None:
        raise HTTPException(status_code=404, detail="File not found")

    file_path = STORAGE_DIR / str(user_id) / row["storage_filename"]

    if not file_path.is_file():
        raise HTTPException(
            status_code=404,
            detail="File missing from storage",
        )

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


@app.get("/admin/users")
def list_users(admin: dict = Depends(get_current_admin)):
    connection = get_connection()
    try:
        rows = connection.execute(
            """
            SELECT
                u.id,
                u.username,
                u.created_at,
                u.is_admin,
                u.storage_quota_bytes,
                u.max_upload_size_bytes,
                COUNT(f.id) AS file_count,
                COALESCE(SUM(f.size_bytes), 0) AS storage_used_bytes
            FROM users AS u
            LEFT JOIN files AS f ON f.user_id = u.id
            GROUP BY u.id
            ORDER BY u.id
            """
        ).fetchall()

        return [dict(row) for row in rows]
    finally:
        connection.close()


class UpdateUserLimitsRequest(BaseModel):
    storage_quota_bytes: int | None = Field(default=None, gt=0)
    max_upload_size_bytes: int | None = Field(default=None, gt=0)


@app.patch("/admin/users/{user_id}/limits")
def update_user_limits(
    user_id: int,
    request: UpdateUserLimitsRequest,
    admin: dict = Depends(get_current_admin),
):
    if (
        request.storage_quota_bytes is None
        and request.max_upload_size_bytes is None
    ):
        raise HTTPException(
            status_code=400,
            detail="Provide at least one storage limit to update",
        )

    connection = get_connection()
    try:
        user_row = connection.execute(
            "SELECT id FROM users WHERE id = ?",
            (user_id,),
        ).fetchone()

        if user_row is None:
            raise HTTPException(status_code=404, detail="User not found")

        updates = []
        values = []

        if request.storage_quota_bytes is not None:
            updates.append("storage_quota_bytes = ?")
            values.append(request.storage_quota_bytes)

        if request.max_upload_size_bytes is not None:
            updates.append("max_upload_size_bytes = ?")
            values.append(request.max_upload_size_bytes)

        values.append(user_id)

        connection.execute(
            f"UPDATE users SET {', '.join(updates)} WHERE id = ?",
            values,
        )
        connection.commit()

        updated_user = connection.execute(
            """
            SELECT username, storage_quota_bytes, max_upload_size_bytes
            FROM users
            WHERE id = ?
            """,
            (user_id,),
        ).fetchone()

        return {
            "username": updated_user["username"],
            "storage_quota_bytes": updated_user["storage_quota_bytes"],
            "max_upload_size_bytes": updated_user["max_upload_size_bytes"],
            "message": "User limits updated successfully",
        }
    finally:
        connection.close()


FRONTEND_DIR = Path(__file__).resolve().parents[2] / "frontend"
app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")
