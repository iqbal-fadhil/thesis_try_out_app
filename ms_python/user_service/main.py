from typing import Optional, List

import asyncpg
import httpx
from fastapi import FastAPI, HTTPException, Query, Path, status
from pydantic import BaseModel

# ---------------- CONFIG ----------------

DB_HOST = "127.0.0.1"
DB_PORT = 5432
DB_USER = "ms_python_user"                # adjust if needed
DB_PASSWORD = "yourStrongPassword123"   # adjust if needed
DB_NAME = "user_python_service_db"

AUTH_BASE_URL = "http://127.0.0.1:8013"  # or "http://157.15.125.7:8013"

POOL: Optional[asyncpg.pool.Pool] = None

app = FastAPI(title="Python FastAPI User Service")


# ---------------- MODELS ----------------

class HealthResponse(BaseModel):
    status: str


class ErrorResponse(BaseModel):
    error: str
    details: Optional[str] = None


class UserProfile(BaseModel):
    username: str
    email: Optional[str]
    full_name: Optional[str]
    score: int


class AuthMeResponse(BaseModel):
    username: str
    email: Optional[str]
    first_name: Optional[str]
    last_name: Optional[str]
    is_staff: bool


class ScoreUpdateRequest(BaseModel):
    score_increment: int


class ScoreUpdateResponse(BaseModel):
    username: str
    new_score: int
    increment: int


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


async def get_pool() -> asyncpg.pool.Pool:
    if POOL is None:
        raise RuntimeError("DB pool not initialized")
    return POOL


# ---------------- HELPERS ----------------

async def get_auth_user_from_token(token: str) -> Optional[AuthMeResponse]:
    """
    Call Auth Service /api/auth/me?token=...
    Return AuthMeResponse or None if invalid.
    """
    if not token:
        return None

    url = f"{AUTH_BASE_URL}/api/auth/me"
    params = {"token": token}

    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            resp = await client.get(url, params=params)
    except Exception:
        return None

    if resp.status_code != 200:
        return None

    try:
        data = resp.json()
    except Exception:
        return None

    if isinstance(data, dict) and data.get("error") is not None:
        return None

    try:
        return AuthMeResponse(**data)
    except Exception:
        return None


# ---------------- ROUTES ----------------

# GET /healthz (no DB)
@app.get("/healthz", response_model=HealthResponse)
async def healthz():
    return HealthResponse(status="ok")


# GET /users?token=...  (staff only)
@app.get("/users", response_model=List[UserProfile])
async def get_all_users(token: str = Query(..., description="Auth token")):
    auth_user = await get_auth_user_from_token(token)
    if auth_user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        )

    if not auth_user.is_staff:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: staff only",
        )

    pool = await get_pool()
    async with pool.acquire() as conn:
        try:
            rows = await conn.fetch(
                "SELECT username, email, full_name, score "
                "FROM user_profiles ORDER BY id ASC"
            )
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Query failed: {e}",
            )

    users = [
        UserProfile(
            username=row["username"],
            email=row["email"],
            full_name=row["full_name"],
            score=int(row["score"]),
        )
        for row in rows
    ]
    return users


# GET /users/{username} (public)
@app.get("/users/{username}", response_model=UserProfile)
async def get_user_by_username(username: str = Path(...)):
    pool = await get_pool()
    async with pool.acquire() as conn:
        try:
            row = await conn.fetchrow(
                "SELECT username, email, full_name, score "
                "FROM user_profiles WHERE username = $1 LIMIT 1",
                username,
            )
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Query failed: {e}",
            )

    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    return UserProfile(
        username=row["username"],
        email=row["email"],
        full_name=row["full_name"],
        score=int(row["score"]),
    )


# POST /users/{username}/score?token=... (self only)
@app.post("/users/{username}/score", response_model=ScoreUpdateResponse)
async def update_score(
    username: str = Path(...),
    token: str = Query(..., description="Auth token"),
    payload: ScoreUpdateRequest = ...,
):
    if payload.score_increment == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="score_increment must be non-zero",
        )

    auth_user = await get_auth_user_from_token(token)
    if auth_user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        )

    if auth_user.username != username:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: can only update own score",
        )

    pool = await get_pool()
    async with pool.acquire() as conn:
        tr = conn.transaction()
        await tr.start()

        try:
            row = await conn.fetchrow(
                "SELECT score FROM user_profiles WHERE username = $1 FOR UPDATE",
                username,
            )

            if row is None:
                new_score = payload.score_increment
                await conn.execute(
                    "INSERT INTO user_profiles (username, score) VALUES ($1, $2)",
                    username,
                    new_score,
                )
            else:
                current = int(row["score"])
                new_score = current + payload.score_increment
                await conn.execute(
                    "UPDATE user_profiles SET score = $1 WHERE username = $2",
                    new_score,
                    username,
                )

            await tr.commit()
        except Exception as e:
            await tr.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Update failed: {e}",
            )

    return ScoreUpdateResponse(
        username=username,
        new_score=new_score,
        increment=payload.score_increment,
    )
