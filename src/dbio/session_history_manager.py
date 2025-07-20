import sqlite3
import os
from typing import List, Dict
from datetime import datetime

from src.constants.db import CHAT_MEMORY_DB_NAME
from src.utils.session import get_user_session
from src.logger import logger
DB_PATH = CHAT_MEMORY_DB_NAME


class SessionHistoryManager:
    def __init__(self):
        self.session_id = self._get_a_session_id()
        self.initialize_db()
        self.store_session_id(self.session_id)


    def _get_a_session_id(self):
        session = get_user_session()
        session_id = session.session_id

        return session_id

    def initialize_db(self):
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("""
            CREATE TABLE IF NOT EXISTS session_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)

        logger.info("Session DB initialized.")

        conn.commit()
        conn.close()

    def store_session_id(self,
                         session_id: str):
        """Store session id in db"""
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("INSERT INTO session_history (session_id) VALUES (?)", (session_id,))
        conn.commit()
        logger.info(f"Session id: {session_id} stored in db successfully.")
        conn.close()


    @staticmethod
    def get_last_session_id() -> str:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("""
            SELECT session_id FROM session_history
            ORDER BY timestamp DESC LIMIT 1
        """)
        row = c.fetchone()
        conn.close()
        return row[0] if row else None




