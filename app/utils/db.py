"""SQLite data layer for MediPredict (users, predictions, doctor notes, login attempts).

Schema changes are applied as *additive migrations*, so databases created by the
earlier version of the project keep working and keep their data.
"""
import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone

from app.utils.config import DB_PATH, LOCKOUT_MINUTES, MAX_FAILED_LOGINS

DB_PATH.parent.mkdir(parents=True, exist_ok=True)


@contextmanager
def get_conn():
    conn = sqlite3.connect(DB_PATH, timeout=15)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def _columns(conn, table):
    return {r["name"] for r in conn.execute(f"PRAGMA table_info({table})")}


def _add_column(conn, table, name, ddl):
    if name not in _columns(conn, table):
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {name} {ddl}")


def init_db():
    """Create tables if missing and migrate older databases. Safe to call on every run."""
    with get_conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                role TEXT DEFAULT 'patient',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )""")
        conn.execute("""
            CREATE TABLE IF NOT EXISTS predictions (
                pred_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                disease TEXT NOT NULL,
                risk_score REAL NOT NULL,
                risk_level TEXT,
                input_params TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            )""")
        conn.execute("""
            CREATE TABLE IF NOT EXISTS doctor_notes (
                note_id INTEGER PRIMARY KEY AUTOINCREMENT,
                pred_id INTEGER NOT NULL,
                doctor_id INTEGER NOT NULL,
                note TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (pred_id) REFERENCES predictions(pred_id) ON DELETE CASCADE,
                FOREIGN KEY (doctor_id) REFERENCES users(user_id)
            )""")
        conn.execute("""
            CREATE TABLE IF NOT EXISTS login_attempts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT NOT NULL,
                success INTEGER NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )""")

        # --- additive migrations (older DBs) ---
        _add_column(conn, "users", "age", "INTEGER")
        _add_column(conn, "users", "sex", "TEXT")
        _add_column(conn, "users", "last_login", "TIMESTAMP")
        _add_column(conn, "users", "share_with_doctors", "INTEGER DEFAULT 1")
        _add_column(conn, "predictions", "kind", "TEXT DEFAULT 'risk'")
        _add_column(conn, "predictions", "model_name", "TEXT")
        _add_column(conn, "predictions", "explanation", "TEXT")
        # rows written by v1 have no 'kind': recognise symptom analyses by their payload
        conn.execute("UPDATE predictions SET kind='symptom' "
                     "WHERE kind='risk' AND input_params LIKE '{\"symptoms\"%'")
        conn.execute("UPDATE users SET share_with_doctors = 1 WHERE share_with_doctors IS NULL")

        conn.execute("CREATE INDEX IF NOT EXISTS idx_pred_user ON predictions(user_id, created_at)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_attempts ON login_attempts(email, created_at)")


# ------------------------------------------------------------------ users
def create_user(name, email, password_hash, role="patient", age=None, sex=None):
    """Returns user_id on success, None if the email already exists."""
    try:
        with get_conn() as conn:
            cur = conn.execute(
                "INSERT INTO users (name, email, password_hash, role, age, sex) VALUES (?,?,?,?,?,?)",
                (name.strip(), email.strip().lower(), password_hash, role, age, sex),
            )
            return cur.lastrowid
    except sqlite3.IntegrityError:
        return None


def get_user_by_email(email):
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM users WHERE lower(email) = ?", (email.strip().lower(),)).fetchone()
    return dict(row) if row else None


def get_user(user_id):
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)).fetchone()
    return dict(row) if row else None


def update_user(user_id, **fields):
    allowed = {"name", "age", "sex", "share_with_doctors", "password_hash", "last_login"}
    fields = {k: v for k, v in fields.items() if k in allowed}
    if not fields:
        return
    sets = ", ".join(f"{k} = ?" for k in fields)
    with get_conn() as conn:
        conn.execute(f"UPDATE users SET {sets} WHERE user_id = ?", (*fields.values(), user_id))


def delete_user(user_id):
    with get_conn() as conn:
        conn.execute("DELETE FROM doctor_notes WHERE pred_id IN (SELECT pred_id FROM predictions WHERE user_id=?)", (user_id,))
        conn.execute("DELETE FROM predictions WHERE user_id = ?", (user_id,))
        conn.execute("DELETE FROM users WHERE user_id = ?", (user_id,))


# ------------------------------------------------------- login throttling
def record_login_attempt(email, success):
    with get_conn() as conn:
        conn.execute("INSERT INTO login_attempts (email, success) VALUES (?, ?)",
                     (email.strip().lower(), int(success)))
        if success:  # a good login clears the failure streak
            conn.execute("DELETE FROM login_attempts WHERE email = ? AND success = 0", (email.strip().lower(),))


def minutes_locked(email):
    """Returns minutes remaining if the account is temporarily locked, else 0."""
    since = (datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(minutes=LOCKOUT_MINUTES)).strftime("%Y-%m-%d %H:%M:%S")
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT created_at FROM login_attempts WHERE email = ? AND success = 0 AND created_at >= ? "
            "ORDER BY created_at DESC", (email.strip().lower(), since)).fetchall()
    if len(rows) < MAX_FAILED_LOGINS:
        return 0
    last = datetime.strptime(rows[0]["created_at"], "%Y-%m-%d %H:%M:%S")
    remaining = LOCKOUT_MINUTES - (datetime.now(timezone.utc).replace(tzinfo=None) - last).total_seconds() / 60
    return max(1, int(round(remaining))) if remaining > 0 else 0


# ------------------------------------------------------------ predictions
def save_prediction(user_id, disease, risk_score, risk_level, input_params,
                    kind="risk", model_name=None, explanation=None):
    """Insert a prediction and return its pred_id."""
    with get_conn() as conn:
        cur = conn.execute(
            """INSERT INTO predictions
               (user_id, disease, risk_score, risk_level, input_params, kind, model_name, explanation)
               VALUES (?,?,?,?,?,?,?,?)""",
            (user_id, disease, float(risk_score), risk_level, json.dumps(input_params, default=str),
             kind, model_name, json.dumps(explanation, default=str) if explanation is not None else None),
        )
        return cur.lastrowid


def update_prediction(pred_id, disease, risk_score, risk_level, input_params, model_name=None, explanation=None):
    """Refine an existing symptom analysis instead of creating duplicates."""
    with get_conn() as conn:
        conn.execute(
            """UPDATE predictions SET disease=?, risk_score=?, risk_level=?, input_params=?,
               model_name=?, explanation=? WHERE pred_id=?""",
            (disease, float(risk_score), risk_level, json.dumps(input_params, default=str), model_name,
             json.dumps(explanation, default=str) if explanation is not None else None, pred_id),
        )


def _decode(row):
    d = dict(row)
    if d.get("kind") == "symptom" and d.get("disease"):   # tidy v1 labels such as 'hepatitis A ' / 'Diabetes '
        from app.utils.knowledge import clean_disease_name
        d["disease"] = clean_disease_name(d["disease"])
    for k in ("input_params", "explanation"):
        if d.get(k):
            try:
                d[k] = json.loads(d[k])
            except (TypeError, ValueError):
                pass
    return d


def get_prediction(pred_id):
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM predictions WHERE pred_id = ?", (pred_id,)).fetchone()
    return _decode(row) if row else None


def get_user_history(user_id, limit=500):
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM predictions WHERE user_id = ? ORDER BY created_at DESC, pred_id DESC LIMIT ?",
            (user_id, limit)).fetchall()
    return [_decode(r) for r in rows]


def delete_prediction(pred_id, user_id):
    with get_conn() as conn:
        conn.execute("DELETE FROM doctor_notes WHERE pred_id = ?", (pred_id,))
        conn.execute("DELETE FROM predictions WHERE pred_id = ? AND user_id = ?", (pred_id, user_id))


def clear_user_history(user_id):
    with get_conn() as conn:
        conn.execute("DELETE FROM doctor_notes WHERE pred_id IN (SELECT pred_id FROM predictions WHERE user_id=?)", (user_id,))
        conn.execute("DELETE FROM predictions WHERE user_id = ?", (user_id,))


def get_all_predictions(limit=1000):
    """Predictions of patients who agreed to share with doctors."""
    with get_conn() as conn:
        rows = conn.execute(
            """SELECT p.*, u.name, u.email, u.age, u.sex FROM predictions p
               JOIN users u ON p.user_id = u.user_id
               WHERE COALESCE(u.share_with_doctors, 1) = 1 AND u.role = 'patient'
               ORDER BY p.created_at DESC, p.pred_id DESC LIMIT ?""", (limit,)).fetchall()
    return [_decode(r) for r in rows]


def get_stats():
    with get_conn() as conn:
        patients = conn.execute("SELECT COUNT(*) FROM users WHERE role='patient'").fetchone()[0]
        total = conn.execute("SELECT COUNT(*) FROM predictions").fetchone()[0]
        high = conn.execute("SELECT COUNT(*) FROM predictions WHERE risk_level='HIGH'").fetchone()[0]
        doctors = conn.execute("SELECT COUNT(*) FROM users WHERE role='doctor'").fetchone()[0]
    return {"patients": patients, "predictions": total, "high_risk": high, "doctors": doctors}


# --------------------------------------------------------- doctor notes
def add_note(pred_id, doctor_id, note):
    with get_conn() as conn:
        conn.execute("INSERT INTO doctor_notes (pred_id, doctor_id, note) VALUES (?,?,?)",
                     (pred_id, doctor_id, note.strip()))


def get_notes(pred_id):
    with get_conn() as conn:
        rows = conn.execute(
            """SELECT n.*, u.name AS doctor_name FROM doctor_notes n
               JOIN users u ON n.doctor_id = u.user_id WHERE n.pred_id = ? ORDER BY n.created_at DESC""",
            (pred_id,)).fetchall()
    return [dict(r) for r in rows]
