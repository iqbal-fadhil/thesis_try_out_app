// package main

// import (
// 	"database/sql"
// 	"fmt"
// 	"log"

// 	_ "github.com/lib/pq"
// )

// func main() {
// 	// Adjust connection string
// 	connStr := "host=localhost port=5432 user=test_user password=yourpassword dbname=test_db sslmode=disable"

// 	db, err := sql.Open("postgres", connStr)
// 	if err != nil {
// 		log.Fatal("DB connection failed:", err)
// 	}
// 	defer db.Close()

// 	if err := db.Ping(); err != nil {
// 		log.Fatal("DB unreachable:", err)
// 	}

// 	log.Println("Connected to DB")

// 	// --- Seed Questions ---
// 	questions := []struct {
// 		text          string
// 		a, b, c, d    string
// 		correctOption string
// 	}{
// 		{"What is the capital of France?", "London", "Berlin", "Paris", "Rome", "C"},
// 		{"Which planet is known as the Red Planet?", "Earth", "Mars", "Jupiter", "Venus", "B"},
// 		{"2 + 2 = ?", "3", "4", "5", "6", "B"},
// 	}

// 	for _, q := range questions {
// 		_, err := db.Exec(`
// 			INSERT INTO questions (question_text, option_a, option_b, option_c, option_d, correct_option)
// 			VALUES ($1, $2, $3, $4, $5, $6)
// 		`, q.text, q.a, q.b, q.c, q.d, q.correctOption)
// 		if err != nil {
// 			log.Fatal("Insert question failed:", err)
// 		}
// 	}

// 	log.Printf("Seeded %d questions\n", len(questions))

// 	// --- Optional: Seed a Submission + Answers for Testing ---
// 	username := "test_user"
// 	var submissionID int
// 	err = db.QueryRow(`INSERT INTO submissions (username, score) VALUES ($1, 0) RETURNING id`, username).Scan(&submissionID)
// 	if err != nil {
// 		log.Fatal("Insert submission failed:", err)
// 	}

// 	// Insert answers (first two correct, one wrong)
// 	answers := []struct {
// 		qID     int
// 		selected string
// 		correct  bool
// 	}{
// 		{1, "C", true},
// 		{2, "B", true},
// 		{3, "A", false},
// 	}

// 	score := 0
// 	for _, a := range answers {
// 		if a.correct {
// 			score++
// 		}
// 		_, err := db.Exec(`
// 			INSERT INTO answers (submission_id, question_id, selected_option, is_correct)
// 			VALUES ($1, $2, $3, $4)
// 		`, submissionID, a.qID, a.selected, a.correct)
// 		if err != nil {
// 			log.Fatal("Insert answer failed:", err)
// 		}
// 	}

// 	// Update submission score
// 	_, err = db.Exec(`UPDATE submissions SET score = $1 WHERE id = $2`, score, submissionID)
// 	if err != nil {
// 		log.Fatal("Update score failed:", err)
// 	}

// 	log.Printf("Seeded submission %d with %d/%d correct answers\n", submissionID, score, len(answers))
// 	fmt.Println("✅ Seeding complete")
// }


package main

import (
	"database/sql"
	"fmt"
	"log"
	"os"

	_ "github.com/lib/pq"
)

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
			username TEXT NOT NULL,
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

func main() {
	dsn := os.Getenv("PG_DSN")
	if dsn == "" {
		// Sesuaikan dengan DSN test_service kamu
		dsn = "host=localhost port=5432 user=ms_go_user password=yourStrongPassword123 dbname=test_go_service_db sslmode=disable"
	}

	db, err := sql.Open("postgres", dsn)
	if err != nil {
		log.Fatal(err)
	}
	defer db.Close()

	if err := db.Ping(); err != nil {
		log.Fatal("DB unreachable:", err)
	}
	log.Println("Connected to DB")

	if err := autoMigrate(db); err != nil {
		log.Fatal("migrate:", err)
	}

	// Seed 10 Structure/Written English (TOEFL ITP style) questions
	res, err := db.Exec(`
		INSERT INTO questions (question_text, option_a, option_b, option_c, option_d, correct_option) VALUES
		(
			'The teacher, along with her students, _____ going to the conference tomorrow.',
			'is',
			'are',
			'were',
			'have been',
			'A'
		),
		(
			'Not only John but also his brothers _____ to the party last night.',
			'was invited',
			'were invited',
			'has invited',
			'invited',
			'B'
		),
		(
			'The books on the top shelf _____ covered with dust.',
			'is',
			'was',
			'are',
			'has been',
			'C'
		),
		(
			'If she _____ harder, she would have passed the exam.',
			'studies',
			'had studied',
			'has studied',
			'will study',
			'B'
		),
		(
			'The committee _____ not yet decided on the final schedule.',
			'have',
			'are',
			'has',
			'were',
			'C'
		),
		(
			'Hardly _____ the announcement when the students started asking questions.',
			'the teacher finished',
			'has the teacher finished',
			'the teacher had finished',
			'had the teacher finished',
			'D'
		),
		(
			'Each of the participants _____ required to submit a written report.',
			'are',
			'were',
			'is',
			'have',
			'C'
		),
		(
			'The new software allows users _____ files more quickly than before.',
			'to transfer',
			'transferring',
			'transfer',
			'to be transferred',
			'A'
		),
		(
			'Rarely _____ such an impressive performance by a beginner.',
			'we see',
			'do we see',
			'we are seeing',
			'we have seen',
			'B'
		),
		(
			'Because the instructions were unclear, many students had difficulty _____ the task.',
			'to complete',
			'complete',
			'completing',
			'completed',
			'C'
		)
		ON CONFLICT DO NOTHING;
	`)
	if err != nil {
		log.Fatal("seed insert:", err)
	}
	fmt.Println("Seed OK:", res)
}
