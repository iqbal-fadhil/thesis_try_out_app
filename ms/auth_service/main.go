package main

import (
    "database/sql"
    "encoding/json"
    "fmt"
    "github.com/google/uuid"
    _ "github.com/lib/pq"
    "golang.org/x/crypto/bcrypt"
    "log"
    "net/http"
    "regexp"
    "strings"
    "time"
)

type LoginRequest struct {
    Username string `json:"username"`
    Password string `json:"password"`
}

type LoginResponse struct {
    Token    string `json:"token"`
    IsStaff  bool   `json:"is_staff"`
}

type RegisterRequest struct {
    Username  string `json:"username"`
    Password  string `json:"password"`
    Email     string `json:"email"`
    FirstName string `json:"first_name"`
    LastName  string `json:"last_name"`
    IsStaff   bool   `json:"is_staff"` // 👈 NEW
}


type User struct {
    Username string
    Password string
    IsStaff  bool
}

var tokens = map[string]string{} // token -> username
var db *sql.DB

var emailRegex = regexp.MustCompile(`^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$`)

func isValidInput(s string, minLen int) bool {
    return strings.TrimSpace(s) != "" && len(s) >= minLen
}

func isValidEmail(email string) bool {
    return emailRegex.MatchString(email)
}

func hashPassword(password string) (string, error) {
    hashedBytes, err := bcrypt.GenerateFromPassword([]byte(password), bcrypt.DefaultCost)
    return string(hashedBytes), err
}

func comparePassword(hashed, plain string) error {
    return bcrypt.CompareHashAndPassword([]byte(hashed), []byte(plain))
}

func loginHandler(w http.ResponseWriter, r *http.Request) {
    enableCORS(&w)
    if r.Method == http.MethodOptions {
        return
    }
    if r.Method != http.MethodPost {
        http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
        return
    }

    var req LoginRequest
    err := json.NewDecoder(r.Body).Decode(&req)
    if err != nil || !isValidInput(req.Username, 3) || !isValidInput(req.Password, 6) {
        http.Error(w, "Invalid input", http.StatusBadRequest)
        return
    }

    var user User
    err = db.QueryRow("SELECT username, password, is_staff FROM users WHERE username = $1", req.Username).
        Scan(&user.Username, &user.Password, &user.IsStaff)

    if err == sql.ErrNoRows || comparePassword(user.Password, req.Password) != nil {
        http.Error(w, "Invalid username or password", http.StatusUnauthorized)
        return
    } else if err != nil {
        log.Println("DB error:", err)
        http.Error(w, "Server error", http.StatusInternalServerError)
        return
    }

    token := uuid.New().String()
    tokens[token] = user.Username

    w.Header().Set("Content-Type", "application/json")
    json.NewEncoder(w).Encode(LoginResponse{
        Token:   token,
        IsStaff: user.IsStaff,
    })
}

func registerHandler(w http.ResponseWriter, r *http.Request) {
    enableCORS(&w)
    if r.Method == http.MethodOptions {
        return
    }
    if r.Method != http.MethodPost {
        http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
        return
    }

    var req RegisterRequest
    err := json.NewDecoder(r.Body).Decode(&req)
    if err != nil ||
        !isValidInput(req.Username, 3) ||
        !isValidInput(req.Password, 6) ||
        !isValidEmail(req.Email) {
        http.Error(w, "Invalid input", http.StatusBadRequest)
        return
    }

    var existing string
    err = db.QueryRow("SELECT username FROM users WHERE username = $1 OR email = $2", req.Username, req.Email).Scan(&existing)
    if err != sql.ErrNoRows {
        http.Error(w, "Username or email already exists", http.StatusConflict)
        return
    }

    hashedPassword, err := hashPassword(req.Password)
    if err != nil {
        http.Error(w, "Password hashing failed", http.StatusInternalServerError)
        return
    }

    _, err = db.Exec(`
        INSERT INTO users (username, email, password, first_name, last_name, date_joined, is_staff)
        VALUES ($1, $2, $3, $4, $5, $6, $7)
    `, req.Username, req.Email, hashedPassword, req.FirstName, req.LastName, time.Now(), req.IsStaff)


    if err != nil {
        log.Println("Register DB error:", err)
        http.Error(w, "Failed to register", http.StatusInternalServerError)
        return
    }

    w.WriteHeader(http.StatusCreated)
    json.NewEncoder(w).Encode(map[string]string{
        "message": "Registration successful",
    })
}

func validateHandler(w http.ResponseWriter, r *http.Request) {
    enableCORS(&w)
    if r.Method == http.MethodOptions {
        return
    }

    token := r.URL.Query().Get("token")
    username, exists := tokens[token]
    if !exists {
        http.Error(w, "Invalid token", http.StatusUnauthorized)
        return
    }

    w.Header().Set("Content-Type", "application/json")
    json.NewEncoder(w).Encode(map[string]string{
        "username": username,
    })
}

func meHandler(w http.ResponseWriter, r *http.Request) {
    enableCORS(&w)
    if r.Method == http.MethodOptions {
        return
    }

    token := r.URL.Query().Get("token")
    username, exists := tokens[token]
    if !exists {
        http.Error(w, "Invalid token", http.StatusUnauthorized)
        return
    }

    var isStaff bool
    err := db.QueryRow("SELECT is_staff FROM users WHERE username = $1", username).Scan(&isStaff)
    if err != nil {
        http.Error(w, "User not found", http.StatusUnauthorized)
        return
    }

    w.Header().Set("Content-Type", "application/json")
    json.NewEncoder(w).Encode(map[string]interface{}{
        "username": username,
        "is_staff": isStaff,
    })
}

func enableCORS(w *http.ResponseWriter) {
    (*w).Header().Set("Access-Control-Allow-Origin", "*")
    (*w).Header().Set("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
    (*w).Header().Set("Access-Control-Allow-Headers", "Content-Type, Authorization")
}

func healthHandler(w http.ResponseWriter, r *http.Request) {
    enableCORS(&w)
    if r.Method == http.MethodOptions {
        return
    }
    w.Header().Set("Content-Type", "application/json")
    w.WriteHeader(http.StatusOK)
    _ = json.NewEncoder(w).Encode(map[string]string{"status": "ok"})
}

func main() {
    connStr := fmt.Sprintf("host=localhost port=5432 user=auth_user password=NewStrongPasswordHere dbname=auth_db sslmode=disable")
    var err error
    db, err = sql.Open("postgres", connStr)
    if err != nil {
        log.Fatal("Failed to connect to database:", err)
    }

    err = db.Ping()
    if err != nil {
        log.Fatal("Database unreachable:", err)
    }

    log.Println("Connected to PostgreSQL!")

    http.HandleFunc("/api/auth/login", loginHandler)
    http.HandleFunc("/api/auth/register", registerHandler)
    http.HandleFunc("/api/auth/validate", validateHandler)
    http.HandleFunc("/api/auth/me", meHandler)
    http.HandleFunc("/healthz", healthHandler)


    log.Println("Auth service running on :8003")
    log.Fatal(http.ListenAndServe(":8003", nil))
}
