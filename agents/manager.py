import json
import os
import re
from typing import List, Union

import ollama
from openai import OpenAI
from openai.types.chat import (
    ChatCompletionAssistantMessageParam,
    ChatCompletionSystemMessageParam,
    ChatCompletionUserMessageParam,
)

from db import load_agent, save_agent

from .models import Agent


def run_agent(
    agent: Agent, event: str, cursor, all_agents: List[Agent], api="ollama"
) -> str:
    """Send an event to the agent and get a reply using their persona."""

    # Load the agent's memory from database
    memory = agent.load_memory(cursor)

    system_prompt = f"You are {agent.name}, defined as: {agent.persona}. " + (
        "Speak only as yourself. Never speak for other characters. "
        "Stay fully in character and never copy others' speech patterns."
        "Remember, do NOT use words like 'nya' or 'purr' unless you are Neko-Chan. "
        "Do not include the other characters' lines in your response. "
        "Avoid em dashes — and asteriks * use simple punctuation."
        "Use max 20 words."
    )

    system_message: ChatCompletionSystemMessageParam = {
        "role": "system",
        "content": system_prompt,
    }
    history: List[
        Union[
            ChatCompletionSystemMessageParam,
            ChatCompletionUserMessageParam,
            ChatCompletionAssistantMessageParam,
        ]
    ] = [system_message]

    # Add recent memory for context (last 20 messages)
    recent_memory = memory[-20:] if len(memory) > 20 else memory
    for msg in recent_memory:
        assistant_message: ChatCompletionAssistantMessageParam = {
            "role": "assistant",
            "content": msg,
        }
        history.append(assistant_message)

    # Add the current event/prompt
    user_message: ChatCompletionUserMessageParam = {"role": "user", "content": event}
    history.append(user_message)

    try:
        if api == "ollama":
            response = ollama.chat(model="mythomax:latest", messages=history)
            content = response.get("message", {}).get("content", "")
            raw_reply = content if isinstance(content, str) else ""
        elif api == "openai":
            # TODO differentiate between github and openai token
            client = OpenAI(
                base_url="https://models.github.ai/inference",
                api_key=os.environ.get("GITHUB_TOKEN"),
            )
            if not client.api_key:
                raise ValueError("OPENAI_API_KEY environment variable not set")
            response = client.chat.completions.create(
                messages=history,
                temperature=0.7,
                max_tokens=4000,
                model="openai/gpt-4o-mini",
            )
            content = response.choices[0].message.content
            raw_reply = content if content is not None else ""
        else:
            raise ValueError(f"Unsupported API: {api}")

        reply = clean_reply(raw_reply)
        agent.add_memory(cursor, reply, role="assistant")
        return reply
    except Exception as e:
        error_msg = (
            f"Error generating response for {agent.name} with {api} API: {str(e)}"
        )
        agent.add_memory(cursor, error_msg, role="assistant")
        return error_msg


def create_agent_conversation(
    agents: List[Agent], initial_prompt: str, cursor, turns: int = 3, api="ollama"
):
    """Get agents to react to each other, initial prompt for conversation starter."""
    conversation = []
    current_prompt = initial_prompt

    for turn in range(turns):
        current_agent = agents[turn % len(agents)]

        if conversation:
            # Get only the last agent's reply (last turn)
            last_turn = conversation[-1]
            last_speaker, last_line = list(last_turn.items())[0]

            # Feed only the last line as user prompt
            context = (
                f"{last_speaker} said: {last_line}\nRespond as {current_agent.name}."
            )
        else:
            context = current_prompt

        response = run_agent(current_agent, context, cursor, agents, api)
        conversation.append({current_agent.name: response})
        cursor.connection.commit()

        print(f"\n--- Turn {turn + 1} ---")
        print(f"{current_agent.name}: {response}")

    return conversation


def clean_reply(raw_reply: str) -> str:
    """Remove <think> tags and strip surrounding double quotes."""
    cleaned = re.sub(r"<think>.*?</think>", "", raw_reply, flags=re.DOTALL).strip()
    if cleaned.startswith('"') and cleaned.endswith('"'):
        cleaned = cleaned[1:-1].strip()
    return cleaned


def get_agent(name: str) -> Agent:
    data = load_agent(name)
    if data is None:
        raise ValueError(f"Agent {name} not found")
    return Agent(**data)


def save_and_get_agent(name: str, persona: str) -> Agent:
    save_agent(name, persona)
    return get_agent(name)


def import_agents_from_json() -> List[Agent]:
    with open("agents.json", "r", encoding="utf-8") as f:
        agents_data = json.load(f)
    agents = [
        save_and_get_agent(agent["name"], agent["persona"]) for agent in agents_data
    ]
    return agents
