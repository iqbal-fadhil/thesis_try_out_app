// ==========================================
// Minimal Node.js Auth Microservice (MySQL)
// Run: node index.js
// ==========================================

const http = require("http");
const url = require("url");
const mysql = require("mysql2/promise");
const bcrypt = require("bcryptjs");
const crypto = require("crypto");

// ---------- CONFIG ----------
const PORT = 8003;

const pool = mysql.createPool({
  host: "127.0.0.1",
  port: 3306,
  user: "ms_nodejs_user",            // ganti sesuai kebutuhan
  password: "StrongPassw0rd!", // ganti
  database: "auth_nodejs_service_db",
  waitForConnections: true,
  connectionLimit: 10,
  queueLimit: 0,
});

// ---------- HELPERS ----------
function sendJson(res, statusCode, data) {
  res.writeHead(statusCode, { "Content-Type": "application/json" });
  res.end(JSON.stringify(data));
}

function parseBody(req) {
  return new Promise((resolve, reject) => {
    let body = "";
    req.on("data", chunk => (body += chunk.toString()));
    req.on("end", () => {
      if (!body) return resolve({});
      try {
        resolve(JSON.parse(body));
      } catch (err) {
        reject(err);
      }
    });
  });
}

function generateToken() {
  return crypto.randomBytes(32).toString("hex");
}

// ---------- ROUTER ----------
const allowedOrigins = [
  "https://microservices.iqbalfadhil.biz.id",
  "https://auth-microservices.iqbalfadhil.biz.id",
  "http://localhost:3000",
  "http://127.0.0.1:3000"
];

const server = http.createServer(async (req, res) => {
  const origin = req.headers.origin;

  if (allowedOrigins.includes(origin)) {
    res.setHeader("Access-Control-Allow-Origin", origin);
  }

  res.setHeader("Vary", "Origin");
  res.setHeader("Access-Control-Allow-Credentials", "true");
  res.setHeader(
    "Access-Control-Allow-Headers",
    "Content-Type, Authorization, X-Requested-With"
  );
  res.setHeader(
    "Access-Control-Allow-Methods",
    "GET, POST, OPTIONS, PUT, DELETE"
  );

  // OPTIONS preflight
  if (req.method === "OPTIONS") {
    res.writeHead(204);
    return res.end();
  }

  const parsedUrl = url.parse(req.url, true);
  const path = parsedUrl.pathname;
  const method = req.method;

  // HEALTHCHECK
  if (path === "/healthz" && method === "GET") {
    return sendJson(res, 200, { status: "ok" });
  }

  // DB Connection
  let conn;
  try {
    conn = await pool.getConnection();
  } catch (err) {
    return sendJson(res, 500, { error: "DB Connection failed", details: err.message });
  }

  try {
    // REGISTER
    if (path === "/api/auth/register" && method === "POST") {
      const body = await parseBody(req);

      const { username, password, email, first_name, last_name, is_staff } = body;

      if (!username || !password) {
        conn.release();
        return sendJson(res, 400, { error: "username and password are required" });
      }

      const hashed = await bcrypt.hash(password, 10);

      try {
        await conn.execute(
          `INSERT INTO users (username, password, email, first_name, last_name, is_staff)
           VALUES (?, ?, ?, ?, ?, ?)`,
          [
            username,
            hashed,
            email || null,
            first_name || null,
            last_name || null,
            is_staff ? 1 : 0,
          ]
        );
      } catch (err) {
        conn.release();
        return sendJson(res, 500, { error: "Insert failed", details: err.message });
      }

      conn.release();
      return sendJson(res, 200, { message: "User Registered" });
    }

    // LOGIN
    if (path === "/api/auth/login" && method === "POST") {
      const body = await parseBody(req);
      const { username, password } = body;

      if (!username || !password) {
        conn.release();
        return sendJson(res, 400, { error: "username and password are required" });
      }

      const [rows] = await conn.execute(
        `SELECT * FROM users
         WHERE LOWER(username)=LOWER(?) OR LOWER(email)=LOWER(?)
         LIMIT 1`,
        [username, username]
      );

      if (rows.length === 0) {
        conn.release();
        return sendJson(res, 401, { error: "Invalid credentials" });
      }

      const user = rows[0];
      const match = await bcrypt.compare(password, user.password);

      if (!match) {
        conn.release();
        return sendJson(res, 401, { error: "Invalid credentials" });
      }

      const token = generateToken();

      await conn.execute(
        `INSERT INTO tokens (token, username) VALUES (?, ?)`,
        [token, user.username]
      );

      conn.release();
      return sendJson(res, 200, {
        token: token,
        is_staff: !!user.is_staff,
      });
    }

    // VALIDATE TOKEN
    if (path === "/api/auth/validate" && method === "GET") {
      const token = parsedUrl.query.token;
      if (!token) {
        conn.release();
        return sendJson(res, 400, { error: "Token missing" });
      }

      const [rows] = await conn.execute(
        `SELECT 1 FROM tokens WHERE token = ? LIMIT 1`,
        [token]
      );

      conn.release();
      return sendJson(res, 200, { valid: rows.length > 0 });
    }

    // ME
    if (path === "/api/auth/me" && method === "GET") {
      const token = parsedUrl.query.token;
      if (!token) {
        conn.release();
        return sendJson(res, 400, { error: "Token missing" });
      }

      const [rows] = await conn.execute(
        `SELECT u.username, u.email, u.first_name, u.last_name, u.is_staff
         FROM users u
         JOIN tokens t ON t.username = u.username
         WHERE t.token = ?
         LIMIT 1`,
        [token]
      );

      if (rows.length === 0) {
        conn.release();
        return sendJson(res, 401, { error: "Invalid token" });
      }

      conn.release();
      return sendJson(res, 200, rows[0]);
    }

    conn.release();
    return sendJson(res, 404, { error: "Not Found" });

  } catch (err) {
    if (conn) conn.release();
    return sendJson(res, 500, { error: "Internal Server Error", details: err.message });
  }
});

// ---------- START ----------
server.listen(PORT, "0.0.0.0", () => {
  console.log(`Node auth service (MySQL) running at http://0.0.0.0:${PORT}`);
});
