<?php
// auth_service/config.php

// === DATABASE CONFIG ===
$DB_HOST = "127.0.0.1";
$DB_NAME = "auth_python_service_db";   // sesuaikan dengan DB kamu
$DB_USER = "ms_python_user";           // user MySQL
$DB_PASS = "yourStrongPassword123"; // password MySQL

// === DB CONNECTION ===
function get_db() {
    global $DB_HOST, $DB_NAME, $DB_USER, $DB_PASS;

    static $pdo = null;
    if ($pdo === null) {
        $dsn = "mysql:host=$DB_HOST;dbname=$DB_NAME;charset=utf8mb4";
        $pdo = new PDO($dsn, $DB_USER, $DB_PASS, [
            PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION,
            PDO::ATTR_DEFAULT_FETCH_MODE => PDO::FETCH_ASSOC,
        ]);
    }
    return $pdo;
}

// === HELPERS ===
function json_response($data, $status = 200) {
    http_response_code($status);
    header('Content-Type: application/json');
    echo json_encode($data);
    exit;
}

function get_json_body() {
    $raw = file_get_contents('php://input');
    if ($raw === false) {
        return null;
    }
    $data = json_decode($raw, true);
    if (json_last_error() !== JSON_ERROR_NONE) {
        return null;
    }
    return $data;
}

function generate_token() {
    return bin2hex(random_bytes(32));
}
