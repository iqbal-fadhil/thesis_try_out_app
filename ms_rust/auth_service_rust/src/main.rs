use axum::{
    extract::{Query, State},
    routing::{get, post},
    Json, Router,
};
use deadpool_postgres::{Manager, Pool};
use once_cell::sync::Lazy;
use serde::{Deserialize, Serialize};
use std::net::SocketAddr;
use tokio_postgres::{Config, NoTls};
use uuid::Uuid;
use std::env;
use axum::http::HeaderValue;
use axum::http::Method;
use tower_http::cors::CorsLayer;
// use bcrypt::BcryptError;

// If you uploaded a screenshot and want to reference the local path, here's the path saved earlier.
// The container/local path (from your upload) is:
// const UPLOADED_IMAGE_PATH: &str = "/mnt/data/Screen Shot 2025-11-24 at 13.18.51.png";

static DB_POOL: Lazy<Pool> = Lazy::new(|| {
    // Read DB config from environment, fallback to defaults
    let mut cfg = Config::new();
    cfg.host(&env::var("PGHOST").unwrap_or_else(|_| "127.0.0.1".to_string()));
    cfg.port(env::var("PGPORT").ok().and_then(|p| p.parse().ok()).unwrap_or(5432));
    cfg.user(&env::var("PGUSER").unwrap_or_else(|_| "ms_rust_user".to_string()));
    cfg.password(&env::var("PGPASSWORD").unwrap_or_else(|_| "yourStrongPassword123".to_string()));
    cfg.dbname(&env::var("PGDATABASE").unwrap_or_else(|_| "auth_rust_service_db".to_string()));

    let mgr = Manager::new(cfg, NoTls);
    Pool::builder(mgr)
        .max_size(env::var("DB_POOL_MAX").ok().and_then(|v| v.parse().ok()).unwrap_or(16))
        .build()
        .expect("Failed to build DB pool")
});

#[derive(Clone)]
struct AppState {
    pool: Pool,
}

// --------- Request / Response Models ---------

#[derive(Deserialize)]
struct RegisterRequest {
    username: String,
    password: String,
    email: Option<String>,
    first_name: Option<String>,
    last_name: Option<String>,
    is_staff: Option<bool>,
}

#[derive(Deserialize)]
struct LoginRequest {
    username: String, // username or email
    password: String,
}

#[derive(Serialize)]
struct LoginResponse {
    token: String,
    is_staff: bool,
}

#[derive(Deserialize)]
struct TokenQuery {
    token: String,
}

#[derive(Serialize)]
struct HealthResponse {
    status: String,
}

#[derive(Serialize)]
struct ValidResponse {
    valid: bool,
}

#[derive(Serialize)]
struct ErrorResponse {
    error: String,
    details: Option<String>,
}

#[derive(Serialize)]
struct MeResponse {
    username: String,
    email: Option<String>,
    first_name: Option<String>,
    last_name: Option<String>,
    is_staff: bool,
}

// --------- Handlers ---------

// GET /healthz (no DB)
async fn healthz() -> Json<HealthResponse> {
    Json(HealthResponse {
        status: "ok".to_string(),
    })
}

// POST /api/auth/register
async fn register(
    State(state): State<AppState>,
    Json(payload): Json<RegisterRequest>,
) -> Result<Json<serde_json::Value>, (axum::http::StatusCode, Json<ErrorResponse>)> {
    if payload.username.is_empty() || payload.password.is_empty() {
        return Err((
            axum::http::StatusCode::BAD_REQUEST,
            Json(ErrorResponse {
                error: "username and password are required".to_string(),
                details: None,
            }),
        ));
    }

    let hashed = match bcrypt::hash(&payload.password, 10) {
        Ok(h) => h,
        Err(e) => {
            return Err((
                axum::http::StatusCode::INTERNAL_SERVER_ERROR,
                Json(ErrorResponse {
                    error: "Hashing failed".to_string(),
                    details: Some(e.to_string()),
                }),
            ))
        }
    };

    let client = state
        .pool
        .get()
        .await
        .map_err(|e| {
            (
                axum::http::StatusCode::INTERNAL_SERVER_ERROR,
                Json(ErrorResponse {
                    error: "DB Connection failed".to_string(),
                    details: Some(e.to_string()),
                }),
            )
        })?;

    let stmt = client
        .prepare(
            "INSERT INTO users (username, password, email, first_name, last_name, is_staff)
             VALUES ($1, $2, $3, $4, $5, $6)",
        )
        .await
        .map_err(|e| {
            (
                axum::http::StatusCode::INTERNAL_SERVER_ERROR,
                Json(ErrorResponse {
                    error: "Prepare failed".to_string(),
                    details: Some(e.to_string()),
                }),
            )
        })?;

    let is_staff = payload.is_staff.unwrap_or(false);

    client
        .execute(
            &stmt,
            &[
                &payload.username,
                &hashed,
                &payload.email,
                &payload.first_name,
                &payload.last_name,
                &is_staff,
            ],
        )
        .await
        .map_err(|e| {
            (
                axum::http::StatusCode::INTERNAL_SERVER_ERROR,
                Json(ErrorResponse {
                    error: "Insert failed".to_string(),
                    details: Some(e.to_string()),
                }),
            )
        })?;

    Ok(Json(serde_json::json!({
        "message": "User Registered"
    })))
}

// POST /api/auth/login
async fn login(
    State(state): State<AppState>,
    Json(payload): Json<LoginRequest>,
) -> Result<Json<LoginResponse>, (axum::http::StatusCode, Json<ErrorResponse>)> {
    if payload.username.is_empty() || payload.password.is_empty() {
        return Err((
            axum::http::StatusCode::BAD_REQUEST,
            Json(ErrorResponse {
                error: "username and password are required".to_string(),
                details: None,
            }),
        ));
    }

    let client = state
        .pool
        .get()
        .await
        .map_err(|e| {
            (
                axum::http::StatusCode::INTERNAL_SERVER_ERROR,
                Json(ErrorResponse {
                    error: "DB Connection failed".to_string(),
                    details: Some(e.to_string()),
                }),
            )
        })?;

    let stmt = client
        .prepare(
            "SELECT username, password, email, first_name, last_name, is_staff
             FROM users
             WHERE LOWER(username) = LOWER($1) OR LOWER(email) = LOWER($1)
             LIMIT 1",
        )
        .await
        .map_err(|e| {
            (
                axum::http::StatusCode::INTERNAL_SERVER_ERROR,
                Json(ErrorResponse {
                    error: "Prepare failed".to_string(),
                    details: Some(e.to_string()),
                }),
            )
        })?;

    let row = client
        .query_opt(&stmt, &[&payload.username])
        .await
        .map_err(|e| {
            (
                axum::http::StatusCode::INTERNAL_SERVER_ERROR,
                Json(ErrorResponse {
                    error: "Query failed".to_string(),
                    details: Some(e.to_string()),
                }),
            )
        })?;

    let row = match row {
        Some(r) => r,
        None => {
            return Err((
                axum::http::StatusCode::UNAUTHORIZED,
                Json(ErrorResponse {
                    error: "Invalid credentials".to_string(),
                    details: None,
                }),
            ))
        }
    };

    let stored_hash: String = row.get("password");
    let is_valid = bcrypt::verify(&payload.password, &stored_hash).unwrap_or(false);
    if !is_valid {
        return Err((
            axum::http::StatusCode::UNAUTHORIZED,
            Json(ErrorResponse {
                error: "Invalid credentials".to_string(),
                details: None,
            }),
        ));
    }

    let username: String = row.get("username");
    let is_staff: bool = row.get("is_staff");

    let token = Uuid::new_v4().to_string();

    let stmt_insert = client
        .prepare("INSERT INTO tokens (token, username) VALUES ($1, $2)")
        .await
        .map_err(|e| {
            (
                axum::http::StatusCode::INTERNAL_SERVER_ERROR,
                Json(ErrorResponse {
                    error: "Prepare failed".to_string(),
                    details: Some(e.to_string()),
                }),
            )
        })?;

    client
        .execute(&stmt_insert, &[&token, &username])
        .await
        .map_err(|e| {
            (
                axum::http::StatusCode::INTERNAL_SERVER_ERROR,
                Json(ErrorResponse {
                    error: "Insert token failed".to_string(),
                    details: Some(e.to_string()),
                }),
            )
        })?;

    Ok(Json(LoginResponse { token, is_staff }))
}

// GET /api/auth/validate?token=...
async fn validate_token(
    State(state): State<AppState>,
    Query(q): Query<TokenQuery>,
) -> Result<Json<ValidResponse>, (axum::http::StatusCode, Json<ErrorResponse>)> {
    let client = state
        .pool
        .get()
        .await
        .map_err(|e| {
            (
                axum::http::StatusCode::INTERNAL_SERVER_ERROR,
                Json(ErrorResponse {
                    error: "DB Connection failed".to_string(),
                    details: Some(e.to_string()),
                }),
            )
        })?;

    let stmt = client
        .prepare("SELECT 1 FROM tokens WHERE token = $1 LIMIT 1")
        .await
        .map_err(|e| {
            (
                axum::http::StatusCode::INTERNAL_SERVER_ERROR,
                Json(ErrorResponse {
                    error: "Prepare failed".to_string(),
                    details: Some(e.to_string()),
                }),
            )
        })?;

    let row = client
        .query_opt(&stmt, &[&q.token])
        .await
        .map_err(|e| {
            (
                axum::http::StatusCode::INTERNAL_SERVER_ERROR,
                Json(ErrorResponse {
                    error: "Query failed".to_string(),
                    details: Some(e.to_string()),
                }),
            )
        })?;

    Ok(Json(ValidResponse {
        valid: row.is_some(),
    }))
}

// GET /api/auth/me?token=...
async fn get_me(
    State(state): State<AppState>,
    Query(q): Query<TokenQuery>,
) -> Result<Json<MeResponse>, (axum::http::StatusCode, Json<ErrorResponse>)> {
    let client = state
        .pool
        .get()
        .await
        .map_err(|e| {
            (
                axum::http::StatusCode::INTERNAL_SERVER_ERROR,
                Json(ErrorResponse {
                    error: "DB Connection failed".to_string(),
                    details: Some(e.to_string()),
                }),
            )
        })?;

    let stmt = client
        .prepare(
            "SELECT u.username, u.email, u.first_name, u.last_name, u.is_staff
             FROM users u
             JOIN tokens t ON t.username = u.username
             WHERE t.token = $1
             LIMIT 1",
        )
        .await
        .map_err(|e| {
            (
                axum::http::StatusCode::INTERNAL_SERVER_ERROR,
                Json(ErrorResponse {
                    error: "Prepare failed".to_string(),
                    details: Some(e.to_string()),
                }),
            )
        })?;

    let row = client
        .query_opt(&stmt, &[&q.token])
        .await
        .map_err(|e| {
            (
                axum::http::StatusCode::INTERNAL_SERVER_ERROR,
                Json(ErrorResponse {
                    error: "Query failed".to_string(),
                    details: Some(e.to_string()),
                }),
            )
        })?;

    let row = match row {
        Some(r) => r,
        None => {
            return Err((
                axum::http::StatusCode::UNAUTHORIZED,
                Json(ErrorResponse {
                    error: "Invalid token".to_string(),
                    details: None,
                }),
            ))
        }
    };

    let username: String = row.get("username");
    let email: Option<String> = row.get("email");
    let first_name: Option<String> = row.get("first_name");
    let last_name: Option<String> = row.get("last_name");
    let is_staff: bool = row.get("is_staff");

    Ok(Json(MeResponse {
        username,
        email,
        first_name,
        last_name,
        is_staff,
    }))
}

// --------- MAIN ---------

#[tokio::main]
async fn main() {
    let state = AppState {
        pool: DB_POOL.clone(),
    };

    // CORS configuration
    let cors = CorsLayer::new()
        .allow_origin([
            "https://microservices.iqbalfadhil.biz.id".parse::<HeaderValue>().unwrap(),
            "https://auth-microservices.iqbalfadhil.biz.id".parse::<HeaderValue>().unwrap(),
            "http://localhost:3000".parse::<HeaderValue>().unwrap(),
            "http://127.0.0.1:3000".parse::<HeaderValue>().unwrap(),
        ])
        .allow_methods([Method::GET, Method::POST, Method::OPTIONS])
        .allow_headers([axum::http::header::CONTENT_TYPE, axum::http::header::AUTHORIZATION])
        .allow_credentials(true);

    let app = Router::new()
        .route("/healthz", get(healthz))
        .route("/api/auth/register", post(register))
        .route("/api/auth/login", post(login))
        .route("/api/auth/validate", get(validate_token))
        .route("/api/auth/me", get(get_me))
        .with_state(state)
        .layer(cors);

    let addr = SocketAddr::from(([0, 0, 0, 0], 8003));
    println!("Rust auth service running on http://0.0.0.0:8003");
    // axum::Server::bind(&addr)
    //     .serve(app.into_make_service())
    //     .await
    //     .unwrap();

    let listener = tokio::net::TcpListener::bind(addr).await.unwrap();

    axum::serve(listener, app)
        .await
        .unwrap();

}
