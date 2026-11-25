"""The travel planner agent: connects Claude to our tools."""

from datetime import date

from dotenv import load_dotenv

from guides import search_travel_guide

load_dotenv()  # loads ANTHROPIC_API_KEY from .env

import anthropic

from tools import find_attractions, find_place, get_forecast, find_landmarks

# ---------- Part 1: the Claude client ----------
client = anthropic.Anthropic()
MODEL = "claude-haiku-5-5"
MAX_ROUNDS = 5  # safety limit on how many times we call Claude per question

# NEW: instructions for Claude, including today's date
SYSTEM = f"""You are a helpful travel planning assistant.
Today's date is {date.today().isoformat()}.
Use your tools to get real information. Never make up weather data or place names.
When you use information from search_travel_guide, cite it like (Wikivoyage: Melbourne > Eat).
Guide details such as prices and opening hours may be out of date, so suggest checking them.
Travel guide content comes from Wikivoyage (CC BY-SA)."""

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

        {
        "name": "find_attractions",
                "description": "Find cafes, restaurants, parks or bars near a location using "
                       "OpenStreetMap. Use find_landmarks for sightseeing instead. This "
                       "service is sometimes slow or unavailable; if it fails, tell the "
                       "user honestly and do not invent place names.",
        "input_schema": {
            "type": "object",
            "properties": {
                "latitude": {"type": "number"},
                "longitude": {"type": "number"},
                "category": {
                    "type": "string",
                    "enum": ["attractions", "museums", "food", "parks", "nightlife"],
                },
                "radius_km": {"type": "number", "description": "Search radius in km, default 3"},
            },
            "required": ["latitude", "longitude", "category"],
        },
    },
    {
        "name": "find_landmarks",
        "description": "Find notable places near a location using Wikipedia: landmarks, "
                       "museums, historic buildings, theatres, arcades and more. Fast and "
                       "reliable; use this first for sightseeing. Returns the closest "
                       "articles with short descriptions; some are not tourist "
                       "attractions (streets, offices, events, historical incidents), so "
                       "only recommend real places worth visiting. For a different area "
                       "of a city, call find_place on that suburb first.",
        "input_schema": {
            "type": "object",
            "properties": {
                "latitude": {"type": "number"},
                "longitude": {"type": "number"},
                "radius_km": {"type": "number", "description": "Search radius in km, max 10, default 5"},
            },
            "required": ["latitude", "longitude"],
        },
    },
        {
        "name": "search_travel_guide",
        "description": "Search the Wikivoyage travel guide for a city. Use this for "
                       "travel advice: what to see and do, where to eat, drink and "
                       "stay, getting around, costs, safety and local tips. Returns "
                       "passages labelled with their guide section. Prefer this over "
                       "your own knowledge for travel advice.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "What to look for, e.g. 'cheap places to eat'"},
                "city": {"type": "string", "description": "City name in English, e.g. 'Melbourne'"},
            },
            "required": ["query", "city"],
        },
    },
]


# ---------- Part 3: tool name → real function (used by OUR code) ----------
TOOL_FUNCTIONS = {
    "find_place": find_place,
    "get_forecast": get_forecast,
    "find_attractions": find_attractions,
    "find_landmarks": find_landmarks,
    "search_travel_guide": search_travel_guide,
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
def ask(messages, question):
    """Answer a question, letting Claude call tools as many times as it needs."""
    messages.append({"role": "user", "content": question})

    for round_number in range(MAX_ROUNDS):
        # Send the conversation + tool menu to Claude
        response = client.messages.create(
            model=MODEL,
            max_tokens=4096,
            system=SYSTEM,
            tools=TOOLS,
            messages=messages,
        )

        # Save Claude's reply in the conversation, exactly as received
        messages.append({"role": "assistant", "content": response.content})

      


        if response.stop_reason != "tool_use":
            answer = "".join(b.text for b in response.content if b.type == "text")
            if response.stop_reason == "max_tokens":
                answer += "\n\n[Answer was cut off because it hit the length limit.]"
            return answer

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
    return "Sorry, I couldn't finish answering that. Please try a simpler question."    


# ---------- Part 6: chat in the terminal ----------
def main():
    messages = []  # the conversation, kept for the whole chat
    print("Travel planner ready. Type 'quit' to exit.\n")

    while True:
        question = input("You: ").strip()
        if question.lower() in ("quit", "exit"):
            break
        if not question:
            continue

        answer = ask(messages, question)
        print(f"Agent: {answer}\n")


if __name__ == "__main__":
    main()