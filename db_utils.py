import os
import pickle
import sqlite3
from typing import List, Tuple

import numpy as np

DB_PATH = os.path.join("data", "face_attendance.db")


def ensure_database(db_path: str = DB_PATH) -> None:
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS students (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS face_samples (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_id INTEGER NOT NULL,
                sample BLOB NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE
            )
            """
        )




    migrate_legacy_pickles(db_path)

def migrate_legacy_pickles(db_path: str = DB_PATH) -> None:
    names_path = os.path.join("data", "names.pkl")
    faces_path = os.path.join("data", "faces_data.pkl")

    if not (os.path.exists(names_path) and os.path.exists(faces_path)):
        return

    with sqlite3.connect(db_path) as conn:
        sample_count = conn.execute("SELECT COUNT(*) FROM face_samples").fetchone()[0]
    if sample_count > 0:
        return

    with open(names_path, "rb") as nf:
        names = pickle.load(nf)
    with open(faces_path, "rb") as ff:
        faces = pickle.load(ff)

    if len(names) != len(faces):
        min_len = min(len(names), len(faces))
        names = names[:min_len]
        faces = faces[:min_len]

    grouped = {}
    for label, sample in zip(names, faces):
        grouped.setdefault(label, []).append(np.asarray(sample, dtype=np.float32))

    for label, samples in grouped.items():
        upsert_student_samples(label, np.vstack(samples), replace_existing=False, db_path=db_path)

def student_exists(name: str, db_path: str = DB_PATH) -> bool:
    with sqlite3.connect(db_path) as conn:
        row = conn.execute("SELECT 1 FROM students WHERE name = ?", (name,)).fetchone()
    return row is not None


def upsert_student_samples(name: str, samples: np.ndarray, replace_existing: bool = False, db_path: str = DB_PATH) -> None:
    if samples.ndim != 2:
        raise ValueError("samples must be a 2D array of flattened face vectors")

    with sqlite3.connect(db_path) as conn:
        conn.execute("PRAGMA foreign_keys = ON")
        row = conn.execute("SELECT id FROM students WHERE name = ?", (name,)).fetchone()

        if row is None:
            cursor = conn.execute("INSERT INTO students(name) VALUES (?)", (name,))
            student_id = cursor.lastrowid
        else:
            student_id = row[0]
            if replace_existing:
                conn.execute("DELETE FROM face_samples WHERE student_id = ?", (student_id,))
            else:
                raise ValueError(f"Student '{name}' already exists. Use replace_existing=True to overwrite.")

        for sample in samples:
            payload = np.asarray(sample, dtype=np.float32).tobytes()
            conn.execute(
                "INSERT INTO face_samples(student_id, sample) VALUES (?, ?)",
                (student_id, payload),
            )


def load_training_data(db_path: str = DB_PATH) -> Tuple[np.ndarray, List[str]]:
    query = """
        SELECT s.name, fs.sample
        FROM face_samples fs
        JOIN students s ON s.id = fs.student_id
        ORDER BY s.name, fs.id
    """

    labels: List[str] = []
    faces: List[np.ndarray] = []

    with sqlite3.connect(db_path) as conn:
        rows = conn.execute(query).fetchall()

    for name, sample_blob in rows:
        sample_vector = np.frombuffer(sample_blob, dtype=np.float32)
        faces.append(sample_vector)
        labels.append(name)

    if not faces:
        return np.empty((0, 0), dtype=np.float32), labels

    return np.vstack(faces), labels


def count_students(db_path: str = DB_PATH) -> int:
    with sqlite3.connect(db_path) as conn:
        row = conn.execute("SELECT COUNT(*) FROM students").fetchone()
    return int(row[0]) if row else 0
