from fastapi import APIRouter, Depends
from sqlite3 import Connection
from .dependencies import get_db
from ollama import chat
from starlette.concurrency import run_in_threadpool
from pydantic import BaseModel

router = APIRouter()

@router.get("/agents")
async def get_agents(db: Connection = Depends(get_db)):
    cur = db.cursor()
    cur.execute("SELECT * FROM agents")
    return cur.fetchall()

class ChatRequest(BaseModel):
    prompt: str

@router.post("/chat")
async def chat_with_ollama(request: ChatRequest):
    messages = [{"role": "user", "content": request.prompt}]
    response = await run_in_threadpool(chat, model="mistral:7b", messages=messages)
    return {"response": response.message.content}
