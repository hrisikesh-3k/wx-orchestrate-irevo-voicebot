from langchain_core.chat_history import BaseChatMessageHistory
from langchain_community.chat_message_histories.sql import SQLChatMessageHistory
from typing import List, Dict
from sqlalchemy import create_engine

from src.constants.db import CHAT_MEMORY_DB_NAME
from src.dbio.session_history_manager import SessionHistoryManager


class MemoryManager:
    def __init__(self, db_url: str = None):
        if not db_url:
            db_url = f"sqlite:///{CHAT_MEMORY_DB_NAME}"
        self._store = {}
        self.db_url = db_url
        self._engine = create_engine(self.db_url)  # ✅ Use SQLAlchemy engine instead of deprecated connection_string

    def _get_memory_instance(self, session_id: str) -> BaseChatMessageHistory:
        """Get SQLChatMessageHistory instance (non-deprecated)."""
        return SQLChatMessageHistory(session_id=session_id, connection=self._engine)

    def get(self, session_id: str) -> BaseChatMessageHistory:
        """Retrieve or create SQL-based chat memory for a session."""
        if session_id not in self._store:
            self._store[session_id] = self._get_memory_instance(session_id)
        return self._store[session_id]

    def reset(self, session_id: str):
        """Delete messages for a session."""
        if session_id in self._store:
            self._store[session_id].clear()
            del self._store[session_id]

    def cleanup(self, session_id: str):
        """Alias for reset."""
        self.reset(session_id)

    def list_sessions(self):
        """Return active session IDs from in-memory cache (not from DB)."""
        return list(self._store.keys())

    def get_message_history_as_list(self, session_id: str):
        """
        Return chat message history as a list of dictionaries like:
        [{ "type": "human"/"ai", "content": "..." }, ...]
        """
        history = self._get_memory_instance(session_id)
        messages = history.messages
        return messages

    def get_current_message_history(self):
        current_session_id = SessionHistoryManager.get_last_session_id()
        if not current_session_id:
            return []
        return self.get_message_history_as_list(session_id=current_session_id)
