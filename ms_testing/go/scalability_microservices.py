import requests
import time
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
import statistics as stats
import random

# ==========================
# CONFIGURATION
# ==========================

ARCHITECTURE = "microservices"

BASE_HOST = "http://157.15.125.7"
AUTH_BASE = f"{BASE_HOST}:8003"
TEST_BASE = f"{BASE_HOST}:8005"

# Use a valid test account
USERNAME = "user_1"       # change to your test user
PASSWORD = "SecretPassword123!!"    # change to your test password


# How many questions to answer per flow (max)
NUM_QUESTIONS = 5

# Per-request timeout (seconds)
REQUEST_TIMEOUT = 5

# Ramp-up: 50, 100, 150, ..., 1000 concurrent users
LOAD_LEVELS = list(range(50, 1001, 50))

# How many full exam flows each virtual user performs
# (1 is enough for heavy loads up to 1000 users)
REQUESTS_PER_USER = 1

# Break between each ramp level (seconds)
SLEEP_BETWEEN_LEVELS = 60

# Optional: stop further tests if error rate too high (in percent)
EARLY_STOP_ERROR_THRESHOLD = 95.0


# ==========================
# SINGLE USER FLOW
# ==========================

def exam_flow(session_id: int):
    """
    One full microservices user flow:

    - POST /api/auth/login
    - GET  /api/auth/me?token=...
    - GET  /questions
    - POST /submit?token=... (random answers)

    Returns:
        (success: bool, total_time_ms: float, error_detail: str | None)
    """
    s = requests.Session()
    start_total = time.perf_counter()

    try:
        # 1. LOGIN (Auth Service)
        login_url = f"{AUTH_BASE}/api/auth/login"
        login_payload = {
            "username": USERNAME,
            "password": PASSWORD,
        }

        r = s.post(login_url, json=login_payload, timeout=REQUEST_TIMEOUT)
        if r.status_code != 200:
            total_ms = (time.perf_counter() - start_total) * 1000.0
            return False, total_ms, f"LOGIN_STATUS_{r.status_code}"

        try:
            login_data = r.json()
        except Exception as e:
            total_ms = (time.perf_counter() - start_total) * 1000.0
            return False, total_ms, f"LOGIN_JSON_ERROR_{type(e).__name__}"

        token = login_data.get("token")
        if not token:
            total_ms = (time.perf_counter() - start_total) * 1000.0
            return False, total_ms, "LOGIN_NO_TOKEN_IN_RESPONSE"

        # 2. /me (Auth Service)
        me_url = f"{AUTH_BASE}/api/auth/me"
        r = s.get(me_url, params={"token": token}, timeout=REQUEST_TIMEOUT)
        if r.status_code != 200:
            total_ms = (time.perf_counter() - start_total) * 1000.0
            return False, total_ms, f"ME_STATUS_{r.status_code}"

        try:
            me_data = r.json()
        except Exception as e:
            total_ms = (time.perf_counter() - start_total) * 1000.0
            return False, total_ms, f"ME_JSON_ERROR_{type(e).__name__}"

        # not strictly needed, but nice for debugging
        profile_username = me_data.get("username") or me_data.get("email") or "unknown"

        # 3. GET questions (Test Service)
        questions_url = f"{TEST_BASE}/questions"
        r = s.get(questions_url, timeout=REQUEST_TIMEOUT)
        if r.status_code != 200:
            total_ms = (time.perf_counter() - start_total) * 1000.0
            return False, total_ms, f"QUESTIONS_STATUS_{r.status_code}"

        try:
            questions_data = r.json()
        except Exception as e:
            total_ms = (time.perf_counter() - start_total) * 1000.0
            return False, total_ms, f"QUESTIONS_JSON_ERROR_{type(e).__name__}"

        if isinstance(questions_data, list):
            questions = questions_data
        else:
            questions = questions_data.get("questions", [])

        if not questions:
            total_ms = (time.perf_counter() - start_total) * 1000.0
            return False, total_ms, "QUESTIONS_EMPTY_LIST"

        # 4. SUBMIT answers (Test Service)
        possible_options = ["A", "B", "C", "D"]
        answers = []

        selected_questions = questions[: min(NUM_QUESTIONS, len(questions))]
        for q in selected_questions:
            q_id = q.get("id") or q.get("question_id")
            if q_id is None:
                continue
            answers.append(
                {
                    "question_id": int(q_id),
                    "selected_option": random.choice(possible_options),
                }
            )

        if not answers:
            total_ms = (time.perf_counter() - start_total) * 1000.0
            return False, total_ms, "NO_VALID_QUESTION_IDS"

        submit_url = f"{TEST_BASE}/submit"
        submit_payload = {"answers": answers}

        r = s.post(
            submit_url,
            params={"token": token},
            json=submit_payload,
            timeout=REQUEST_TIMEOUT,
        )
        if r.status_code != 200:
            total_ms = (time.perf_counter() - start_total) * 1000.0
            return False, total_ms, f"SUBMIT_STATUS_{r.status_code}"

        try:
            submit_data = r.json()
        except Exception as e:
            total_ms = (time.perf_counter() - start_total) * 1000.0
            return False, total_ms, f"SUBMIT_JSON_ERROR_{type(e).__name__}"

        score = (
            submit_data.get("score")
            or submit_data.get("total_score")
            or (submit_data.get("result") or {}).get("score")
            or 0
        )

        total_ms = (time.perf_counter() - start_total) * 1000.0
        # Uncomment for debugging each flow:
        # print(f"[DEBUG] session={session_id}, user={profile_username}, score={score}, total={total_ms:.2f} ms")
        return True, total_ms, None

    except Exception as e:
        total_ms = (time.perf_counter() - start_total) * 1000.0
        return False, total_ms, f"EXCEPTION_{type(e).__name__}"


# ==========================
# LOAD TEST RUNNER
# ==========================

def run_load_test(num_users: int):
    """
    Run exam_flow concurrently with num_users threads.
    Each user runs REQUESTS_PER_USER flows.
    """
    print(f"\n=== Running scalability test: {num_users} virtual users ===")
    start_overall = time.perf_counter()

    success_times = []
    errors = []

    total_tasks = num_users * REQUESTS_PER_USER

    with ThreadPoolExecutor(max_workers=num_users) as executor:
        futures = [
            executor.submit(exam_flow, i + 1)
            for i in range(total_tasks)
        ]
        for fut in as_completed(futures):
            success, total_ms, err = fut.result()
            if success:
                success_times.append(total_ms)
            else:
                errors.append(err)

    duration_overall = time.perf_counter() - start_overall

    if success_times:
        avg_ms = stats.mean(success_times)
        min_ms = min(success_times)
        max_ms = max(success_times)
    else:
        avg_ms = min_ms = max_ms = 0.0

    success_count = len(success_times)
    error_count = len(errors)
    total_flows = success_count + error_count

    error_rate = (error_count / total_flows * 100.0) if total_flows else 0.0
    throughput = success_count / duration_overall if duration_overall > 0 else 0.0

    print(f"Users              : {num_users}")
    print(f"Total flows        : {total_flows}")
    print(f"Successful flows   : {success_count}")
    print(f"Test duration      : {duration_overall:.2f} s")
    print(f"Avg total time     : {avg_ms:.2f} ms")
    print(f"Min / Max time     : {min_ms:.2f} ms / {max_ms:.2f} ms")
    print(f"Throughput         : {throughput:.2f} successful flows/s")
    print(f"Errors             : {error_count} ({error_rate:.2f} %)")

    if error_count > 0:
        print("Sample errors (first 5):", errors[:5])

    return {
        "users": num_users,
        "total_flows": total_flows,
        "success_flows": success_count,
        "duration_s": duration_overall,
        "avg_ms": avg_ms,
        "min_ms": min_ms,
        "max_ms": max_ms,
        "throughput_flows_s": throughput,
        "error_count": error_count,
        "error_rate_pct": error_rate,
    }


# ==========================
# MAIN
# ==========================

if __name__ == "__main__":
    print(f"Starting scalability test for {ARCHITECTURE} using AUTH_BASE={AUTH_BASE}, TEST_BASE={TEST_BASE}")
    summary_rows = []

    for idx, users in enumerate(LOAD_LEVELS):
        res = run_load_test(users)
        summary_rows.append(res)

        # EARLY STOP: kalau error rate sudah sangat tinggi, hentikan test berikutnya
        if res["error_rate_pct"] >= EARLY_STOP_ERROR_THRESHOLD:
            print(f"\nError rate {res['error_rate_pct']:.2f}% >= {EARLY_STOP_ERROR_THRESHOLD}%. Stopping further levels.\n")
            break

        # Sleep between ramp levels
        if idx < len(LOAD_LEVELS) - 1:
            print(f"\nSleeping {SLEEP_BETWEEN_LEVELS}s before next level...\n")
            time.sleep(SLEEP_BETWEEN_LEVELS)

    print("\n=== Summary (copy this to your thesis table) ===")
    print("Users,Success_flows,Avg_ms,Min_ms,Max_ms,Throughput_flows_per_s,Error_rate_pct")
    for row in summary_rows:
        print(
            f"{row['users']},"
            f"{row['success_flows']},"
            f"{row['avg_ms']:.2f},"
            f"{row['min_ms']:.2f},"
            f"{row['max_ms']:.2f},"
            f"{row['throughput_flows_s']:.2f},"
            f"{row['error_rate_pct']:.2f}"
        )
