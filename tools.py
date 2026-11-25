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

# Which OpenStreetMap tags count as each category
PLACE_CATEGORIES = {
    "attractions": '["tourism"~"attraction|viewpoint|zoo|theme_park|aquarium"]',
    "museums": '["tourism"~"museum|gallery"]',
    "food": '["amenity"~"restaurant|cafe"]',
    "parks": '["leisure"~"park|garden|nature_reserve"]',
    "nightlife": '["amenity"~"bar|pub|nightclub"]',
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


def find_attractions(latitude, longitude, category="attractions", radius_km=3, limit=10):
    """Find named places of one category near a location, using OpenStreetMap.

    Returns a list of dicts with name, type, latitude and longitude.
    """
    tag_filter = PLACE_CATEGORIES[category]
    radius_m = int(radius_km * 1000)

    # Overpass query: everything matching the filter within radius_m of the point
    query = f"""
    [out:json][timeout:20];
    nwr{tag_filter}(around:{radius_m},{latitude},{longitude});
    out center 30;
    """

    # response = httpx.post(
    #     "https://overpass-api.de/api/interpreter",
    #     data={"data": query},
    #     headers={"User-Agent": "travel-planner-agent (student project)"},
    #     timeout=30,
    # )
    # response.raise_for_status()

    # Overpass is a free shared service; if one server fails, try the next
    servers = [
        "https://overpass-api.de/api/interpreter",
        "https://overpass.kumi.systems/api/interpreter",
    ]
    for url in servers:
        try:
            response = httpx.post(
                url,
                data={"data": query},
                headers={"User-Agent": "travel-planner-agent (student project)"},
                timeout=30,
            )
            response.raise_for_status()
            break  # success, stop trying other servers
        except httpx.HTTPError as error:
            last_error = error
    else:
        # only runs if no server succeeded
        raise last_error

    places = []
    for item in response.json()["elements"]:
        tags = item.get("tags", {})
        if "name" not in tags:
            continue  # skip unnamed places
        # Points have lat/lon directly; areas and buildings have a "center"
        point = item if "lat" in item else item.get("center", {})
        places.append({
            "name": tags["name"],
            "type": tags.get("tourism") or tags.get("amenity") or tags.get("leisure"),
            "latitude": point.get("lat"),
            "longitude": point.get("lon"),
        })
        if len(places) >= limit:
            break
    return places


def find_landmarks(latitude, longitude, radius_km=5, limit=40):
    """Find notable places near a location using Wikipedia's location search.

    Returns a list of dicts with name, a short description, latitude and longitude.
    Wikipedia only covers places notable enough to have an article.
    """
    radius_m = min(int(radius_km * 1000), 10000)  # Wikipedia allows max 10 km

    response = httpx.get(
        "https://en.wikipedia.org/w/api.php",
        params={
            "action": "query",
            "generator": "geosearch",            # find articles near a point...
            "ggscoord": f"{latitude}|{longitude}",
            "ggsradius": radius_m,
            "ggslimit": limit,
            "prop": "description|coordinates",   # ...and include a short description
            "colimit": "max",
            "format": "json",
            "formatversion": 2,
        },
        headers={"User-Agent": "travel-planner-agent/0.1 (student project)"},
        timeout=15,
    )
    response.raise_for_status()
    pages = response.json().get("query", {}).get("pages", [])

    places = []
    for page in pages:
        if not page.get("description"):               # NEW
            continue  # skip articles with no description  # NEW
        coords = page.get("coordinates", [{}])[0]
        places.append({
            "name": page["title"],
            "description": page.get("description", ""),
            "latitude": coords.get("lat"),
            "longitude": coords.get("lon"),
        })
    return places

if __name__ == "__main__":
    place = find_place("Melbourne")
    for p in find_landmarks(place["latitude"], place["longitude"]):
        print(p)
