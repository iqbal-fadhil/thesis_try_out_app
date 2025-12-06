package main

import (
	"context"
	"database/sql"
	"encoding/json"
	"fmt"
	"github.com/google/uuid"
	_ "github.com/lib/pq"
	"golang.org/x/crypto/bcrypt"
	"log"
	"net/http"
	"os"
	"os/signal"
	"regexp"
	"runtime"
	"strings"
	"syscall"
	"time"
)

// ==== REQUEST/RESPONSE TYPES ====

type LoginRequest struct {
	Username string `json:"username"`
	Password string `json:"password"`
}

type LoginResponse struct {
	Token   string `json:"token"`
	IsStaff bool   `json:"is_staff"`
}

type RegisterRequest struct {
	Username  string `json:"username"`
	Password  string `json:"password"`
	Email     string `json:"email"`
	FirstName string `json:"first_name"`
	LastName  string `json:"last_name"`
	IsStaff   bool   `json:"is_staff"`
}

// ==== DOMAIN TYPES ====

type User struct {
	Username string
	Password string
	IsStaff  bool
}

// ==== GLOBALS ====

var (
	db         *sql.DB
	emailRegex = regexp.MustCompile(`^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$`)
	// semaphore channel to limit concurrent bcrypt operations
	bcryptSem chan struct{}
)

// ==== HELPERS ====

func isValidInput(s string, minLen int) bool {
	return strings.TrimSpace(s) != "" && len(s) >= minLen
}

func isValidEmail(email string) bool {
	return emailRegex.MatchString(email)
}

func hashPassword(password string) (string, error) {
	// limit concurrent bcrypt hashes
	bcryptSem <- struct{}{}
	defer func() { <-bcryptSem }()
	hashedBytes, err := bcrypt.GenerateFromPassword([]byte(password), bcrypt.DefaultCost)
	return string(hashedBytes), err
}

func comparePassword(hashed, plain string) error {
	// limit concurrent bcrypt compares
	bcryptSem <- struct{}{}
	defer func() { <-bcryptSem }()
	return bcrypt.CompareHashAndPassword([]byte(hashed), []byte(plain))
}

func enableCORS(w *http.ResponseWriter) {
	(*w).Header().Set("Access-Control-Allow-Origin", "*") // change to specific origin(s) in prod
	(*w).Header().Set("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
	(*w).Header().Set("Access-Control-Allow-Headers", "Content-Type, Authorization")
}

// writeJSON helper
func writeJSON(w http.ResponseWriter, code int, payload interface{}) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(code)
	_ = json.NewEncoder(w).Encode(payload)
}

// ==== HANDLERS ====

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
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil || !isValidInput(req.Username, 3) || !isValidInput(req.Password, 6) {
		http.Error(w, "Invalid input", http.StatusBadRequest)
		return
	}

	// DB query with context timeout
	ctx, cancel := context.WithTimeout(r.Context(), 3*time.Second)
	defer cancel()

	var user User
	// query by username OR email (exact match)
	err := db.QueryRowContext(ctx, "SELECT username, password, is_staff FROM users WHERE username = $1 OR email = $1 LIMIT 1", req.Username).
		Scan(&user.Username, &user.Password, &user.IsStaff)

	if err == sql.ErrNoRows {
		http.Error(w, "Invalid username or password", http.StatusUnauthorized)
		return
	} else if err != nil {
		log.Println("DB error in login:", err)
		http.Error(w, "Server error", http.StatusInternalServerError)
		return
	}

	// compare password (bounded by semaphore)
	if err := comparePassword(user.Password, req.Password); err != nil {
		http.Error(w, "Invalid username or password", http.StatusUnauthorized)
		return
	}

	// generate token and persist in tokens table with expiry
	token := uuid.New().String()
	expires := time.Now().Add(7 * 24 * time.Hour) // 7 days expiry

	ctx2, cancel2 := context.WithTimeout(context.Background(), 3*time.Second)
	defer cancel2()

	_, err = db.ExecContext(ctx2, "INSERT INTO tokens (token, username, created_at, expires_at) VALUES ($1, $2, now(), $3)",
		token, user.Username, expires)
	if err != nil {
		log.Println("failed to insert token:", err)
		http.Error(w, "Server error", http.StatusInternalServerError)
		return
	}

	writeJSON(w, http.StatusOK, LoginResponse{
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
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil ||
		!isValidInput(req.Username, 3) ||
		!isValidInput(req.Password, 6) ||
		!isValidEmail(req.Email) {
		http.Error(w, "Invalid input", http.StatusBadRequest)
		return
	}

	ctx, cancel := context.WithTimeout(r.Context(), 3*time.Second)
	defer cancel()

	// check existing username/email
	var existing string
	err := db.QueryRowContext(ctx, "SELECT username FROM users WHERE username = $1 OR email = $2 LIMIT 1", req.Username, req.Email).Scan(&existing)
	if err != nil && err != sql.ErrNoRows {
		log.Println("Error checking existing user:", err)
		http.Error(w, "Server error", http.StatusInternalServerError)
		return
	}
	if err == nil {
		http.Error(w, "Username or email already exists", http.StatusConflict)
		return
	}

	// hash password (bounded)
	hashedPassword, err := hashPassword(req.Password)
	if err != nil {
		log.Println("hash error:", err)
		http.Error(w, "Password hashing failed", http.StatusInternalServerError)
		return
	}

	ctx2, cancel2 := context.WithTimeout(context.Background(), 3*time.Second)
	defer cancel2()

	_, err = db.ExecContext(ctx2, `
        INSERT INTO users (username, email, password, first_name, last_name, date_joined, is_staff)
        VALUES ($1, $2, $3, $4, $5, now(), $6)
    `, req.Username, req.Email, hashedPassword, req.FirstName, req.LastName, req.IsStaff)
	if err != nil {
		log.Println("Register DB error:", err)
		http.Error(w, "Failed to register", http.StatusInternalServerError)
		return
	}

	writeJSON(w, http.StatusCreated, map[string]string{"message": "Registration successful"})
}

func validateHandler(w http.ResponseWriter, r *http.Request) {
	enableCORS(&w)
	if r.Method == http.MethodOptions {
		return
	}

	token := r.URL.Query().Get("token")
	if token == "" {
		http.Error(w, "Token missing", http.StatusBadRequest)
		return
	}

	ctx, cancel := context.WithTimeout(r.Context(), 2*time.Second)
	defer cancel()

	var username string
	err := db.QueryRowContext(ctx, "SELECT username FROM tokens WHERE token = $1 AND (expires_at IS NULL OR expires_at > now())", token).Scan(&username)
	if err == sql.ErrNoRows {
		http.Error(w, "Invalid token", http.StatusUnauthorized)
		return
	} else if err != nil {
		log.Println("validate token db error:", err)
		http.Error(w, "Server error", http.StatusInternalServerError)
		return
	}

	writeJSON(w, http.StatusOK, map[string]string{"username": username})
}

func meHandler(w http.ResponseWriter, r *http.Request) {
	enableCORS(&w)
	if r.Method == http.MethodOptions {
		return
	}

	token := r.URL.Query().Get("token")
	if token == "" {
		http.Error(w, "Token missing", http.StatusBadRequest)
		return
	}

	ctx, cancel := context.WithTimeout(r.Context(), 3*time.Second)
	defer cancel()

	var username string
	err := db.QueryRowContext(ctx, "SELECT username FROM tokens WHERE token = $1 AND (expires_at IS NULL OR expires_at > now())", token).Scan(&username)
	if err == sql.ErrNoRows {
		http.Error(w, "Invalid token", http.StatusUnauthorized)
		return
	} else if err != nil {
		log.Println("token lookup error in /me:", err)
		http.Error(w, "Server error", http.StatusInternalServerError)
		return
	}

	var isStaff bool
	err = db.QueryRowContext(ctx, "SELECT is_staff FROM users WHERE username = $1 LIMIT 1", username).Scan(&isStaff)
	if err == sql.ErrNoRows {
		http.Error(w, "User not found", http.StatusUnauthorized)
		return
	} else if err != nil {
		log.Println("DB error in /me:", err)
		http.Error(w, "Server error", http.StatusInternalServerError)
		return
	}

	writeJSON(w, http.StatusOK, map[string]interface{}{
		"username": username,
		"is_staff": isStaff,
	})
}

func healthHandler(w http.ResponseWriter, r *http.Request) {
	enableCORS(&w)
	if r.Method == http.MethodOptions {
		return
	}
	writeJSON(w, http.StatusOK, map[string]string{"status": "ok"})
}

// ==== MAIN ====

func main() {
	// Replace credentials with safe config or env vars in production
	connStr := fmt.Sprintf("host=localhost port=5432 user=ms_go_user password=yourStrongPassword123 dbname=auth_go_service_db sslmode=disable")

	var err error
	db, err = sql.Open("postgres", connStr)
	if err != nil {
		log.Fatal("Failed to open database:", err)
	}

	// tune DB pool
	db.SetMaxOpenConns(50)                // adjust to your Postgres capacity
	db.SetMaxIdleConns(25)
	db.SetConnMaxLifetime(5 * time.Minute)

	// quick ping with timeout
	pingCtx, pingCancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer pingCancel()
	if err = db.PingContext(pingCtx); err != nil {
		log.Fatal("Database unreachable:", err)
	}

	log.Println("Connected to PostgreSQL!")

	// init bcrypt semaphore: limit concurrent bcrypt ops to cpu-1
	maxBcrypt := runtime.NumCPU() - 1
	if maxBcrypt < 1 {
		maxBcrypt = 1
	}
	bcryptSem = make(chan struct{}, maxBcrypt)
	log.Printf("bcrypt concurrency limit: %d", maxBcrypt)

	// register handlers
	http.HandleFunc("/api/auth/login", loginHandler)
	http.HandleFunc("/api/auth/register", registerHandler)
	http.HandleFunc("/api/auth/validate", validateHandler)
	http.HandleFunc("/api/auth/me", meHandler)
	http.HandleFunc("/healthz", healthHandler)

	// create http.Server with timeouts
	srv := &http.Server{
		Addr:         ":8003",
		ReadTimeout:  5 * time.Second,
		WriteTimeout: 15 * time.Second,
		IdleTimeout:  120 * time.Second,
		Handler:      nil, // default mux
	}

	// run server
	go func() {
		log.Println("Auth service running on :8003")
		if err := srv.ListenAndServe(); err != nil && err != http.ErrServerClosed {
			log.Fatalf("listen: %s\n", err)
		}
	}()

	// graceful shutdown
	quit := make(chan os.Signal, 1)
	signal.Notify(quit, os.Interrupt, syscall.SIGTERM)
	<-quit
	log.Println("Shutting down server...")

	ctxShut, cancel := context.WithTimeout(context.Background(), 10*time.Second)
	defer cancel()
	if err := srv.Shutdown(ctxShut); err != nil {
		log.Fatalf("Server forced to shutdown: %v", err)
	}

	// close DB
	if err := db.Close(); err != nil {
		log.Println("Error closing DB:", err)
	}

	log.Println("Server exiting")
}
