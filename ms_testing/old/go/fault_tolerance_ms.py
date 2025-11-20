# import requests
# import time
# from datetime import datetime

# # ==========================
# # CONFIG
# # ==========================

# BASE_URL = "http://157.15.125.7"   # monolith base URL
# USERNAME = "user_1"                 # change to real user
# PASSWORD = "user123"                    # change to real password

# PATH_LOGIN_PAGE = "/accounts/login/"
# PATH_LOGIN_POST = "/accounts/login/"
# PATH_DASHBOARD  = "/accounts/profile/"

# INTERVAL = 2  # seconds between attempts


# def log(msg):
#     print(f"{datetime.now().isoformat()} - {msg}")


# def try_login_and_dashboard():
#     """
#     1. New session
#     2. GET login page (get CSRF)
#     3. POST login
#     4. GET dashboard
#     Return (ok: bool, detail: str)
#     """
#     s = requests.Session()

#     # 1. GET login page
#     login_page_url = BASE_URL + PATH_LOGIN_PAGE
#     start = time.perf_counter()
#     try:
#         r = s.get(login_page_url, timeout=5)
#         t_login_page = (time.perf_counter() - start) * 1000.0
#     except Exception as e:
#         return False, f"LOGIN_PAGE_ERROR | {e}"

#     if r.status_code != 200:
#         return False, f"LOGIN_PAGE_STATUS_{r.status_code}"

#     # extract CSRF token if available
#     csrf_token = s.cookies.get("csrftoken", None)

#     # 2. POST login
#     login_post_url = BASE_URL + PATH_LOGIN_POST
#     data = {
#         "username": USERNAME,
#         "password": PASSWORD,
#     }
#     headers = {}

#     if csrf_token:
#         data["csrfmiddlewaretoken"] = csrf_token
#         headers["X-CSRFToken"] = csrf_token

#     start = time.perf_counter()
#     try:
#         r = s.post(login_post_url, data=data, headers=headers,
#                    allow_redirects=True, timeout=5)
#         t_login_post = (time.perf_counter() - start) * 1000.0
#     except Exception as e:
#         return False, f"LOGIN_POST_ERROR | {e}"

#     if r.status_code >= 400:
#         return False, f"LOGIN_POST_STATUS_{r.status_code}"

#     # 3. GET dashboard
#     dash_url = BASE_URL + PATH_DASHBOARD
#     start = time.perf_counter()
#     try:
#         r = s.get(dash_url, timeout=5)
#         t_dashboard = (time.perf_counter() - start) * 1000.0
#     except Exception as e:
#         return False, f"DASHBOARD_ERROR | {e}"

#     if r.status_code != 200:
#         return False, f"DASHBOARD_STATUS_{r.status_code}"

#     total_time = t_login_page + t_login_post + t_dashboard
#     return True, f"OK | login_page={t_login_page:.2f} ms, login_post={t_login_post:.2f} ms, dashboard={t_dashboard:.2f} ms, total={total_time:.2f} ms"


# if __name__ == "__main__":
#     log(f"Starting login+dashboard monitor against {BASE_URL}")
#     while True:
#         ok, detail = try_login_and_dashboard()
#         if ok:
#             log(detail)
#         else:
#             log("ERROR | " + detail)
#         time.sleep(INTERVAL)


import requests
import time
import random
from datetime import datetime

# ==========================
# CONFIG
# ==========================

BASE_HOST = "http://157.15.125.7"   # base host for all services

AUTH_BASE = f"{BASE_HOST}:8003"
TEST_BASE = f"{BASE_HOST}:8005"
# If you want to hit User Service too later:
# USER_BASE = f"{BASE_HOST}:8004"

USERNAME = "user_1"                 # change to real user
PASSWORD = "SecretPassword123!!"    # change to real password

INTERVAL = 2  # seconds between attempts
REQUEST_TIMEOUT = 5  # seconds


def log(msg: str):
    print(f"{datetime.now().isoformat()} - {msg}")


def ms_tryout_flow():
    """
    One full microservices flow:

    1. POST /api/auth/login         -> get token
    2. GET  /api/auth/me?token=...  -> get user profile
    3. GET  /questions              -> get question list
    4. POST /submit?token=...       -> submit random answers

    Returns:
        (ok: bool, detail: str)
    """
    s = requests.Session()

    # ==========================
    # 1. LOGIN
    # ==========================
    login_url = f"{AUTH_BASE}/api/auth/login"
    login_payload = {
        "username": USERNAME,
        "password": PASSWORD,
    }

    start = time.perf_counter()
    try:
        r = s.post(login_url, json=login_payload, timeout=REQUEST_TIMEOUT)
        t_login = (time.perf_counter() - start) * 1000.0
    except Exception as e:
        return False, f"LOGIN_ERROR | {e}"

    if r.status_code != 200:
        return False, f"LOGIN_STATUS_{r.status_code}"

    try:
        login_data = r.json()
    except Exception as e:
        return False, f"LOGIN_JSON_ERROR | {e}"

    token = login_data.get("token")
    if not token:
        return False, "LOGIN_NO_TOKEN_IN_RESPONSE"

    # ==========================
    # 2. /me
    # ==========================
    me_url = f"{AUTH_BASE}/api/auth/me"
    start = time.perf_counter()
    try:
        r = s.get(me_url, params={"token": token}, timeout=REQUEST_TIMEOUT)
        t_me = (time.perf_counter() - start) * 1000.0
    except Exception as e:
        return False, f"ME_ERROR | {e}"

    if r.status_code != 200:
        return False, f"ME_STATUS_{r.status_code}"

    try:
        me_data = r.json()
    except Exception as e:
        return False, f"ME_JSON_ERROR | {e}"

    # Optional: get username from me_data if you want to check consistency
    profile_username = me_data.get("username") or me_data.get("email") or "unknown"

    # ==========================
    # 3. GET QUESTIONS
    # ==========================
    questions_url = f"{TEST_BASE}/questions"

    start = time.perf_counter()
    try:
        r = s.get(questions_url, timeout=REQUEST_TIMEOUT)
        t_questions = (time.perf_counter() - start) * 1000.0
    except Exception as e:
        return False, f"QUESTIONS_ERROR | {e}"

    if r.status_code != 200:
        return False, f"QUESTIONS_STATUS_{r.status_code}"

    try:
        questions_data = r.json()
    except Exception as e:
        return False, f"QUESTIONS_JSON_ERROR | {e}"

    # The API might return either:
    # - a list of questions
    # - or { "questions": [ ... ] }
    if isinstance(questions_data, list):
        questions = questions_data
    else:
        questions = questions_data.get("questions", [])

    if not questions:
        return False, "QUESTIONS_EMPTY_LIST"

    # ==========================
    # 4. SUBMIT ANSWERS
    # ==========================

    # Build random answers for up to 5 questions
    possible_options = ["A", "B", "C", "D"]
    answers = []
    selected_questions = questions[: min(5, len(questions))]

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
        return False, "NO_VALID_QUESTION_IDS"

    submit_url = f"{TEST_BASE}/submit"
    submit_payload = {"answers": answers}

    start = time.perf_counter()
    try:
        r = s.post(
            submit_url,
            params={"token": token},
            json=submit_payload,
            timeout=REQUEST_TIMEOUT,
        )
        t_submit = (time.perf_counter() - start) * 1000.0
    except Exception as e:
        return False, f"SUBMIT_ERROR | {e}"

    if r.status_code != 200:
        return False, f"SUBMIT_STATUS_{r.status_code}"

    try:
        submit_data = r.json()
    except Exception as e:
        return False, f"SUBMIT_JSON_ERROR | {e}"

    # Try to read score from different possible keys
    score = (
        submit_data.get("score")
        or submit_data.get("total_score")
        or (submit_data.get("result") or {}).get("score")
        or 0
    )

    total_time = t_login + t_me + t_questions + t_submit

    detail = (
        f"OK | user={profile_username} | "
        f"login={t_login:.2f} ms, "
        f"me={t_me:.2f} ms, "
        f"questions={t_questions:.2f} ms, "
        f"submit={t_submit:.2f} ms, "
        f"total={total_time:.2f} ms, "
        f"score={score}"
    )
    return True, detail


if __name__ == "__main__":
    log(
        f"Starting microservices tryout monitor against "
        f"AUTH_BASE={AUTH_BASE}, TEST_BASE={TEST_BASE}"
    )
    while True:
        ok, detail = ms_tryout_flow()
        if ok:
            log(detail)
        else:
            log("ERROR | " + detail)
        time.sleep(INTERVAL)
