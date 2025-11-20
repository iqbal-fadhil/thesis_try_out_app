// ==========================================
// Minimal Node.js Auth Microservice
// Run: node index.js
// Will listen on 0.0.0.0:8011
// ==========================================

const http = require("http");
const url = require("url");
const { Pool } = require("pg");
const bcrypt = require("bcryptjs");
const crypto = require("crypto");

// ---------- CONFIG ----------
const PORT = 8011;

const pool = new Pool({
  host: "127.0.0.1",
  port: 5432,
  user: "ms_nodejs_user",          // change if needed
  password: "yourStrongPassword123", // change
  database: "auth_nodejs_service_db",
});

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

function generateToken() {
  return crypto.randomBytes(16).toString("hex");
}

// ---------- ROUTER ----------
const server = http.createServer(async (req, res) => {
  const parsedUrl = url.parse(req.url, true);
  const path = parsedUrl.pathname;
  const method = req.method;

  // HEALTHCHECK (no DB)
  if (path === "/healthz" && method === "GET") {
    return sendJson(res, 200, { status: "ok" });
  }

  // Everything below uses DB
  let client;
  try {
    client = await pool.connect();
  } catch (err) {
    return sendJson(res, 500, { error: "DB Connection failed", details: err.message });
  }

  try {
    // ---------------- REGISTER ----------------
    if (path === "/api/auth/register" && method === "POST") {
      const body = await parseBody(req);

      const {
        username,
        password,
        email,
        first_name,
        last_name,
        is_staff,
      } = body;

      if (!username || !password) {
        return sendJson(res, 400, { error: "username and password are required" });
      }

      const hashed = await bcrypt.hash(password, 10);

      const query = `
        INSERT INTO users (username, password, email, first_name, last_name, is_staff)
        VALUES ($1, $2, $3, $4, $5, $6)
      `;
      try {
        await client.query(query, [
          username,
          hashed,
          email || null,
          first_name || null,
          last_name || null,
          is_staff ? true : false,
        ]);
      } catch (err) {
        return sendJson(res, 500, { error: "Insert failed", details: err.message });
      }

      return sendJson(res, 200, { message: "User Registered" });
    }

    // ---------------- LOGIN ----------------
    if (path === "/api/auth/login" && method === "POST") {
      const body = await parseBody(req);
      const { username, password } = body;

      if (!username || !password) {
        return sendJson(res, 400, { error: "username and password are required" });
      }

      const query = `
        SELECT * FROM users
        WHERE LOWER(username) = LOWER($1) OR LOWER(email) = LOWER($1)
        LIMIT 1
      `;
      const result = await client.query(query, [username]);

      if (result.rows.length === 0) {
        return sendJson(res, 401, { error: "Invalid credentials" });
      }

      const user = result.rows[0];

      const match = await bcrypt.compare(password, user.password);
      if (!match) {
        return sendJson(res, 401, { error: "Invalid credentials" });
      }

      const token = generateToken();
      await client.query(
        "INSERT INTO tokens (token, username) VALUES ($1, $2)",
        [token, user.username]
      );

      return sendJson(res, 200, {
        token: token,
        is_staff: !!user.is_staff,
      });
    }

    // ---------------- VALIDATE TOKEN ----------------
    if (path === "/api/auth/validate" && method === "GET") {
      const token = parsedUrl.query.token;
      if (!token) {
        return sendJson(res, 400, { error: "Token missing" });
      }

      const result = await client.query(
        "SELECT * FROM tokens WHERE token = $1",
        [token]
      );

      return sendJson(res, 200, { valid: result.rows.length > 0 });
    }

    // ---------------- GET CURRENT USER (ME) ----------------
    if (path === "/api/auth/me" && method === "GET") {
      const token = parsedUrl.query.token;
      if (!token) {
        return sendJson(res, 400, { error: "Token missing" });
      }

      const query = `
        SELECT u.username, u.email, u.first_name, u.last_name, u.is_staff
        FROM users u
        JOIN tokens t ON t.username = u.username
        WHERE t.token = $1
        LIMIT 1
      `;
      const result = await client.query(query, [token]);

      if (result.rows.length === 0) {
        return sendJson(res, 401, { error: "Invalid token" });
      }

      return sendJson(res, 200, result.rows[0]);
    }

    // ---------------- NOT FOUND ----------------
    return sendJson(res, 404, { error: "Not Found" });

  } catch (err) {
    return sendJson(res, 500, { error: "Internal Server Error", details: err.message });
  } finally {
    if (client) client.release();
  }
});

// ---------- START SERVER ----------
server.listen(PORT, "0.0.0.0", () => {
  console.log(`Node auth service running on http://0.0.0.0:${PORT}`);
});
