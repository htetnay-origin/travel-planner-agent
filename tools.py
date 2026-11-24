import httpx

def find_place(name):
    response = httpx.get(
        "https://geocoding-api.open-meteo.com/v1/search",
        params={"name": name, "count": 1, "language": "en"},
        timeout=10,
    )
    response.raise_for_status()
    data = response.json()

    if "results" not in data:
        return None

    place = data["results"][0]
    return {
        "name": place["name"],
        "state": place.get("admin1", ""),
        "country": place.get("country", ""),
        "latitude": place["latitude"],
        "longitude": place["longitude"],
        "timezone": place.get("timezone", "auto"),
    }

if __name__ == "__main__":
    print(find_place("Melbourne"))