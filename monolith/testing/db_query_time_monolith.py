import mysql.connector
import time

# CHANGE THESE to your DB config
DB_CONFIG = {
    "host": "localhost",
    "user": "monolith_user",
    "password": "yourpassword",
    "database": "monolith_db",
}


# DATABASES = {
#     'default': {
#         'ENGINE': 'django.db.backends.mysql',
#         'NAME': 'monolith_db', # your database name
#         'USER': 'monolith_user', # your database user
#         'PASSWORD': 'yourpassword', # your database user
#         'HOST': 'localhost', # your database host
#         'PORT': '3306', # your database port
#     } 
# }
QUERY = "SELECT COUNT(*) FROM toefl_prep_app_question;"  # adjust table if different
RUNS = 30

def main():
    conn = mysql.connector.connect(**DB_CONFIG)
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
    print(f"\nAverage query time: {avg:.2f} ms")

if __name__ == "__main__":
    main()
