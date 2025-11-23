import asyncio
import asyncpg
import bcrypt

# ---------------- CONFIG ----------------
DB_HOST = "127.0.0.1"
DB_PORT = 5432
DB_USER = "ms_nodejs_user"
DB_PASSWORD = "yourStrongPassword123"
DB_NAME = "auth_nodejs_service_db"

# ---------------- PASSWORD HASH ----------------
def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

# ---------------- USERS TO SEED ----------------
SEED_USERS = [
    {
        "username": "admin",
        "password": "Admin123!",
        "email": "admin@example.com",
        "first_name": "System",
        "last_name": "Admin",
        "is_staff": True,
    },
    {
        "username": "staff1",
        "password": "Staff123!",
        "email": "staff1@example.com",
        "first_name": "Staff",
        "last_name": "One",
        "is_staff": True,
    },
    {
        "username": "student1",
        "password": "Student123!",
        "email": "student1@example.com",
        "first_name": "Student",
        "last_name": "One",
        "is_staff": False,
    },
]

# ---------------- MAIN SEED LOGIC ----------------
async def seed():
    print("Connecting to PostgreSQL...")

    conn = await asyncpg.connect(
        host=DB_HOST,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME,
    )

    print("Connected.")

    for user in SEED_USERS:

        # check whether exists
        exists = await conn.fetchrow(
            "SELECT username FROM users WHERE username = $1 LIMIT 1",
            user["username"],
        )

        if exists:
            print(f"⚠ Skipped: {user['username']} already exists")
            continue

        hashed = hash_password(user["password"])

        await conn.execute(
            """
            INSERT INTO users (username, password, email, first_name, last_name, is_staff)
            VALUES ($1, $2, $3, $4, $5, $6)
            """,
            user["username"],
            hashed,
            user["email"],
            user["first_name"],
            user["last_name"],
            user["is_staff"],
        )

        print(f"✔ Created user: {user['username']} (password: {user['password']})")

    await conn.close()
    print("\n=== Seeding completed ===")


if __name__ == "__main__":
    asyncio.run(seed())
