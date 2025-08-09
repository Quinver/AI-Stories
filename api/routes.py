from fastapi import APIRouter, Depends, HTTPException
from sqlite3 import Connection
from .dependencies import get_db
from agents import Agent, create_agent_conversation, run_agent
from db.queries import load_agent
from starlette.concurrency import run_in_threadpool
from pydantic import BaseModel
from typing import List, Optional


router = APIRouter()


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


@router.post("/chat")
async def chat_with_agent(request: ChatRequest, db: Connection = Depends(get_db)):
    """Chat with a specific agent."""
    cur = db.cursor()

    if request.api not in ["ollama", "openai"]:
        raise HTTPException(
            status_code=400, detail="API must be either 'ollama' or 'openai'"
        )

    if not request.agent_name:
        raise HTTPException(
            status_code=400, detail="agent_name is required"
        )

    agent_data = load_agent(request.agent_name)
    if not agent_data:
        raise HTTPException(
            status_code=404, detail=f"Agent {request.agent_name} not found"
        )

    agent = Agent(**agent_data)

    cur.execute("SELECT id, name, persona FROM agents")
    all_agent_data = cur.fetchall()
    all_agents = [Agent(id=row[0], name=row[1], persona=row[2]) for row in all_agent_data]

    # Run in thread pool to avoid blocking
    response = await run_in_threadpool(
        run_agent, agent, request.prompt, cur, all_agents, request.api
    )

    db.commit()

    return {"agent": request.agent_name, "response": response, "api": request.api}


class ConversationRequest(BaseModel):
    prompt: str
    agent_names: List[str]
    turns: int = 3
    api: Optional[str] = "ollama"


@router.post("/conversation")
async def create_conversation(
    request: ConversationRequest, db: Connection = Depends(get_db)
):
    """Create a multi-turn conversation between specified agents."""
    cur = db.cursor()

    if request.api not in ["ollama", "openai"]:
        raise HTTPException(
            status_code=400, detail="API must be either 'ollama' or 'openai'"
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
        create_agent_conversation,
        agents,
        request.prompt,
        cur,
        request.turns,
        request.api,
    )

    return {
        "prompt": request.prompt,
        "agents": [agent.name for agent in agents],
        "turns": request.turns,
        "conversation": conversation,
        "api": request.api,
    }


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
