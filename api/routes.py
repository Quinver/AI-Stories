import os
from sqlite3 import Connection
from typing import List, Optional

import ollama
from fastapi import APIRouter, Depends, HTTPException
from openai import OpenAI
from pydantic import BaseModel
from starlette.concurrency import run_in_threadpool

from agents import Agent
from db.queries import load_agent

from .dependencies import get_db

router = APIRouter()


class Settings(BaseModel):
    ollamaUrl: Optional[str] = "http://localhost:11434"
    ollamaModel: Optional[str] = "mythomax:latest"
    openaiApiKey: Optional[str] = ""
    openaiBaseUrl: Optional[str] = "https://api.openai.com/v1"
    openaiModel: Optional[str] = "gpt-4o-mini"
    githubToken: Optional[str] = ""
    githubModel: Optional[str] = "openai/gpt-4o-mini"


@router.get("/agents")
async def get_agents(db: Connection = Depends(get_db)):
    """Get all available agents."""
    cur = db.cursor()
    cur.execute("SELECT id, name, persona FROM agents")
    agents = cur.fetchall()
    return [{"id": agent[0], "name": agent[1], "persona": agent[2]} for agent in agents]


@router.get("/agents/{agent_name}")
async def get_agent_details(agent_name: str, db: Connection = Depends(get_db)):
    """Get details for a specific agent including recent memory."""
    cur = db.cursor()

    agent_data = load_agent(agent_name)
    if not agent_data:
        raise HTTPException(status_code=404, detail=f"Agent {agent_name} not found")

    agent = Agent(**agent_data)

    recent_messages = agent.get_conversation_history(cur, limit=20)

    return {
        "id": agent.id,
        "name": agent.name,
        "persona": agent.persona,
        "recent_messages": recent_messages,
    }


class ChatRequest(BaseModel):
    prompt: str
    agent_name: Optional[str] = None
    api: Optional[str] = "ollama"
    settings: Optional[Settings] = None


def run_agent_with_settings(
    agent: Agent,
    event: str,
    cursor,
    all_agents: List[Agent],
    api="ollama",
    settings: Optional[Settings] = None,
) -> str:
    """Enhanced run_agent function that uses custom settings."""

    # Load the agent's memory from database
    memory = agent.load_memory(cursor)

    # Get info of all other personas as info in system_prompt
    others = [a for a in all_agents if a.name != agent.name]
    others_info = ", ".join([f"{a.name} ({a.persona})" for a in others])

    system_prompt = (
        f"You are {agent.name}, defined as: {agent.persona}. "
        + (f"You know the others: {others_info}. " if others_info else "")
        + (
            "Speak only as yourself. Never speak for other characters. "
            "Stay fully in character and never copy others' speech patterns."
            "Avoid filler or flowery language. "
            "Do not include the other characters' lines in your response. "
            "Avoid em dashes — and asteriks * use simple punctuation."
            "Be yourself, but don't cling too much to your persona"
            "Try to make it an intresting story create new events if fitting"
            "Use max 20 words."
        )
    )

    from typing import Union

    from openai.types.chat import (
        ChatCompletionAssistantMessageParam,
        ChatCompletionSystemMessageParam,
        ChatCompletionUserMessageParam,
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
            # Use custom Ollama settings if provided
            if settings and settings.ollamaUrl:
                # Set custom Ollama host
                client = ollama.Client(host=settings.ollamaUrl)
                model = (
                    settings.ollamaModel if settings.ollamaModel else "mythomax:latest"
                )
                response = client.chat(model=model, messages=history)
            else:
                response = ollama.chat(model="mythomax:latest", messages=history)

            content = response.get("message", {}).get("content", "")
            raw_reply = content if isinstance(content, str) else ""

        elif api == "openai":
            # Use custom OpenAI settings if provided
            api_key = (
                settings.openaiApiKey
                if settings and settings.openaiApiKey
                else os.environ.get("OPENAI_API_KEY")
            )
            base_url = (
                settings.openaiBaseUrl
                if settings and settings.openaiBaseUrl
                else "https://api.openai.com/v1"
            )
            model = (
                settings.openaiModel
                if settings and settings.openaiModel
                else "gpt-4o-mini"
            )

            if not api_key:
                raise ValueError(
                    "OpenAI API key not provided in settings or environment"
                )

            client = OpenAI(api_key=api_key, base_url=base_url)
            response = client.chat.completions.create(
                messages=history,
                temperature=0.7,
                max_tokens=4000,
                model=model,
            )
            content = response.choices[0].message.content
            raw_reply = content if content is not None else ""

        elif api == "github":
            # Use GitHub Models settings
            github_token = (
                settings.githubToken
                if settings and settings.githubToken
                else os.environ.get("GITHUB_TOKEN")
            )
            model = (
                settings.githubModel
                if settings and settings.githubModel
                else "openai/gpt-4o-mini"
            )

            if not github_token:
                raise ValueError("GitHub token not provided in settings or environment")

            client = OpenAI(
                base_url="https://models.github.ai/inference",
                api_key=github_token,
            )
            response = client.chat.completions.create(
                messages=history,
                max_completion_tokens=4000,
                model=model,
            )
            content = response.choices[0].message.content
            raw_reply = content if content is not None else ""
        else:
            raise ValueError(f"Unsupported API: {api}")

        from agents.manager import clean_reply

        reply = clean_reply(raw_reply)
        agent.add_memory(cursor, reply, role="assistant")
        return reply
    except Exception as e:
        error_msg = (
            f"Error generating response for {agent.name} with {api} API: {str(e)}"
        )
        agent.add_memory(cursor, error_msg, role="assistant")
        return error_msg


@router.post("/chat")
async def chat_with_agent(request: ChatRequest, db: Connection = Depends(get_db)):
    """Chat with a specific agent."""
    cur = db.cursor()

    if request.api not in ["ollama", "openai", "github"]:
        raise HTTPException(
            status_code=400, detail="API must be either 'ollama', 'openai', or 'github'"
        )

    if not request.agent_name:
        raise HTTPException(status_code=400, detail="agent_name is required")

    agent_data = load_agent(request.agent_name)
    if not agent_data:
        raise HTTPException(
            status_code=404, detail=f"Agent {request.agent_name} not found"
        )

    agent = Agent(**agent_data)

    cur.execute("SELECT id, name, persona FROM agents")
    all_agent_data = cur.fetchall()
    all_agents = [
        Agent(id=row[0], name=row[1], persona=row[2]) for row in all_agent_data
    ]

    # Run in thread pool to avoid blocking
    response = await run_in_threadpool(
        run_agent_with_settings,
        agent,
        request.prompt,
        cur,
        all_agents,
        request.api,
        request.settings or Settings(),
    )

    db.commit()

    return {"agent": request.agent_name, "response": response, "api": request.api}


class ConversationRequest(BaseModel):
    prompt: str
    agent_names: List[str]
    turns: int = 3
    api: Optional[str] = "ollama"
    settings: Optional[Settings] = None


def create_agent_conversation_with_settings(
    agents: List[Agent],
    initial_prompt: str,
    cursor,
    turns: int = 3,
    api="ollama",
    settings: Optional[Settings] = None,
):
    """Enhanced conversation function that uses custom settings."""
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

        response = run_agent_with_settings(
            current_agent, context, cursor, agents, api, settings
        )
        conversation.append({current_agent.name: response})
        cursor.connection.commit()

    return conversation


@router.post("/conversation")
async def create_conversation(
    request: ConversationRequest, db: Connection = Depends(get_db)
):
    """Create a multi-turn conversation between specified agents."""
    cur = db.cursor()

    if request.api not in ["ollama", "openai", "github"]:
        raise HTTPException(
            status_code=400, detail="API must be either 'ollama', 'openai', or 'github'"
        )

    # Load specified agents
    agents = []
    for agent_name in request.agent_names:
        agent_data = load_agent(agent_name)
        if not agent_data:
            raise HTTPException(status_code=404, detail=f"Agent {agent_name} not found")
        agents.append(Agent(**agent_data))

    if len(agents) < 2:
        raise HTTPException(
            status_code=400, detail="Need at least 2 agents for a conversation"
        )

    # Create conversation in thread pool
    conversation = await run_in_threadpool(
        create_agent_conversation_with_settings,
        agents,
        request.prompt,
        cur,
        request.turns,
        request.api,
        request.settings or Settings(),
    )

    return {
        "prompt": request.prompt,
        "agents": [agent.name for agent in agents],
        "turns": request.turns,
        "conversation": conversation,
        "api": request.api,
    }


class TestConnectionRequest(BaseModel):
    api: str
    settings: Settings


@router.post("/test-connection")
async def test_connection(request: TestConnectionRequest):
    """Test connection to the specified API with given settings."""
    try:
        if request.api == "ollama":
            # Test Ollama connection
            url = request.settings.ollamaUrl or "http://localhost:11434"
            model = request.settings.ollamaModel or "mythomax:latest"

            client = ollama.Client(host=url)
            # Try to get model info or make a simple request
            try:
                models = client.list()
                model_names = [m["name"] for m in models["models"]]
                if model not in model_names:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Model '{model}' not found. Available models: {
                            ', '.join(model_names)
                        }",
                    )

                # Test with a simple message
                response = client.chat(
                    model=model,
                    messages=[{"role": "user", "content": "Hello"}],
                    # Limit response length for test
                    options={"num_predict": 10},
                )
                return {
                    "success": True,
                    "message": f"Successfully connected to Ollama at {url} with model {model}",
                }
            except Exception as e:
                raise HTTPException(
                    status_code=400, detail=f"Failed to connect to Ollama: {str(e)}"
                )

        elif request.api == "openai":
            # Test OpenAI connection
            api_key = request.settings.openaiApiKey
            base_url = request.settings.openaiBaseUrl or "https://api.openai.com/v1"
            model = request.settings.openaiModel or "gpt-4o-mini"

            if not api_key:
                raise HTTPException(
                    status_code=400, detail="OpenAI API key is required"
                )

            client = OpenAI(api_key=api_key, base_url=base_url)

            # Test with a simple message
            response = client.chat.completions.create(
                messages=[{"role": "user", "content": "Hello"}],
                model=model,
                max_tokens=10,
            )
            return {
                "success": True,
                "message": f"Successfully connected to OpenAI with model {model}",
            }

        elif request.api == "github":
            # Test GitHub Models connection
            github_token = request.settings.githubToken
            model = request.settings.githubModel or "openai/gpt-4o-mini"

            if not github_token:
                raise HTTPException(status_code=400, detail="GitHub token is required")

            client = OpenAI(
                base_url="https://models.inference.ai.azure.com",
                api_key=github_token,
            )

            # Test with a simple message
            response = client.chat.completions.create(
                messages=[{"role": "user", "content": "Hello"}],
                model=model,
                max_tokens=10,
            )
            return {
                "success": True,
                "message": f"Successfully connected to GitHub Models with model {model}",
            }

        else:
            raise HTTPException(
                status_code=400, detail=f"Unsupported API: {request.api}"
            )

    except HTTPException:
        # Re-raise HTTPExceptions as-is
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Connection test failed: {str(e)}")


@router.delete("/agents/{agent_name}/memory")
async def clear_agent_memory(agent_name: str, db: Connection = Depends(get_db)):
    """Clear all memory for a specific agent."""
    cur = db.cursor()

    agent_data = load_agent(agent_name)
    if not agent_data:
        raise HTTPException(status_code=404, detail=f"Agent {agent_name} not found")

    agent = Agent(**agent_data)
    agent.clear_memory(cur, commit=True)

    return {"message": f"Memory cleared for agent {agent_name}"}


@router.post("/clear-all-memory")
async def clear_all_agent_memory(db: Connection = Depends(get_db)):
    """Clear all memory for all agents."""
    cur = db.cursor()

    # Get all agents
    cur.execute("SELECT id, name, persona FROM agents")
    all_agent_data = cur.fetchall()

    # Clear memory for each agent
    for agent_data in all_agent_data:
        agent = Agent(id=agent_data[0], name=agent_data[1], persona=agent_data[2])
        agent.clear_memory(cur)

    db.commit()

    return {"message": "Memory cleared for all agents"}


# Health check endpoint
@router.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "message": "Agent API is running"}
