# main.py (MySQL Version)
from typing import List, Optional, Dict, Any
from fastapi.middleware.cors import CORSMiddleware
import aiomysql
import httpx
from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel


# ---------------- CONFIG ----------------

DB_HOST = "127.0.0.1"
DB_PORT = 3306
DB_USER = "ms_python_user"
DB_PASSWORD = "yourStrongPassword123"
DB_NAME = "test_python_service_db"

AUTH_BASE_URL = "http://127.0.0.1:8003"     # your auth service


POOL: Optional[aiomysql.Pool] = None
app = FastAPI(title="Python FastAPI Test Service (MySQL)")


# ---------------- CORS ----------------

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
    allow_methods=["*"],
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


class AnswerInput(BaseModel):
    question_id: int
    selected_option: str


class SubmitRequest(BaseModel):
    answers: List[AnswerInput]


# ---------------- DB POOL ----------------

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
        autocommit=False,     # we control commit/rollback
    )
    print("MySQL pool created.")


@app.on_event("shutdown")
async def shutdown():
    global POOL
    if POOL:
        POOL.close()
        await POOL.wait_closed()


async def get_pool():
    if POOL is None:
        raise RuntimeError("MySQL pool not initialized")
    return POOL


# ---------------- HELPER: CALL AUTH SERVICE ----------------

async def get_auth_user_from_token(token: str) -> Optional[AuthMeResponse]:
    if not token:
        return None

    url = f"{AUTH_BASE_URL}/api/auth/me"
    try:
        async with httpx.AsyncClient(timeout=3) as client:
            resp = await client.get(url, params={"token": token})
    except Exception:
        return None

    if resp.status_code != 200:
        return None

    data = resp.json()
    if "error" in data:
        return None

    try:
        return AuthMeResponse(**data)
    except Exception:
        return None


# ---------------- ROUTES ----------------

@app.get("/health", response_model=HealthResponse)
async def health():
    return HealthResponse(status="ok")


# GET /questions
@app.get("/questions", response_model=List[Question])
async def get_questions():
    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor(aiomysql.DictCursor) as cur:
            await cur.execute("""
                SELECT id, question_text, option_a, option_b, option_c, option_d
                FROM questions ORDER BY id ASC
            """)
            rows = await cur.fetchall()

    return [Question(**r) for r in rows]


# POST /submit?token=...
@app.post("/submit")
async def submit(payload: SubmitRequest, token: str = Query(...)):
    if not payload.answers:
        raise HTTPException(400, "answers must be a non-empty array")

    auth_user = await get_auth_user_from_token(token)
    if not auth_user:
        raise HTTPException(401, "Invalid token")

    username = auth_user.username

    # collect question_ids
    question_ids = list({a.question_id for a in payload.answers})
    if not question_ids:
        raise HTTPException(400, "No valid question_id")

    # fetch answers
    pool = await get_pool()
    qmap: Dict[int, Dict[str, Any]] = {}

    async with pool.acquire() as conn:
        async with conn.cursor(aiomysql.DictCursor) as cur:
            # dynamic placeholders (%s, %s, ...)
            qs = ",".join(["%s"] * len(question_ids))
            await cur.execute(
                f"SELECT id, question_text, correct_option FROM questions WHERE id IN ({qs})",
                tuple(question_ids)
            )
            rows = await cur.fetchall()

    for r in rows:
        qmap[r["id"]] = {
            "correct_option": (r["correct_option"] or "").upper(),
            "question_text": r["question_text"],
        }

    total_questions = 0
    correct_answers = 0
    details = []

    for ans in payload.answers:
        qid = ans.question_id
        sel = ans.selected_option.strip().upper()

        if qid not in qmap:
            correct_opt = None
            is_correct = False
            qtext = None
        else:
            correct_opt = qmap[qid]["correct_option"]
            qtext = qmap[qid]["question_text"]
            is_correct = (sel == correct_opt)

        total_questions += 1
        if is_correct:
            correct_answers += 1

        details.append({
            "question_id": qid,
            "question_text": qtext,
            "selected_option": sel,
            "is_correct": is_correct,
            "correct_option": correct_opt,
        })

    # save submission
    submission_id = None

    async with pool.acquire() as conn:
        try:
            async with conn.cursor() as cur:
                # insert submission
                await cur.execute(
                    """INSERT INTO submissions (username, total_questions, correct_answers)
                       VALUES (%s, %s, %s)""",
                    (username, total_questions, correct_answers)
                )
                submission_id = cur.lastrowid

                # insert answers
                for d in details:
                    await cur.execute(
                        """INSERT INTO submission_answers
                           (submission_id, question_id, selected_option, is_correct)
                           VALUES (%s, %s, %s, %s)""",
                        (
                            submission_id,
                            d["question_id"],
                            d["selected_option"],
                            1 if d["is_correct"] else 0,
                        )
                    )

                await conn.commit()

        except Exception as e:
            await conn.rollback()
            print("DB Error:", e)
            # return score even if save failed

    # compute percent
    score_percent = int(round(correct_answers / total_questions * 100)) if total_questions else 0

    return {
        "status": "success",
        "username": username,
        "submission_id": submission_id,
        "total_questions": total_questions,
        "correct_answers": correct_answers,
        "score_percent": score_percent,
        "score": score_percent,
        "total_score": score_percent,
        "details": details,
    }


# GET /submissions/latest
@app.get("/submissions/latest")
async def latest(token: str = Query(...)):
    auth_user = await get_auth_user_from_token(token)
    if not auth_user:
        raise HTTPException(401, "Invalid token")

    username = auth_user.username
    pool = await get_pool()

    async with pool.acquire() as conn:
        async with conn.cursor(aiomysql.DictCursor) as cur:
            await cur.execute(
                """SELECT id, username, total_questions, correct_answers, created_at
                   FROM submissions WHERE username=%s ORDER BY id DESC LIMIT 1""",
                (username,)
            )
            row = await cur.fetchone()

            if not row:
                return {"status": "ok", "submission": None}

            submission_id = row["id"]
            total_q = row["total_questions"]
            correct = row["correct_answers"]
            score_percent = int(round(correct / total_q * 100)) if total_q else 0

            # answers
            await cur.execute(
                """SELECT question_id, selected_option, is_correct
                   FROM submission_answers WHERE submission_id=%s ORDER BY id ASC""",
                (submission_id,)
            )
            ans_rows = await cur.fetchall()

            answers = [
                {
                    "question_id": r["question_id"],
                    "selected_option": r["selected_option"],
                    "is_correct": bool(r["is_correct"]),
                }
                for r in ans_rows
            ]

    return {
        "status": "ok",
        "submission": {
            "submission_id": submission_id,
            "username": username,
            "total_questions": total_q,
            "correct_answers": correct,
            "score_percent": score_percent,
            "score": score_percent,
            "created_at": str(row["created_at"]) if row["created_at"] else None,
            "answers": answers,
        }
    }


# ---------------- 404 ----------------

@app.get("/{path:path}")
async def fallback(path: str):
    raise HTTPException(404, "Not Found")
