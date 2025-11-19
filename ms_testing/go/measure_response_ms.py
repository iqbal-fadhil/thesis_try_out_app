import requests
import time
import csv
from datetime import datetime

# ==========================
# CONFIGURATION
# ==========================

# CHANGE THIS to your monolith domain/IP (no trailing slash)
BASE_URL = "http://157.15.125.7"     # <<< CHANGE THIS IF NEEDED
ARCHITECTURE = "microservices_go"               # label for CSV

USERNAME = "user_1"   # <<< CHANGE THIS
PASSWORD = "SecretPassword123!!"      # <<< CHANGE THIS

NUM_SESSIONS = 30       # number of exam flows (30 recommended)
NUM_QUESTIONS = 10      # adjust if you have more/less

OUTPUT_CSV = f"response_time_{ARCHITECTURE}.csv"

# Django URL paths (based on your urls.py)
PATH_LOGIN_PAGE   = "/accounts/login/"
PATH_LOGIN_POST   = "/accounts/login/"
PATH_DASHBOARD    = "/accounts/profile/"
PATH_TEST_FIRST_Q = "/accounts/test/1/"
PATH_TEST_QUESTION_TEMPLATE = "/accounts/test/{qid}/"
PATH_LOGOUT       = "/accounts/logout/"


# ==========================
# HELPER FUNCTIONS
# ==========================

def measure_step(session, base_url, session_id, step_name, method, path, **kwargs):
    """
    Send an HTTP request and measure response time in ms.
    Returns a dict row to write into CSV.
    """
    url = base_url + path
    start = time.perf_counter()
    try:
        resp = session.request(method, url, **kwargs)
        duration_ms = (time.perf_counter() - start) * 1000.0
        status_code = resp.status_code
    except Exception as e:
        duration_ms = (time.perf_counter() - start) * 1000.0
        status_code = -1  # indicate error
        print(f"[ERROR] Step {step_name} session {session_id}: {e}")

    return {
        "timestamp": datetime.now().isoformat(),
        "architecture": ARCHITECTURE,
        "session_id": session_id,
        "step": step_name,
        "method": method,
        "path": path,
        "status_code": status_code,
        "response_time_ms": round(duration_ms, 2),
    }


def login_with_csrf(session, base_url, session_id, writer):
    """
    Handle Django login with CSRF token.
    Steps:
    1. GET /accounts/login/ -> get csrftoken cookie
    2. POST /accounts/login/ -> send credentials + csrf token
    """

    # 1. GET login page
    row = measure_step(
        session, base_url, session_id,
        "open_login", "GET", PATH_LOGIN_PAGE
    )
    writer.writerow(row)

    # Extract CSRF token from cookie
    csrf_token = session.cookies.get("csrftoken", None)

    # 2. POST login
    login_data = {
        "username": USERNAME,
        "password": PASSWORD,
    }

    if csrf_token:
        login_data["csrfmiddlewaretoken"] = csrf_token

    headers = {}
    if csrf_token:
        headers["X-CSRFToken"] = csrf_token

    row = measure_step(
        session, base_url, session_id,
        "login", "POST", PATH_LOGIN_POST,
        data=login_data,
        headers=headers,
        allow_redirects=True,
    )
    writer.writerow(row)


# ==========================
# MAIN FLOW
# ==========================

def run_monolith_flow(base_url, output_csv):
    with open(output_csv, "w", newline="") as f:
        fieldnames = [
            "timestamp", "architecture", "session_id", "step",
            "method", "path", "status_code", "response_time_ms"
        ]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        for session_id in range(1, NUM_SESSIONS + 1):
            print(f"[{ARCHITECTURE}] Session {session_id}/{NUM_SESSIONS}")
            s = requests.Session()

            # 1–2: Login with CSRF
            login_with_csrf(s, base_url, session_id, writer)

            # 3. Dashboard
            writer.writerow(measure_step(
                s, base_url, session_id,
                "open_dashboard", "GET", PATH_DASHBOARD
            ))

            # 4. Start test by loading question 1
            writer.writerow(measure_step(
                s, base_url, session_id,
                "start_test", "GET", PATH_TEST_FIRST_Q
            ))

            # 5. Next questions
            for q in range(2, NUM_QUESTIONS + 1):
                path_q = PATH_TEST_QUESTION_TEMPLATE.format(qid=q)
                writer.writerow(measure_step(
                    s, base_url, session_id,
                    f"question_{q}", "GET", path_q
                ))

            # 6. Submit test
            # Django may not have a submit endpoint, so we simulate using last question POST
            submit_data = {"finish": "true"}
            csrf_token = s.cookies.get("csrftoken", None)

            headers = {}
            if csrf_token:
                submit_data["csrfmiddlewaretoken"] = csrf_token
                headers["X-CSRFToken"] = csrf_token

            last_question = PATH_TEST_QUESTION_TEMPLATE.format(qid=NUM_QUESTIONS)

            writer.writerow(measure_step(
                s, base_url, session_id,
                "submit_test", "POST", last_question,
                data=submit_data,
                headers=headers,
                allow_redirects=True,
            ))

            # 7. Logout
            writer.writerow(measure_step(
                s, base_url, session_id,
                "logout", "GET", PATH_LOGOUT
            ))

    print(f"Done. Results saved to {output_csv}")


if __name__ == "__main__":
    run_monolith_flow(BASE_URL, OUTPUT_CSV)
