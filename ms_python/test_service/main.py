# main.py (modified)
from typing import List, Optional, Dict, Any
from fastapi.middleware.cors import CORSMiddleware
import asyncpg
import httpx
from fastapi import FastAPI, HTTPException, Query, status
from pydantic import BaseModel

# ---------------- CONFIG ----------------

DB_HOST = "127.0.0.1"
DB_PORT = 5432
DB_USER = "ms_python_user"              # sesuaikan
DB_PASSWORD = "yourStrongPassword123"  # sesuaikan
DB_NAME = "test_python_service_db"

AUTH_BASE_URL = "http://127.0.0.1:8003"  # sesuaikan ke service auth Anda

POOL: Optional[asyncpg.pool.Pool] = None

app = FastAPI(title="Python FastAPI Test Service")

# allowed origins (explicit)
FRONTEND_ORIGINS = [
    "https://microservices.iqbalfadhil.biz.id",
    "https://auth-microservices.iqbalfadhil.biz.id",
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=FRONTEND_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS", "PUT", "DELETE"],
    allow_headers=["*"],
)

# ---------------- MODELS ----------------

class HealthResponse(BaseModel):
    status: str


class Question(BaseModel):
    id: int
    question_text: str
    option_a: str
    option_b: str
    option_c: str
    option_d: str


class AuthMeResponse(BaseModel):
    username: str
    email: Optional[str]
    first_name: Optional[str]
    last_name: Optional[str]
    is_staff: bool


class CreateQuestionRequest(BaseModel):
    question_text: str
    option_a: str
    option_b: str
    option_c: str
    option_d: str
    correct_option: str  # A/B/C/D


class CreateQuestionResponse(BaseModel):
    message: str
    id: int


class AnswerInput(BaseModel):
    question_id: int
    selected_option: str


class SubmitRequest(BaseModel):
    answers: List[AnswerInput]


class AnswerResult(BaseModel):
    question_id: int
    selected_option: str
    is_correct: bool
    correct_option: Optional[str]


# NOTE: We will return dicts for submit and latest endpoints so we can include
# score_percent without changing many models.


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
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            resp = await client.get(url, params={"token": token})
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

# GET /health
@app.get("/health", response_model=HealthResponse)
async def health():
    return HealthResponse(status="ok")


# GET /questions
@app.get("/questions", response_model=List[Question])
async def get_questions():
    pool = await get_pool()
    async with pool.acquire() as conn:
        try:
            rows = await conn.fetch(
                """
                SELECT id, question_text, option_a, option_b, option_c, option_d
                FROM questions
                ORDER BY id ASC
                """
            )
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Query failed: {e}",
            )

    return [
        Question(
            id=row["id"],
            question_text=row["question_text"],
            option_a=row["option_a"],
            option_b=row["option_b"],
            option_c=row["option_c"],
            option_d=row["option_d"],
        )
        for row in rows
    ]


# POST /questions?token=...  (staff only)
@app.post("/questions", response_model=CreateQuestionResponse)
async def create_question(
    payload: CreateQuestionRequest,
    token: str = Query(..., description="Auth token (staff only)"),
):
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

    # Validate question & options
    if (
        not payload.question_text.strip()
        or not payload.option_a.strip()
        or not payload.option_b.strip()
        or not payload.option_c.strip()
        or not payload.option_d.strip()
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="All options and question_text are required",
        )

    correct_opt = payload.correct_option.strip().upper()
    if correct_opt not in {"A", "B", "C", "D"}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="correct_option must be one of A, B, C, D",
        )

    pool = await get_pool()
    async with pool.acquire() as conn:
        try:
            row = await conn.fetchrow(
                """
                INSERT INTO questions
                (question_text, option_a, option_b, option_c, option_d, correct_option)
                VALUES ($1, $2, $3, $4, $5, $6)
                RETURNING id
                """,
                payload.question_text,
                payload.option_a,
                payload.option_b,
                payload.option_c,
                payload.option_d,
                correct_opt,
            )
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Insert failed: {e}",
            )

    new_id = row["id"]
    return CreateQuestionResponse(message="Question created", id=new_id)


# POST /submit?token=...
@app.post("/submit")
async def submit(
    payload: SubmitRequest,
    token: str = Query(..., description="Auth token"),
):
    if not payload.answers:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="answers must be a non-empty array",
        )

    auth_user = await get_auth_user_from_token(token)
    if auth_user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        )

    username = auth_user.username

    # Kumpulkan question_id unik
    question_ids = list({ans.question_id for ans in payload.answers})
    if not question_ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No valid question_id provided",
        )

    pool = await get_pool()
    async with pool.acquire() as conn:
        # Ambil correct_option
        try:
            rows = await conn.fetch(
                """
                SELECT id, correct_option, question_text
                FROM questions
                WHERE id = ANY($1::int[])
                """,
                question_ids,
            )
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Question lookup failed: {e}",
            )

        questions_map: Dict[int, Dict[str, Any]] = {
            row["id"]: {
                "correct_option": (row["correct_option"] or "").strip().upper(),
                "question_text": row["question_text"],
            }
            for row in rows
        }

        if not questions_map:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No matching questions found for provided IDs",
            )

        total_questions = 0
        correct_answers = 0
        answers_result: List[Dict[str, Any]] = []

        for ans in payload.answers:
            qid = ans.question_id
            sel = (ans.selected_option or "").strip().upper()

            qdata = questions_map.get(qid)
            if not qdata:
                is_correct = False
                correct_opt_out = None
                qtext = None
            else:
                correct_opt_out = qdata["correct_option"]
                qtext = qdata.get("question_text")
                is_correct = sel == correct_opt_out

            total_questions += 1
            if is_correct:
                correct_answers += 1

            answers_result.append({
                "question_id": qid,
                "question_text": qtext,
                "selected_option": sel,
                "is_correct": is_correct,
                "correct_option": correct_opt_out,
            })

        # Simpan ke submissions & submission_answers dalam transaction
        submission_id = None
        tr = conn.transaction()
        await tr.start()
        try:
            row = await conn.fetchrow(
                """
                INSERT INTO submissions (username, total_questions, correct_answers)
                VALUES ($1, $2, $3)
                RETURNING id
                """,
                username,
                total_questions,
                correct_answers,
            )
            submission_id = row["id"]

            for ar in answers_result:
                await conn.execute(
                    """
                    INSERT INTO submission_answers
                    (submission_id, question_id, selected_option, is_correct)
                    VALUES ($1, $2, $3, $4)
                    """,
                    submission_id,
                    ar["question_id"],
                    ar["selected_option"],
                    1 if ar["is_correct"] else 0,
                )

            await tr.commit()
        except Exception as e:
            await tr.rollback()
            # log error but do not send 500 for client — still return computed result
            # This avoids frontend failing if DB insert partially fails.
            # You may want to log to a file/monitoring system in production.
            print("Submission save failed:", e)
            submission_id = submission_id  # may be None

    # compute score percent
    if total_questions > 0:
        score_percent = int(round((correct_answers / total_questions) * 100))
    else:
        score_percent = 0

    # Reliable response for frontend (many aliases so frontend can read)
    return {
        "status": "success",
        "username": username,
        "submission_id": submission_id,
        "total_questions": total_questions,
        "correct_answers": correct_answers,
        "score_percent": score_percent,
        "score": score_percent,
        "total_score": score_percent,
        "details": answers_result,
    }


# GET /submissions/latest?token=...
@app.get("/submissions/latest")
async def get_latest_submission(token: str = Query(..., description="Auth token")):
    auth_user = await get_auth_user_from_token(token)
    if auth_user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    username = auth_user.username
    pool = await get_pool()
    async with pool.acquire() as conn:
        try:
            row = await conn.fetchrow(
                """
                SELECT id, username, total_questions, correct_answers, created_at
                FROM submissions
                WHERE username = $1
                ORDER BY id DESC
                LIMIT 1
                """,
                username,
            )
        except Exception as e:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Query failed: {e}")

        if row is None:
            return {"status": "ok", "submission": None}

        submission_id = row["id"]
        total_q = row["total_questions"] or 0
        correct = row["correct_answers"] or 0
        score_percent = int(round((correct / total_q) * 100)) if total_q > 0 else 0

        # get submission answers (optional but useful)
        try:
            ans_rows = await conn.fetch(
                """
                SELECT question_id, selected_option, is_correct
                FROM submission_answers
                WHERE submission_id = $1
                ORDER BY id ASC
                """,
                submission_id,
            )
            answers = [
                {
                    "question_id": r["question_id"],
                    "selected_option": r["selected_option"],
                    "is_correct": bool(r["is_correct"]),
                }
                for r in ans_rows
            ]
        except Exception:
            answers = []

        return {
            "status": "ok",
            "submission": {
                "submission_id": submission_id,
                "username": row["username"],
                "total_questions": total_q,
                "correct_answers": correct,
                "score_percent": score_percent,
                "score": score_percent,
                "created_at": row["created_at"].isoformat() if row["created_at"] else None,
                "answers": answers,
            }
        }

# Fallback 404
@app.get("/{full_path:path}")
async def fallback(full_path: str):
    raise HTTPException(status_code=404, detail="Not Found")
