import asyncio
import asyncpg

# ---------------- CONFIG - update if needed ----------------
DB_HOST = "127.0.0.1"
DB_PORT = 5432
DB_USER = "ms_python_user"
DB_PASSWORD = "yourStrongPassword123"
DB_NAME = "test_python_service_db"

# uploaded Postman collection path (for reference)
POSTMAN_COLLECTION_PATH = "/mnt/data/Test Service API - 157.15.125.7-8005.postman_collection.json"

# ---------------- MIGRATION SQL ----------------
CREATE_QUESTIONS = """
CREATE TABLE IF NOT EXISTS questions (
    id SERIAL PRIMARY KEY,
    question_text TEXT NOT NULL,
    option_a TEXT NOT NULL,
    option_b TEXT NOT NULL,
    option_c TEXT NOT NULL,
    option_d TEXT NOT NULL,
    correct_option CHAR(1) NOT NULL CHECK (correct_option IN ('A','B','C','D')),
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW()
);
"""

CREATE_SUBMISSIONS = """
CREATE TABLE IF NOT EXISTS submissions (
    id SERIAL PRIMARY KEY,
    username VARCHAR(200) NOT NULL,
    total_questions INTEGER NOT NULL DEFAULT 0,
    correct_answers INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW()
);
"""

CREATE_SUBMISSION_ANSWERS = """
CREATE TABLE IF NOT EXISTS submission_answers (
    id SERIAL PRIMARY KEY,
    submission_id INTEGER NOT NULL,
    question_id INTEGER NOT NULL,
    selected_option CHAR(1) NOT NULL,
    is_correct BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW(),
    CONSTRAINT fk_sa_submission FOREIGN KEY (submission_id) REFERENCES submissions(id) ON DELETE CASCADE,
    CONSTRAINT fk_sa_question FOREIGN KEY (question_id) REFERENCES questions(id) ON DELETE CASCADE,
    CONSTRAINT ck_selected_option CHECK (selected_option IN ('A','B','C','D'))
);
"""

async def migrate():
    print("Connecting to Postgres...")
    conn = await asyncpg.connect(
        host=DB_HOST, port=DB_PORT, user=DB_USER, password=DB_PASSWORD, database=DB_NAME
    )
    try:
        print("Ensuring tables...")
        await conn.execute(CREATE_QUESTIONS)
        print(" - questions ok")
        await conn.execute(CREATE_SUBMISSIONS)
        print(" - submissions ok")
        await conn.execute(CREATE_SUBMISSION_ANSWERS)
        print(" - submission_answers ok")
        print("\nMigration completed.")
    except Exception as e:
        print("Migration failed:", e)
    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(migrate())
