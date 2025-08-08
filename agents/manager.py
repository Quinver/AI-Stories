import ollama
from .models import Agent

def run_agent(agent: Agent, event: str) -> str:
    """Send an event to the agent and get a reply."""
    history = [{"role": "system", "content": agent.persona}]
    for msg in agent.memory[-5:]:  # last 5 messages for context
        history.append({"role": "user", "content": msg})
    history.append({"role": "user", "content": event})

    response = ollama.chat(model="mistral", messages=history)
    reply = response["message"]["content"]
    agent.add_memory(reply)
    return reply

def run_all_agents(agents: list, event: str) -> dict:
    """Trigger all agents to respond to the same event."""
    return {agent.name: run_agent(agent, event) for agent in agents}
