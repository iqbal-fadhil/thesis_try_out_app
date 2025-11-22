# auth_main_mysql.py
import uuid
from typing import Optional

import aiomysql
import bcrypt
import httpx
from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware

# ---------------- CONFIG ----------------
DB_HOST = "127.0.0.1"
DB_PORT = 3306
DB_USER = "ms_python_user"                 # sesuaikan
DB_PASSWORD = "yourStrongPassword123"      # sesuaikan
DB_NAME = "auth_python_service_db"

POOL: Optional[aiomysql.Pool] = None

app = FastAPI(title="Python FastAPI Auth Service (MySQL)")

# allowed origins — use explicit origin(s)
FRONTEND_ORIGINS = [
    "https://microservices.iqbalfadhil.biz.id",
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=FRONTEND_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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
    POOL = await aiomysql.create_pool(
        host=DB_HOST,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASSWORD,
        db=DB_NAME,
        minsize=1,
        maxsize=10,
        autocommit=False,
    )
    print("MySQL pool created for auth service.")


@app.on_event("shutdown")
async def shutdown():
    global POOL
    if POOL:
        POOL.close()
        await POOL.wait_closed()


async def get_pool():
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

# GET /healthz
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

    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor(aiomysql.DictCursor) as cur:
            # check uniqueness
            await cur.execute("SELECT 1 FROM users WHERE username=%s OR email=%s LIMIT 1",
                              (payload.username, payload.email))
            if await cur.fetchone():
                raise HTTPException(status_code=409, detail="Username or email already exists")

            hashed_pw = hash_password(payload.password)
            try:
                await cur.execute(
                    """
                    INSERT INTO users (username, password, email, first_name, last_name, is_staff)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    """,
                    (
                        payload.username,
                        hashed_pw,
                        payload.email,
                        payload.first_name,
                        payload.last_name,
                        1 if payload.is_staff else 0,
                    ),
                )
                await conn.commit()
            except Exception as e:
                await conn.rollback()
                raise HTTPException(status_code=500, detail=f"Insert failed: {e}")

    return {"message": "User Registered"}


# POST /api/auth/login
@app.post("/api/auth/login", response_model=LoginResponse)
async def login(payload: LoginRequest):
    if not payload.username or not payload.password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="username and password are required",
        )

    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor(aiomysql.DictCursor) as cur:
            await cur.execute(
                """
                SELECT username, password, email, first_name, last_name, is_staff
                FROM users
                WHERE LOWER(username)=LOWER(%s) OR LOWER(email)=LOWER(%s)
                LIMIT 1
                """,
                (payload.username, payload.username),
            )
            row = await cur.fetchone()

    if row is None:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    stored_hash = row["password"]
    if not verify_password(payload.password, stored_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = generate_token()
    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            try:
                await cur.execute("INSERT INTO tokens (token, username) VALUES (%s, %s)",
                                  (token, row["username"]))
                await conn.commit()
            except Exception as e:
                await conn.rollback()
                raise HTTPException(status_code=500, detail=f"Token insert failed: {e}")

    return LoginResponse(token=token, is_staff=bool(row["is_staff"]))


# GET /api/auth/validate?token=...
@app.get("/api/auth/validate", response_model=ValidResponse)
async def validate_token(token: str):
    if not token:
        raise HTTPException(status_code=400, detail="Token missing")

    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute("SELECT 1 FROM tokens WHERE token=%s LIMIT 1", (token,))
            found = await cur.fetchone()

    return ValidResponse(valid=found is not None)


# GET /api/auth/me?token=...
@app.get("/api/auth/me", response_model=MeResponse)
async def get_me(token: str):
    if not token:
        raise HTTPException(status_code=400, detail="Token missing")

    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor(aiomysql.DictCursor) as cur:
            await cur.execute(
                """
                SELECT u.username, u.email, u.first_name, u.last_name, u.is_staff
                FROM users u
                JOIN tokens t ON t.username = u.username
                WHERE t.token = %s
                LIMIT 1
                """,
                (token,),
            )
            row = await cur.fetchone()

    if row is None:
        raise HTTPException(status_code=401, detail="Invalid token")

    return MeResponse(
        username=row["username"],
        email=row["email"],
        first_name=row["first_name"],
        last_name=row["last_name"],
        is_staff=bool(row["is_staff"]),
    )
