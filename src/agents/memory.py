from langchain_core.chat_history import BaseChatMessageHistory
from langchain_community.chat_message_histories import ChatMessageHistory


class MemoryManager:
    def __init__(self):
        self._store = {}

    def get(self, session_id: str) -> BaseChatMessageHistory:
        """Retrieve or create chat memory for a session."""
        if session_id not in self._store:
            self._store[session_id] = ChatMessageHistory()
        return self._store[session_id]

    def reset(self, session_id: str):
        """Reset memory for a session."""
        if session_id in self._store:
            del self._store[session_id]

    def cleanup(self, session_id: str):
        """Alias for reset."""
        self.reset(session_id)

    def list_sessions(self):
        """Return all active session IDs."""
        return list(self._store.keys())
