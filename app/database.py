import sqlite3
import json
import numpy as np
from pathlib import Path


DB_PATH = "data/faces.db"


def init_db():
    Path("data").mkdir(exist_ok=True)

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS persons (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            person_id TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS face_embeddings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            person_id TEXT NOT NULL,
            embedding TEXT NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.commit()
    conn.close()


def save_person(person_id: str, name: str, embedding: np.ndarray):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        INSERT OR REPLACE INTO persons (person_id, name)
        VALUES (?, ?)
    """, (person_id, name))

    cursor.execute("""
        INSERT INTO face_embeddings (person_id, embedding)
        VALUES (?, ?)
    """, (
        person_id,
        json.dumps(embedding.tolist())
    ))

    conn.commit()
    conn.close()


def load_all_embeddings():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT 
            p.person_id,
            p.name,
            fe.embedding
        FROM face_embeddings fe
        INNER JOIN persons p ON p.person_id = fe.person_id
    """)

    rows = cursor.fetchall()
    conn.close()

    results = []

    for person_id, name, embedding_json in rows:
        results.append({
            "person_id": person_id,
            "name": name,
            "embedding": np.array(json.loads(embedding_json), dtype=np.float32)
        })

    return results