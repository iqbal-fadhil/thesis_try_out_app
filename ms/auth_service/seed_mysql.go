package main

import (
    "database/sql"
    "fmt"
    "log"
    "time"

    _ "github.com/go-sql-driver/mysql"
    "golang.org/x/crypto/bcrypt"
)

func main() {
    // Match your DSN
    dsn := "ms_go_user:yourStrongPassword123@tcp(127.0.0.1:3306)/auth_go_mysql_db?parseTime=true&charset=utf8mb4&loc=Local"

    db, err := sql.Open("mysql", dsn)
    if err != nil {
        log.Fatal("DB open error:", err)
    }
    defer db.Close()

    if err := db.Ping(); err != nil {
        log.Fatal("DB unreachable:", err)
    }
    fmt.Println("Connected to MySQL")

    // Ensure table exists
    _, err = db.Exec(`
        CREATE TABLE IF NOT EXISTS users (
            id INT AUTO_INCREMENT PRIMARY KEY,
            username VARCHAR(50) NOT NULL UNIQUE,
            email VARCHAR(100) NOT NULL UNIQUE,
            password TEXT NOT NULL,
            first_name VARCHAR(100),
            last_name VARCHAR(100),
            date_joined DATETIME NOT NULL,
            is_staff TINYINT(1) NOT NULL DEFAULT 0
        );
    `)
    if err != nil {
        log.Fatal("Table creation failed:", err)
    }

    // Hash password
    hashed, err := bcrypt.GenerateFromPassword([]byte("Student123!"), bcrypt.DefaultCost)
    if err != nil {
        log.Fatal("Password hash error:", err)
    }

    // Insert student1
    _, err = db.Exec(`
        INSERT INTO users (username, email, password, first_name, last_name, date_joined, is_staff)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    `,
        "student1",
        "student1@example.com",
        string(hashed),
        "Student",
        "One",
        time.Now(),
        0, // is_staff = false
    )

    if err != nil {
        log.Println("Insert error:", err)
    } else {
        fmt.Println("User student1 created successfully!")
    }
}
