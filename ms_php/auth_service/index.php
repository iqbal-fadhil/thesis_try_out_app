<?php
// =======================================
// Minimal PHP Microservice for Auth
// Port example: 8010
// Run: php -S 0.0.0.0:8010 index.php
// =======================================

// ---------- CONFIG ----------
$db_host = "127.0.0.1";
$db_port = "5432";
$db_user = "ms_php_user";
$db_pass = "yourStrongPassword123"; 
$db_name = "auth_php_service_db";

// ---------- DB CONNECTION ----------
try {
    $pdo = new PDO("pgsql:host=$db_host;port=$db_port;dbname=$db_name", $db_user, $db_pass);
    $pdo->setAttribute(PDO::ATTR_ERRMODE, PDO::ERRMODE_EXCEPTION);
} catch (Exception $e) {
    http_response_code(500);
    echo json_encode(["error" => "DB Connection failed", "details" => $e->getMessage()]);
    exit;
}

// ---------- HELPER FUNCTIONS ----------
function json_response($data, $code = 200) {
    http_response_code($code);
    header("Content-Type: application/json");
    echo json_encode($data);
    exit;
}

function parse_json_body() {
    return json_decode(file_get_contents("php://input"), true);
}

function uuid() {
    return bin2hex(random_bytes(16));
}

// ---------- ROUTER ----------
$method = $_SERVER['REQUEST_METHOD'];
$path   = parse_url($_SERVER['REQUEST_URI'], PHP_URL_PATH);

// ----- HEALTH CHECK -----
if ($path === "/healthz" && $method === "GET") {
    json_response(["status" => "ok"]);
}

// ----- REGISTER -----
if ($path === "/api/auth/register" && $method === "POST") {
    $body = parse_json_body();

    $sql = "INSERT INTO users (username, password, email, first_name, last_name, is_staff)
            VALUES (:username, :password, :email, :first_name, :last_name, :is_staff)";
    try {
        $stmt = $pdo->prepare($sql);
        $stmt->execute([
            ":username"   => $body["username"],
            ":password"   => password_hash($body["password"], PASSWORD_BCRYPT),
            ":email"      => $body["email"],
            ":first_name" => $body["first_name"],
            ":last_name"  => $body["last_name"],
            ":is_staff"   => $body["is_staff"] ? 1 : 0
        ]);
    } catch (Exception $e) {
        json_response(["error" => "Insert failed", "details" => $e->getMessage()], 500);
    }

    json_response(["message" => "User Registered"]);
}

// ----- LOGIN -----
if ($path === "/api/auth/login" && $method === "POST") {
    $body = parse_json_body();

    $stmt = $pdo->prepare("SELECT * FROM users WHERE LOWER(username)=LOWER(:u) OR LOWER(email)=LOWER(:u)");
    $stmt->execute([":u" => $body["username"]]);
    $user = $stmt->fetch(PDO::FETCH_ASSOC);

    if (!$user) json_response(["error" => "Invalid credentials"], 401);
    if (!password_verify($body["password"], $user["password"])) {
        json_response(["error" => "Invalid credentials"], 401);
    }

    // CREATE TOKEN
    $token = uuid();

    $pdo->prepare("INSERT INTO tokens (token, username) VALUES (:t, :u)")
        ->execute([":t" => $token, ":u" => $user["username"]]);

    json_response([
        "token"   => $token,
        "is_staff"=> $user["is_staff"] == 1
    ]);
}

// ----- VALIDATE TOKEN -----
if ($path === "/api/auth/validate" && $method === "GET") {
    $token = $_GET["token"] ?? null;

    if (!$token) json_response(["error" => "Token missing"], 400);

    $stmt = $pdo->prepare("SELECT * FROM tokens WHERE token=:t");
    $stmt->execute([":t" => $token]);
    $found = $stmt->fetch(PDO::FETCH_ASSOC);

    json_response(["valid" => $found ? true : false]);
}

// ----- GET CURRENT USER -----
if ($path === "/api/auth/me" && $method === "GET") {
    $token = $_GET["token"] ?? null;

    if (!$token) json_response(["error" => "Token missing"], 400);

    $stmt = $pdo->prepare(
        "SELECT u.username, u.email, u.first_name, u.last_name, u.is_staff
         FROM users u 
         JOIN tokens t ON t.username = u.username
         WHERE t.token = :t"
    );

    $stmt->execute([":t" => $token]);
    $user = $stmt->fetch(PDO::FETCH_ASSOC);

    if (!$user) json_response(["error" => "Invalid token"], 401);

    json_response($user);
}

// ----- NOT FOUND -----
json_response(["error" => "Not Found"], 404);
