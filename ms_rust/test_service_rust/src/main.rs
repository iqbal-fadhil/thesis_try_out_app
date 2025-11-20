use axum::{
    extract::{Query, State},
    routing::{get, post},
    Json, Router,
};
use deadpool_postgres::{Manager, Pool};
use once_cell::sync::Lazy;
use serde::{Deserialize, Serialize};
use std::collections::{HashMap, HashSet};
use std::net::SocketAddr;
use tokio::net::TcpListener;
use tokio_postgres::{Config, NoTls};

// --------------- CONFIG & GLOBALS ---------------

// DB config (user_service DB)
static DB_POOL: Lazy<Pool> = Lazy::new(|| {
    let mut cfg = Config::new();
    cfg.host("127.0.0.1");
    cfg.port(5432);
    cfg.user("ms_rust_user"); // adjust if needed
    cfg.password("yourStrongPassword123"); // adjust
    cfg.dbname("test_rust_service_db");

    let mgr = Manager::new(cfg, NoTls);
    Pool::builder(mgr)
        .max_size(16)
        .build()
        .expect("Failed to create DB pool")
});

// Auth service base URL
const AUTH_BASE_URL: &str = "http://127.0.0.1:8012";

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
struct Question {
    id: i32,
    question_text: String,
    option_a: String,
    option_b: String,
    option_c: String,
    option_d: String,
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
struct CreateQuestionRequest {
    question_text: String,
    option_a: String,
    option_b: String,
    option_c: String,
    option_d: String,
    correct_option: String, // A/B/C/D
}

#[derive(Serialize)]
struct CreateQuestionResponse {
    message: String,
    id: i32,
}

#[derive(Deserialize)]
struct AnswerInput {
    question_id: i32,
    selected_option: String,
}

#[derive(Deserialize)]
struct SubmitRequest {
    answers: Vec<AnswerInput>,
}

#[derive(Serialize)]
struct AnswerResult {
    question_id: i32,
    selected_option: String,
    is_correct: bool,
    correct_option: Option<String>,
}

#[derive(Serialize)]
struct SubmitResponse {
    username: String,
    submission_id: i32,
    total_questions: i32,
    correct_answers: i32,
    answers: Vec<AnswerResult>,
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

// GET /health
async fn health() -> Json<HealthResponse> {
    Json(HealthResponse {
        status: "ok".to_string(),
    })
}

// GET /questions
async fn get_questions(
    State(state): State<AppState>,
) -> Result<Json<Vec<Question>>, (axum::http::StatusCode, Json<ErrorResponse>)> {
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
            "SELECT id, question_text, option_a, option_b, option_c, option_d
             FROM questions
             ORDER BY id ASC",
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

    let questions = rows
        .into_iter()
        .map(|row| Question {
            id: row.get("id"),
            question_text: row.get("question_text"),
            option_a: row.get("option_a"),
            option_b: row.get("option_b"),
            option_c: row.get("option_c"),
            option_d: row.get("option_d"),
        })
        .collect();

    Ok(Json(questions))
}

// POST /questions?token=...  (staff only)
async fn create_question(
    State(state): State<AppState>,
    Query(q): Query<TokenQuery>,
    Json(payload): Json<CreateQuestionRequest>,
) -> Result<Json<CreateQuestionResponse>, (axum::http::StatusCode, Json<ErrorResponse>)> {
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

    // Validate payload
    if payload.question_text.trim().is_empty()
        || payload.option_a.trim().is_empty()
        || payload.option_b.trim().is_empty()
        || payload.option_c.trim().is_empty()
        || payload.option_d.trim().is_empty()
    {
        return Err((
            axum::http::StatusCode::BAD_REQUEST,
            Json(ErrorResponse {
                error: "All options and question_text are required".to_string(),
                details: None,
            }),
        ));
    }

    let correct_opt = payload.correct_option.trim().to_uppercase();
    if !["A", "B", "C", "D"].contains(&correct_opt.as_str()) {
        return Err((
            axum::http::StatusCode::BAD_REQUEST,
            Json(ErrorResponse {
                error: "correct_option must be one of A, B, C, D".to_string(),
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

    let row = client
        .query_one(
            "INSERT INTO questions
             (question_text, option_a, option_b, option_c, option_d, correct_option)
             VALUES ($1, $2, $3, $4, $5, $6)
             RETURNING id",
            &[
                &payload.question_text,
                &payload.option_a,
                &payload.option_b,
                &payload.option_c,
                &payload.option_d,
                &correct_opt,
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

    let new_id: i32 = row.get("id");

    Ok(Json(CreateQuestionResponse {
        message: "Question created".to_string(),
        id: new_id,
    }))
}

// POST /submit?token=...
async fn submit_answers(
    State(state): State<AppState>,
    Query(q): Query<TokenQuery>,
    Json(payload): Json<SubmitRequest>,
) -> Result<Json<SubmitResponse>, (axum::http::StatusCode, Json<ErrorResponse>)> {
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
    let username = auth_user.username;

    if payload.answers.is_empty() {
        return Err((
            axum::http::StatusCode::BAD_REQUEST,
            Json(ErrorResponse {
                error: "answers must be a non-empty array".to_string(),
                details: None,
            }),
        ));
    }

    // Unique question_ids
    let mut qids_set: HashSet<i32> = HashSet::new();
    for ans in &payload.answers {
        qids_set.insert(ans.question_id);
    }

    if qids_set.is_empty() {
        return Err((
            axum::http::StatusCode::BAD_REQUEST,
            Json(ErrorResponse {
                error: "No valid question_id provided".to_string(),
                details: None,
            }),
        ));
    }

    let question_ids: Vec<i32> = qids_set.into_iter().collect();

    let client = state.pool.get().await.map_err(|e| {
        (
            axum::http::StatusCode::INTERNAL_SERVER_ERROR,
            Json(ErrorResponse {
                error: "DB Connection failed".to_string(),
                details: Some(e.to_string()),
            }),
        )
    })?;

    // Get correct_option from DB
    let rows = client
        .query(
            "SELECT id, correct_option FROM questions WHERE id = ANY($1::int[])",
            &[&question_ids],
        )
        .await
        .map_err(|e| {
            (
                axum::http::StatusCode::INTERNAL_SERVER_ERROR,
                Json(ErrorResponse {
                    error: "Question lookup failed".to_string(),
                    details: Some(e.to_string()),
                }),
            )
        })?;

    let mut questions_map: HashMap<i32, String> = HashMap::new();
    for row in rows {
        let id: i32 = row.get("id");
        let co: String = row.get("correct_option");
        questions_map.insert(id, co.trim().to_uppercase());
    }

    if questions_map.is_empty() {
        return Err((
            axum::http::StatusCode::BAD_REQUEST,
            Json(ErrorResponse {
                error: "No matching questions found for provided IDs".to_string(),
                details: None,
            }),
        ));
    }

    let mut total_questions: i32 = 0;
    let mut correct_answers: i32 = 0;
    let mut answers_result: Vec<AnswerResult> = Vec::new();

    for ans in &payload.answers {
        let qid = ans.question_id;
        let sel = ans.selected_option.trim().to_uppercase();

        let (is_correct, correct_opt) = if let Some(co) = questions_map.get(&qid) {
            let ok = &sel == co;
            (ok, Some(co.clone()))
        } else {
            (false, None)
        };

        total_questions += 1;
        if is_correct {
            correct_answers += 1;
        }

        answers_result.push(AnswerResult {
            question_id: qid,
            selected_option: sel,
            is_correct,
            correct_option: correct_opt,
        });
    }

    // Transaction: insert submission + answers
    let mut client = client;
    let tx = client.transaction().await.map_err(|e| {
        (
            axum::http::StatusCode::INTERNAL_SERVER_ERROR,
            Json(ErrorResponse {
                error: "Transaction start failed".to_string(),
                details: Some(e.to_string()),
            }),
        )
    })?;

    let row = tx
        .query_one(
            "INSERT INTO submissions (username, total_questions, correct_answers)
             VALUES ($1, $2, $3)
             RETURNING id",
            &[&username, &total_questions, &correct_answers],
        )
        .await
        .map_err(|e| {
            (
                axum::http::StatusCode::INTERNAL_SERVER_ERROR,
                Json(ErrorResponse {
                    error: "Submission insert failed".to_string(),
                    details: Some(e.to_string()),
                }),
            )
        })?;

    let submission_id: i32 = row.get("id");

    for ar in &answers_result {
        tx.execute(
            "INSERT INTO submission_answers
             (submission_id, question_id, selected_option, is_correct)
             VALUES ($1, $2, $3, $4)",
            &[
                &submission_id,
                &ar.question_id,
                &ar.selected_option,
                &ar.is_correct,
            ],
        )
        .await
        .map_err(|e| {
            (
                axum::http::StatusCode::INTERNAL_SERVER_ERROR,
                Json(ErrorResponse {
                    error: "Answer insert failed".to_string(),
                    details: Some(e.to_string()),
                }),
            )
        })?;
    }

    tx.commit().await.map_err(|e| {
        (
            axum::http::StatusCode::INTERNAL_SERVER_ERROR,
            Json(ErrorResponse {
                error: "Commit failed".to_string(),
                details: Some(e.to_string()),
            }),
        )
    })?;

    Ok(Json(SubmitResponse {
        username,
        submission_id,
        total_questions,
        correct_answers,
        answers: answers_result,
    }))
}

// --------------- MAIN ---------------

#[tokio::main]
async fn main() {
    let state = AppState {
        pool: DB_POOL.clone(),
    };

    let app = Router::new()
        .route("/health", get(health))
        .route("/questions", get(get_questions).post(create_question))
        .route("/submit", post(submit_answers))
        .with_state(state);

    let addr = SocketAddr::from(([0, 0, 0, 0], 8032));
    println!("Rust test service running on http://0.0.0.0:8032");

    let listener = TcpListener::bind(addr).await.unwrap();
    axum::serve(listener, app).await.unwrap();
}
