"""
weather.py - Detailed Climate & Google Maps Integration for Hello Kitty Assistant.
Fetches comprehensive climate data (temperature in C & F, feels like, condition,
high/low, humidity, wind, precipitation chance, exact coordinates) and generates
Google Maps links and interactive map preview frames for any city, region, or country worldwide.
"""

import os
import re
import urllib.parse
from typing import Tuple, Dict, Any, Optional
import requests

# In-memory storage for the latest climate and map query result
LAST_CLIMATE_MAP_INFO: Optional[Dict[str, Any]] = None


def clear_last_climate_map_info() -> None:
    """Clears the stored climate and map query info."""
    global LAST_CLIMATE_MAP_INFO
    LAST_CLIMATE_MAP_INFO = None


def get_last_climate_map_info() -> Optional[Dict[str, Any]]:
    """Returns the most recent climate and map query info dictionary."""
    global LAST_CLIMATE_MAP_INFO
    return LAST_CLIMATE_MAP_INFO


def get_weather_emoji(condition: str) -> str:
    """Returns an appropriate emoji matching the weather condition description."""
    c = condition.lower()
    if any(k in c for k in ["thunder", "storm", "lightning"]):
        return "⛈️"
    if any(k in c for k in ["snow", "blizzard", "ice", "sleet", "flurries"]):
        return "❄️"
    if any(k in c for k in ["heavy rain", "torrential", "downpour"]):
        return "🌧️"
    if any(k in c for k in ["rain", "drizzle", "shower", "patchy light rain"]):
        return "🌦️"
    if any(k in c for k in ["fog", "mist", "haze", "smoke", "dust"]):
        return "🌫️"
    if any(k in c for k in ["partly cloudy", "scattered clouds"]):
        return "🌤️"
    if any(k in c for k in ["cloud", "overcast"]):
        return "☁️"
    if any(k in c for k in ["sunny", "clear"]):
        return "☀️"
    return "🌤️"


def get_climate_and_map(location_query: str) -> Tuple[str, Dict[str, Any]]:
    """
    Fetches real-time detailed climate information and Google Maps integration
    for any region, city, or country worldwide.

    Args:
        location_query (str): Name of the country, region, state, or city.

    Returns:
        Tuple[str, Dict[str, Any]]: (spoken_text_summary, structured_climate_dict)
    """
    global LAST_CLIMATE_MAP_INFO

    clean_query = location_query.strip()
    if not clean_query:
        msg = "Which city, region, or country would you like to see on Google Maps and check the climate for?"
        return msg, {"success": False, "error": msg}

    # Clean out query prefix words and conversational noise words
    clean_query = re.sub(
        r'^(?:the\s+climate\s+of|climate\s+of|climate\s+in|map\s+of|google\s+map\s+of|map\s+for|weather\s+in|weather\s+of|detailed\s+weather\s+of)\s+',
        '', clean_query, flags=re.IGNORECASE
    ).strip()
    clean_query = re.sub(
        r'\b(right\s+now|right|now|today|outside|currently|please|in\s+detail|detail|detailed)\b',
        '', clean_query, flags=re.IGNORECASE
    ).strip()

    # Step 1: Query wttr.in JSON API (Comprehensive climate metrics + coordinates)
    climate_dict = None
    try:
        clean_encoded = urllib.parse.quote(clean_query)
        url = f"https://wttr.in/{clean_encoded}?format=j1"
        headers = {"User-Agent": "curl/7.68.0", "Accept": "application/json"}
        resp = requests.get(url, headers=headers, timeout=8)

        if resp.status_code == 200:
            data = resp.json()
            curr = data["current_condition"][0]
            area = data.get("nearest_area", [{}])[0]
            w0 = data.get("weather", [{}])[0]

            lat = float(area.get("latitude", 0.0))
            lon = float(area.get("longitude", 0.0))
            resolved_name = area.get("areaName", [{}])[0].get("value", clean_query.title())
            country = area.get("country", [{}])[0].get("value", "")
            region = area.get("region", [{}])[0].get("value", "")

            temp_c = int(curr.get("temp_C", 20))
            temp_f = int(curr.get("temp_F", round(temp_c * 9 / 5 + 32)))
            feels_c = int(curr.get("FeelsLikeC", temp_c))
            feels_f = int(curr.get("FeelsLikeF", round(feels_c * 9 / 5 + 32)))
            condition = curr.get("weatherDesc", [{}])[0].get("value", "Clear").strip()
            humidity = int(curr.get("humidity", 50))
            wind_kmph = int(curr.get("windspeedKmph", 0))
            precip_mm = float(curr.get("precipMM", 0.0))
            max_c = int(w0.get("maxtempC", temp_c))
            min_c = int(w0.get("mintempC", temp_c))
            hourly = w0.get("hourly", [{}])
            rain_chance = int(hourly[0].get("chanceofrain", 0)) if hourly else 0

            climate_dict = {
                "success": True,
                "location": clean_query.title(),
                "resolved_name": resolved_name,
                "country": country,
                "region": region,
                "latitude": round(lat, 4),
                "longitude": round(lon, 4),
                "temp_c": temp_c,
                "temp_f": temp_f,
                "feels_like_c": feels_c,
                "feels_like_f": feels_f,
                "condition": condition,
                "emoji": get_weather_emoji(condition),
                "humidity": humidity,
                "wind_kmph": wind_kmph,
                "precip_mm": precip_mm,
                "max_temp_c": max_c,
                "min_temp_c": min_c,
                "rain_chance": rain_chance,
            }
    except Exception as exc:
        print(f"[Weather Engine Notice]: wttr.in lookup notice: {exc}", flush=True)

    # Step 2: Fallback to OpenStreetMap Nominatim + Open-Meteo
    if not climate_dict or not climate_dict.get("success"):
        try:
            s = requests.Session()
            s.headers.update({"User-Agent": "HelloKittyAssistant/1.0 (contact@hellokitty.local)"})
            geo_resp = s.get(
                "https://nominatim.openstreetmap.org/search",
                params={"q": clean_query, "format": "json", "limit": 1},
                timeout=6
            )
            if geo_resp.status_code == 200 and geo_resp.json():
                first = geo_resp.json()[0]
                lat = float(first["lat"])
                lon = float(first["lon"])
                disp = first.get("display_name", clean_query)
                parts = [p.strip() for p in disp.split(",")]
                resolved_name = parts[0]
                country = parts[-1] if len(parts) > 1 else ""

                w_resp = s.get(
                    "https://api.open-meteo.com/v1/forecast",
                    params={
                        "latitude": lat,
                        "longitude": lon,
                        "current": "temperature_2m,relative_humidity_2m,apparent_temperature,weather_code,wind_speed_10m",
                        "daily": "temperature_2m_max,temperature_2m_min,precipitation_probability_max",
                        "timezone": "auto"
                    },
                    timeout=6
                ).json()

                curr = w_resp.get("current", {})
                daily = w_resp.get("daily", {})
                temp_c = round(curr.get("temperature_2m", 22))
                temp_f = round(temp_c * 9 / 5 + 32)
                feels_c = round(curr.get("apparent_temperature", temp_c))
                feels_f = round(feels_c * 9 / 5 + 32)
                humidity = int(curr.get("relative_humidity_2m", 50))
                wind_kmph = round(curr.get("wind_speed_10m", 0))
                max_c = round(daily.get("temperature_2m_max", [temp_c])[0])
                min_c = round(daily.get("temperature_2m_min", [temp_c])[0])
                rain_chance = int(daily.get("precipitation_probability_max", [0])[0])
                condition = "Clear"
                w_code = curr.get("weather_code", 0)
                if w_code in [1, 2]:
                    condition = "Partly Cloudy"
                elif w_code == 3:
                    condition = "Overcast"
                elif w_code in [45, 48]:
                    condition = "Foggy"
                elif w_code in [51, 53, 55, 61, 63, 65, 80, 81, 82]:
                    condition = "Rain"
                elif w_code in [71, 73, 75, 77, 85, 86]:
                    condition = "Snow"
                elif w_code in [95, 96, 99]:
                    condition = "Thunderstorm"

                climate_dict = {
                    "success": True,
                    "location": clean_query.title(),
                    "resolved_name": resolved_name,
                    "country": country,
                    "region": "",
                    "latitude": round(lat, 4),
                    "longitude": round(lon, 4),
                    "temp_c": temp_c,
                    "temp_f": temp_f,
                    "feels_like_c": feels_c,
                    "feels_like_f": feels_f,
                    "condition": condition,
                    "emoji": get_weather_emoji(condition),
                    "humidity": humidity,
                    "wind_kmph": wind_kmph,
                    "precip_mm": 0.0,
                    "max_temp_c": max_c,
                    "min_temp_c": min_c,
                    "rain_chance": rain_chance,
                }
        except Exception as exc2:
            print(f"[Weather Engine Notice]: Fallback lookup notice: {exc2}", flush=True)

    # If all lookups failed
    if not climate_dict or not climate_dict.get("success"):
        fail_msg = f"I'm sorry, I couldn't find detailed climate or map data for '{clean_query}'. Please check the spelling or try another location."
        LAST_CLIMATE_MAP_INFO = None
        return fail_msg, {"success": False, "error": fail_msg}

    # Generate Google Maps & OpenStreetMap embed URLs
    lat = climate_dict["latitude"]
    lon = climate_dict["longitude"]
    loc_display = climate_dict["resolved_name"]
    if climate_dict["country"] and climate_dict["country"] not in loc_display:
        loc_display += f", {climate_dict['country']}"

    # Direct Google Maps navigation URL with pin coordinates
    google_maps_url = f"https://www.google.com/maps/search/?api=1&query={lat},{lon}"
    # Embedded OpenStreetMap iframe URL
    embed_map_url = (
        f"https://www.openstreetmap.org/export/embed.html?"
        f"bbox={lon - 0.25:.4f}%2C{lat - 0.18:.4f}%2C{lon + 0.25:.4f}%2C{lat + 0.18:.4f}"
        f"&layer=mapnik&marker={lat:.4f}%2C{lon:.4f}"
    )

    climate_dict["google_maps_url"] = google_maps_url
    climate_dict["embed_map_url"] = embed_map_url
    climate_dict["display_location"] = loc_display

    # Store in module state for web server serialization
    LAST_CLIMATE_MAP_INFO = climate_dict

    # Build comprehensive spoken/readable summary
    spoken_summary = (
        f"Here is the detailed climate and map for {loc_display}! "
        f"Currently, it is {climate_dict['temp_c']}°C ({climate_dict['temp_f']}°F) and {climate_dict['condition']} {climate_dict['emoji']}, "
        f"feeling like {climate_dict['feels_like_c']}°C. "
        f"Today's high is {climate_dict['max_temp_c']}°C and low is {climate_dict['min_temp_c']}°C, "
        f"with {climate_dict['humidity']}% humidity, wind at {climate_dict['wind_kmph']} km/h, "
        f"and a {climate_dict['rain_chance']}% chance of rain. "
        f"Coordinates are {lat}° N, {lon}° E. "
        f"You can view the interactive map below or click 'Open in Google Maps'!"
    )

    return spoken_summary, climate_dict


def get_weather_for_city(city_name: str) -> str:
    """
    Fetches real-time weather and climate for the specified city, region, or country.
    Backward-compatible wrapper for get_climate_and_map.

    Args:
        city_name (str): Name of the city, region, or country.

    Returns:
        str: Spoken weather and climate description.
    """
    clean_city = city_name.strip()
    if not clean_city:
        return "Which city would you like to know the weather for?"

    summary, _ = get_climate_and_map(clean_city)
    return summary
