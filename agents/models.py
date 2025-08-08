from dataclasses import dataclass
from typing import List, Tuple, Dict

@dataclass
class Agent:
    id: int
    name: str
    persona: str

    def load_memory(self, cursor) -> List[str]:
        """
        Load all message contents from the DB for this agent,
        ordered by creation time ascending.
        """
        cursor.execute(
            "SELECT content FROM messages WHERE agent_id = ? AND role = 'assistant' ORDER BY created_at ASC",
            (self.id,)
        )
        rows = cursor.fetchall()
        return [row[0] for row in rows]

    def load_full_memory(self, cursor) -> List[Tuple[str, str, str]]:
        """
        Load full messages for this agent: role, content, created_at,
        useful for building context or displaying chat history.
        Returns a list of tuples (role, content, created_at).
        """
        cursor.execute(
            "SELECT role, content, created_at FROM messages WHERE agent_id = ? ORDER BY created_at ASC",
            (self.id,)
        )
        return cursor.fetchall()

    def add_memory(self, cursor, content: str, role: str = "assistant", commit: bool = False):
        """
        Add a message to the agent's memory in the DB.
        If commit=True, commit the connection after inserting.
        """
        cursor.execute(
            "INSERT INTO messages (agent_id, role, content) VALUES (?, ?, ?)",
            (self.id, role, content)
        )
        if commit:
            cursor.connection.commit()

    def get_conversation_history(self, cursor, limit: int = 10) -> List[Dict[str, str]]:
        """
        Get formatted conversation history for this agent.
        Returns list of message dictionaries with role and content.
        """
        cursor.execute(
            "SELECT role, content FROM messages WHERE agent_id = ? ORDER BY created_at DESC LIMIT ?",
            (self.id, limit)
        )
        rows = cursor.fetchall()
        return [{"role": row[0], "content": row[1]} for row in reversed(rows)]

    def clear_memory(self, cursor, commit: bool = False):
        """Clear all messages for this agent."""
        cursor.execute("DELETE FROM messages WHERE agent_id = ?", (self.id,))
        if commit:
            cursor.connection.commit()

    def __repr__(self):
        return f"<Agent id={self.id} name={self.name!r} persona={self.persona!r}>"
