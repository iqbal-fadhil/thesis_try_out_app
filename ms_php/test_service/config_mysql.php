<?php
// test_service/config.php

// === DATABASE CONFIG ===
$DB_HOST = "127.0.0.1";
$DB_NAME = "test_python_service_db";
$DB_USER = "ms_python_user";
$DB_PASS = "yourStrongPassword123";

// === AUTH SERVICE CONFIG ===
$AUTH_SERVICE_BASE = "http://127.0.0.1:8003"; // sesuaikan kalau beda host/port

// === CORS CONFIG ===
$origin = $_SERVER['HTTP_ORIGIN'] ?? '*';
header("Access-Control-Allow-Origin: $origin");
header("Access-Control-Allow-Methods: GET, POST, OPTIONS");
header("Access-Control-Allow-Headers: Content-Type, Authorization");
header("Access-Control-Allow-Credentials: true");

if (($_SERVER['REQUEST_METHOD'] ?? '') === 'OPTIONS') {
    http_response_code(204);
    exit;
}

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
    if ($raw === false) return null;
    $data = json_decode($raw, true);
    if (json_last_error() !== JSON_ERROR_NONE) return null;
    return $data;
}

// Call auth_service to get user info from token
function auth_get_me($token) {
    global $AUTH_SERVICE_BASE;

    if (!$token) return null;

    $url = $AUTH_SERVICE_BASE . "/api/auth/me?token=" . urlencode($token);
    $resp = @file_get_contents($url);
    if ($resp === false) return null;

    $data = json_decode($resp, true);
    if (json_last_error() !== JSON_ERROR_NONE) return null;
    if (isset($data['error'])) return null;
    if (!isset($data['user'])) return null;

    return $data['user'];
}
