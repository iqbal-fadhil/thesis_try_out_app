import uuid
from typing import Optional

import asyncpg
import bcrypt
from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware

# ---------------- CONFIG ----------------

DB_HOST = "127.0.0.1"
DB_PORT = 5432
DB_USER = "ms_python_user"                 # change if needed
DB_PASSWORD = "yourStrongPassword123"  # change if needed
DB_NAME = "auth_python_service_db"

POOL: Optional[asyncpg.pool.Pool] = None

app = FastAPI(title="Python FastAPI Auth Service")



# allowed origins — use explicit origin(s), not '*' for production if you use credentials
FRONTEND_ORIGINS = [
    "https://microservices.iqbalfadhil.biz.id",
    # add local dev urls if needed:
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]

app = FastAPI(title="Python FastAPI Auth Service")

# Add this block immediately after app = FastAPI(...)
app.add_middleware(
    CORSMiddleware,
    allow_origins=FRONTEND_ORIGINS,   # exact origins
    allow_credentials=True,           # True if you use cookies or Authorization header with credentials
    allow_methods=["*"],              # allow POST, GET, OPTIONS, etc.
    allow_headers=["*"],              # allow Content-Type, Authorization, X-Whatever
)

# ---------------- MODELS ----------------

class RegisterRequest(BaseModel):
    username: str
    password: str
    email: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    is_staff: Optional[bool] = False


class LoginRequest(BaseModel):
    username: str   # username OR email
    password: str


class LoginResponse(BaseModel):
    token: str
    is_staff: bool


class HealthResponse(BaseModel):
    status: str


class ValidResponse(BaseModel):
    valid: bool


class MeResponse(BaseModel):
    username: str
    email: Optional[str]
    first_name: Optional[str]
    last_name: Optional[str]
    is_staff: bool


# ---------------- DB LIFECYCLE ----------------

@app.on_event("startup")
async def startup():
    global POOL
    POOL = await asyncpg.create_pool(
        host=DB_HOST,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME,
        min_size=1,
        max_size=10,
    )


@app.on_event("shutdown")
async def shutdown():
    global POOL
    if POOL is not None:
        await POOL.close()
        POOL = None


async def get_conn():
    if POOL is None:
        raise RuntimeError("DB pool not initialized")
    return POOL


# ---------------- HELPERS ----------------

def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))
    except Exception:
        return False


def generate_token() -> str:
    return uuid.uuid4().hex


# ---------------- ROUTES ----------------

# GET /healthz (no DB)
@app.get("/healthz", response_model=HealthResponse)
async def healthz():
    return HealthResponse(status="ok")


# POST /api/auth/register
@app.post("/api/auth/register")
async def register(payload: RegisterRequest):
    if not payload.username or not payload.password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="username and password are required",
        )

    conn_pool = await get_conn()
    async with conn_pool.acquire() as conn:
        hashed_pw = hash_password(payload.password)
        query = """
            INSERT INTO users (username, password, email, first_name, last_name, is_staff)
            VALUES ($1, $2, $3, $4, $5, $6)
        """
        try:
            await conn.execute(
                query,
                payload.username,
                hashed_pw,
                payload.email,
                payload.first_name,
                payload.last_name,
                bool(payload.is_staff),
            )
        except Exception as e:
            # You can print for debugging if needed:
            # print("Insert failed:", repr(e))
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Insert failed: {e}",
            )

    return {"message": "User Registered"}


# POST /api/auth/login
@app.post("/api/auth/login", response_model=LoginResponse)
async def login(payload: LoginRequest):
    if not payload.username or not payload.password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="username and password are required",
        )

    conn_pool = await get_conn()
    async with conn_pool.acquire() as conn:
        query = """
            SELECT username, password, email, first_name, last_name, is_staff
            FROM users
            WHERE LOWER(username) = LOWER($1) OR LOWER(email) = LOWER($1)
            LIMIT 1
        """
        row = await conn.fetchrow(query, payload.username)
        if row is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials",
            )

        stored_hash = row["password"]
        if not verify_password(payload.password, stored_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials",
            )

        token = generate_token()
        await conn.execute(
            "INSERT INTO tokens (token, username) VALUES ($1, $2)",
            token,
            row["username"],
        )

        return LoginResponse(token=token, is_staff=bool(row["is_staff"]))


# GET /api/auth/validate?token=...
@app.get("/api/auth/validate", response_model=ValidResponse)
async def validate_token(token: str):
    if not token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Token missing",
        )

    conn_pool = await get_conn()
    async with conn_pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT 1 FROM tokens WHERE token = $1 LIMIT 1",
            token,
        )

    return ValidResponse(valid=row is not None)


# GET /api/auth/me?token=...
@app.get("/api/auth/me", response_model=MeResponse)
async def get_me(token: str):
    if not token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Token missing",
        )

    conn_pool = await get_conn()
    async with conn_pool.acquire() as conn:
        query = """
            SELECT u.username, u.email, u.first_name, u.last_name, u.is_staff
            FROM users u
            JOIN tokens t ON t.username = u.username
            WHERE t.token = $1
            LIMIT 1
        """
        row = await conn.fetchrow(query, token)

        if row is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token",
            )

        return MeResponse(
            username=row["username"],
            email=row["email"],
            first_name=row["first_name"],
            last_name=row["last_name"],
            is_staff=bool(row["is_staff"]),
        )
