# db_query_bench.py
import psycopg2
import time
import csv
import os
from datetime import datetime
from statistics import mean

RESULTS_DIR = "results"
os.makedirs(RESULTS_DIR, exist_ok=True)

ARCHITECTURE_NAME = "python_postgres"  # jawaban di grafik nanti bisa dipisah per kombinasi
DBMS_NAME = "postgresql"           # atau "mysql", dll

# Sesuaikan DSN untuk varian ini
DSN = "host=localhost port=5432 user=ms_python_user password=yourStrongPassword123 dbname=test_python_service_db sslmode=disable"

TEST_QUERY = "SELECT id, question_text FROM questions LIMIT 10;"


def query_latency_test(num_iterations=200):
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = os.path.join(RESULTS_DIR, f"db_latency_{ARCHITECTURE_NAME}_{DBMS_NAME}_{ts}.csv")

    latencies = []
    with psycopg2.connect(DSN) as conn, conn.cursor() as cur, open(filename, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["iteration", "architecture", "dbms", "start_time", "end_time", "latency_ms"])

        for i in range(num_iterations):
            start = time.monotonic()
            cur.execute(TEST_QUERY)
            _ = cur.fetchall()
            end = time.monotonic()
            latency_ms = (end - start) * 1000.0
            latencies.append(latency_ms)
            writer.writerow([i, ARCHITECTURE_NAME, DBMS_NAME, start, end, round(latency_ms, 2)])

    summary = {
        "architecture": ARCHITECTURE_NAME,
        "dbms": DBMS_NAME,
        "num_iterations": num_iterations,
        "avg_latency_ms": round(mean(latencies), 2) if latencies else 0,
        "min_latency_ms": round(min(latencies), 2) if latencies else 0,
        "max_latency_ms": round(max(latencies), 2) if latencies else 0,
    }
    print("[DB] Query latency summary:", summary)
    return summary


def main():
    query_latency_test(num_iterations=300)


if __name__ == "__main__":
    main()
    