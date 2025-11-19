import requests
import time
from datetime import datetime

# ==========================
# CONFIG
# ==========================

BASE_URL = "http://157.15.125.7:90"   # monolith base URL
USERNAME = "john"                 # change to real user
PASSWORD = "user123"                    # change to real password

PATH_LOGIN_PAGE = "/accounts/login/"
PATH_LOGIN_POST = "/accounts/login/"
PATH_DASHBOARD  = "/accounts/profile/"

INTERVAL = 2  # seconds between attempts


def log(msg):
    print(f"{datetime.now().isoformat()} - {msg}")


def try_login_and_dashboard():
    """
    1. New session
    2. GET login page (get CSRF)
    3. POST login
    4. GET dashboard
    Return (ok: bool, detail: str)
    """
    s = requests.Session()

    # 1. GET login page
    login_page_url = BASE_URL + PATH_LOGIN_PAGE
    start = time.perf_counter()
    try:
        r = s.get(login_page_url, timeout=5)
        t_login_page = (time.perf_counter() - start) * 1000.0
    except Exception as e:
        return False, f"LOGIN_PAGE_ERROR | {e}"

    if r.status_code != 200:
        return False, f"LOGIN_PAGE_STATUS_{r.status_code}"

    # extract CSRF token if available
    csrf_token = s.cookies.get("csrftoken", None)

    # 2. POST login
    login_post_url = BASE_URL + PATH_LOGIN_POST
    data = {
        "username": USERNAME,
        "password": PASSWORD,
    }
    headers = {}

    if csrf_token:
        data["csrfmiddlewaretoken"] = csrf_token
        headers["X-CSRFToken"] = csrf_token

    start = time.perf_counter()
    try:
        r = s.post(login_post_url, data=data, headers=headers,
                   allow_redirects=True, timeout=5)
        t_login_post = (time.perf_counter() - start) * 1000.0
    except Exception as e:
        return False, f"LOGIN_POST_ERROR | {e}"

    if r.status_code >= 400:
        return False, f"LOGIN_POST_STATUS_{r.status_code}"

    # 3. GET dashboard
    dash_url = BASE_URL + PATH_DASHBOARD
    start = time.perf_counter()
    try:
        r = s.get(dash_url, timeout=5)
        t_dashboard = (time.perf_counter() - start) * 1000.0
    except Exception as e:
        return False, f"DASHBOARD_ERROR | {e}"

    if r.status_code != 200:
        return False, f"DASHBOARD_STATUS_{r.status_code}"

    total_time = t_login_page + t_login_post + t_dashboard
    return True, f"OK | login_page={t_login_page:.2f} ms, login_post={t_login_post:.2f} ms, dashboard={t_dashboard:.2f} ms, total={total_time:.2f} ms"


if __name__ == "__main__":
    log(f"Starting login+dashboard monitor against {BASE_URL}")
    while True:
        ok, detail = try_login_and_dashboard()
        if ok:
            log(detail)
        else:
            log("ERROR | " + detail)
        time.sleep(INTERVAL)
