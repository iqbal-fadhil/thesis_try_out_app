use axum::{
    extract::{Path, Query, State},
    routing::{get, post},
    Json, Router,
};
use deadpool_postgres::{Manager, Pool};
use once_cell::sync::Lazy;
use serde::{Deserialize, Serialize};
use std::net::SocketAddr;
use tokio::net::TcpListener;
use tokio_postgres::{Config, NoTls};

// --------------- CONFIG & GLOBALS ---------------

// DB config (user_service DB)
static DB_POOL: Lazy<Pool> = Lazy::new(|| {
    let mut cfg = Config::new();
    cfg.host("127.0.0.1");
    cfg.port(5432);
    cfg.user("ms_user_user"); // adjust if needed
    cfg.password("yourStrongPassword123"); // adjust
    cfg.dbname("user_service");

    let mgr = Manager::new(cfg, NoTls);
    Pool::builder(mgr)
        .max_size(16)
        .build()
        .expect("Failed to create DB pool")
});

// Auth service base URL
const AUTH_BASE_URL: &str = "http://127.0.0.1:8003";

#[derive(Clone)]
struct AppState {
    pool: Pool,
}

// --------------- MODELS ---------------

#[derive(Serialize)]
struct HealthResponse {
    status: String,
}

#[derive(Serialize)]
struct ErrorResponse {
    error: String,
    details: Option<String>,
}

#[derive(Serialize)]
struct UserProfile {
    username: String,
    email: Option<String>,
    full_name: Option<String>,
    score: i32,
}

#[derive(Serialize, Deserialize, Debug, Clone)]
struct AuthMeResponse {
    username: String,
    email: Option<String>,
    first_name: Option<String>,
    last_name: Option<String>,
    is_staff: bool,
}

#[derive(Deserialize)]
struct TokenQuery {
    token: String,
}

#[derive(Deserialize)]
struct ScoreUpdateRequest {
    score_increment: i32,
}

#[derive(Serialize)]
struct ScoreUpdateResponse {
    username: String,
    new_score: i32,
    increment: i32,
}

// --------------- HELPERS ---------------

async fn get_auth_user_from_token(token: &str) -> Option<AuthMeResponse> {
    if token.is_empty() {
        return None;
    }

    let client = reqwest::Client::new();
    let url = format!("{}/api/auth/me", AUTH_BASE_URL);

    let resp = client
        .get(&url)
        .query(&[("token", token)])
        .send()
        .await
        .ok()?;

    if !resp.status().is_success() {
        return None;
    }

    let json_val: serde_json::Value = resp.json().await.ok()?;
    if json_val.get("error").is_some() {
        return None;
    }

    serde_json::from_value(json_val).ok()
}

// --------------- HANDLERS ---------------

// GET /healthz
async fn healthz() -> Json<HealthResponse> {
    Json(HealthResponse {
        status: "ok".to_string(),
    })
}

// GET /users?token=... (staff only)
async fn get_all_users(
    State(state): State<AppState>,
    Query(q): Query<TokenQuery>,
) -> Result<Json<Vec<UserProfile>>, (axum::http::StatusCode, Json<ErrorResponse>)> {
    let token = q.token;

    let auth_user = get_auth_user_from_token(&token).await;
    if auth_user.is_none() {
        return Err((
            axum::http::StatusCode::UNAUTHORIZED,
            Json(ErrorResponse {
                error: "Invalid token".to_string(),
                details: None,
            }),
        ));
    }

    let auth_user = auth_user.unwrap();
    if !auth_user.is_staff {
        return Err((
            axum::http::StatusCode::FORBIDDEN,
            Json(ErrorResponse {
                error: "Forbidden: staff only".to_string(),
                details: None,
            }),
        ));
    }

    let client = state.pool.get().await.map_err(|e| {
        (
            axum::http::StatusCode::INTERNAL_SERVER_ERROR,
            Json(ErrorResponse {
                error: "DB Connection failed".to_string(),
                details: Some(e.to_string()),
            }),
        )
    })?;

    let rows = client
        .query(
            "SELECT username, email, full_name, score FROM user_profiles ORDER BY id ASC",
            &[],
        )
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

    let users = rows
        .into_iter()
        .map(|row| UserProfile {
            username: row.get("username"),
            email: row.get("email"),
            full_name: row.get("full_name"),
            score: row.get("score"),
        })
        .collect();

    Ok(Json(users))
}

// GET /users/:username (public)
async fn get_user_by_username(
    State(state): State<AppState>,
    Path(username): Path<String>,
) -> Result<Json<UserProfile>, (axum::http::StatusCode, Json<ErrorResponse>)> {
    let client = state.pool.get().await.map_err(|e| {
        (
            axum::http::StatusCode::INTERNAL_SERVER_ERROR,
            Json(ErrorResponse {
                error: "DB Connection failed".to_string(),
                details: Some(e.to_string()),
            }),
        )
    })?;

    let row = client
        .query_opt(
            "SELECT username, email, full_name, score FROM user_profiles WHERE username = $1 LIMIT 1",
            &[&username],
        )
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
                axum::http::StatusCode::NOT_FOUND,
                Json(ErrorResponse {
                    error: "User not found".to_string(),
                    details: None,
                }),
            ))
        }
    };

    let user = UserProfile {
        username: row.get("username"),
        email: row.get("email"),
        full_name: row.get("full_name"),
        score: row.get("score"),
    };

    Ok(Json(user))
}

// POST /users/:username/score?token=... (self only)
async fn update_score(
    State(state): State<AppState>,
    Path(username): Path<String>,
    Query(q): Query<TokenQuery>,
    Json(payload): Json<ScoreUpdateRequest>,
) -> Result<Json<ScoreUpdateResponse>, (axum::http::StatusCode, Json<ErrorResponse>)> {
    let token = q.token;

    if payload.score_increment == 0 {
        return Err((
            axum::http::StatusCode::BAD_REQUEST,
            Json(ErrorResponse {
                error: "score_increment must be non-zero".to_string(),
                details: None,
            }),
        ));
    }

    let auth_user = get_auth_user_from_token(&token).await;
    if auth_user.is_none() {
        return Err((
            axum::http::StatusCode::UNAUTHORIZED,
            Json(ErrorResponse {
                error: "Invalid token".to_string(),
                details: None,
            }),
        ));
    }

    let auth_user = auth_user.unwrap();
    if auth_user.username != username {
        return Err((
            axum::http::StatusCode::FORBIDDEN,
            Json(ErrorResponse {
                error: "Forbidden: can only update own score".to_string(),
                details: None,
            }),
        ));
    }

    let mut client = state.pool.get().await.map_err(|e| {
        (
            axum::http::StatusCode::INTERNAL_SERVER_ERROR,
            Json(ErrorResponse {
                error: "DB Connection failed".to_string(),
                details: Some(e.to_string()),
            }),
        )
    })?;

    let transaction = client.transaction().await.map_err(|e| {
        (
            axum::http::StatusCode::INTERNAL_SERVER_ERROR,
            Json(ErrorResponse {
                error: "Transaction start failed".to_string(),
                details: Some(e.to_string()),
            }),
        )
    })?;

    let row = transaction
        .query_opt(
            "SELECT score FROM user_profiles WHERE username = $1 FOR UPDATE",
            &[&username],
        )
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

    let new_score: i32;

    if let Some(r) = row {
        let current: i32 = r.get("score");
        new_score = current + payload.score_increment;
        transaction
            .execute(
                "UPDATE user_profiles SET score = $1 WHERE username = $2",
                &[&new_score, &username],
            )
            .await
            .map_err(|e| {
                (
                    axum::http::StatusCode::INTERNAL_SERVER_ERROR,
                    Json(ErrorResponse {
                        error: "Update failed".to_string(),
                        details: Some(e.to_string()),
                    }),
                )
            })?;
    } else {
        new_score = payload.score_increment;
        transaction
            .execute(
                "INSERT INTO user_profiles (username, score) VALUES ($1, $2)",
                &[&username, &new_score],
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
    }

    transaction.commit().await.map_err(|e| {
        (
            axum::http::StatusCode::INTERNAL_SERVER_ERROR,
            Json(ErrorResponse {
                error: "Commit failed".to_string(),
                details: Some(e.to_string()),
            }),
        )
    })?;

    Ok(Json(ScoreUpdateResponse {
        username,
        new_score,
        increment: payload.score_increment,
    }))
}

// --------------- MAIN ---------------

#[tokio::main]
async fn main() {
    let state = AppState {
        pool: DB_POOL.clone(),
    };

    let app = Router::new()
        .route("/healthz", get(healthz))
        .route("/users", get(get_all_users))
        .route("/users/:username", get(get_user_by_username))
        .route("/users/:username/score", post(update_score))
        .with_state(state);

    let addr = SocketAddr::from(([0, 0, 0, 0], 8022));
    println!("Rust user service running on http://0.0.0.0:8022");

    let listener = TcpListener::bind(addr).await.unwrap();
    axum::serve(listener, app).await.unwrap();
}
