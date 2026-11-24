"""Tools for the travel planner agent.

Each function fetches real data from a free public API (Open-Meteo, no API key
needed) and returns a small, clean result the agent can use.
"""

from datetime import date, timedelta
import httpx

# Open-Meteo returns weather as code numbers; this maps them to readable text.
WEATHER_CODES = {
    0: "Clear sky", 1: "Mainly clear", 2: "Partly cloudy", 3: "Overcast",
    45: "Fog", 48: "Fog",
    51: "Light drizzle", 53: "Drizzle", 55: "Heavy drizzle",
    61: "Light rain", 63: "Rain", 65: "Heavy rain",
    71: "Light snow", 73: "Snow", 75: "Heavy snow",
    80: "Rain showers", 81: "Rain showers", 82: "Violent rain showers",
    95: "Thunderstorm", 96: "Thunderstorm with hail", 99: "Thunderstorm with hail",
}

def find_place(name):
    """Look up a place by name and return its location details.

    Returns a dict with name, state, country, latitude, longitude and timezone,
    or None if no place matches.
    """
    
    response = httpx.get(
        "https://geocoding-api.open-meteo.com/v1/search",
        params={"name": name, "count": 1, "language": "en"},
        timeout=10,
    )
    response.raise_for_status()
    data = response.json()

    if "results" not in data:
        return None

    # Keep only the fields need;
    place = data["results"][0]
    return {
        "name": place["name"],
        "state": place.get("admin1", ""),
        "country": place.get("country", ""),
        "latitude": place["latitude"],
        "longitude": place["longitude"],
        "timezone": place.get("timezone", "auto"),
    }

def get_forecast(latitude, longitude, start_date, end_date):
    """Get the daily weather forecast for a location.

    Dates are 'YYYY-MM-DD' strings (both included). Open-Meteo only forecasts
    about 16 days ahead. Returns a list with one dict per day.
    """

    response = httpx.get(
        "https://api.open-meteo.com/v1/forecast",
        params={
            "latitude": latitude,
            "longitude": longitude,
            "daily": "weather_code,temperature_2m_max,temperature_2m_min,precipitation_probability_max",
            "timezone": "auto",
            "start_date": start_date,
            "end_date": end_date,
        },
        timeout=10,
    )
    response.raise_for_status()
    daily = response.json()["daily"]

    days = []
    for i in range(len(daily["time"])):
        days.append({
            "date": daily["time"][i],
            "weather": WEATHER_CODES.get(daily["weather_code"][i], "Unknown"),
            "max_temp_c": daily["temperature_2m_max"][i],
            "min_temp_c": daily["temperature_2m_min"][i],
            "rain_chance_percent": daily["precipitation_probability_max"][i],
        })
    return days



if __name__ == "__main__":
    place = find_place("Adelaide")
    today = date.today()
    print(get_forecast(
        place["latitude"],
        place["longitude"],
        today.isoformat(),
        (today + timedelta(days=2)).isoformat(),
    ))
