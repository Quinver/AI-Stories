from agents import Agent
from db.queries import save_agent, load_agent, con
from db import init_db
from api import run

def main():
    init_db()

    # Create or load agents
    alice = save_and_get_agent("Alice", "Witty merchant who loves gossip")
    bob = save_and_get_agent("Bob", "Grumpy blacksmith with a heart of gold")

    # Example: add memory entries
    with con:
        cur = con.cursor()
        alice.add_memory(cur, "Hello! I'm Alice.", role="assistant")
        bob.add_memory(cur, "Hey there, Bob at your service.", role="assistant")

    # Print loaded memory to verify
    with con:
        cur = con.cursor()
        print("Alice's memory:", alice.load_memory(cur))
        print("Bob's memory:", bob.load_memory(cur))

def get_agent(name: str) -> Agent:
    data = load_agent(name)
    if data is None:
        raise ValueError(f"Agent {name} not found")
    return Agent(**data)

def save_and_get_agent(name: str, persona: str) -> Agent:
    save_agent(name, persona)
    return get_agent(name)

if __name__ == "__main__":
    main()
    run()
