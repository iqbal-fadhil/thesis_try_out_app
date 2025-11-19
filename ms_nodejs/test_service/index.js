// ==========================================
// Node.js Test Service (single file)
// Endpoints:
//  GET  /health
//  GET  /questions
//  POST /questions?token=...        (staff only)
//  POST /submit?token=...           (user)
// Run: node index.js
// ==========================================

const http = require("http");
const url = require("url");
const { Pool } = require("pg");

// ---------- CONFIG ----------
const PORT = 8031;

const pool = new Pool({
  host: "127.0.0.1",
  port: 5432,
  user: "ms_nodejs_user",               // sesuaikan kalau beda
  password: "yourStrongPassword123",  // sesuaikan
  database: "test_nodejs_service",
});

// Auth service (Go)
const AUTH_BASE_URL = "http://127.0.0.1:8011"; // atau "http://157.15.125.7:8011"

// ---------- HELPERS ----------
function sendJson(res, statusCode, data) {
  res.writeHead(statusCode, { "Content-Type": "application/json" });
  res.end(JSON.stringify(data));
}

function parseBody(req) {
  return new Promise((resolve, reject) => {
    let body = "";
    req.on("data", chunk => {
      body += chunk.toString();
    });
    req.on("end", () => {
      if (!body) return resolve({});
      try {
        const json = JSON.parse(body);
        resolve(json);
      } catch (err) {
        reject(err);
      }
    });
  });
}

/**
 * Call Auth Service /api/auth/me?token=...
 * Return user object or null if invalid.
 */
function getUserFromToken(token) {
  return new Promise((resolve) => {
    if (!token) return resolve(null);

    const targetUrl = `${AUTH_BASE_URL}/api/auth/me?token=${encodeURIComponent(
      token
    )}`;

    const parsed = url.parse(targetUrl);
    const options = {
      hostname: parsed.hostname,
      port: parsed.port || 80,
      path: parsed.path,
      method: "GET",
      timeout: 3000,
    };

    const req = http.request(options, (resp) => {
      let data = "";
      resp.on("data", chunk => (data += chunk.toString()));
      resp.on("end", () => {
        try {
          const json = JSON.parse(data);
          if (json && !json.error) {
            resolve(json);
          } else {
            resolve(null);
          }
        } catch (e) {
          resolve(null);
        }
      });
    });

    req.on("error", () => resolve(null));
    req.on("timeout", () => {
      req.abort();
      resolve(null);
    });

    req.end();
  });
}

// ---------- SERVER ----------
const server = http.createServer(async (req, res) => {
  const parsedUrl = url.parse(req.url, true);
  const path = (parsedUrl.pathname || "/").replace(/^\/+|\/+$/g, "");
  const method = req.method;
  const segments = path === "" ? [] : path.split("/");

  // -------- HEALTH (no DB, no auth) --------
  if (path === "health" && method === "GET") {
    return sendJson(res, 200, { status: "ok" });
  }

  // Anything below uses DB
  let client;
  try {
    client = await pool.connect();
  } catch (err) {
    return sendJson(res, 500, {
      error: "DB Connection failed",
      details: err.message,
    });
  }

  try {
    // -------- GET /questions --------
    if (method === "GET" && segments.length === 1 && segments[0] === "questions") {
      try {
        const result = await client.query(
          `SELECT id, question_text, option_a, option_b, option_c, option_d
           FROM questions
           ORDER BY id ASC`
        );
        return sendJson(res, 200, result.rows);
      } catch (err) {
        return sendJson(res, 500, {
          error: "Query failed",
          details: err.message,
        });
      }
    }

    // -------- POST /questions?token=... (staff only) --------
    if (method === "POST" && segments.length === 1 && segments[0] === "questions") {
      const token = parsedUrl.query.token;
      if (!token) {
        return sendJson(res, 400, { error: "Token missing" });
      }

      const authUser = await getUserFromToken(token);
      if (!authUser) {
        return sendJson(res, 401, { error: "Invalid token" });
      }

      const isStaff = !!authUser.is_staff;
      if (!isStaff) {
        return sendJson(res, 403, { error: "Forbidden: staff only" });
      }

      let body;
      try {
        body = await parseBody(req);
      } catch (err) {
        return sendJson(res, 400, { error: "Invalid JSON body" });
      }

      const questionText = body.question_text;
      const optionA = body.option_a;
      const optionB = body.option_b;
      const optionC = body.option_c;
      const optionD = body.option_d;
      const correctOption = (body.correct_option || "").toString().trim().toUpperCase();

      if (!questionText || !optionA || !optionB || !optionC || !optionD) {
        return sendJson(res, 400, {
          error: "All options and question_text are required",
        });
      }

      if (!["A", "B", "C", "D"].includes(correctOption)) {
        return sendJson(res, 400, {
          error: "correct_option must be one of A, B, C, D",
        });
      }

      try {
        const result = await client.query(
          `INSERT INTO questions
           (question_text, option_a, option_b, option_c, option_d, correct_option)
           VALUES ($1, $2, $3, $4, $5, $6)
           RETURNING id`,
          [questionText, optionA, optionB, optionC, optionD, correctOption]
        );

        const newId = result.rows[0]?.id;
        return sendJson(res, 200, {
          message: "Question created",
          id: newId,
        });
      } catch (err) {
        return sendJson(res, 500, {
          error: "Insert failed",
          details: err.message,
        });
      }
    }

    // -------- POST /submit?token=... --------
    if (method === "POST" && segments.length === 1 && segments[0] === "submit") {
      const token = parsedUrl.query.token;
      if (!token) {
        return sendJson(res, 400, { error: "Token missing" });
      }

      const authUser = await getUserFromToken(token);
      if (!authUser) {
        return sendJson(res, 401, { error: "Invalid token" });
      }

      const username = authUser.username;
      if (!username) {
        return sendJson(res, 500, { error: "Invalid user data" });
      }

      let body;
      try {
        body = await parseBody(req);
      } catch (err) {
        return sendJson(res, 400, { error: "Invalid JSON body" });
      }

      const answers = Array.isArray(body.answers) ? body.answers : null;
      if (!answers || answers.length === 0) {
        return sendJson(res, 400, {
          error: "answers must be a non-empty array",
        });
      }

      // Kumpulkan question_ids unik
      const questionIdsSet = new Set();
      for (const ans of answers) {
        if (
          typeof ans.question_id === "undefined" ||
          typeof ans.selected_option === "undefined"
        ) {
          return sendJson(res, 400, {
            error: "Each answer must have question_id and selected_option",
          });
        }
        const qid = parseInt(ans.question_id, 10);
        if (isNaN(qid)) {
          return sendJson(res, 400, { error: "question_id must be integer" });
        }
        questionIdsSet.add(qid);
      }

      const questionIds = Array.from(questionIdsSet);
      if (questionIds.length === 0) {
        return sendJson(res, 400, {
          error: "No valid question_id provided",
        });
      }

      // Ambil correct_option dari DB
      let questionsMap = {};
      try {
        const result = await client.query(
          "SELECT id, correct_option FROM questions WHERE id = ANY($1::int[])",
          [questionIds]
        );
        for (const row of result.rows) {
          questionsMap[row.id] = (row.correct_option || "").toString().trim().toUpperCase();
        }
      } catch (err) {
        return sendJson(res, 500, {
          error: "Question lookup failed",
          details: err.message,
        });
      }

      if (Object.keys(questionsMap).length === 0) {
        return sendJson(res, 400, {
          error: "No matching questions found for provided IDs",
        });
      }

      let totalQuestions = 0;
      let correctAnswers = 0;
      const answersResult = [];

      for (const ans of answers) {
        const qid = parseInt(ans.question_id, 10);
        const sel = (ans.selected_option || "").toString().trim().toUpperCase();

        let correctOpt = questionsMap[qid];
        let isCorrect = false;

        if (!correctOpt) {
          correctOpt = null;
          isCorrect = false;
        } else {
          isCorrect = sel === correctOpt;
        }

        totalQuestions++;
        if (isCorrect) {
          correctAnswers++;
        }

        answersResult.push({
          question_id: qid,
          selected_option: sel,
          is_correct: isCorrect,
          correct_option: correctOpt,
        });
      }

      // Simpan submissions + submission_answers dalam transaction
      try {
        await client.query("BEGIN");

        const subResult = await client.query(
          `INSERT INTO submissions (username, total_questions, correct_answers)
           VALUES ($1, $2, $3)
           RETURNING id`,
          [username, totalQuestions, correctAnswers]
        );
        const submissionId = subResult.rows[0]?.id;

        const insertAnswerText = `
          INSERT INTO submission_answers
          (submission_id, question_id, selected_option, is_correct)
          VALUES ($1, $2, $3, $4)
        `;

        for (const ar of answersResult) {
          await client.query(insertAnswerText, [
            submissionId,
            ar.question_id,
            ar.selected_option,
            ar.is_correct,
          ]);
        }

        await client.query("COMMIT");

        return sendJson(res, 200, {
          username,
          submission_id: submissionId,
          total_questions: totalQuestions,
          correct_answers: correctAnswers,
          answers: answersResult,
        });
      } catch (err) {
        try {
          await client.query("ROLLBACK");
        } catch (_) {}
        return sendJson(res, 500, {
          error: "Submission save failed",
          details: err.message,
        });
      }
    }

    // -------- NOT FOUND --------
    return sendJson(res, 404, { error: "Not Found" });
  } finally {
    if (client) client.release();
  }
});

// ---------- START ----------
server.listen(PORT, "0.0.0.0", () => {
  console.log(`Node test service running on http://0.0.0.0:${PORT}`);
});
