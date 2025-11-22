<?php
/**
 * Seeder for Test Service (MySQL)
 * Inserts default 10 grammar questions
 */

require_once __DIR__ . '/config_mysql.php';

echo "=== Test Service Seeder ===\n";

try {
    $db = get_db();
} catch (Exception $e) {
    echo "❌ Failed to connect to DB: " . $e->getMessage() . "\n";
    exit(1);
}

$questions = [
    [
        'The teacher, along with her students, _____ going to the conference tomorrow.',
        'is',
        'are',
        'were',
        'have been',
        'A'
    ],
    [
        'Not only John but also his brothers _____ to the party last night.',
        'was invited',
        'were invited',
        'has invited',
        'invited',
        'B'
    ],
    [
        'The books on the top shelf _____ covered with dust.',
        'is',
        'was',
        'are',
        'has been',
        'C'
    ],
    [
        'If she _____ harder, she would have passed the exam.',
        'studies',
        'had studied',
        'has studied',
        'will study',
        'B'
    ],
    [
        'The committee _____ not yet decided on the final schedule.',
        'have',
        'are',
        'has',
        'were',
        'C'
    ],
    [
        'Hardly _____ the announcement when the students started asking questions.',
        'the teacher finished',
        'has the teacher finished',
        'the teacher had finished',
        'had the teacher finished',
        'D'
    ],
    [
        'Each of the participants _____ required to submit a written report.',
        'are',
        'were',
        'is',
        'have',
        'C'
    ],
    [
        'The new software allows users _____ files more quickly than before.',
        'to transfer',
        'transferring',
        'transfer',
        'to be transferred',
        'A'
    ],
    [
        'Rarely _____ such an impressive performance by a beginner.',
        'we see',
        'do we see',
        'we are seeing',
        'we have seen',
        'B'
    ],
    [
        'Because the instructions were unclear, many students had difficulty _____ the task.',
        'to complete',
        'complete',
        'completing',
        'completed',
        'C'
    ]
];

foreach ($questions as $q) {

    // Check for duplicates
    $check = $db->prepare("SELECT id FROM questions WHERE question_text = :qt LIMIT 1");
    $check->execute([':qt' => $q[0]]);
    if ($check->fetch()) {
        echo "⚠ Skipped (already exists): {$q[0]}\n";
        continue;
    }

    $stmt = $db->prepare("
        INSERT INTO questions (
            question_text, option_a, option_b, option_c, option_d, correct_option, created_at
        )
        VALUES (:qt, :a, :b, :c, :d, :co, NOW())
    ");

    $stmt->execute([
        ':qt' => $q[0],
        ':a'  => $q[1],
        ':b'  => $q[2],
        ':c'  => $q[3],
        ':d'  => $q[4],
        ':co' => $q[5],
    ]);

    echo "✔ Inserted: {$q[0]}\n";
}

echo "=== Seeder complete ===\n";
