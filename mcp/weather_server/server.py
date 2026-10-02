from __future__ import annotations

import sys
from pathlib import Path

# Add project root to sys.path
root_dir = Path(__file__).resolve().parent.parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

from mcp.server.mcpserver import MCPServer
from mcp.weather_server.tools import (
    resolve_location_tool,
    get_current_weather_tool,
    get_hourly_weather_tool,
    get_daily_weather_tool,
    compare_weather_tool,
)

server = MCPServer("weather-service")


@server.tool(name="resolve_location", description="Geocodes a city or location name to latitude and longitude coordinates.")
def resolve_location(city_name: str) -> str:
    """Geocode city name into geographical coordinates."""
    import json
    return json.dumps(resolve_location_tool(city_name))


@server.tool(name="get_current_weather", description="Fetches current verified weather observations for given coordinates.")
def get_current_weather(latitude: float, longitude: float) -> str:
    """Get current weather metrics."""
    import json
    return json.dumps(get_current_weather_tool(latitude, longitude))


@server.tool(name="get_hourly_weather", description="Fetches hourly weather forecast metrics for given coordinates.")
def get_hourly_weather(latitude: float, longitude: float, hours: int = 24) -> str:
    """Get hourly weather forecast up to specified hours."""
    import json
    return json.dumps(get_hourly_weather_tool(latitude, longitude, hours))


@server.tool(name="get_daily_weather", description="Fetches daily weather forecasts and aggregated extremes.")
def get_daily_weather(latitude: float, longitude: float, days: int = 7) -> str:
    """Get daily weather summary and extremes."""
    import json
    return json.dumps(get_daily_weather_tool(latitude, longitude, days))


@server.tool(name="compare_weather", description="Compares current conditions against today's forecast extremes.")
def compare_weather(latitude: float, longitude: float) -> str:
    """Compare current conditions with daily extremes."""
    import json
    return json.dumps(compare_weather_tool(latitude, longitude))


def run_stdio_server():
    """Runs the MCP server over standard I/O."""
    server.run(transport="stdio")


if __name__ == "__main__":
    run_stdio_server()
