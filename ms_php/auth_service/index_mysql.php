<?php
// auth_service/index.php
// Run: php -S 0.0.0.0:8003 index.php

// ================== CORS (PALING ATAS) ==================
$allowed_origins = [
    'https://microservices.iqbalfadhil.biz.id',
];

$origin = $_SERVER['HTTP_ORIGIN'] ?? '';

if (in_array($origin, $allowed_origins, true)) {
    header("Access-Control-Allow-Origin: $origin");
} else {
    // fallback, biar panggilan langsung via Postman/curl tetap bisa
    header("Access-Control-Allow-Origin: https://microservices.iqbalfadhil.biz.id");
}

header("Vary: Origin");
header("Access-Control-Allow-Credentials: true");
header("Access-Control-Allow-Methods: GET, POST, OPTIONS");
header("Access-Control-Allow-Headers: Content-Type, Authorization, X-Requested-With");

// Preflight OPTIONS: jangan masuk router/DB
if (($_SERVER['REQUEST_METHOD'] ?? '') === 'OPTIONS') {
    http_response_code(204);
    exit;
}
// ========================================================

require_once __DIR__ . '/config_mysql.php';

if (!isset($_SERVER['REQUEST_METHOD'], $_SERVER['REQUEST_URI'])) {
    echo "This script must be run via web server.";
    exit;
}

$method = $_SERVER['REQUEST_METHOD'];
$uri = parse_url($_SERVER['REQUEST_URI'], PHP_URL_PATH);

// Simple router
try {
    if ($uri === '/healthz' && $method === 'GET') {
        json_response(["status" => "ok", "service" => "auth_service"]);
    }

    if ($uri === '/api/auth/register' && $method === 'POST') {
        handle_register();
    }

    if ($uri === '/api/auth/login' && $method === 'POST') {
        handle_login();
    }

    if ($uri === '/api/auth/validate' && $method === 'GET') {
        handle_validate();
    }

    if ($uri === '/api/auth/me' && $method === 'GET') {
        handle_me();
    }

    // 404 fallback
    json_response(["error" => "Not found"], 404);

} catch (Exception $e) {
    json_response([
        "error" => "Internal server error",
        "details" => $e->getMessage()
    ], 500);
}

// ===== HANDLERS =====

function handle_register() {
    $db = get_db();
    $data = get_json_body();

    if (!$data) {
        json_response(["error" => "Invalid JSON"], 400);
    }

    $username   = trim($data['username'] ?? '');
    $password   = $data['password'] ?? '';
    $email      = trim($data['email'] ?? '');
    $first_name = trim($data['first_name'] ?? '');
    $last_name  = trim($data['last_name'] ?? '');
    $is_staff   = !empty($data['is_staff']) ? 1 : 0;

    if ($username === '' || $password === '' || $email === '') {
        json_response(["error" => "username, password, and email are required"], 400);
    }

    // Check uniqueness
    $stmt = $db->prepare("SELECT id FROM users WHERE username = :u OR email = :e LIMIT 1");
    $stmt->execute([':u' => $username, ':e' => $email]);
    if ($stmt->fetch()) {
        json_response(["error" => "Username or email already exists"], 409);
    }

    $password_hash = password_hash($password, PASSWORD_BCRYPT);

    $stmt = $db->prepare("
        INSERT INTO users (username, password_hash, email, first_name, last_name, is_staff, created_at)
        VALUES (:u, :ph, :e, :fn, :ln, :is_staff, NOW())
    ");
    $stmt->execute([
        ':u' => $username,
        ':ph' => $password_hash,
        ':e' => $email,
        ':fn' => $first_name,
        ':ln' => $last_name,
        ':is_staff' => $is_staff,
    ]);

    $id = $db->lastInsertId();

    json_response([
        "status" => "success",
        "user" => [
            "id" => (int)$id,
            "username" => $username,
            "email" => $email,
            "first_name" => $first_name,
            "last_name" => $last_name,
            "is_staff" => (bool)$is_staff,
        ]
    ], 201);
}

function handle_login() {
    $db = get_db();
    $data = get_json_body();

    if (!$data) {
        json_response(["error" => "Invalid JSON"], 400);
    }

    $username = trim($data['username'] ?? '');
    $password = $data['password'] ?? '';

    if ($username === '' || $password === '') {
        json_response(["error" => "username and password are required"], 400);
    }

    $stmt = $db->prepare("SELECT * FROM users WHERE username = :u LIMIT 1");
    $stmt->execute([':u' => $username]);
    $user = $stmt->fetch();

    if (!$user || !password_verify($password, $user['password_hash'])) {
        json_response(["error" => "Invalid username or password"], 401);
    }

    $token = generate_token();
    $expires_at = date('Y-m-d H:i:s', time() + 60 * 60 * 24 * 7); // 7 days

    $stmt = $db->prepare("
        INSERT INTO auth_tokens (user_id, token, created_at, expires_at)
        VALUES (:uid, :token, NOW(), :exp)
    ");
    $stmt->execute([
        ':uid' => $user['id'],
        ':token' => $token,
        ':exp' => $expires_at,
    ]);

    json_response([
        "status" => "success",
        "token" => $token,
        "user" => [
            "id" => (int)$user['id'],
            "username" => $user['username'],
            "email" => $user['email'],
            "first_name" => $user['first_name'],
            "last_name" => $user['last_name'],
            "is_staff" => (bool)$user['is_staff'],
        ]
    ]);
}

function find_user_by_token($token) {
    if (!$token) return null;

    $db = get_db();
    $stmt = $db->prepare("
        SELECT u.* FROM auth_tokens t
        JOIN users u ON u.id = t.user_id
        WHERE t.token = :token
          AND (t.expires_at IS NULL OR t.expires_at > NOW())
        LIMIT 1
    ");
    $stmt->execute([':token' => $token]);
    $user = $stmt->fetch();
    if (!$user) return null;

    return [
        "id" => (int)$user['id'],
        "username" => $user['username'],
        "email" => $user['email'],
        "first_name" => $user['first_name'],
        "last_name" => $user['last_name'],
        "is_staff" => (bool)$user['is_staff'],
    ];
}

function handle_validate() {
    $token = $_GET['token'] ?? '';

    if ($token === '') {
        json_response(["valid" => false, "error" => "Missing token"], 400);
    }

    $user = find_user_by_token($token);
    if (!$user) {
        json_response(["valid" => false], 200);
    }

    json_response(["valid" => true, "user" => $user]);
}

function handle_me() {
    $token = $_GET['token'] ?? '';

    if ($token === '') {
        json_response(["error" => "Missing token"], 400);
    }

    $user = find_user_by_token($token);
    if (!$user) {
        json_response(["error" => "Invalid token"], 401);
    }

    json_response(["user" => $user]);
}
