"""
test_climate_map.py - Automated tests for Google Maps and Climate Integration.
Tests:
1. features.weather.get_climate_and_map for countries, cities, and regions.
2. features.dispatcher.extract_map_or_climate_request and handle_feature.
3. web.app POST /chat endpoint returning is_weather_map: True and weather_map dict.
"""

import sys
import unittest
import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from features.weather import get_climate_and_map, get_weather_emoji, get_last_climate_map_info
from features.dispatcher import extract_map_or_climate_request, handle_feature, clear_pending_action
from web.app import app


class TestClimateAndMaps(unittest.TestCase):
    """Tests for Climate and Google Maps feature integration."""

    def test_weather_emoji(self):
        self.assertEqual(get_weather_emoji("Thunderstorm with heavy rain"), "⛈️")
        self.assertEqual(get_weather_emoji("Snow"), "❄️")
        self.assertEqual(get_weather_emoji("Heavy rain"), "🌧️")
        self.assertEqual(get_weather_emoji("Patchy light rain"), "🌦️")
        self.assertEqual(get_weather_emoji("Sunny"), "☀️")
        self.assertEqual(get_weather_emoji("Overcast"), "☁️")

    def test_extract_map_or_climate_request(self):
        is_m, loc = extract_map_or_climate_request("climate of Switzerland")
        self.assertTrue(is_m)
        self.assertEqual(loc, "switzerland")

        is_m, loc = extract_map_or_climate_request("google map of Pakistan")
        self.assertTrue(is_m)
        self.assertEqual(loc, "pakistan")

        is_m, loc = extract_map_or_climate_request("where is Lahore on google map")
        self.assertTrue(is_m)
        self.assertEqual(loc, "lahore")

        is_m, loc = extract_map_or_climate_request("show map of California in detail")
        self.assertTrue(is_m)
        self.assertEqual(loc, "california")

        is_m, loc = extract_map_or_climate_request("google map")
        self.assertTrue(is_m)
        self.assertIsNone(loc)

        is_m, loc = extract_map_or_climate_request("what time is it")
        self.assertFalse(is_m)

    def test_get_climate_and_map_data(self):
        summary, info = get_climate_and_map("Switzerland")
        self.assertTrue(info.get("success"))
        self.assertIn("Switzerland", summary)
        self.assertIn("google_maps_url", info)
        self.assertIn("embed_map_url", info)
        self.assertIn("https://www.google.com/maps/search/?api=1&query=", info["google_maps_url"])
        self.assertIn("latitude", info)
        self.assertIn("longitude", info)
        self.assertIn("temp_c", info)
        self.assertIn("humidity", info)
        self.assertIn("wind_kmph", info)

    def test_web_chat_climate_response(self):
        app.config["TESTING"] = True
        client = app.test_client()

        payload = {"message": "climate of Switzerland"}
        response = client.post(
            "/chat",
            data=json.dumps(payload),
            content_type="application/json"
        )
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertTrue(data.get("is_feature"))
        self.assertTrue(data.get("is_weather_map"))
        self.assertIsNotNone(data.get("weather_map"))
        w_map = data["weather_map"]
        self.assertIn("google_maps_url", w_map)
        self.assertIn("embed_map_url", w_map)
        self.assertIn("temp_c", w_map)

    def test_web_chat_map_followup(self):
        app.config["TESTING"] = True
        client = app.test_client()

        clear_pending_action()
        resp1 = client.post("/chat", data=json.dumps({"message": "google map"}), content_type="application/json")
        self.assertEqual(resp1.status_code, 200)
        d1 = resp1.get_json()
        self.assertIn("Which city, region, or country", d1.get("reply"))

        resp2 = client.post("/chat", data=json.dumps({"message": "Lahore"}), content_type="application/json")
        self.assertEqual(resp2.status_code, 200)
        d2 = resp2.get_json()
        self.assertTrue(d2.get("is_weather_map"))
        self.assertIn("google_maps_url", d2.get("weather_map", {}))


if __name__ == "__main__":
    unittest.main()
