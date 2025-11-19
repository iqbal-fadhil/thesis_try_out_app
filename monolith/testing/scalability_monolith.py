import requests
import time
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
import statistics as stats

# ==========================
# CONFIGURATION
# ==========================

BASE_URL = "http://157.15.125.7:90"   # monolith base URL
ARCHITECTURE = "monolith"

USERNAME = "john"      # change to your test user
PASSWORD = "user123"         # change to your test password

PATH_LOGIN_PAGE   = "/accounts/login/"
PATH_LOGIN_POST   = "/accounts/login/"
PATH_DASHBOARD    = "/accounts/profile/"
PATH_TEST_FIRST_Q = "/accounts/test/1/"
PATH_TEST_QUESTION_TEMPLATE = "/accounts/test/{qid}/"
NUM_QUESTIONS = 5          # to keep the flow short for load test

# Scalability levels: "virtual users"
LOAD_LEVELS = [10, 50, 100]   # you can remove 100 if time is short
REQUESTS_PER_USER = 1         # how many exam flows per user


# ==========================
# SINGLE USER FLOW
# ==========================

def exam_flow(session_id: int):
    """
    One full user flow:
    - GET login page
    - POST login
    - GET dashboard
    - GET first test question
    - GET several next questions

    Returns: (success: bool, total_time_ms: float, error_detail: str | None)
    """
    s = requests.Session()
    start_total = time.perf_counter()

    try:
        # 1. GET login page
        login_page_url = BASE_URL + PATH_LOGIN_PAGE
        r = s.get(login_page_url, timeout=5)
        if r.status_code != 200:
            return False, (time.perf_counter() - start_total) * 1000.0, f"LOGIN_PAGE_STATUS_{r.status_code}"

        csrf_token = s.cookies.get("csrftoken", None)

        # 2. POST login
        login_post_url = BASE_URL + PATH_LOGIN_POST
        data = {"username": USERNAME, "password": PASSWORD}
        headers = {}
        if csrf_token:
            data["csrfmiddlewaretoken"] = csrf_token
            headers["X-CSRFToken"] = csrf_token

        r = s.post(login_post_url, data=data, headers=headers, allow_redirects=True, timeout=5)
        if r.status_code >= 400:
            return False, (time.perf_counter() - start_total) * 1000.0, f"LOGIN_POST_STATUS_{r.status_code}"

        # 3. GET dashboard
        dash_url = BASE_URL + PATH_DASHBOARD
        r = s.get(dash_url, timeout=5)
        if r.status_code != 200:
            return False, (time.perf_counter() - start_total) * 1000.0, f"DASHBOARD_STATUS_{r.status_code}"

        # 4. GET first question
        r = s.get(BASE_URL + PATH_TEST_FIRST_Q, timeout=5)
        if r.status_code != 200:
            return False, (time.perf_counter() - start_total) * 1000.0, f"Q1_STATUS_{r.status_code}"

        # 5. GET next questions
        for q in range(2, NUM_QUESTIONS + 1):
            path_q = PATH_TEST_QUESTION_TEMPLATE.format(qid=q)
            r = s.get(BASE_URL + path_q, timeout=5)
            if r.status_code != 200:
                return False, (time.perf_counter() - start_total) * 1000.0, f"Q{q}_STATUS_{r.status_code}"

        total_ms = (time.perf_counter() - start_total) * 1000.0
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

    results = []
    errors = []

    total_tasks = num_users * REQUESTS_PER_USER

    with ThreadPoolExecutor(max_workers=num_users) as executor:
        futures = [
            executor.submit(exam_flow, i + 1)
            for i in range(total_tasks)
        ]
        for fut in as_completed(futures):
            success, total_ms, err = fut.result()
            results.append(total_ms)
            if not success:
                errors.append(err)

    duration_overall = time.perf_counter() - start_overall

    if results:
        avg_ms = stats.mean(results)
        min_ms = min(results)
        max_ms = max(results)
    else:
        avg_ms = min_ms = max_ms = 0.0

    error_count = len(errors)
    error_rate = (error_count / len(results) * 100.0) if results else 0.0

    throughput = len(results) / duration_overall if duration_overall > 0 else 0.0

    print(f"Users              : {num_users}")
    print(f"Total flows        : {len(results)}")
    print(f"Test duration      : {duration_overall:.2f} s")
    print(f"Avg total time     : {avg_ms:.2f} ms")
    print(f"Min / Max time     : {min_ms:.2f} ms / {max_ms:.2f} ms")
    print(f"Throughput         : {throughput:.2f} flows/s")
    print(f"Errors             : {error_count} ({error_rate:.2f} %)")

    if error_count > 0:
        print("Sample errors (first 5):", errors[:5])

    return {
        "users": num_users,
        "total_flows": len(results),
        "duration_s": duration_overall,
        "avg_ms": avg_ms,
        "min_ms": min_ms,
        "max_ms": max_ms,
        "throughput_flows_s": throughput,
        "error_count": error_count,
        "error_rate_pct": error_rate,
    }


if __name__ == "__main__":
    print(f"Starting scalability test for {ARCHITECTURE} at {BASE_URL}")
    summary_rows = []
    for users in LOAD_LEVELS:
        res = run_load_test(users)
        summary_rows.append(res)

    print("\n=== Summary (copy this to your thesis table) ===")
    print("Users,Avg_ms,Min_ms,Max_ms,Throughput_flows_per_s,Error_rate_pct")
    for row in summary_rows:
        print(f"{row['users']},{row['avg_ms']:.2f},{row['min_ms']:.2f},{row['max_ms']:.2f},{row['throughput_flows_s']:.2f},{row['error_rate_pct']:.2f}")
