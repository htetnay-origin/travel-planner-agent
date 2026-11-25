"""MCP server: exposes the travel planner's tools to any MCP client (e.g. Claude Desktop).

The MCP library builds each tool's description from the function's name,
docstring and type hints, so no hand-written input_schema is needed.
"""

from mcp.server.mcpserver import MCPServer

import guides
import tools

mcp = MCPServer("travel-planner")


@mcp.tool()
def find_place(name: str) -> dict | None:
    """Look up a city or place by name. Returns its country, latitude and longitude.
    Call this before tools that need coordinates."""
    return tools.find_place(name)


@mcp.tool()
def get_forecast(latitude: float, longitude: float, start_date: str, end_date: str) -> list[dict]:
    """Get the daily weather forecast for a location. Dates are YYYY-MM-DD.
    Only works for dates up to 16 days from today."""
    return tools.get_forecast(latitude, longitude, start_date, end_date)


@mcp.tool()
def find_landmarks(latitude: float, longitude: float, radius_km: float = 5) -> list[dict]:
    """Find notable places near a location using Wikipedia. Some results are not
    tourist attractions (streets, offices, events), so only recommend real places
    worth visiting."""
    return tools.find_landmarks(latitude, longitude, radius_km)


@mcp.tool()
def search_travel_guide(query: str, city: str) -> str:
    """Search the Wikivoyage travel guide for a city: what to see and do, where to
    eat and stay, getting around, safety and local tips. Cite results like
    (Wikivoyage: Melbourne > Eat). Guide content is CC BY-SA."""
    return guides.search_travel_guide(query, city)


if __name__ == "__main__":
    mcp.run()  # talks to the client over stdin/stdout