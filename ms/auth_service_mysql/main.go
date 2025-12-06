package main

import (
	"context"
	"database/sql"
	"encoding/json"
	"fmt"
	"github.com/google/uuid"
	_ "github.com/go-sql-driver/mysql"
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
	// semaphore to limit concurrent bcrypt ops
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
	bcryptSem <- struct{}{}
	defer func() { <-bcryptSem }()
	hashedBytes, err := bcrypt.GenerateFromPassword([]byte(password), bcrypt.DefaultCost)
	return string(hashedBytes), err
}

func comparePassword(hashed, plain string) error {
	bcryptSem <- struct{}{}
	defer func() { <-bcryptSem }()
	return bcrypt.CompareHashAndPassword([]byte(hashed), []byte(plain))
}

func enableCORS(w *http.ResponseWriter) {
	(*w).Header().Set("Access-Control-Allow-Origin", "*") // tighten in prod
	(*w).Header().Set("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
	(*w).Header().Set("Access-Control-Allow-Headers", "Content-Type, Authorization")
}

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

	ctx, cancel := context.WithTimeout(r.Context(), 3*time.Second)
	defer cancel()

	var user User
	// note: pass username twice because MySQL '?' placeholders are positional
	err := db.QueryRowContext(ctx, "SELECT username, password, is_staff FROM users WHERE username = ? OR email = ? LIMIT 1", req.Username, req.Username).
		Scan(&user.Username, &user.Password, &user.IsStaff)

	if err == sql.ErrNoRows {
		http.Error(w, "Invalid username or password", http.StatusUnauthorized)
		return
	} else if err != nil {
		log.Println("DB error in login:", err)
		http.Error(w, "Server error", http.StatusInternalServerError)
		return
	}

	if err := comparePassword(user.Password, req.Password); err != nil {
		http.Error(w, "Invalid username or password", http.StatusUnauthorized)
		return
	}

	token := uuid.New().String()
	expires := time.Now().Add(7 * 24 * time.Hour)

	ctx2, cancel2 := context.WithTimeout(context.Background(), 3*time.Second)
	defer cancel2()

	_, err = db.ExecContext(ctx2, "INSERT INTO tokens (token, username, created_at, expires_at) VALUES (?, ?, NOW(), ?)", token, user.Username, expires)
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

	var existing string
	err := db.QueryRowContext(ctx, "SELECT username FROM users WHERE username = ? OR email = ? LIMIT 1", req.Username, req.Email).Scan(&existing)
	if err != nil && err != sql.ErrNoRows {
		log.Println("Error checking existing user:", err)
		http.Error(w, "Server error", http.StatusInternalServerError)
		return
	}
	if err == nil {
		http.Error(w, "Username or email already exists", http.StatusConflict)
		return
	}

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
        VALUES (?, ?, ?, ?, ?, NOW(), ?)
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
	err := db.QueryRowContext(ctx, "SELECT username FROM tokens WHERE token = ? AND (expires_at IS NULL OR expires_at > NOW())", token).Scan(&username)
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
	err := db.QueryRowContext(ctx, "SELECT username FROM tokens WHERE token = ? AND (expires_at IS NULL OR expires_at > NOW())", token).Scan(&username)
	if err == sql.ErrNoRows {
		http.Error(w, "Invalid token", http.StatusUnauthorized)
		return
	} else if err != nil {
		log.Println("token lookup error in /me:", err)
		http.Error(w, "Server error", http.StatusInternalServerError)
		return
	}

	var isStaff bool
	err = db.QueryRowContext(ctx, "SELECT is_staff FROM users WHERE username = ? LIMIT 1", username).Scan(&isStaff)
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

// ==== AUTO MIGRATE (MySQL) ====
// func autoMigrate(db *sql.DB) error {
// 	stmts := []string{
// 		`CREATE TABLE IF NOT EXISTS users (
// 			username VARCHAR(100) PRIMARY KEY,
// 			email VARCHAR(255) UNIQUE,
// 			password TEXT NOT NULL,
// 			first_name VARCHAR(100),
// 			last_name VARCHAR(100),
// 			date_joined DATETIME DEFAULT CURRENT_TIMESTAMP,
// 			is_staff TINYINT(1) DEFAULT 0
// 		) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;`,
// 		`CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);`,
// 		`CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);`,
// 		`CREATE TABLE IF NOT EXISTS tokens (
// 			token VARCHAR(64) PRIMARY KEY,
// 			username VARCHAR(100) NOT NULL,
// 			created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
// 			expires_at DATETIME NULL,
// 			INDEX idx_tokens_expires_at (expires_at),
// 			FOREIGN KEY (username) REFERENCES users(username) ON DELETE CASCADE
// 		) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;`,
// 	}

// 	for _, s := range stmts {
// 		if _, err := db.Exec(s); err != nil {
// 			return err
// 		}
// 	}
// 	return nil
// }

func autoMigrate(db *sql.DB) error {
    // create tables (no IF NOT EXISTS problem here)
    stmts := []string{
        `CREATE TABLE IF NOT EXISTS users (
            username VARCHAR(100) PRIMARY KEY,
            email VARCHAR(255) UNIQUE,
            password TEXT NOT NULL,
            first_name VARCHAR(100),
            last_name VARCHAR(100),
            date_joined DATETIME DEFAULT CURRENT_TIMESTAMP,
            is_staff TINYINT(1) DEFAULT 0
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;`,
        `CREATE TABLE IF NOT EXISTS tokens (
            token VARCHAR(64) PRIMARY KEY,
            username VARCHAR(100) NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            expires_at DATETIME NULL,
            INDEX idx_tokens_expires_at (expires_at),
            FOREIGN KEY (username) REFERENCES users(username) ON DELETE CASCADE
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;`,
    }

    for _, s := range stmts {
        if _, err := db.Exec(s); err != nil {
            return err
        }
    }

    // get current database/schema name
    var schema string
    if err := db.QueryRow("SELECT DATABASE()").Scan(&schema); err != nil {
        return fmt.Errorf("failed to get current database: %w", err)
    }
    if schema == "" {
        return fmt.Errorf("current database is empty")
    }

    // helper to check if an index exists
    indexExists := func(tableName, indexName string) (bool, error) {
        var cnt int
        q := `
            SELECT COUNT(*) FROM information_schema.statistics
            WHERE table_schema = ? AND table_name = ? AND index_name = ?
        `
        if err := db.QueryRow(q, schema, tableName, indexName).Scan(&cnt); err != nil {
            return false, err
        }
        return cnt > 0, nil
    }

    // ensure indexes if not present
    checks := []struct {
        table string
        idx   string
        stmt  string
    }{
        {"users", "idx_users_username", "CREATE INDEX idx_users_username ON users(username)"},
        {"users", "idx_users_email", "CREATE INDEX idx_users_email ON users(email)"},
    }

    for _, c := range checks {
        ok, err := indexExists(c.table, c.idx)
        if err != nil {
            return fmt.Errorf("failed checking index %s on %s: %w", c.idx, c.table, err)
        }
        if !ok {
            if _, err := db.Exec(c.stmt); err != nil {
                // if concurrent process already created it, we can ignore duplicate error.
                // But return other errors.
                if !strings.Contains(err.Error(), "Duplicate key name") && !strings.Contains(err.Error(), "already exists") {
                    return fmt.Errorf("failed creating index %s: %w", c.idx, err)
                }
            }
        }
    }

    return nil
}


// ==== MAIN ====
func main() {
	// change these credentials to your MySQL setup or use ENV vars
	mysqlUser := "ms_go_user"
	mysqlPass := "yourStrongPassword123"
	mysqlHost := "127.0.0.1"
	mysqlPort := "3306"
	mysqlDB := "auth_go_mysql_db"

	dsn := fmt.Sprintf("%s:%s@tcp(%s:%s)/%s?parseTime=true&loc=Local", mysqlUser, mysqlPass, mysqlHost, mysqlPort, mysqlDB)

	var err error
	db, err = sql.Open("mysql", dsn)
	if err != nil {
		log.Fatal("Failed to open database:", err)
	}

	// tune DB pool for expected load
	db.SetMaxOpenConns(100)
	db.SetMaxIdleConns(25)
	db.SetConnMaxLifetime(5 * time.Minute)

	pingCtx, pingCancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer pingCancel()
	if err = db.PingContext(pingCtx); err != nil {
		log.Fatal("Database unreachable:", err)
	}

	log.Println("Connected to MySQL!")

	// auto-migrate (dev-friendly)
	if err := autoMigrate(db); err != nil {
		log.Fatalf("auto migrate failed: %v", err)
	}
	log.Println("DB migration OK")

	// init bcrypt semaphore
	maxBcrypt := runtime.NumCPU() - 1
	if maxBcrypt < 1 {
		maxBcrypt = 1
	}
	bcryptSem = make(chan struct{}, maxBcrypt)
	log.Printf("bcrypt concurrency limit: %d", maxBcrypt)

	// handlers
	http.HandleFunc("/api/auth/login", loginHandler)
	http.HandleFunc("/api/auth/register", registerHandler)
	http.HandleFunc("/api/auth/validate", validateHandler)
	http.HandleFunc("/api/auth/me", meHandler)
	http.HandleFunc("/healthz", healthHandler)

	srv := &http.Server{
		Addr:         ":8003",
		ReadTimeout:  5 * time.Second,
		WriteTimeout: 15 * time.Second,
		IdleTimeout:  120 * time.Second,
		Handler:      nil,
	}

	go func() {
		log.Println("Auth service (MySQL) running on :8003")
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

	if err := db.Close(); err != nil {
		log.Println("Error closing DB:", err)
	}

	log.Println("Server exiting")
}
