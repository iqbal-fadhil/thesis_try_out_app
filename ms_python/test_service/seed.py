import asyncio
import asyncpg

# ---------------- CONFIG - update if needed ----------------
DB_HOST = "127.0.0.1"
DB_PORT = 5432
DB_USER = "ms_python_user"
DB_PASSWORD = "yourStrongPassword123"
DB_NAME = "test_python_service_db"

POSTMAN_COLLECTION_PATH = "/mnt/data/Test Service API - 157.15.125.7-8005.postman_collection.json"

QUESTIONS = [
    ("The teacher, along with her students, _____ going to the conference tomorrow.", "is", "are", "were", "have been", "A"),
    ("Not only John but also his brothers _____ to the party last night.", "was invited", "were invited", "has invited", "invited", "B"),
    ("The books on the top shelf _____ covered with dust.", "is", "was", "are", "has been", "C"),
    ("If she _____ harder, she would have passed the exam.", "studies", "had studied", "has studied", "will study", "B"),
    ("The committee _____ not yet decided on the final schedule.", "have", "are", "has", "were", "C"),
    ("Hardly _____ the announcement when the students started asking questions.", "the teacher finished", "has the teacher finished", "the teacher had finished", "had the teacher finished", "D"),
    ("Each of the participants _____ required to submit a written report.", "are", "were", "is", "have", "C"),
    ("The new software allows users _____ files more quickly than before.", "to transfer", "transferring", "transfer", "to be transferred", "A"),
    ("Rarely _____ such an impressive performance by a beginner.", "we see", "do we see", "we are seeing", "we have seen", "B"),
    ("Because the instructions were unclear, many students had difficulty _____ the task.", "to complete", "complete", "completing", "completed", "C"),
]

INSERT_SQL = """
INSERT INTO questions (question_text, option_a, option_b, option_c, option_d, correct_option)
VALUES ($1,$2,$3,$4,$5,$6)
RETURNING id
"""

CHECK_SQL = "SELECT id FROM questions WHERE question_text = $1 LIMIT 1"

async def seed():
    print("Connecting to Postgres...")
    conn = await asyncpg.connect(
        host=DB_HOST, port=DB_PORT, user=DB_USER, password=DB_PASSWORD, database=DB_NAME
    )
    try:
        for q in QUESTIONS:
            question_text = q[0].strip()
            exists = await conn.fetchrow(CHECK_SQL, question_text)
            if exists:
                print("Skipped (exists):", question_text)
                continue
            row = await conn.fetchrow(INSERT_SQL, question_text, q[1], q[2], q[3], q[4], q[5])
            print("Inserted id", row["id"], "-", question_text)
        print("\nSeeding completed.")
    except Exception as e:
        print("Seeding failed:", e)
    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(seed())
