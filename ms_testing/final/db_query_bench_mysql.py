#!/usr/bin/env python3
# db_query_bench_mysql.py (robust)
import pymysql
import time
import csv
import os
from datetime import datetime
from statistics import mean
from pymysql import OperationalError, MySQLError

RESULTS_DIR = "results"
os.makedirs(RESULTS_DIR, exist_ok=True)

ARCHITECTURE_NAME = "python_mysql"
DBMS_NAME = "mysql"

# MySQL DSN - sesuaikan sebelum run
DB_HOST = "127.0.0.1"
DB_PORT = 3306
DB_USER = "ms_python_user"
DB_PASS = "yourStrongPassword123"
DB_NAME = "test_python_service_db"

# Jika True, script akan mencoba CREATE DATABASE jika tidak ditemukan.
AUTO_CREATE_DB = False

TEST_QUERY = "SELECT id, question_text FROM questions LIMIT 10;"

def connect_with_database():
    return pymysql.connect(
        host=DB_HOST,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASS,
        database=DB_NAME,
        charset="utf8mb4",
        cursorclass=pymysql.cursors.DictCursor,
        connect_timeout=5
    )

def connect_without_database():
    # connect tanpa parameter database agar bisa melihat daftar database
    return pymysql.connect(
        host=DB_HOST,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASS,
        charset="utf8mb4",
        cursorclass=pymysql.cursors.DictCursor,
        connect_timeout=5
    )

def ensure_database_exists():
    """
    Pastikan DB tersedia di server yang sama tempat client terhubung.
    Mengembalikan True jika DB sudah ada atau berhasil dibuat.
    Jika tidak bisa membuat (privilege), kembalikan False dan print daftar DB.
    """
    try:
        with connect_without_database() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT @@hostname AS host, @@port AS port, @@version AS version;")
                server = cur.fetchone()
                print("[DB] Connected server:", server)
                cur.execute("SHOW DATABASES;")
                dbs = [r['Database'] for r in cur.fetchall()]
                print("[DB] Databases on server:", dbs)
                if DB_NAME in dbs:
                    print(f"[DB] Database '{DB_NAME}' exists on this server.")
                    return True
                else:
                    print(f"[DB] Database '{DB_NAME}' NOT found on this server.")
                    if AUTO_CREATE_DB:
                        try:
                            print(f"[DB] Attempting to create database '{DB_NAME}' ...")
                            cur.execute(f"CREATE DATABASE `{DB_NAME}` CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci;")
                            conn.commit()
                            print(f"[DB] Database '{DB_NAME}' created.")
                            return True
                        except MySQLError as e:
                            print(f"[DB][ERROR] Failed to create database: {e}")
                            return False
                    else:
                        return False
    except OperationalError as e:
        # contoh: authentication issue, plugin, dsb.
        print("[DB][ERROR] OperationalError when connecting without database:", e)
        raise

def query_latency_test(num_iterations=200):
    print("[INFO] DB_HOST:", DB_HOST, "DB_PORT:", DB_PORT, "DB_USER:", DB_USER, "DB_NAME repr:", repr(DB_NAME))
    # cek existence
    try:
        exists = ensure_database_exists()
    except RuntimeError as e:
        # contohnya: cryptography missing untuk caching_sha2_password
        print("[FATAL] RuntimeError:", e)
        print(" -> Jika auth method caching_sha2_password, install 'cryptography' di virtualenv:")
        print("    pip install cryptography")
        return

    if not exists:
        print(f"[FATAL] Database '{DB_NAME}' tidak tersedia pada server {DB_HOST}:{DB_PORT}.")
        print("-> Pilihan:")
        print("   1) Set DB_NAME ke salah satu DB yang ada di server.")
        print("   2) Atur AUTO_CREATE_DB=True dan jalankan lagi (but require CREATE DATABASE privilege).")
        print("   3) Ubah DB_HOST/DB_PORT ke server yang benar (mungkin kamu punya instance lain).")
        return

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = os.path.join(RESULTS_DIR, f"db_latency_{ARCHITECTURE_NAME}_{DBMS_NAME}_{ts}.csv")

    latencies = []

    try:
        conn = connect_with_database()
    except OperationalError as e:
        print("[DB][ERROR] Failed to connect with database param:", e)
        # Jika error 1049 sebelumnya, sudah ditangani oleh ensure_database_exists(), tapi tetap safety
        return

    with conn, conn.cursor() as cur, open(filename, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["iteration","architecture","dbms","start_time","end_time","latency_ms"])
        for i in range(num_iterations):
            try:
                start = time.monotonic()
                cur.execute(TEST_QUERY)
                _ = cur.fetchall()
                end = time.monotonic()
                latency_ms = (end - start) * 1000.0
                latencies.append(latency_ms)
                writer.writerow([i, ARCHITECTURE_NAME, DBMS_NAME, start, end, round(latency_ms, 2)])
            except MySQLError as e:
                print(f"[DB][ERROR] Query failed at iteration {i}: {e}")
                break

    summary = {
        "architecture": ARCHITECTURE_NAME,
        "dbms": DBMS_NAME,
        "num_iterations": len(latencies),
        "avg_latency_ms": round(mean(latencies), 2) if latencies else 0,
        "min_latency_ms": round(min(latencies), 2) if latencies else 0,
        "max_latency_ms": round(max(latencies), 2) if latencies else 0,
    }

    print("[DB] Query latency summary:", summary)
    return summary

def main():
    # ganti ke 300 jika mau
    query_latency_test(num_iterations=300)

if __name__ == "__main__":
    main()
