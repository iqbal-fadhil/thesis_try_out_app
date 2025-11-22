<?php
/**
 * Seeder for Auth Service
 * Creates default staff and student accounts
 */

require_once __DIR__ . '/config_mysql.php';

try {
    $db = get_db();
} catch (Exception $e) {
    echo "❌ Failed to connect to DB: " . $e->getMessage() . PHP_EOL;
    exit(1);
}

echo "=== Auth Service Seeder ===" . PHP_EOL;

// List of users to insert
$users = [
    [
        "username" => "student1",
        "password" => "Student123!",
        "email" => "student1@example.com",
        "first_name" => "Student",
        "last_name" => "One",
        "is_staff" => 0
    ]
];

foreach ($users as $u) {
    // Check if user exists
    $stmt = $db->prepare("SELECT id FROM users WHERE username = :u LIMIT 1");
    $stmt->execute([':u' => $u['username']]);
    $exists = $stmt->fetch();

    if ($exists) {
        echo "⚠ Skipped: user '{$u['username']}' already exists." . PHP_EOL;
        continue;
    }

    // Create new account
    $password_hash = password_hash($u['password'], PASSWORD_BCRYPT);

    $stmt = $db->prepare("
        INSERT INTO users (username, password_hash, email, first_name, last_name, is_staff, created_at)
        VALUES (:username, :ph, :email, :fn, :ln, :is_staff, NOW())
    ");

    $stmt->execute([
        ':username' => $u['username'],
        ':ph'       => $password_hash,
        ':email'    => $u['email'],
        ':fn'       => $u['first_name'],
        ':ln'       => $u['last_name'],
        ':is_staff' => $u['is_staff']
    ]);

    echo "✔ Created user: {$u['username']} (password: {$u['password']})" . PHP_EOL;
}

echo PHP_EOL . "=== Seeder completed ===" . PHP_EOL;
