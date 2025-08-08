from dataclasses import dataclass
from typing import List, Tuple

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
            "SELECT content FROM messages WHERE agent_id = ? ORDER BY created_at ASC",
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

    def __repr__(self):
        return f"<Agent id={self.id} name={self.name!r} persona={self.persona!r}>"
