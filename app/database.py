import json
import sqlite3
from pathlib import Path

import numpy as np

from app.config import DB_PATH


def get_connection():
    Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def _columns(conn, table_name):
    rows = conn.execute(f"PRAGMA table_info({table_name})").fetchall()
    return {row["name"] for row in rows}


def _add_column(conn, table_name, definition):
    column_name = definition.split()[0]
    if column_name not in _columns(conn, table_name):
        conn.execute(f"ALTER TABLE {table_name} ADD COLUMN {definition}")


def _drop_column(conn, table_name, column_name):
    if column_name in _columns(conn, table_name):
        conn.execute(f"ALTER TABLE {table_name} DROP COLUMN {column_name}")


def init_db():
    conn = get_connection()

    conn.execute("""
        CREATE TABLE IF NOT EXISTS people (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            person_id TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            unit TEXT,
            role TEXT,
            active INTEGER DEFAULT 1,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    _drop_column(conn, "people", "document")
    _drop_column(conn, "people", "region")

    legacy_exists = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='persons'"
    ).fetchone()
    if legacy_exists:
        conn.execute("""
            INSERT OR IGNORE INTO people (person_id, name)
            SELECT person_id, name FROM persons
        """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS face_embeddings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            person_id TEXT NOT NULL,
            embedding TEXT NOT NULL,
            image_path TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (person_id) REFERENCES people(person_id)
        )
    """)
    _add_column(conn, "face_embeddings", "image_path TEXT")

    conn.execute("""
        CREATE TABLE IF NOT EXISTS checkins (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            person_id TEXT NOT NULL,
            name TEXT NOT NULL,
            method TEXT NOT NULL,
            confidence REAL,
            already_checked_in INTEGER DEFAULT 0,
            checked_in_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            action TEXT NOT NULL,
            person_id TEXT,
            message TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.commit()
    conn.close()


def row_to_dict(row):
    return dict(row) if row is not None else None


def create_person(person_id, name, unit=None, role=None):
    with get_connection() as conn:
        conn.execute("""
            INSERT INTO people (person_id, name, unit, role)
            VALUES (?, ?, ?, ?)
        """, (person_id, name, unit, role))


def update_or_create_person(person_id, name, unit=None, role=None):
    with get_connection() as conn:
        conn.execute("""
            INSERT INTO people (person_id, name, unit, role)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(person_id) DO UPDATE SET
                name = excluded.name,
                unit = COALESCE(excluded.unit, people.unit),
                role = COALESCE(excluded.role, people.role),
                active = 1
        """, (person_id, name, unit, role))


def get_person(person_id):
    with get_connection() as conn:
        row = conn.execute("""
            SELECT
                p.*,
                COUNT(fe.id) AS photos_count
            FROM people p
            LEFT JOIN face_embeddings fe ON fe.person_id = p.person_id
            WHERE p.person_id = ?
            GROUP BY p.id
        """, (person_id,)).fetchone()
        return row_to_dict(row)


def list_people():
    with get_connection() as conn:
        rows = conn.execute("""
            SELECT
                p.*,
                COUNT(fe.id) AS photos_count
            FROM people p
            LEFT JOIN face_embeddings fe ON fe.person_id = p.person_id
            WHERE p.active = 1
            GROUP BY p.id
            ORDER BY p.created_at DESC, p.id DESC
        """).fetchall()
        return [row_to_dict(row) for row in rows]


def save_embedding(person_id, embedding, image_path=None):
    with get_connection() as conn:
        conn.execute("""
            INSERT INTO face_embeddings (person_id, embedding, image_path)
            VALUES (?, ?, ?)
        """, (person_id, json.dumps(embedding.tolist()), image_path))


def save_person(person_id: str, name: str, embedding: np.ndarray):
    update_or_create_person(person_id, name)
    save_embedding(person_id, embedding)


def load_all_embeddings():
    with get_connection() as conn:
        rows = conn.execute("""
            SELECT
                p.person_id,
                p.name,
                p.unit,
                p.role,
                fe.embedding
            FROM face_embeddings fe
            INNER JOIN people p ON p.person_id = fe.person_id
            WHERE p.active = 1
        """).fetchall()

    results = []
    for row in rows:
        item = row_to_dict(row)
        item["embedding"] = np.array(json.loads(item["embedding"]), dtype=np.float32)
        results.append(item)
    return results


def count_embeddings():
    with get_connection() as conn:
        row = conn.execute("SELECT COUNT(*) AS total FROM face_embeddings").fetchone()
        return int(row["total"])


def get_existing_checkin(person_id):
    with get_connection() as conn:
        row = conn.execute("""
            SELECT * FROM checkins
            WHERE person_id = ? AND already_checked_in = 0
            ORDER BY checked_in_at ASC
            LIMIT 1
        """, (person_id,)).fetchone()
        return row_to_dict(row)


def create_checkin(person_id, name, method, confidence=None, already_checked_in=False):
    with get_connection() as conn:
        cursor = conn.execute("""
            INSERT INTO checkins (person_id, name, method, confidence, already_checked_in)
            VALUES (?, ?, ?, ?, ?)
        """, (person_id, name, method, confidence, int(already_checked_in)))
        row = conn.execute("SELECT * FROM checkins WHERE id = ?", (cursor.lastrowid,)).fetchone()
        return row_to_dict(row)


def list_checkins():
    with get_connection() as conn:
        rows = conn.execute("""
            SELECT * FROM checkins
            ORDER BY checked_in_at DESC, id DESC
        """).fetchall()
        return [row_to_dict(row) for row in rows]


def add_log(action, person_id=None, message=None):
    with get_connection() as conn:
        cursor = conn.execute("""
            INSERT INTO logs (action, person_id, message)
            VALUES (?, ?, ?)
        """, (action, person_id, message))
        row = conn.execute("SELECT * FROM logs WHERE id = ?", (cursor.lastrowid,)).fetchone()
        return row_to_dict(row)


def list_logs(limit=200):
    with get_connection() as conn:
        rows = conn.execute("""
            SELECT * FROM logs
            ORDER BY created_at DESC, id DESC
            LIMIT ?
        """, (limit,)).fetchall()
        return [row_to_dict(row) for row in rows]


def dashboard_stats():
    with get_connection() as conn:
        people = conn.execute("SELECT COUNT(*) AS total FROM people WHERE active = 1").fetchone()["total"]
        photos = conn.execute("SELECT COUNT(*) AS total FROM face_embeddings").fetchone()["total"]
        checkins = conn.execute(
            "SELECT COUNT(*) AS total FROM checkins WHERE already_checked_in = 0"
        ).fetchone()["total"]
        by_method_rows = conn.execute("""
            SELECT method, COUNT(*) AS total
            FROM checkins
            WHERE already_checked_in = 0
            GROUP BY method
        """).fetchall()

    by_method = {row["method"]: row["total"] for row in by_method_rows}
    return {
        "people": people,
        "photos": photos,
        "checkins": checkins,
        "face_checkins": by_method.get("face", 0),
        "manual_checkins": by_method.get("manual", 0),
    }
