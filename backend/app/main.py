from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from sqlite3 import IntegrityError

from app.config import APP_NAME, APP_VERSION
from app.database import initialize_database
from app.auth import register_user

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
