// ==========================================
// Node.js User Service (single file)
// Endpoints:
//  GET  /healthz
//  GET  /users?token=...                (staff only)
//  GET  /users/:username                (public)
//  POST /users/:username/score?token=.. (self only)
// Run: node index.js
// ==========================================

const http = require("http");
const url = require("url");
const { Pool } = require("pg");

// ---------- CONFIG ----------
const PORT = 8021;

const pool = new Pool({
  host: "127.0.0.1",
  port: 5432,
  user: "ms_nodejs_user",               // change if needed
  password: "yourStrongPassword123",  // change if needed
  database: "user_nodejs_service",
});

// Auth service (Go) base URL
const AUTH_BASE_URL = "http://127.0.0.1:8011"; // or http://157.15.125.7:8011

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

    const req = http.request(options, (res) => {
      let data = "";
      res.on("data", chunk => (data += chunk.toString()));
      res.on("end", () => {
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

  // -------- HEALTHZ (no DB, no auth) --------
  if (path === "healthz" && method === "GET") {
    return sendJson(res, 200, { status: "ok" });
  }

  // Anything below needs DB
  let client;
  try {
    client = await pool.connect();
  } catch (err) {
    return sendJson(res, 500, { error: "DB Connection failed", details: err.message });
  }

  try {
    // -------- GET /users?token=... (staff only) --------
    if (method === "GET" && segments.length === 1 && segments[0] === "users") {
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

      let result;
      try {
        result = await client.query(
          "SELECT username, email, full_name, score FROM user_profiles ORDER BY id ASC"
        );
      } catch (err) {
        return sendJson(res, 500, { error: "Query failed", details: err.message });
      }

      return sendJson(res, 200, result.rows);
    }

    // -------- GET /users/:username (public) --------
    if (method === "GET" && segments.length === 2 && segments[0] === "users") {
      const username = segments[1];

      let result;
      try {
        result = await client.query(
          "SELECT username, email, full_name, score FROM user_profiles WHERE username = $1 LIMIT 1",
          [username]
        );
      } catch (err) {
        return sendJson(res, 500, { error: "Query failed", details: err.message });
      }

      if (result.rows.length === 0) {
        return sendJson(res, 404, { error: "User not found" });
      }

      return sendJson(res, 200, result.rows[0]);
    }

    // -------- POST /users/:username/score?token=... (self only) --------
    if (
      method === "POST" &&
      segments.length === 3 &&
      segments[0] === "users" &&
      segments[2] === "score"
    ) {
      const username = segments[1];
      const token = parsedUrl.query.token;

      if (!token) {
        return sendJson(res, 400, { error: "Token missing" });
      }

      const authUser = await getUserFromToken(token);
      if (!authUser) {
        return sendJson(res, 401, { error: "Invalid token" });
      }

      const tokenUsername = authUser.username;
      if (tokenUsername !== username) {
        return sendJson(res, 403, { error: "Forbidden: can only update own score" });
      }

      let body;
      try {
        body = await parseBody(req);
      } catch (err) {
        return sendJson(res, 400, { error: "Invalid JSON body" });
      }

      const increment = parseInt(body.score_increment, 10);
      if (!increment || isNaN(increment)) {
        return sendJson(res, 400, { error: "score_increment must be non-zero integer" });
      }

      try {
        await client.query("BEGIN");

        const result = await client.query(
          "SELECT score FROM user_profiles WHERE username = $1 FOR UPDATE",
          [username]
        );

        let newScore;
        if (result.rows.length === 0) {
          newScore = increment;
          await client.query(
            "INSERT INTO user_profiles (username, score) VALUES ($1, $2)",
            [username, newScore]
          );
        } else {
          const current = parseInt(result.rows[0].score, 10) || 0;
          newScore = current + increment;
          await client.query(
            "UPDATE user_profiles SET score = $1 WHERE username = $2",
            [newScore, username]
          );
        }

        await client.query("COMMIT");

        return sendJson(res, 200, {
          username: username,
          new_score: newScore,
          increment: increment,
        });
      } catch (err) {
        try {
          await client.query("ROLLBACK");
        } catch (_) {}
        return sendJson(res, 500, { error: "Update failed", details: err.message });
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
  console.log(`Node user service running on http://0.0.0.0:${PORT}`);
});
