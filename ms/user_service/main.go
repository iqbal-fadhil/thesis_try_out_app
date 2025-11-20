package main

import (
    "database/sql"
    "encoding/json"
    "fmt"
    "log"
    "net/http"
    "strings"

    _ "github.com/lib/pq"
)

type User struct {
    Username      string `json:"username"`
    Email         string `json:"email"`
    FirstName     string `json:"first_name"`
    LastName      string `json:"last_name"`
    Score         int    `json:"score"`
    TestAttempted int    `json:"test_attempted"`
}

type ScoreUpdateRequest struct {
    ScoreIncrement int `json:"score_increment"`
}

var db *sql.DB

// Call auth service to validate token and get user role
func validateToken(token string) (username string, isStaff bool, err error) {
    url := fmt.Sprintf("http://localhost:8003/api/auth/me?token=%s", token)
    resp, err := http.Get(url)
    if err != nil {
        return "", false, err
    }
    defer resp.Body.Close()

    if resp.StatusCode != 200 {
        return "", false, fmt.Errorf("unauthorized")
    }

    var result struct {
        Username string `json:"username"`
        IsStaff  bool   `json:"is_staff"`
    }

    err = json.NewDecoder(resp.Body).Decode(&result)
    if err != nil {
        return "", false, err
    }

    return result.Username, result.IsStaff, nil
}

func getAllUsersHandler(w http.ResponseWriter, r *http.Request) {
    token := r.URL.Query().Get("token")
    username, isStaff, err := validateToken(token)
    if err != nil || !isStaff {
        http.Error(w, "Access denied", http.StatusForbidden)
        return
    }

    log.Printf("Staff user %s requested all users\n", username)

    rows, err := db.Query(`SELECT username, email, first_name, last_name, score, test_attempted FROM users`)
    if err != nil {
        http.Error(w, "DB error", http.StatusInternalServerError)
        return
    }
    defer rows.Close()

    var users []User
    for rows.Next() {
        var u User
        err := rows.Scan(&u.Username, &u.Email, &u.FirstName, &u.LastName, &u.Score, &u.TestAttempted)
        if err != nil {
            http.Error(w, "Scan error", http.StatusInternalServerError)
            return
        }
        users = append(users, u)
    }

    w.Header().Set("Content-Type", "application/json")
    json.NewEncoder(w).Encode(users)
}

func getUserHandler(w http.ResponseWriter, r *http.Request) {
    parts := strings.Split(r.URL.Path, "/")
    if len(parts) < 3 {
        http.Error(w, "Username required", http.StatusBadRequest)
        return
    }
    username := parts[2]

    var u User
    err := db.QueryRow(`SELECT username, email, first_name, last_name, score, test_attempted FROM users WHERE username = $1`, username).
        Scan(&u.Username, &u.Email, &u.FirstName, &u.LastName, &u.Score, &u.TestAttempted)
    if err == sql.ErrNoRows {
        http.Error(w, "User not found", http.StatusNotFound)
        return
    } else if err != nil {
        http.Error(w, "DB error", http.StatusInternalServerError)
        return
    }

    w.Header().Set("Content-Type", "application/json")
    json.NewEncoder(w).Encode(u)
}

func updateScoreHandler(w http.ResponseWriter, r *http.Request) {
    parts := strings.Split(r.URL.Path, "/")
    if len(parts) < 4 {
        http.Error(w, "Username required", http.StatusBadRequest)
        return
    }
    username := parts[2]

    token := r.URL.Query().Get("token")
    caller, _, err := validateToken(token)
    if err != nil || caller != username {
        http.Error(w, "You can only update your own score", http.StatusForbidden)
        return
    }

    var req ScoreUpdateRequest
    err = json.NewDecoder(r.Body).Decode(&req)
    if err != nil || req.ScoreIncrement == 0 {
        http.Error(w, "Invalid request body", http.StatusBadRequest)
        return
    }

    _, err = db.Exec(`UPDATE users SET score = score + $1, test_attempted = test_attempted + 1 WHERE username = $2`, req.ScoreIncrement, username)
    if err != nil {
        http.Error(w, "Failed to update score", http.StatusInternalServerError)
        return
    }

    w.WriteHeader(http.StatusOK)
    json.NewEncoder(w).Encode(map[string]string{
        "message": "Score updated successfully",
    })
}

func main() {
    connStr := "host=localhost port=5432 user=ms_go_user password=yourStrongPassword123 dbname=user_go_service_db sslmode=disable"
    var err error
    db, err = sql.Open("postgres", connStr)
    if err != nil {
        log.Fatal("DB connection failed:", err)
    }

    if err := db.Ping(); err != nil {
        log.Fatal("DB ping failed:", err)
    }

    log.Println("User service connected to PostgreSQL!")

    http.HandleFunc("/users", func(w http.ResponseWriter, r *http.Request) {
        if r.Method == http.MethodGet {
            getAllUsersHandler(w, r)
        } else {
            http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
        }
    })

    http.HandleFunc("/users/", func(w http.ResponseWriter, r *http.Request) {
        if r.Method == http.MethodGet {
            getUserHandler(w, r)
        } else if r.Method == http.MethodPost && strings.HasSuffix(r.URL.Path, "/score") {
            updateScoreHandler(w, r)
        } else {
            http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
        }
    })

    log.Println("User service running on :8004")
    log.Fatal(http.ListenAndServe(":8004", nil))
}
