// ==========================================
// Node.js Test Service (MySQL single-file)
// Endpoints:
//  GET  /health
//  GET  /questions
//  POST /questions?token=...        (staff only)
//  POST /submit?token=...           (user)
// Run: node index.js
// ==========================================

const http = require("http");
const url = require("url");
const mysql = require("mysql2/promise");

// ---------- CONFIG ----------
const PORT = 8005;

const pool = mysql.createPool({
  host: "127.0.0.1",
  port: 3306,
  user: "ms_nodejs_user",            // adjust if needed
  password: "StrongPassw0rd!", // adjust
  database: "test_nodejs_service_db",
  waitForConnections: true,
  connectionLimit: 10,
  queueLimit: 0,
});

// Auth service (adjust if different)
const AUTH_BASE_URL = "http://127.0.0.1:8003";

// ---------- CORS CONFIG ----------
const ALLOWED_ORIGINS = [
  "https://microservices.iqbalfadhil.biz.id",
  "https://auth-microservices.iqbalfadhil.biz.id",
  "http://localhost:3000",
  "http://127.0.0.1:3000",
];

function setCorsHeaders(req, res) {
  const origin = req.headers.origin;
  if (origin && ALLOWED_ORIGINS.includes(origin)) {
    res.setHeader("Access-Control-Allow-Origin", origin);
  }
  res.setHeader("Access-Control-Allow-Methods", "GET, POST, OPTIONS, PUT, DELETE");
  res.setHeader("Access-Control-Allow-Headers", "Content-Type, Authorization");
  res.setHeader("Access-Control-Allow-Credentials", "true");
  res.setHeader("Access-Control-Expose-Headers", "Content-Type");
}

// ---------- HELPERS ----------
function sendJson(res, statusCode, data) {
  res.statusCode = statusCode;
  if (!res.getHeader("Content-Type")) {
    res.setHeader("Content-Type", "application/json");
  }
  res.end(JSON.stringify(data));
}

function parseBody(req) {
  return new Promise((resolve, reject) => {
    let body = "";
    req.on("data", chunk => {
      body += chunk.toString();
      if (body.length > 1e6) { // 1MB
        req.connection.destroy();
        reject(new Error("Payload too large"));
      }
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

    const targetUrl = `${AUTH_BASE_URL}/api/auth/me?token=${encodeURIComponent(token)}`;
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
  setCorsHeaders(req, res);

  if (req.method === "OPTIONS") {
    res.statusCode = 204;
    return res.end();
  }

  const parsedUrl = url.parse(req.url, true);
  const path = (parsedUrl.pathname || "/").replace(/^\/+|\/+$/g, "");
  const method = req.method;
  const segments = path === "" ? [] : path.split("/");

  // HEALTH
  if (path === "health" && method === "GET") {
    return sendJson(res, 200, { status: "ok" });
  }

  // DB connection
  let conn;
  try {
    conn = await pool.getConnection();
  } catch (err) {
    return sendJson(res, 500, {
      error: "DB Connection failed",
      details: err.message,
    });
  }

  try {
    // GET /questions
    if (method === "GET" && segments.length === 1 && segments[0] === "questions") {
      try {
        const [rows] = await conn.execute(
          `SELECT id, question_text, option_a, option_b, option_c, option_d
           FROM questions
           ORDER BY id ASC`
        );
        return sendJson(res, 200, rows);
      } catch (err) {
        return sendJson(res, 500, { error: "Query failed", details: err.message });
      }
    }

    // POST /questions?token=... (staff only)
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
        return sendJson(res, 400, { error: "All options and question_text are required" });
      }

      if (!["A", "B", "C", "D"].includes(correctOption)) {
        return sendJson(res, 400, { error: "correct_option must be one of A, B, C, D" });
      }

      try {
        const [resIns] = await conn.execute(
          `INSERT INTO questions
           (question_text, option_a, option_b, option_c, option_d, correct_option)
           VALUES (?, ?, ?, ?, ?, ?)`,
          [questionText, optionA, optionB, optionC, optionD, correctOption]
        );
        const newId = resIns.insertId;
        return sendJson(res, 200, { message: "Question created", id: newId });
      } catch (err) {
        return sendJson(res, 500, { error: "Insert failed", details: err.message });
      }
    }

    // POST /submit?token=...
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
        return sendJson(res, 400, { error: "answers must be a non-empty array" });
      }

      // collect unique question ids
      const questionIdsSet = new Set();
      for (const ans of answers) {
        if (typeof ans.question_id === "undefined" || typeof ans.selected_option === "undefined") {
          return sendJson(res, 400, { error: "Each answer must have question_id and selected_option" });
        }
        const qid = parseInt(ans.question_id, 10);
        if (isNaN(qid)) {
          return sendJson(res, 400, { error: "question_id must be integer" });
        }
        questionIdsSet.add(qid);
      }
      const questionIds = Array.from(questionIdsSet);
      if (questionIds.length === 0) {
        return sendJson(res, 400, { error: "No valid question_id provided" });
      }

      // fetch correct_option for the questions (build placeholders)
      try {
        const placeholders = questionIds.map(_ => '?').join(',');
        const [rows] = await conn.execute(
          `SELECT id, correct_option FROM questions WHERE id IN (${placeholders})`,
          questionIds
        );
        const questionsMap = {};
        for (const r of rows) questionsMap[r.id] = (r.correct_option || "").toString().trim().toUpperCase();
        if (Object.keys(questionsMap).length === 0) {
          return sendJson(res, 400, { error: "No matching questions found for provided IDs" });
        }

        let totalQuestions = 0;
        let correctAnswers = 0;
        const answersResult = [];

        for (const ans of answers) {
          const qid = parseInt(ans.question_id, 10);
          const sel = (ans.selected_option || "").toString().trim().toUpperCase();
          const correctOpt = questionsMap[qid] || null;
          const isCorrect = correctOpt ? (sel === correctOpt) : false;

          totalQuestions++;
          if (isCorrect) correctAnswers++;

          answersResult.push({
            question_id: qid,
            selected_option: sel,
            is_correct: isCorrect,
            correct_option: correctOpt,
          });
        }

        // Save submission + answers within transaction
        try {
          await conn.beginTransaction();

          const [subRes] = await conn.execute(
            `INSERT INTO submissions (username, total_questions, correct_answers)
             VALUES (?, ?, ?)`,
            [username, totalQuestions, correctAnswers]
          );
          const submissionId = subRes.insertId;

          const insertAnswerSql = `
            INSERT INTO submission_answers
            (submission_id, question_id, selected_option, is_correct)
            VALUES (?, ?, ?, ?)
          `;
          for (const ar of answersResult) {
            await conn.execute(insertAnswerSql, [
              submissionId,
              ar.question_id,
              ar.selected_option,
              ar.is_correct ? 1 : 0,
            ]);
          }

          await conn.commit();

          return sendJson(res, 200, {
            username,
            submission_id: submissionId,
            total_questions: totalQuestions,
            correct_answers: correctAnswers,
            answers: answersResult,
          });
        } catch (err) {
          try { await conn.rollback(); } catch (_) {}
          return sendJson(res, 500, { error: "Submission save failed", details: err.message });
        }
      } catch (err) {
        return sendJson(res, 500, { error: "Question lookup failed", details: err.message });
      }
    }

    // NOT FOUND
    return sendJson(res, 404, { error: "Not Found" });

  } finally {
    if (conn) conn.release();
  }
});

// ---------- START ----------
server.listen(PORT, "0.0.0.0", () => {
  console.log(`Node test service (MySQL) running on http://0.0.0.0:${PORT}`);
});
