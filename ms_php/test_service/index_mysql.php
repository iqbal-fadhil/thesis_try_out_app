<?php
// test_service/index.php
// Run: php -S 0.0.0.0:8005 index.php

require_once __DIR__ . '/config_mysql.php';

if (!isset($_SERVER['REQUEST_METHOD'], $_SERVER['REQUEST_URI'])) {
    echo "This script must be run via web server.";
    exit;
}

$method = $_SERVER['REQUEST_METHOD'];
$uri = parse_url($_SERVER['REQUEST_URI'], PHP_URL_PATH);

// Router
try {
    if ($uri === '/health' && $method === 'GET') {
        json_response(["status" => "ok", "service" => "test_service"]);
    }

    if ($uri === '/questions' && $method === 'GET') {
        handle_list_questions();
    }

    if ($uri === '/questions' && $method === 'POST') {
        handle_create_question();
    }

    if ($uri === '/submit' && $method === 'POST') {
        handle_submit_answers();
    }

    json_response(["error" => "Not found"], 404);

} catch (Exception $e) {
    json_response([
        "error" => "Internal server error",
        "details" => $e->getMessage()
    ], 500);
}

// ===== HANDLERS =====

function handle_list_questions() {
    $db = get_db();
    $stmt = $db->query("
        SELECT id, question_text, option_a, option_b, option_c, option_d, correct_option
        FROM questions
        ORDER BY id ASC
    ");
    $questions = $stmt->fetchAll();

    json_response(["questions" => $questions]);
}

function handle_create_question() {
    $db = get_db();

    $token = $_GET['token'] ?? '';
    if ($token === '') {
        json_response(["error" => "Missing token"], 400);
    }

    $user = auth_get_me($token);
    if (!$user || empty($user['is_staff'])) {
        json_response(["error" => "Forbidden: staff only"], 403);
    }

    $data = get_json_body();
    if (!$data) {
        json_response(["error" => "Invalid JSON"], 400);
    }

    $question_text  = trim($data['question_text'] ?? '');
    $option_a       = trim($data['option_a'] ?? '');
    $option_b       = trim($data['option_b'] ?? '');
    $option_c       = trim($data['option_c'] ?? '');
    $option_d       = trim($data['option_d'] ?? '');
    $correct_option = strtoupper(trim($data['correct_option'] ?? ''));

    if ($question_text === '' || $option_a === '' || $option_b === '' ||
        $option_c === '' || $option_d === '' ||
        !in_array($correct_option, ['A', 'B', 'C', 'D'], true)) {
        json_response(["error" => "Missing fields or invalid correct_option"], 400);
    }

    $stmt = $db->prepare("
        INSERT INTO questions (question_text, option_a, option_b, option_c, option_d, correct_option, created_at)
        VALUES (:qt, :a, :b, :c, :d, :co, NOW())
    ");
    $stmt->execute([
        ':qt' => $question_text,
        ':a'  => $option_a,
        ':b'  => $option_b,
        ':c'  => $option_c,
        ':d'  => $option_d,
        ':co' => $correct_option,
    ]);

    $id = (int)$db->lastInsertId();

    json_response([
        "status" => "success",
        "question" => [
            "id" => $id,
            "question_text" => $question_text,
            "option_a" => $option_a,
            "option_b" => $option_b,
            "option_c" => $option_c,
            "option_d" => $option_d,
            "correct_option" => $correct_option,
        ]
    ], 201);
}

function handle_submit_answers() {
    $db = get_db();

    $token = $_GET['token'] ?? '';
    if ($token === '') {
        json_response(["error" => "Missing token"], 400);
    }

    $user = auth_get_me($token);
    if (!$user) {
        json_response(["error" => "Invalid token"], 401);
    }

    $data = get_json_body();
    if (!$data || !isset($data['answers']) || !is_array($data['answers'])) {
        json_response(["error" => "Invalid JSON or missing 'answers' array"], 400);
    }

    $answers = $data['answers'];

    if (count($answers) === 0) {
        json_response(["error" => "Answers cannot be empty"], 400);
    }

    // Evaluate
    $details = [];
    $correct_count = 0;
    $total = 0;

    // Start transaction to save submission
    $db->beginTransaction();
    try {
        // Insert submission header
        $stmt = $db->prepare("
            INSERT INTO submissions (user_id, token, total_questions, correct_count, created_at)
            VALUES (:uid, :token, 0, 0, NOW())
        ");
        $uid = $user['id'] ?? null;
        $stmt->execute([
            ':uid' => $uid,
            ':token' => $token,
        ]);
        $submission_id = (int)$db->lastInsertId();

        $stmt_q = $db->prepare("SELECT * FROM questions WHERE id = :id LIMIT 1");
        $stmt_ans = $db->prepare("
            INSERT INTO submission_answers (submission_id, question_id, selected_option, is_correct)
            VALUES (:sid, :qid, :sel, :isc)
        ");

        foreach ($answers as $ans) {
            $question_id = (int)($ans['question_id'] ?? 0);
            $selected_option = strtoupper(trim($ans['selected_option'] ?? ''));

            if ($question_id <= 0 || !in_array($selected_option, ['A', 'B', 'C', 'D'], true)) {
                continue;
            }

            $stmt_q->execute([':id' => $question_id]);
            $question = $stmt_q->fetch();
            if (!$question) {
                continue;
            }

            $is_correct = ($selected_option === strtoupper($question['correct_option'])) ? 1 : 0;
            if ($is_correct) {
                $correct_count++;
            }
            $total++;

            $stmt_ans->execute([
                ':sid' => $submission_id,
                ':qid' => $question_id,
                ':sel' => $selected_option,
                ':isc' => $is_correct,
            ]);

            $details[] = [
                "question_id" => $question_id,
                "question_text" => $question['question_text'],
                "correct_option" => strtoupper($question['correct_option']),
                "selected_option" => $selected_option,
                "is_correct" => (bool)$is_correct,
            ];
        }

        // Update header
        $stmt = $db->prepare("
            UPDATE submissions
            SET total_questions = :tq, correct_count = :cc
            WHERE id = :id
        ");
        $stmt->execute([
            ':tq' => $total,
            ':cc' => $correct_count,
            ':id' => $submission_id,
        ]);

        $db->commit();

    } catch (Exception $e) {
        $db->rollBack();
        throw $e;
    }

    if ($total === 0) {
        json_response([
            "error" => "No valid answers",
            "details" => $details,
        ], 400);
    }

    $score_percent = ($correct_count / $total) * 100.0;

    json_response([
        "status" => "success",
        "submission_id" => $submission_id,
        "total_questions" => $total,
        "correct" => $correct_count,
        "score_percent" => $score_percent,
        "details" => $details,
    ]);
}
