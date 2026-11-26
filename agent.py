"""The travel planner agent: an MCP client that lets Claude use our MCP server's tools.

agent.py knows nothing about weather or guides itself. It starts server.py,
asks it which tools exist, and asks it to run them when Claude requests one.
"""

import asyncio
import sys
from datetime import date
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()  # loads ANTHROPIC_API_KEY from .env

import anthropic
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

# ---------- Part 1: settings ----------
client = anthropic.AsyncAnthropic()  # async version, to work with the async MCP client
MODEL = "claude-haiku-5-5"
MAX_ROUNDS = 5

SYSTEM = f"""You are a helpful travel planning assistant.
Today's date is {date.today().isoformat()}.
Use your tools to get real information. Never make up weather data or place names.
When you use information from search_travel_guide, cite it like (Wikivoyage: Melbourne > Eat).
Guide details such as prices and opening hours may be out of date, so suggest checking them.
Travel guide content comes from Wikivoyage (CC BY-SA)."""

# How to start our MCP server (absolute path, so it works from any folder)
SERVER_PATH = Path(__file__).parent / "server.py"
SERVER = StdioServerParameters(command=sys.executable, args=[str(SERVER_PATH)])


# ---------- Part 2: get the tool menu FROM the server ----------
async def load_tools(session):
    """Ask the MCP server for its tools and convert them to Claude's format."""
    result = await session.list_tools()
    return [
        {"name": t.name, "description": t.description or "", "input_schema": t.input_schema}
        for t in result.tools
    ]


# ---------- Part 3: ask the server to run a tool ----------
async def run_tool(session, name, inputs):
    """Ask the MCP server to run a tool and return the result as text."""
    try:
        result = await session.call_tool(name, inputs)
        text = "\n".join(getattr(c, "text", "") for c in result.content)
        return f"Error: {text}" if result.is_error else text
    except Exception as error:
        return f"Error: {error}"


# ---------- Part 4: the agent loop (same as before, plus await) ----------
async def ask(session, tools, messages, question):
    """Answer a question, letting Claude call tools as many times as it needs."""
    messages.append({"role": "user", "content": question})
    steps = []
    for round_number in range(MAX_ROUNDS):
        response = await client.messages.create(
            model=MODEL,
            max_tokens=4096,
            system=SYSTEM,
            tools=tools,
            messages=messages,
        )
        messages.append({"role": "assistant", "content": response.content})

        if response.stop_reason != "tool_use":
            answer = "".join(b.text for b in response.content if b.type == "text")
            if response.stop_reason == "max_tokens":
                answer += "\n\n[Answer was cut off because it hit the length limit.]"
            return answer, steps

        results = []
        for block in response.content:
            if block.type == "tool_use":
                steps.append({"tool": block.name, "input": block.input})
                output = await run_tool(session, block.name, block.input)
                results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": output,
                })
        messages.append({"role": "user", "content": results})

    return "Sorry, I couldn't finish answering that. Please try a simpler question.", steps


# ---------- Part 5: connect to the server, then chat ----------
async def main():
    async with stdio_client(SERVER) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools = await load_tools(session)
            print("Connected to MCP server. Tools:", ", ".join(t["name"] for t in tools))
            print("Travel planner ready. Type 'quit' to exit.\n")

            messages = []
            while True:
                question = input("You: ").strip()
                if question.lower() in ("quit", "exit"):
                    break
                if not question:
                    continue
                answer, steps = await ask(session, tools, messages, question)
                for step in steps:
                    print(f"  [tool] {step['tool']}({step['input']})")
                print(f"Agent: {answer}\n")
                


if __name__ == "__main__":
    asyncio.run(main())