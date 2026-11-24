"""The travel planner agent: connects Claude to our tools."""

from datetime import date

from dotenv import load_dotenv

load_dotenv()  # loads ANTHROPIC_API_KEY from .env

import anthropic

from tools import find_place, get_forecast

# ---------- Part 1: the Claude client ----------
client = anthropic.Anthropic()
MODEL = "claude-haiku-5-5"
MAX_ROUNDS = 5  # safety limit on how many times we call Claude per question

# NEW: instructions for Claude, including today's date
SYSTEM = f"""You are a helpful travel planning assistant.
Today's date is {date.today().isoformat()}.
Use your tools to get real information. Never make up weather data."""


# ---------- Part 2: the tool menu (sent TO Claude) ----------
TOOLS = [
    {
        "name": "find_place",
        "description": "Look up a city or place by name. Returns its country, "
                       "latitude and longitude. Call this before get_forecast.",
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Place name, e.g. 'Melbourne'"},
            },
            "required": ["name"],
        },
    },
    {
        "name": "get_forecast",
        "description": "Get the daily weather forecast for a location. "
                       "Only works for dates up to 16 days from today.",
        "input_schema": {
            "type": "object",
            "properties": {
                "latitude": {"type": "number"},
                "longitude": {"type": "number"},
                "start_date": {"type": "string", "description": "YYYY-MM-DD"},
                "end_date": {"type": "string", "description": "YYYY-MM-DD"},
            },
            "required": ["latitude", "longitude", "start_date", "end_date"],
        },
    },
]


# ---------- Part 3: tool name → real function (used by OUR code) ----------
TOOL_FUNCTIONS = {
    "find_place": find_place,
    "get_forecast": get_forecast,
}


# ---------- Part 4: run the tool Claude asked for ----------
def run_tool(name, inputs):
    """Run the tool Claude asked for and return the result as text."""
    try:
        function = TOOL_FUNCTIONS[name]   # "find_place" → the real function
        result = function(**inputs)       # e.g. find_place(name="Melbourne")
        return str(result)                # Claude needs text
    except Exception as error:
        # Give the error to Claude instead of crashing, so it can recover
        return f"Error: {error}"


# ---------- Part 5: the agent loop ----------
def ask(question):
    """Answer a question, letting Claude call tools as many times as it needs."""
    messages = [{"role": "user", "content": question}]

    while True:
        # Send the conversation + tool menu to Claude
        response = client.messages.create(
            model=MODEL,
            max_tokens=1024,
            system=SYSTEM,
            tools=TOOLS,
            messages=messages,
        )

        # Save Claude's reply in the conversation, exactly as received
        messages.append({"role": "assistant", "content": response.content})

        # No tool requested → this is the final answer
        if response.stop_reason != "tool_use":
            return "".join(b.text for b in response.content if b.type == "text")

        # Run every tool Claude asked for and collect the results
        results = []
        for block in response.content:
            if block.type == "tool_use":
                print(f"  [tool] {block.name}({block.input})")
                output = run_tool(block.name, block.input)
                results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,   # links this result to Claude's request
                    "content": output,
                })

        # Send the results back to Claude, then loop again
        messages.append({"role": "user", "content": results})


# ---------- Part 6: quick test ----------
if __name__ == "__main__":
    print(ask("What's the weather in Tokyo tomorrow?"))