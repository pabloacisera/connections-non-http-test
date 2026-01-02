import sqlite3
import os
from dotenv import load_dotenv

load_dotenv()

def get_connection():
    return sqlite3.connect(os.getenv("DB_PATH", "ai_bridge.db"))

def init():
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
                CREATE TABLE IF NOT EXISTS messages(id INTEGER PRIMARY KEY AUTOINCREMENT, client_id TEXT, role TEXT, content TEXT, timestamp DATETIME)
            """
        )
        cursor.execute(
            """
                CREATE TABLE IF NOT EXISTS summaries(id INTEGER PRIMARY KEY AUTOINCREMENT, client_id TEXT, summary_text TEXT, created_at DATETIME)
            """
        )
        conn.commit()

init()
