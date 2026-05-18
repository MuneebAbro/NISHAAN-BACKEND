import os
import requests

def fetch_weather_signal():
    # Karachi coordinates
    lat = 24.8607
    lon = 67.0011
    api_key = os.environ.get("OPENWEATHERMAP_API_KEY")
    
    # Default mock if no API key
    data = {
        "rainfall_mm_hr": 0.0,
        "temperature": 32.0,
        "humidity": 60,
        "wind_speed": 10.0,
        "conditionCode": "Clear",
        "credibility": 0.9
    }
    
    if api_key:
        url = f"https://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&appid={api_key}&units=metric"
        try:
            resp = requests.get(url, timeout=5)
            if resp.status_code == 200:
                res = resp.json()
                data["temperature"] = res.get("main", {}).get("temp", data["temperature"])
                data["humidity"] = res.get("main", {}).get("humidity", data["humidity"])
                data["wind_speed"] = res.get("wind", {}).get("speed", data["wind_speed"])
                rain_1h = res.get("rain", {}).get("1h", 0.0)
                data["rainfall_mm_hr"] = rain_1h
                if res.get("weather"):
                    data["conditionCode"] = res["weather"][0]["main"]
        except Exception:
            pass
            
    return data
