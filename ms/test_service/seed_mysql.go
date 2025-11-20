package main

import (
	"database/sql"
	"fmt"
	"log"
	"os"

	_ "github.com/go-sql-driver/mysql"
)

func main() {
	// DSN untuk MySQL test service
	// Bisa juga baca dari ENV, misalnya MYSQL_DSN
	dsn := os.Getenv("MYSQL_DSN")
	if dsn == "" {
		// Sesuaikan dengan DSN test_service kamu (db & user MySQL)
		dsn = "ms_go_user:yourStrongPassword123@tcp(127.0.0.1:3306)/test_go_mysql_db?parseTime=true&charset=utf8mb4&loc=Local"
	}

	db, err := sql.Open("mysql", dsn)
	if err != nil {
		log.Fatal("open DB error:", err)
	}
	defer db.Close()

	if err := db.Ping(); err != nil {
		log.Fatal("DB unreachable:", err)
	}
	log.Println("Connected to MySQL test_go_mysql_db")

	// OPTIONAL: kalau mau selalu clean sebelum seed, uncomment ini:
	// _, _ = db.Exec("TRUNCATE TABLE answers;")
	// _, _ = db.Exec("TRUNCATE TABLE submissions;")
	// _, _ = db.Exec("TRUNCATE TABLE questions;")

	// Insert 10 Structure/Written English (TOEFL ITP style) questions
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
		);
	`)
	if err != nil {
		log.Fatal("seed insert error:", err)
	}

	affected, _ := res.RowsAffected()
	fmt.Println("Seed OK, rows inserted:", affected)
}
