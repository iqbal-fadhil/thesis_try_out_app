import asyncio
import asyncpg

# ---------------- CONFIG ----------------
DB_HOST = "127.0.0.1"
DB_PORT = 5432
DB_USER = "ms_python_user"
DB_PASSWORD = "yourStrongPassword123"
DB_NAME = "auth_python_service_db"


# ---------------- MIGRATION SQL ----------------
CREATE_USERS_TABLE = """
CREATE TABLE IF NOT EXISTS users (
    username     VARCHAR(100) PRIMARY KEY,
    password     VARCHAR(200) NOT NULL,        -- bcrypt hash
    email        VARCHAR(200),
    first_name   VARCHAR(200),
    last_name    VARCHAR(200),
    is_staff     BOOLEAN NOT NULL DEFAULT FALSE
);
"""

CREATE_TOKENS_TABLE = """
CREATE TABLE IF NOT EXISTS tokens (
    token        VARCHAR(100) PRIMARY KEY,
    username     VARCHAR(100) NOT NULL,
    created_at   TIMESTAMP DEFAULT NOW(),

    CONSTRAINT fk_tokens_user
        FOREIGN KEY (username)
        REFERENCES users(username)
        ON DELETE CASCADE
);
"""

# ---------------- MAIN LOGIC ----------------
async def migrate():
    print("Connecting to PostgreSQL...")

    conn = await asyncpg.connect(
        host=DB_HOST,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME,
    )

    print("Connected.\nRunning migrations...")

    try:
        await conn.execute(CREATE_USERS_TABLE)
        print("✔ users table ensured")

        await conn.execute(CREATE_TOKENS_TABLE)
        print("✔ tokens table ensured")

    except Exception as e:
        print("\n❌ Migration failed:", repr(e))
        await conn.close()
        return

    await conn.close()
    print("\n=== Migration completed successfully ===")


if __name__ == "__main__":
    asyncio.run(migrate())
