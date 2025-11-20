<?php
// =======================================
// PHP User Service (single file)
// Endpoints:
//  GET  /healthz
//  GET  /users?token=...                (staff only)
//  GET  /users/{username}               (public)
//  POST /users/{username}/score?token=  (self only)
// Run: php -S 0.0.0.0:8020 index.php
// =======================================

// ---------- CONFIG ----------
$db_host = "127.0.0.1";
$db_port = "5432";
$db_user = "ms_php_user";              // change if needed
$db_pass = "yourStrongPassword123";     // change if needed
$db_name = "user_php_service_db";

// Auth Service base URL (Php service)
$auth_base_url = "http://127.0.0.1:8010"; // or "http://157.15.125.7:8010"

// ---------- HELPER FUNCTIONS ----------
function json_response($data, $code = 200) {
    http_response_code($code);
    header("Content-Type: application/json");
    echo json_encode($data);
    exit;
}

function parse_json_body() {
    $raw = file_get_contents("php://input");
    if (!$raw) return [];
    $decoded = json_decode($raw, true);
    return is_array($decoded) ? $decoded : [];
}

/**
 * Call Auth Service /api/auth/me?token=...
 * Returns array with user info or null if invalid.
 */
function get_user_from_token($token, $auth_base_url) {
    if (!$token) return null;
    $url = $auth_base_url . "/api/auth/me?token=" . urlencode($token);

    $ctx = stream_context_create([
        "http" => [
            "method"  => "GET",
            "timeout" => 3,
        ]
    ]);

    $resp = @file_get_contents($url, false, $ctx);
    if ($resp === false) {
        return null;
    }

    $data = json_decode($resp, true);
    if (!is_array($data) || isset($data["error"])) {
        return null;
    }

    return $data;
}

// ---------- ROUTER BASICS ----------
$method = $_SERVER['REQUEST_METHOD'];
$path   = parse_url($_SERVER['REQUEST_URI'], PHP_URL_PATH);
$path   = trim($path, "/");
$parts  = $path === "" ? [] : explode("/", $path);

// Health check (no DB, no auth)
if ($path === "healthz" && $method === "GET") {
    json_response(["status" => "ok"]);
}

// ---------- DB CONNECTION ----------
try {
    $pdo = new PDO("pgsql:host=$db_host;port=$db_port;dbname=$db_name", $db_user, $db_pass);
    $pdo->setAttribute(PDO::ATTR_ERRMODE, PDO::ERRMODE_EXCEPTION);
} catch (Exception $e) {
    json_response(["error" => "DB Connection failed", "details" => $e->getMessage()], 500);
}

// ---------- ROUTES ----------

// GET /users?token=...  (staff only)
if ($method === "GET" && count($parts) === 1 && $parts[0] === "users") {
    $token = $_GET["token"] ?? null;
    if (!$token) {
        json_response(["error" => "Token missing"], 400);
    }

    global $auth_base_url;
    $auth_user = get_user_from_token($token, $auth_base_url);
    if ($auth_user === null) {
        json_response(["error" => "Invalid token"], 401);
    }

    // Require staff
    $is_staff = !empty($auth_user["is_staff"]);
    if (!$is_staff) {
        json_response(["error" => "Forbidden: staff only"], 403);
    }

    // Fetch all user_profiles
    try {
        $stmt = $pdo->query("SELECT username, email, full_name, score FROM user_profiles ORDER BY id ASC");
        $rows = $stmt->fetchAll(PDO::FETCH_ASSOC);
    } catch (Exception $e) {
        json_response(["error" => "Query failed", "details" => $e->getMessage()], 500);
    }

    json_response($rows);
}

// GET /users/{username}  (public)
if ($method === "GET" && count($parts) === 2 && $parts[0] === "users") {
    $username = $parts[1];

    try {
        $stmt = $pdo->prepare("SELECT username, email, full_name, score FROM user_profiles WHERE username = :u LIMIT 1");
        $stmt->execute([":u" => $username]);
        $user = $stmt->fetch(PDO::FETCH_ASSOC);
    } catch (Exception $e) {
        json_response(["error" => "Query failed", "details" => $e->getMessage()], 500);
    }

    if (!$user) {
        json_response(["error" => "User not found"], 404);
    }

    json_response($user);
}

// POST /users/{username}/score?token=...  (self only)
if ($method === "POST" && count($parts) === 3 && $parts[0] === "users" && $parts[2] === "score") {
    $username = $parts[1];
    $token = $_GET["token"] ?? null;

    if (!$token) {
        json_response(["error" => "Token missing"], 400);
    }

    global $auth_base_url;
    $auth_user = get_user_from_token($token, $auth_base_url);
    if ($auth_user === null) {
        json_response(["error" => "Invalid token"], 401);
    }

    // Self only: token's username must match path username
    $token_username = $auth_user["username"] ?? null;
    if ($token_username !== $username) {
        json_response(["error" => "Forbidden: can only update own score"], 403);
    }

    $body = parse_json_body();
    $increment = isset($body["score_increment"]) ? (int)$body["score_increment"] : 0;
    if ($increment === 0) {
        json_response(["error" => "score_increment must be non-zero"], 400);
    }

    try {
        // Ensure user exists
        $pdo->beginTransaction();

        $stmt = $pdo->prepare("SELECT score FROM user_profiles WHERE username = :u FOR UPDATE");
        $stmt->execute([":u" => $username]);
        $row = $stmt->fetch(PDO::FETCH_ASSOC);

        if (!$row) {
            // If profile doesn't exist yet, create with initial score = increment
            $stmt_insert = $pdo->prepare(
                "INSERT INTO user_profiles (username, score) VALUES (:u, :s)"
            );
            $stmt_insert->execute([":u" => $username, ":s" => $increment]);
            $new_score = $increment;
        } else {
            $new_score = (int)$row["score"] + $increment;
            $stmt_upd = $pdo->prepare(
                "UPDATE user_profiles SET score = :s WHERE username = :u"
            );
            $stmt_upd->execute([":s" => $new_score, ":u" => $username]);
        }

        $pdo->commit();
    } catch (Exception $e) {
        if ($pdo->inTransaction()) {
            $pdo->rollBack();
        }
        json_response(["error" => "Update failed", "details" => $e->getMessage()], 500);
    }

    json_response([
        "username"   => $username,
        "new_score"  => $new_score,
        "increment"  => $increment
    ]);
}

// Fallback 404
json_response(["error" => "Not Found"], 404);
