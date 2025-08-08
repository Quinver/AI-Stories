from typing import Optional
from .database import cur, con

def init_db():
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS agents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            persona TEXT NOT NULL,
            last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            agent_id INTEGER NOT NULL REFERENCES agents(id) ON DELETE CASCADE,
            role TEXT CHECK (role IN ('system', 'user', 'assistant', 'gm')) NOT NULL,
            content TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """
    )
    con.commit()

def save_agent(name: str, persona: str) -> int:
    cur.execute(
        "INSERT OR IGNORE INTO agents (name, persona) VALUES (?, ?)",
        (name, persona)
    )
    con.commit()

    cur.execute("SELECT id FROM agents WHERE name = ?", (name,))
    agent_id = cur.fetchone()[0]
    return agent_id

def load_agent(name: str) -> Optional[dict]:
    cur.execute(
        "SELECT id, name, persona FROM agents WHERE name = ?", (name,)
    )
    row = cur.fetchone()
    if row:
        return {"id": row[0], "name": row[1], "persona": row[2]}
    return None
