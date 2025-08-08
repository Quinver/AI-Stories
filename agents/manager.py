import os
import ollama
from openai import OpenAI
from .models import Agent
from typing import List, Dict
import re

def run_agent(
    agent: Agent, event: str, cursor, all_agents: List[Agent], api="ollama"
) -> str:
    """Send an event to the agent and get a reply using their persona."""

    # Load the agent's memory from database
    memory = agent.load_memory(cursor)

    others = [a for a in all_agents if a.name != agent.name]
    others_info = ", ".join([f"{a.name} ({a.persona})" for a in others])

    # Build conversation history with persona as system message

    system_prompt = (
        f"You are {agent.name}, defined as: {agent.persona}. "
        + (f"You know the others: {others_info}. " if others_info else "")
        + (
            "Speak only as yourself. Never speak for other characters. "
            "Reply with exactly one sentence. "
            "Be quick and direct (8–12 words). "
            "Avoid filler or flowery language. "
            "Do not include the other characters’ lines in your response. "
            "Avoid em dashes — use simple punctuation."
            "Be yourself, but don't cling too much to your persona"
        )
    )

    history = [{"role": "system", "content": system_prompt}]

    # Add recent memory for context (last 5 messages)
    recent_memory = memory[-5:] if len(memory) > 5 else memory
    for msg in recent_memory:
        history.append({"role": "assistant", "content": msg})

    # Add the current event/prompt
    history.append({"role": "user", "content": event})

    try:
        if api == "ollama":
            response = ollama.chat(model="qwen3:14b", messages=history)
            raw_reply = response["message"]["content"]
        elif api == "openai":

            client= OpenAI(
                api_key=os.environ.get("OPENAI_KEY")
            )
            prompt_str = history_to_prompt(history)

            response = client.responses.create(
                model="gpt-4o",
                input=prompt_str,
                temperature=0.7,
                max_output_tokens=150,
            )
            raw_reply = response.text
        else:
            raise ValueError("Unsupported API")

        reply = clean_reply(raw_reply)

        agent.add_memory(cursor, reply, role="assistant")
        return reply
    except Exception as e:
        return f"Error generating response: {str(e)}"


def history_to_prompt(history):
    # Skip system message or include it as context as you want
    messages = []
    for m in history:
        role = m["role"]
        content = m["content"]
        messages.append(f"{role}: {content}")
    return "\n".join(messages)

def run_all_agents(agents: List[Agent], event: str, cursor) -> Dict[str, str]:
    """Trigger all agents to respond to the same event."""
    responses = {}
    for agent in agents:
        responses[agent.name] = run_agent(agent, event, cursor, agents)
    return responses


def create_agent_conversation(
    agents: List[Agent], initial_prompt: str, cursor, turns: int = 3
):
    conversation = []
    current_prompt = initial_prompt

    for turn in range(turns):
        current_agent = agents[turn % len(agents)]
        if conversation:
            recent_turns = conversation[-4:]  # last 3 turns
            history_snippet = "\n".join(
                f"{speaker}: {line}"
                for turn in recent_turns
                for speaker, line in turn.items()
            )
            context = (
                f"Conversation so far:\n{history_snippet}\nContinue the conversation."
            )
        else:
            context = current_prompt

        response = run_agent(current_agent, context, cursor, agents)
        conversation.append({current_agent.name: response})

        # Commit DB changes right away if you want
        cursor.connection.commit()

        # Print this turn immediately
        print(f"\n--- Turn {turn + 1} ---")
        print(f"{current_agent.name}: {response}")

    return conversation


def clean_reply(raw_reply: str) -> str:
    # Remove the <think>...</think> block including line breaks inside it
    return re.sub(r"<think>.*?</think>", "", raw_reply, flags=re.DOTALL).strip()
