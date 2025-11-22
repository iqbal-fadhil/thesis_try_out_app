# seed_auth_mysql.py (simple)
import pymysql
import bcrypt

conn = pymysql.connect(host="127.0.0.1", user="ms_python_user", password="yourStrongPassword123", db="auth_python_service_db", charset="utf8mb4")
cur = conn.cursor()

def hash_pw(p): return bcrypt.hashpw(p.encode(), bcrypt.gensalt()).decode()

users = [
    ("student1", "Student123!", "student1@example.local", 0),
    ("admin", "Admin123!", "admin@example.local", 1),
]

for u,p,e,is_staff in users:
    cur.execute("SELECT 1 FROM users WHERE username=%s", (u,))
    if cur.fetchone() is None:
        cur.execute("INSERT INTO users (username, password, email, is_staff) VALUES (%s,%s,%s,%s)", (u, hash_pw(p), e, is_staff))
        print("Inserted", u)
    else:
        print("Already exists", u)

conn.commit()
cur.close()
conn.close()
