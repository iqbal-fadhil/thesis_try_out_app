import psycopg2
import time

# =====================
# CONFIG (edit these)
# =====================

DB_CONFIG = {
    "host": "localhost",      # or your container / service host
    "port": 5432,
    "user": "test_user",        # your PostgreSQL user
    "password": "yourpassword",# your PostgreSQL password
    "dbname": "test_db" # name of your ms DB
}

# Example tables from your microservices:
# - auth_service → users table
# - user_service → userscore or similar
# - test_service → questions table

QUERY = "SELECT COUNT(*) FROM questions;"  # adjust table name if needed
RUNS = 30


# =====================
# PROGRAM
# =====================

def main():
    print("Connecting to PostgreSQL...")
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()

    times = []

    for i in range(RUNS):
        start = time.perf_counter()

        cur.execute(QUERY)
        cur.fetchall()

        duration_ms = (time.perf_counter() - start) * 1000.0
        times.append(duration_ms)

        print(f"Run {i+1}/{RUNS}: {duration_ms:.2f} ms")

    cur.close()
    conn.close()

    avg = sum(times) / len(times)
    print("\n===============================")
    print(f"Average PostgreSQL query time: {avg:.2f} ms")
    print("===============================")


if __name__ == "__main__":
    main()
