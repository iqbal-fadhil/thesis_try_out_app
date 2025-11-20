<?php
// =======================================
// PHP Test Service (single file)
// Endpoints:
//  GET  /health
//  GET  /questions
//  POST /questions?token=...        (staff only)
//  POST /submit?token=...           (user)
// Run:
//   cd /opt/ms_php_test_service
//   php -S 0.0.0.0:8018 index.php
// =======================================

// ---------- CONFIG ----------
$db_host = "127.0.0.1";
$db_port = "5432";
$db_user = "ms_php_user";            // sesuaikan jika beda
$db_pass = "yourStrongPassword123";   // sesuaikan
$db_name = "test_php_service_db";

// Auth Service (PHP) base URL
$auth_base_url = "http://127.0.0.1:8010"; // atau "http://157.15.125.7:8010"

// ---------- HELPERS ----------
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
 * Panggil Auth Service /api/auth/me?token=...
 * Return array user info atau null kalau token invalid.
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
if ($path === "health" && $method === "GET") {
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

// GET /questions  (public list)
if ($method === "GET" && count($parts) === 1 && $parts[0] === "questions") {
    try {
        $stmt = $pdo->query(
            "SELECT id, question_text, option_a, option_b, option_c, option_d 
             FROM questions
             ORDER BY id ASC"
        );
        $rows = $stmt->fetchAll(PDO::FETCH_ASSOC);
    } catch (Exception $e) {
        json_response(["error" => "Query failed", "details" => $e->getMessage()], 500);
    }

    json_response($rows);
}

// POST /questions?token=...  (staff only, create question)
if ($method === "POST" && count($parts) === 1 && $parts[0] === "questions") {
    $token = $_GET["token"] ?? null;
    if (!$token) {
        json_response(["error" => "Token missing"], 400);
    }

    global $auth_base_url;
    $auth_user = get_user_from_token($token, $auth_base_url);
    if ($auth_user === null) {
        json_response(["error" => "Invalid token"], 401);
    }

    $is_staff = !empty($auth_user["is_staff"]);
    if (!$is_staff) {
        json_response(["error" => "Forbidden: staff only"], 403);
    }

    $body = parse_json_body();

    $question_text  = $body["question_text"]  ?? null;
    $option_a       = $body["option_a"]       ?? null;
    $option_b       = $body["option_b"]       ?? null;
    $option_c       = $body["option_c"]       ?? null;
    $option_d       = $body["option_d"]       ?? null;
    $correct_option = strtoupper($body["correct_option"] ?? "");

    if (!$question_text || !$option_a || !$option_b || !$option_c || !$option_d) {
        json_response(["error" => "All options and question_text are required"], 400);
    }

    if (!in_array($correct_option, ["A", "B", "C", "D"], true)) {
        json_response(["error" => "correct_option must be one of A, B, C, D"], 400);
    }

    try {
        $stmt = $pdo->prepare(
            "INSERT INTO questions
             (question_text, option_a, option_b, option_c, option_d, correct_option)
             VALUES (:qt, :oa, :ob, :oc, :od, :co)
             RETURNING id"
        );
        $stmt->execute([
            ":qt" => $question_text,
            ":oa" => $option_a,
            ":ob" => $option_b,
            ":oc" => $option_c,
            ":od" => $option_d,
            ":co" => $correct_option,
        ]);
        $row = $stmt->fetch(PDO::FETCH_ASSOC);
        $new_id = $row["id"] ?? null;
    } catch (Exception $e) {
        json_response(["error" => "Insert failed", "details" => $e->getMessage()], 500);
    }

    json_response([
        "message" => "Question created",
        "id"      => $new_id,
    ]);
}

// POST /submit?token=...  (user submits answers)
if ($method === "POST" && count($parts) === 1 && $parts[0] === "submit") {
    $token = $_GET["token"] ?? null;
    if (!$token) {
        json_response(["error" => "Token missing"], 400);
    }

    global $auth_base_url;
    $auth_user = get_user_from_token($token, $auth_base_url);
    if ($auth_user === null) {
        json_response(["error" => "Invalid token"], 401);
    }

    $username = $auth_user["username"] ?? null;
    if (!$username) {
        json_response(["error" => "Invalid user data"], 500);
    }

    $body = parse_json_body();
    $answers = $body["answers"] ?? null;
    if (!is_array($answers) || count($answers) === 0) {
        json_response(["error" => "answers must be a non-empty array"], 400);
    }

    // Kumpulkan question_id
    $question_ids = [];
    foreach ($answers as $ans) {
        if (!isset($ans["question_id"]) || !isset($ans["selected_option"])) {
            json_response(["error" => "Each answer must have question_id and selected_option"], 400);
        }
        $qid = (int)$ans["question_id"];
        $question_ids[$qid] = true;
    }

    if (empty($question_ids)) {
        json_response(["error" => "No valid question_id provided"], 400);
    }

    // Ambil semua soal yang terlibat
    $ids_list = implode(",", array_map("intval", array_keys($question_ids)));
    $questions_map = [];

    try {
        $stmt = $pdo->query(
            "SELECT id, correct_option FROM questions WHERE id IN ($ids_list)"
        );
        while ($row = $stmt->fetch(PDO::FETCH_ASSOC)) {
            $questions_map[(int)$row["id"]] = strtoupper($row["correct_option"]);
        }
    } catch (Exception $e) {
        json_response(["error" => "Question lookup failed", "details" => $e->getMessage()], 500);
    }

    if (empty($questions_map)) {
        json_response(["error" => "No matching questions found for provided IDs"], 400);
    }

    $total_questions  = 0;
    $correct_answers  = 0;
    $answers_result   = [];

    foreach ($answers as $ans) {
        $qid = (int)$ans["question_id"];
        $sel = strtoupper(trim($ans["selected_option"]));

        if (!isset($questions_map[$qid])) {
            // question not found, skip / treat as incorrect
            $is_correct = false;
            $correct_opt = null;
        } else {
            $correct_opt = $questions_map[$qid];
            $is_correct = ($sel === $correct_opt);
        }

        $total_questions++;
        if ($is_correct) {
            $correct_answers++;
        }

        $answers_result[] = [
            "question_id"     => $qid,
            "selected_option" => $sel,
            "is_correct"      => $is_correct,
            "correct_option"  => $correct_opt,
        ];
    }

    // Simpan submission + answer detail ke DB
    try {
        $pdo->beginTransaction();

        $stmt_sub = $pdo->prepare(
            "INSERT INTO submissions (username, total_questions, correct_answers)
             VALUES (:u, :tq, :ca) RETURNING id"
        );
        $stmt_sub->execute([
            ":u"  => $username,
            ":tq" => $total_questions,
            ":ca" => $correct_answers,
        ]);
        $sub = $stmt_sub->fetch(PDO::FETCH_ASSOC);
        $submission_id = $sub["id"];

        $stmt_ans = $pdo->prepare(
            "INSERT INTO submission_answers
             (submission_id, question_id, selected_option, is_correct)
             VALUES (:sid, :qid, :sel, :isc)"
        );

        foreach ($answers_result as $ar) {
            $stmt_ans->execute([
                ":sid" => $submission_id,
                ":qid" => $ar["question_id"],
                ":sel" => $ar["selected_option"],
                ":isc" => $ar["is_correct"],
            ]);
        }

        $pdo->commit();
    } catch (Exception $e) {
        if ($pdo->inTransaction()) {
            $pdo->rollBack();
        }
        json_response(["error" => "Submission save failed", "details" => $e->getMessage()], 500);
    }

    json_response([
        "username"        => $username,
        "submission_id"   => $submission_id,
        "total_questions" => $total_questions,
        "correct_answers" => $correct_answers,
        "answers"         => $answers_result,
    ]);
}

// Fallback 404
json_response(["error" => "Not Found"], 404);
