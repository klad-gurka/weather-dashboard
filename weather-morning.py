#!/usr/bin/env python3
"""Weather Dashboard - Morgon-editon för Rävlanda & Mölndal
Mörkt tema med väder, luftkvalitet och pollen.
"""
from PIL import Image, ImageDraw, ImageFont
import cairosvg
import urllib.request
import json
import os
from datetime import datetime

ICONS_DIR = os.path.dirname(os.path.abspath(__file__)) + "/icons"
os.makedirs(ICONS_DIR, exist_ok=True)

def get_icon(name, size=64):
    path = f"{ICONS_DIR}/{name}_{size}.png"
    if not os.path.exists(path):
        svg_url = f"https://raw.githubusercontent.com/Makin-Things/weather-icons/master/static/{name}.svg"
        try:
            svg_data = urllib.request.urlopen(svg_url, timeout=10).read()
            cairosvg.svg2png(bytestring=svg_data, write_to=path, output_width=size, output_height=size)
        except:
            return None
    return Image.open(path).convert("RGBA")

print("Laddar ikoner...")
weather_icons = {}
for name in ["clear-day", "cloudy-1-day", "cloudy-2-day", "cloudy", "fog", 
             "rainy-1", "rainy-2", "rainy-3", "snowy-1", "snowy-2", "snowy-3", "thunderstorms"]:
    try:
        weather_icons[name] = get_icon(name, 64)
    except:
        pass

aqi_icon = get_icon("air", 40)
wind_icon = get_icon("wind", 24)

def get_icon_name(code):
    mapping = {
        0: "clear-day", 1: "cloudy-1-day", 2: "cloudy-2-day", 3: "cloudy",
        45: "fog", 48: "fog",
        51: "rainy-1", 53: "rainy-1", 55: "rainy-1",
        61: "rainy-2", 63: "rainy-2", 65: "rainy-3",
        71: "snowy-1", 73: "snowy-1", 75: "snowy-3",
        80: "rainy-2", 81: "rainy-2", 82: "rainy-3",
        95: "thunderstorms", 96: "thunderstorms", 99: "thunderstorms",
    }
    return mapping.get(code, "cloudy")

def get_weather(lat, lon):
    url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current=temperature_2m,weather_code,wind_speed_10m&hourly=temperature_2m,precipitation_probability&timezone=Europe/Stockholm&forecast_days=2"
    try:
        data = json.loads(urllib.request.urlopen(url, timeout=10).read().decode())
        return {
            'current': data['current'],
            'hourly': {
                'temp': data['hourly']['temperature_2m'][24:48],
                'precip': data['hourly']['precipitation_probability'][24:48],
            }
        }
    except:
        return None

def get_air_quality(lat, lon):
    try:
        url = f"https://air-quality-api.open-meteo.com/v1/air-quality?latitude={lat}&longitude={lon}&current=us_aqi,pm2_5,pm10&timezone=Europe/Stockholm"
        data = json.loads(urllib.request.urlopen(url, timeout=10).read().decode())
        return data.get('current', {})
    except Exception as e:
        print(f"AQI error: {e}")
        return None

def get_aqi_status(aqi):
    if aqi is None:
        return "?", "#888888"
    if aqi <= 50:
        return "Bra", "#44dd44"
    elif aqi <= 100:
        return "Måttlig", "#dddd44"
    elif aqi <= 150:
        return "Ohälsosamt för känsliga", "#dd8844"
    elif aqi <= 200:
        return "Ohälsosamt", "#dd4444"
    elif aqi <= 300:
        return "Mycket ohälsosamt", "#aa44aa"
    else:
        return "Farligt", "#882222"

def draw_temp_graph(draw, x, y, w, h, temps, precips):
    if not temps:
        return
    
    for i in range(h):
        alpha = int(20 + (i / h) * 30)
        draw.line([x, y + i, x + w, y + i], fill=(60, 80, 120, alpha))
    
    min_temp = min(temps) - 1
    max_temp = max(temps) + 1
    
    for i, p in enumerate(precips):
        if p > 25:
            bar_x = x + (i * w // 24)
            bar_h = int((p / 100) * h * 0.45)
            draw.rectangle([bar_x, y + h - bar_h, bar_x + w // 24 - 1, y + h], 
                          fill=(80, 140, 255, 40 + p))
    
    points = []
    for i, t in enumerate(temps):
        px = x + (i * w // 24) + 4
        py = y + h - int(((t - min_temp) / (max_temp - min_temp)) * h)
        points.append((px, py))
    
    if len(points) > 1:
        for glow in range(3, 0, -1):
            glow_points = [(px, py - glow * 2) for px, py in points]
            draw.line(glow_points, fill=(255, 107, 107, 50), width=glow * 2)
        
        draw.line(points, fill='#ff6b6b', width=3)
        
        for px, py in points[::3]:
            draw.ellipse([px-4, py-4, px+4, py+4], fill='#ff6b6b', outline='#fff', width=1)
            draw.ellipse([px-2, py-2, px+2, py+2], fill='#fff')

def draw_city_card(draw, img, x, y, w, h, loc, w_data, aqi_data, weather_icons, aqi_icon, wind_icon, font_city, font_temp, font_data, font_label, font_small):
    """Draw a city weather card"""
    draw.rounded_rectangle([x, y, x + w, y + h], radius=12, 
                          fill='#1a1a2e', outline='#2a2a4e', width=2)
    
    current = w_data['current']
    icon_name = get_icon_name(current['weather_code'])
    icon = weather_icons.get(icon_name)
    
    # Weather icon
    if icon:
        img.paste(icon, (x + w // 2 - 32, y + 15), icon)
    
    # City name
    city_w = draw.textlength(loc['name'], font=font_city)
    draw.text((x + w // 2 - city_w // 2, y + 85), loc['name'], fill='white', font=font_city)
    
    # Big temp
    temp_str = f"{current['temperature_2m']:.0f}°"
    temp_w = draw.textlength(temp_str, font=font_temp)
    draw.text((x + w // 2 - temp_w // 2, y + 120), temp_str, fill='#ff6b6b', font=font_temp)
    
    # Wind
    wind_y = y + 200
    if wind_icon:
        img.paste(wind_icon, (x + w // 2 - 25, wind_y), wind_icon)
    wind_str = f"{current['wind_speed_10m']:.0f} km/h"
    wind_w = draw.textlength(wind_str, font=font_data)
    draw.text((x + w // 2 - wind_w // 2 + 20, wind_y + 3), wind_str, fill='#4ecdc4', font=font_data)
    
    # AQI
    aq_y = wind_y + 32
    if aqi_icon:
        img.paste(aqi_icon, (x + w // 2 - 20, aq_y), aqi_icon)
    if aqi_data:
        aqi_val = aqi_data.get('us_aqi', 0)
        aqi_status, aqi_color = get_aqi_status(aqi_val)
        aqi_str = f"AQI: {aqi_val} ({aqi_status})"
        aqi_w = draw.textlength(aqi_str, font=font_data)
        draw.text((x + w // 2 - aqi_w // 2 + 20, aq_y + 3), aqi_str, fill=aqi_color, font=font_data)
    
    # 24h graph
    graph_y = y + h - 90
    graph_x = x + 10
    graph_w = w - 20
    graph_h = 70
    
    draw.rounded_rectangle([graph_x, graph_y, graph_x + graph_w, graph_y + graph_h], radius=6,
                          fill='#252540', outline='#3a3a5e', width=1)
    
    draw_temp_graph(draw, graph_x + 5, graph_y + 5, graph_w - 10, graph_h - 10,
                   w_data['hourly']['temp'], w_data['hourly']['precip'])
    
    temps = w_data['hourly']['temp']
    if temps:
        draw.text((graph_x + 5, graph_y + 3), f"{max(temps):.0f}°", fill='#ff6b6b', font=font_small)
        draw.text((graph_x + 5, graph_y + graph_h - 12), f"{min(temps):.0f}°", fill='#ff6b6b', font=font_small)
    
    for idx, label in enumerate(["00", "06", "12", "18", "24"]):
        tx = graph_x + (idx * (graph_w - 10) // 4)
        draw.text((tx, graph_y + graph_h + 3), label, fill='#666677', font=font_small)

# === MAIN IMAGE ===
W, H = 900, 650
img = Image.new('RGB', (W, H), color='#0f0f1a')
draw = ImageDraw.Draw(img)

for y in range(H):
    alpha = int(y / H * 15)
    draw.line([0, y, W, y], fill=(30, 30, 50, alpha))

try:
    font_title = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 32)
    font_city = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 24)
    font_temp = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 56)
    font_data = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 14)
    font_label = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 12)
    font_small = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 11)
    font_pollen_name = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 13)
except:
    font_title = font_city = font_temp = font_data = font_label = font_small = font_pollen_name = ImageFont.load_default()

# Header
title = f"Godmorgon! ☀️ {datetime.now().strftime('%d %b')}"
title_w = draw.textlength(title, font=font_title)
draw.text(((W - title_w) / 2, 20), title, fill='white', font=font_title)

draw.line([50, 62, W - 50, 62], fill='#334455', width=1)

# === TWO CITY CARDS ===
locations = [
    {"name": "Rävlanda", "lat": 57.68, "lon": 12.50},
    {"name": "Mölndal", "lat": 57.6561, "lon": 12.0176},
]

card_w = 400
card_h = 320
card_y = 80
margin = (W - card_w * 2) // 3

for i, loc in enumerate(locations):
    cx = margin + i * (card_w + margin)
    w_data = get_weather(loc['lat'], loc['lon'])
    aqi_data = get_air_quality(loc['lat'], loc['lon'])
    if w_data:
        draw_city_card(draw, img, cx, card_y, card_w, card_h, loc, w_data, aqi_data,
                       weather_icons, aqi_icon, wind_icon, font_city, font_temp, font_data, font_label, font_small)

# === POLLEN ===
POLLEN_REGION = "2a2a2a2a-2a2a-4a2a-aa2a-2a2a2a303a38"

POLLEN_LEVELS = {0: "Inga", 1: "Låga", 2: "Låga-måttliga", 3: "Måttliga", 
                 4: "Måttliga-höga", 5: "Höga", 6: "Höga-mycket höga", 7: "Mycket höga"}

POLLEN_COLORS = {0: "#44dd44", 1: "#88dd44", 2: "#dddd44", 3: "#ddbb44",
                 4: "#ddaa44", 5: "#dd8844", 6: "#dd6644", 7: "#dd4444"}

POLLEN_NAMES = {
    "2a2a2a2a-2a2a-4a2a-aa2a-2a313a323233": "Hassel",
    "2a2a2a2a-2a2a-4a2a-aa2a-2a313a323236": "Al",
    "2a2a2a2a-2a2a-4a2a-aa2a-2a313a323330": "Sälg",
    "2a2a2a2a-2a2a-4a2a-aa2a-2a313a323331": "Alm",
    "2a2a2a2a-2a2a-4a2a-aa2a-2a313a323332": "Björk",
    "2a2a2a2a-2a2a-4a2a-aa2a-2a313a323335": "Bok",
    "2a2a2a2a-2a2a-4a2a-aa2a-2a313a323337": "Ek",
    "2a2a2a2a-2a2a-4a2a-aa2a-2a313a323433": "Gräs",
    "2a2a2a2a-2a2a-4a2a-aa2a-2a313a323530": "Gråbo",
    "2a2a2a2a-2a2a-4a2a-aa2a-2a313a323533": "Ambrosia",
}

def get_pollen():
    try:
        url = f"https://api.pollenrapporten.se/v1/forecasts?region_id={POLLEN_REGION}&current=true"
        data = json.loads(urllib.request.urlopen(url, timeout=10).read().decode())
        result = {}
        for item in data.get("items", []):
            for level_info in item.get("levelSeries", []):
                pollen_id = level_info.get("pollenId", "")
                level = level_info.get("level", 0)
                time = level_info.get("time", "")[:10]
                if pollen_id not in result:
                    result[pollen_id] = {}
                result[pollen_id][time] = level
        return result
    except Exception as e:
        print(f"Pollen error: {e}")
        return {}

pollen_data = get_pollen()
today = datetime.now().strftime("%Y-%m-%d")

pollen_y = 420
pollen_h = 180

draw.rounded_rectangle([50, pollen_y, W - 50, pollen_y + pollen_h], radius=12,
                      fill='#1a1a2e', outline='#2a2a4e', width=2)

draw.text((65, pollen_y + 10), "🐝 Pollen (Göteborg)", fill='white', font=font_data)

active_pollen = []
for pollen_id, levels in pollen_data.items():
    level = levels.get(today, 0)
    if level > 0:
        active_pollen.append((pollen_id, level))

if active_pollen:
    px = 65
    py = pollen_y + 38
    
    for pollen_id, level in active_pollen:
        pollen_name = POLLEN_NAMES.get(pollen_id, pollen_id[:8])
        level_name = POLLEN_LEVELS.get(level, "?")
        level_color = POLLEN_COLORS.get(level, "#888888")
        
        badge_w = 120
        if px + badge_w > W - 65:
            px = 65
            py += 52
        
        draw.rounded_rectangle([px, py, px + badge_w, py + 42], radius=6,
                              fill='#252540', outline=level_color, width=2)
        draw.text((px + 10, py + 5), pollen_name, fill='#aaaacc', font=font_pollen_name)
        draw.text((px + 10, py + 23), level_name, fill=level_color, font=font_small)
        
        px += badge_w + 12
else:
    draw.text((65, pollen_y + 50), "Inga aktiva pollen", fill='#666677', font=font_data)

# Footer
draw.line([50, H - 40, W - 50, H - 40], fill='#334455', width=1)
draw.text((20, H - 25), "Väder & Luft: Open-Meteo  |  Pollen: Pollenrapporten", fill='#444455', font=font_small)

img.save("/tmp/weather-report.png")
print("Klar! 🌿")
