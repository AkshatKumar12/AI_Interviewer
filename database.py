import sqlite3
from datetime import datetime
import json

DB_NAME = "interviews.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS interviews (
            id TEXT PRIMARY KEY,
            candidate_name TEXT,
            transcript TEXT,
            final_score TEXT,
            created_at TEXT
        )
    """)

    conn.commit()
    conn.close()


def save_interview(session_id, candidate_name, transcript, final_score):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute("""
        INSERT OR REPLACE INTO interviews (id, candidate_name, transcript, final_score, created_at)
        VALUES (?, ?, ?, ?, ?)
    """, (
        session_id,
        candidate_name,
        json.dumps(transcript),
        json.dumps(final_score),
        datetime.utcnow().isoformat()
    ))

    conn.commit()
    conn.close()
