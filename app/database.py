import json
import re
import sqlite3
from pathlib import Path

import numpy as np

from app.config import DB_PATH

BASE_DIR = Path(__file__).resolve().parent.parent
UNITS_FILE = BASE_DIR / "unidades.txt"


def get_connection():
    Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
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


def _foreign_keys(conn, table_name):
    rows = conn.execute(f"PRAGMA foreign_key_list({table_name})").fetchall()
    return {
        (row["from"], row["table"], row["to"])
        for row in rows
    }


def _parse_units_file():
    if not UNITS_FILE.exists():
        return []

    units = []
    for line in UNITS_FILE.read_text(encoding="utf-8").splitlines()[1:]:
        stripped = line.rstrip()
        if not stripped:
            continue

        match = re.match(r"^(.*?)\s{2,}(\d+)\s*$", stripped)
        if not match:
            continue

        units.append({
            "id": int(match.group(2)),
            "name": match.group(1).strip(),
        })
    return units


def _seed_units(conn):
    units = _parse_units_file()
    if not units:
        return

    conn.executemany(
        """
            INSERT INTO units (id, name)
            VALUES (:id, :name)
            ON CONFLICT(id) DO UPDATE SET
                name = excluded.name
        """,
        units,
    )


def _rebuild_people_table(conn):
    conn.execute("DROP TABLE IF EXISTS people_new")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS people_new (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            person_id TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            unit_id INTEGER,
            unit TEXT,
            role TEXT,
            active INTEGER DEFAULT 1,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (unit_id) REFERENCES units(id)
        )
    """)

    columns = _columns(conn, "people")
    unit_id_expr = "unit_id" if "unit_id" in columns else "NULL"
    unit_expr = "unit" if "unit" in columns else "NULL"
    role_expr = "role" if "role" in columns else "NULL"
    active_expr = "active" if "active" in columns else "1"
    created_at_expr = "created_at" if "created_at" in columns else "CURRENT_TIMESTAMP"

    conn.execute(f"""
        INSERT INTO people_new (id, person_id, name, unit_id, unit, role, active, created_at)
        SELECT id, person_id, name, {unit_id_expr}, {unit_expr}, {role_expr}, {active_expr}, {created_at_expr}
        FROM people
    """)
    conn.execute("DROP TABLE people")
    conn.execute("ALTER TABLE people_new RENAME TO people")


def _rebuild_checkins_table(conn):
    conn.execute("DROP TABLE IF EXISTS checkins_new")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS checkins_new (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            person_id TEXT NOT NULL,
            name TEXT NOT NULL,
            unit_id INTEGER,
            unit TEXT,
            method TEXT NOT NULL,
            confidence REAL,
            already_checked_in INTEGER DEFAULT 0,
            checked_in_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (person_id) REFERENCES people(person_id),
            FOREIGN KEY (unit_id) REFERENCES units(id)
        )
    """)

    columns = _columns(conn, "checkins")
    unit_id_expr = "unit_id" if "unit_id" in columns else "NULL"
    unit_expr = "unit" if "unit" in columns else "NULL"
    confidence_expr = "confidence" if "confidence" in columns else "NULL"
    duplicate_expr = "already_checked_in" if "already_checked_in" in columns else "0"
    checked_at_expr = "checked_in_at" if "checked_in_at" in columns else "CURRENT_TIMESTAMP"

    conn.execute(f"""
        INSERT INTO checkins_new (id, person_id, name, unit_id, unit, method, confidence, already_checked_in, checked_in_at)
        SELECT id, person_id, name, {unit_id_expr}, {unit_expr}, method, {confidence_expr}, {duplicate_expr}, {checked_at_expr}
        FROM checkins
    """)
    conn.execute("DROP TABLE checkins")
    conn.execute("ALTER TABLE checkins_new RENAME TO checkins")


def _ensure_people_schema(conn):
    expected_columns = {"id", "person_id", "name", "unit_id", "unit", "role", "active", "created_at"}
    foreign_keys = _foreign_keys(conn, "people")

    if expected_columns.issubset(_columns(conn, "people")) and ("unit_id", "units", "id") in foreign_keys:
        return

    _rebuild_people_table(conn)


def _ensure_checkins_schema(conn):
    expected_columns = {"id", "person_id", "name", "unit_id", "unit", "method", "confidence", "already_checked_in", "checked_in_at"}
    foreign_keys = _foreign_keys(conn, "checkins")

    if (
        expected_columns.issubset(_columns(conn, "checkins"))
        and ("person_id", "people", "person_id") in foreign_keys
        and ("unit_id", "units", "id") in foreign_keys
    ):
        return

    _rebuild_checkins_table(conn)


def _sync_people_units(conn):
    if "unit_id" in _columns(conn, "people"):
        conn.execute(
            """
                UPDATE people
                SET unit_id = (
                    SELECT u.id
                    FROM units u
                    WHERE u.name = TRIM(people.unit)
                )
                WHERE unit_id IS NULL
                  AND unit IS NOT NULL
                  AND TRIM(unit) <> ''
            """
        )
        conn.execute(
            """
                UPDATE people
                SET unit = (
                    SELECT u.name
                    FROM units u
                    WHERE u.id = people.unit_id
                )
                WHERE unit_id IS NOT NULL
            """
        )


def _sync_checkins_units(conn):
    if "unit_id" in _columns(conn, "checkins"):
        conn.execute(
            """
                UPDATE checkins
                SET unit_id = COALESCE(
                    unit_id,
                    (
                        SELECT p.unit_id
                        FROM people p
                        WHERE p.person_id = checkins.person_id
                    )
                )
                WHERE unit_id IS NULL
            """
        )
        conn.execute(
            """
                UPDATE checkins
                SET unit = COALESCE(
                    (
                        SELECT u.name
                        FROM units u
                        WHERE u.id = checkins.unit_id
                    ),
                    unit,
                    (
                        SELECT p.unit
                        FROM people p
                        WHERE p.person_id = checkins.person_id
                    )
                )
            """
        )


def _resolve_unit(conn, unit_id=None, unit_name=None):
    if unit_id is None and not unit_name:
        return None, None

    if unit_id is not None:
        row = conn.execute(
            "SELECT id, name FROM units WHERE id = ?",
            (unit_id,),
        ).fetchone()
    else:
        row = conn.execute(
            "SELECT id, name FROM units WHERE name = ?",
            (unit_name,),
        ).fetchone()

    if row is None:
        raise ValueError("Unidade inválida")

    return int(row["id"]), row["name"]


def init_db():
    conn = get_connection()
    conn.execute("PRAGMA foreign_keys = OFF")

    conn.execute("""
        CREATE TABLE IF NOT EXISTS units (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL UNIQUE
        )
    """)
    _seed_units(conn)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS people (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            person_id TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            unit_id INTEGER,
            unit TEXT,
            role TEXT,
            active INTEGER DEFAULT 1,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (unit_id) REFERENCES units(id)
        )
    """)
    _drop_column(conn, "people", "document")
    _drop_column(conn, "people", "region")
    _ensure_people_schema(conn)

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
            unit_id INTEGER,
            unit TEXT,
            method TEXT NOT NULL,
            confidence REAL,
            already_checked_in INTEGER DEFAULT 0,
            checked_in_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (person_id) REFERENCES people(person_id),
            FOREIGN KEY (unit_id) REFERENCES units(id)
        )
    """)
    _ensure_checkins_schema(conn)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            action TEXT NOT NULL,
            person_id TEXT,
            message TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)

    _sync_people_units(conn)
    _sync_checkins_units(conn)

    conn.commit()
    conn.execute("PRAGMA foreign_keys = ON")
    conn.close()


def row_to_dict(row):
    return dict(row) if row is not None else None


def list_units():
    with get_connection() as conn:
        rows = conn.execute("""
            SELECT id, name
            FROM units
            ORDER BY id ASC
        """).fetchall()
        return [row_to_dict(row) for row in rows]


def get_unit(unit_id):
    with get_connection() as conn:
        row = conn.execute(
            "SELECT id, name FROM units WHERE id = ?",
            (unit_id,),
        ).fetchone()
        return row_to_dict(row)


def create_person(person_id, name, unit_id=None, role=None, unit=None):
    with get_connection() as conn:
        resolved_unit_id, resolved_unit_name = _resolve_unit(conn, unit_id, unit)
        conn.execute("""
            INSERT INTO people (person_id, name, unit_id, unit, role)
            VALUES (?, ?, ?, ?, ?)
        """, (person_id, name, resolved_unit_id, resolved_unit_name, role))


def update_person(person_id, name, unit_id=None, role=None, unit=None):
    with get_connection() as conn:
        resolved_unit_id, resolved_unit_name = _resolve_unit(conn, unit_id, unit)
        cursor = conn.execute("""
            UPDATE people
            SET name = ?, unit_id = ?, unit = ?, role = ?
            WHERE person_id = ?
        """, (name, resolved_unit_id, resolved_unit_name, role, person_id))
        if cursor.rowcount == 0:
            return None
        row = conn.execute("""
            SELECT
                p.id,
                p.person_id,
                p.name,
                p.unit_id,
                COALESCE(u.name, p.unit) AS unit,
                p.role,
                p.active,
                p.created_at,
                COUNT(fe.id) AS photos_count
            FROM people p
            LEFT JOIN units u ON u.id = p.unit_id
            LEFT JOIN face_embeddings fe ON fe.person_id = p.person_id
            WHERE p.person_id = ?
            GROUP BY p.id, p.person_id, p.name, p.unit_id, p.unit, u.name, p.role, p.active, p.created_at
        """, (person_id,)).fetchone()
        return row_to_dict(row)


def update_or_create_person(person_id, name, unit_id=None, role=None, unit=None):
    with get_connection() as conn:
        resolved_unit_id, resolved_unit_name = _resolve_unit(conn, unit_id, unit)
        conn.execute("""
            INSERT INTO people (person_id, name, unit_id, unit, role)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(person_id) DO UPDATE SET
                name = excluded.name,
                unit_id = COALESCE(excluded.unit_id, people.unit_id),
                unit = COALESCE(excluded.unit, people.unit),
                role = COALESCE(excluded.role, people.role),
                active = 1
        """, (person_id, name, resolved_unit_id, resolved_unit_name, role))


def get_person(person_id):
    with get_connection() as conn:
        row = conn.execute("""
            SELECT
                p.id,
                p.person_id,
                p.name,
                p.unit_id,
                COALESCE(u.name, p.unit) AS unit,
                p.role,
                p.active,
                p.created_at,
                COUNT(fe.id) AS photos_count
            FROM people p
            LEFT JOIN units u ON u.id = p.unit_id
            LEFT JOIN face_embeddings fe ON fe.person_id = p.person_id
            WHERE p.person_id = ?
            GROUP BY p.id, p.person_id, p.name, p.unit_id, p.unit, u.name, p.role, p.active, p.created_at
        """, (person_id,)).fetchone()
        return row_to_dict(row)


def list_people():
    with get_connection() as conn:
        rows = conn.execute("""
            SELECT
                p.id,
                p.person_id,
                p.name,
                p.unit_id,
                COALESCE(u.name, p.unit) AS unit,
                p.role,
                p.active,
                p.created_at,
                COUNT(fe.id) AS photos_count
            FROM people p
            LEFT JOIN units u ON u.id = p.unit_id
            LEFT JOIN face_embeddings fe ON fe.person_id = p.person_id
            WHERE p.active = 1
            GROUP BY p.id, p.person_id, p.name, p.unit_id, p.unit, u.name, p.role, p.active, p.created_at
            ORDER BY p.created_at DESC, p.id DESC
        """).fetchall()
        return [row_to_dict(row) for row in rows]


def save_embedding(person_id, embedding, image_path=None):
    with get_connection() as conn:
        conn.execute("""
            INSERT INTO face_embeddings (person_id, embedding, image_path)
            VALUES (?, ?, ?)
        """, (person_id, json.dumps(embedding.tolist()), image_path))


def save_person(person_id: str, name: str, embedding: np.ndarray, unit_id=None, unit=None):
    update_or_create_person(person_id, name, unit_id=unit_id, unit=unit)
    save_embedding(person_id, embedding)


def load_all_embeddings():
    with get_connection() as conn:
        rows = conn.execute("""
            SELECT
                p.person_id,
                p.name,
                p.unit_id,
                COALESCE(u.name, p.unit) AS unit,
                p.role,
                fe.embedding
            FROM face_embeddings fe
            INNER JOIN people p ON p.person_id = fe.person_id
            LEFT JOIN units u ON u.id = p.unit_id
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


def delete_person(person_id):
    with get_connection() as conn:
        person = conn.execute("""
            SELECT
                p.id,
                p.person_id,
                p.name,
                p.unit_id,
                COALESCE(u.name, p.unit) AS unit,
                p.role,
                p.active,
                p.created_at
            FROM people p
            LEFT JOIN units u ON u.id = p.unit_id
            WHERE p.person_id = ?
        """, (person_id,)).fetchone()
        if person is None:
            return None

        image_rows = conn.execute(
            "SELECT image_path FROM face_embeddings WHERE person_id = ?",
            (person_id,),
        ).fetchall()
        image_paths = [row["image_path"] for row in image_rows if row["image_path"]]

        deleted_checkins = conn.execute(
            "DELETE FROM checkins WHERE person_id = ?",
            (person_id,),
        ).rowcount
        deleted_embeddings = conn.execute(
            "DELETE FROM face_embeddings WHERE person_id = ?",
            (person_id,),
        ).rowcount
        deleted_logs = conn.execute(
            "DELETE FROM logs WHERE person_id = ?",
            (person_id,),
        ).rowcount
        conn.execute(
            "DELETE FROM people WHERE person_id = ?",
            (person_id,),
        )

        return {
            "person": row_to_dict(person),
            "image_paths": image_paths,
            "deleted_checkins": deleted_checkins,
            "deleted_embeddings": deleted_embeddings,
            "deleted_logs": deleted_logs,
        }


def get_existing_checkin(person_id):
    with get_connection() as conn:
        row = conn.execute("""
            SELECT * FROM checkins
            WHERE person_id = ? AND already_checked_in = 0
            ORDER BY checked_in_at ASC
            LIMIT 1
        """, (person_id,)).fetchone()
        return row_to_dict(row)


def create_checkin(person_id, name, method, confidence=None, already_checked_in=False, unit_id=None, unit=None):
    with get_connection() as conn:
        resolved_unit_id, resolved_unit_name = _resolve_unit(conn, unit_id, unit)
        cursor = conn.execute("""
            INSERT INTO checkins (person_id, name, unit_id, unit, method, confidence, already_checked_in)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (person_id, name, resolved_unit_id, resolved_unit_name, method, confidence, int(already_checked_in)))
        row = conn.execute("SELECT * FROM checkins WHERE id = ?", (cursor.lastrowid,)).fetchone()
        return row_to_dict(row)


def list_checkins():
    with get_connection() as conn:
        rows = conn.execute("""
            SELECT
                c.id,
                c.person_id,
                c.name,
                c.unit_id,
                COALESCE(u.name, c.unit, p.unit) AS unit,
                c.method,
                c.confidence,
                c.already_checked_in,
                c.checked_in_at
            FROM checkins c
            LEFT JOIN units u ON u.id = c.unit_id
            LEFT JOIN people p ON p.person_id = c.person_id
            ORDER BY c.checked_in_at DESC, c.id DESC
        """).fetchall()
        return [row_to_dict(row) for row in rows]


def delete_checkin(checkin_id):
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM checkins WHERE id = ?", (checkin_id,)).fetchone()
        if row is None:
            return None
        conn.execute("DELETE FROM checkins WHERE id = ?", (checkin_id,))
        return row_to_dict(row)


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
