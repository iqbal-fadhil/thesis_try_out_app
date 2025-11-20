from typing import List, Optional

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

AUTH_BASE_URL = "http://127.0.0.1:8013"  # atau "http://157.15.125.7:8013"

POOL: Optional[asyncpg.pool.Pool] = None

app = FastAPI(title="Python FastAPI Test Service")


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


class SubmitResponse(BaseModel):
    username: str
    submission_id: int
    total_questions: int
    correct_answers: int
    answers: List[AnswerResult]


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
@app.post("/submit", response_model=SubmitResponse)
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
                SELECT id, correct_option
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

        questions_map = {
            row["id"]: (row["correct_option"] or "").strip().upper()
            for row in rows
        }

        if not questions_map:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No matching questions found for provided IDs",
            )

        total_questions = 0
        correct_answers = 0
        answers_result: List[AnswerResult] = []

        for ans in payload.answers:
            qid = ans.question_id
            sel = (ans.selected_option or "").strip().upper()

            correct_opt = questions_map.get(qid)
            if correct_opt is None:
                is_correct = False
                correct_opt_out = None
            else:
                is_correct = sel == correct_opt
                correct_opt_out = correct_opt

            total_questions += 1
            if is_correct:
                correct_answers += 1

            answers_result.append(
                AnswerResult(
                    question_id=qid,
                    selected_option=sel,
                    is_correct=is_correct,
                    correct_option=correct_opt_out,
                )
            )

        # Simpan ke submissions & submission_answers dalam transaction
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
                    ar.question_id,
                    ar.selected_option,
                    ar.is_correct,
                )

            await tr.commit()
        except Exception as e:
            await tr.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Submission save failed: {e}",
            )

    return SubmitResponse(
        username=username,
        submission_id=submission_id,
        total_questions=total_questions,
        correct_answers=correct_answers,
        answers=answers_result,
    )
