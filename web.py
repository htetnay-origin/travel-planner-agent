"""Web server: runs the agent behind a simple HTTP API and serves the chat page.

Start it with:  uvicorn web:app --port 8000
"""

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from mcp import ClientSession
from mcp.client.stdio import stdio_client
from pydantic import BaseModel

from agent import SERVER, ask, load_tools

state = {}          # the MCP connection and tool list, shared by every request
conversations = {}  # conversation_id -> that conversation's messages list


@asynccontextmanager
async def lifespan(app):
    """Runs once at startup: connect to the MCP server and keep it open."""
    async with stdio_client(SERVER) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            state["session"] = session
            state["tools"] = await load_tools(session)
            yield  # the web server runs while we're paused here; on shutdown, the connection closes


app = FastAPI(title="Travel Planner Agent", lifespan=lifespan)


class ChatRequest(BaseModel):
    """What the browser sends: which conversation, and the new message."""
    conversation_id: str
    message: str


@app.post("/chat")
async def chat(request: ChatRequest):
    """Run the agent on one message and return its answer plus the tools it used."""
    messages = conversations.setdefault(request.conversation_id, [])
    answer, steps = await ask(state["session"], state["tools"], messages, request.message)
    return {"answer": answer, "steps": steps}


@app.get("/")
async def home():
    """Serve the chat page."""
    return FileResponse(Path(__file__).parent / "index.html")