package main

import (
	"database/sql"
	"encoding/json"
	"errors"
	"fmt"
	"log"
	"net/http"
	"os"
	"strings"
	"time"

	_ "github.com/lib/pq"
)

/* ==== DATA TYPES ==== */

type Question struct {
	ID            int    `json:"id"`
	QuestionText  string `json:"question_text"`
	OptionA       string `json:"option_a"`
	OptionB       string `json:"option_b"`
	OptionC       string `json:"option_c"`
	OptionD       string `json:"option_d"`
	CorrectOption string `json:"-"` // never sent to client
}

type NewQuestionRequest struct {
	QuestionText  string `json:"question_text"`
	OptionA       string `json:"option_a"`
	OptionB       string `json:"option_b"`
	OptionC       string `json:"option_c"`
	OptionD       string `json:"option_d"`
	CorrectOption string `json:"correct_option"`
}

type AnswerSubmission struct {
	QuestionID     int    `json:"question_id"`
	SelectedOption string `json:"selected_option"`
}

type SubmitRequest struct {
	Answers []AnswerSubmission `json:"answers"`
}

type SubmitResponse struct {
	Score   int    `json:"score"`
	Total   int    `json:"total"`
	Message string `json:"message"`
}

/* ==== GLOBALS ==== */

var db *sql.DB

/* ==== UTIL ==== */

func writeJSON(w http.ResponseWriter, status int, v any) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	_ = json.NewEncoder(w).Encode(v)
}

func writeError(w http.ResponseWriter, status int, msg string) {
	writeJSON(w, status, map[string]any{"error": msg})
}

func cors(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		// Simple permissive CORS for dev/Postman/browser
		w.Header().Set("Access-Control-Allow-Origin", "*")
		w.Header().Set("Access-Control-Allow-Headers", "Content-Type, Authorization")
		w.Header().Set("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
		if r.Method == http.MethodOptions {
			w.WriteHeader(http.StatusNoContent)
			return
		}
		next.ServeHTTP(w, r)
	})
}

/* ==== AUTH ==== */

func validateToken(token string) (string, bool, error) {
	if token == "" {
		return "", false, errors.New("missing token")
	}
	url := fmt.Sprintf("http://localhost:8003/api/auth/me?token=%s", token)
	resp, err := http.Get(url)
	if err != nil {
		return "", false, err
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		return "", false, fmt.Errorf("unauthorized")
	}

	var result struct {
		Username string `json:"username"`
		IsStaff  bool   `json:"is_staff"`
	}
	if err := json.NewDecoder(resp.Body).Decode(&result); err != nil {
		return "", false, err
	}
	return result.Username, result.IsStaff, nil
}

func isValidOption(opt string) bool {
	switch strings.ToUpper(strings.TrimSpace(opt)) {
	case "A", "B", "C", "D":
		return true
	default:
		return false
	}
}

/* ==== DB MIGRATIONS ==== */

func autoMigrate(db *sql.DB) error {
	stmts := []string{
		`CREATE TABLE IF NOT EXISTS questions (
			id SERIAL PRIMARY KEY,
			question_text TEXT NOT NULL,
			option_a TEXT,
			option_b TEXT,
			option_c TEXT,
			option_d TEXT,
			correct_option CHAR(1) NOT NULL CHECK (correct_option IN ('A','B','C','D'))
		);`,
		`CREATE TABLE IF NOT EXISTS submissions (
			id SERIAL PRIMARY KEY,
			username VARCHAR(100) NOT NULL,
			score INTEGER NOT NULL DEFAULT 0,
			created_at TIMESTAMP NOT NULL DEFAULT NOW()
		);`,
		`CREATE TABLE IF NOT EXISTS answers (
			id SERIAL PRIMARY KEY,
			submission_id INTEGER NOT NULL REFERENCES submissions(id) ON DELETE CASCADE,
			question_id INTEGER NOT NULL REFERENCES questions(id) ON DELETE RESTRICT,
			selected_option CHAR(1) NOT NULL CHECK (selected_option IN ('A','B','C','D')),
			is_correct BOOLEAN NOT NULL DEFAULT FALSE
		);`,
		`CREATE INDEX IF NOT EXISTS idx_answers_submission ON answers(submission_id);`,
		`CREATE INDEX IF NOT EXISTS idx_answers_question ON answers(question_id);`,
	}

	for _, s := range stmts {
		if _, err := db.Exec(s); err != nil {
			return err
		}
	}
	return nil
}

/* ==== HANDLERS ==== */

func createQuestionHandler(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		writeError(w, http.StatusMethodNotAllowed, "Method not allowed")
		return
	}

	token := r.URL.Query().Get("token")
	_, isStaff, err := validateToken(token)
	if err != nil || !isStaff {
		writeError(w, http.StatusUnauthorized, "Unauthorized")
		return
	}

	var q NewQuestionRequest
	if err := json.NewDecoder(r.Body).Decode(&q); err != nil {
		writeError(w, http.StatusBadRequest, "Invalid JSON")
		return
	}
	if strings.TrimSpace(q.QuestionText) == "" || !isValidOption(q.CorrectOption) {
		writeError(w, http.StatusBadRequest, "Invalid input: question_text and correct_option (A/B/C/D) are required")
		return
	}

	_, err = db.Exec(`
		INSERT INTO questions (question_text, option_a, option_b, option_c, option_d, correct_option)
		VALUES ($1, $2, $3, $4, $5, $6)
	`,
		q.QuestionText, q.OptionA, q.OptionB, q.OptionC, q.OptionD, strings.ToUpper(strings.TrimSpace(q.CorrectOption)),
	)
	if err != nil {
		log.Println("Insert question error:", err)
		writeError(w, http.StatusInternalServerError, "Failed to insert question")
		return
	}

	writeJSON(w, http.StatusOK, map[string]string{"message": "Question added"})
}

func listQuestionsHandler(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodGet {
		writeError(w, http.StatusMethodNotAllowed, "Method not allowed")
		return
	}

	rows, err := db.Query(`SELECT id, question_text, option_a, option_b, option_c, option_d FROM questions ORDER BY id ASC`)
	if err != nil {
		log.Println("DB query error:", err)
		writeError(w, http.StatusInternalServerError, "DB error")
		return
	}
	defer rows.Close()

	var questions []Question
	for rows.Next() {
		var q Question
		if err := rows.Scan(&q.ID, &q.QuestionText, &q.OptionA, &q.OptionB, &q.OptionC, &q.OptionD); err != nil {
			log.Println("Scan error:", err)
			writeError(w, http.StatusInternalServerError, "Scan error")
			return
		}
		questions = append(questions, q)
	}
	if err := rows.Err(); err != nil {
		log.Println("Rows error:", err)
		writeError(w, http.StatusInternalServerError, "DB error")
		return
	}

	writeJSON(w, http.StatusOK, questions)
}

func submitHandler(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		writeError(w, http.StatusMethodNotAllowed, "Method not allowed")
		return
	}

	token := r.URL.Query().Get("token")
	username, _, err := validateToken(token)
	if err != nil {
		writeError(w, http.StatusUnauthorized, "Unauthorized")
		return
	}

	var req SubmitRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		writeError(w, http.StatusBadRequest, "Invalid JSON")
		return
	}
	if len(req.Answers) == 0 {
		writeError(w, http.StatusBadRequest, "No answers submitted")
		return
	}

	tx, err := db.Begin()
	if err != nil {
		writeError(w, http.StatusInternalServerError, "Transaction error")
		return
	}
	defer func() { _ = tx.Rollback() }()

	// Insert submission and get id using RETURNING
	var submissionID int
	if err := tx.QueryRow(`INSERT INTO submissions (username, score) VALUES ($1, 0) RETURNING id`, username).Scan(&submissionID); err != nil {
		log.Println("Insert submission failed:", err)
		writeError(w, http.StatusInternalServerError, "Insert submission failed")
		return
	}

	score := 0
	for _, ans := range req.Answers {
		var correct string
		if err := tx.QueryRow(`SELECT correct_option FROM questions WHERE id = $1`, ans.QuestionID).Scan(&correct); err != nil {
			writeError(w, http.StatusBadRequest, fmt.Sprintf("Question not found: %d", ans.QuestionID))
			return
		}

		sel := strings.ToUpper(strings.TrimSpace(ans.SelectedOption))
		if !isValidOption(sel) {
			writeError(w, http.StatusBadRequest, "Selected option must be one of A/B/C/D")
			return
		}

		isCorrect := sel == correct
		if isCorrect {
			score++
		}

		if _, err := tx.Exec(`
			INSERT INTO answers (submission_id, question_id, selected_option, is_correct)
			VALUES ($1, $2, $3, $4)`,
			submissionID, ans.QuestionID, sel, isCorrect,
		); err != nil {
			log.Println("Answer insert failed:", err)
			writeError(w, http.StatusInternalServerError, "Answer insert failed")
			return
		}
	}

	if _, err := tx.Exec(`UPDATE submissions SET score = $1 WHERE id = $2`, score, submissionID); err != nil {
		log.Println("Score update failed:", err)
		writeError(w, http.StatusInternalServerError, "Score update failed")
		return
	}

	if err := tx.Commit(); err != nil {
		log.Println("Commit failed:", err)
		writeError(w, http.StatusInternalServerError, "Commit failed")
		return
	}

	writeJSON(w, http.StatusOK, SubmitResponse{
		Score:   score,
		Total:   len(req.Answers),
		Message: "Submission saved",
	})
}

func healthHandler(w http.ResponseWriter, r *http.Request) {
	writeJSON(w, http.StatusOK, map[string]any{"status": "ok", "time": time.Now().Format(time.RFC3339)})
}

/* ==== MAIN ==== */

func main() {
	// Prefer env vars, fallback to literal (adjust as needed)
	connStr := os.Getenv("PG_DSN")
	if connStr == "" {
		connStr = "host=localhost port=5432 user=ms_go_user password=yourStrongPassword123 dbname=test_go_service_db sslmode=disable"
	}

	var err error
	db, err = sql.Open("postgres", connStr)
	if err != nil {
		log.Fatal("DB connection failed:", err)
	}
	db.SetMaxOpenConns(10)
	db.SetMaxIdleConns(5)
	db.SetConnMaxLifetime(30 * time.Minute)

	if err := db.Ping(); err != nil {
		log.Fatal("DB unreachable:", err)
	}
	log.Println("Connected to PostgreSQL")

	if err := autoMigrate(db); err != nil {
		log.Fatal("Auto-migrate failed:", err)
	}
	log.Println("Migrations OK")

	mux := http.NewServeMux()
	mux.HandleFunc("/health", healthHandler)
	mux.HandleFunc("/questions", func(w http.ResponseWriter, r *http.Request) {
		switch r.Method {
		case http.MethodGet:
			listQuestionsHandler(w, r)
		case http.MethodPost:
			createQuestionHandler(w, r)
		default:
			writeError(w, http.StatusMethodNotAllowed, "Method not allowed")
		}
	})
	mux.HandleFunc("/submit", submitHandler)

	addr := ":8005"
	log.Println("Test service running on", addr)
	log.Fatal(http.ListenAndServe(addr, cors(mux)))
}
