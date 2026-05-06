#!/usr/bin/env python3
"""Weather Dashboard - Premium Edition with Air Quality!
Modern dark theme with weather graphs and air quality data.
"""
from PIL import Image, ImageDraw, ImageFont
import cairosvg
import urllib.request
import json
import os
import requests
import random
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

# Load all icons
print("Laddar ikoner...")
weather_icons = {}
for name in ["clear-day", "cloudy-1-day", "cloudy-2-day", "cloudy", "fog", 
             "rainy-1", "rainy-2", "rainy-3", "snowy-1", "snowy-2", "snowy-3", "thunderstorms"]:
    try:
        weather_icons[name] = get_icon(name, 64)
    except:
        pass

# Air quality icon
aqi_icon = get_icon("air", 40)

# Wind icon
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
    """Get air quality from Open-Meteo"""
    try:
        url = f"https://air-quality-api.open-meteo.com/v1/air-quality?latitude={lat}&longitude={lon}&current=us_aqi,pm2_5,pm10&timezone=Europe/Stockholm"
        data = json.loads(urllib.request.urlopen(url, timeout=10).read().decode())
        return data.get('current', {})
    except Exception as e:
        print(f"AQI error: {e}")
        return None

def get_aqi_status(aqi):
    """Get AQI status text and color"""
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
    
    # Gradient background
    for i in range(h):
        alpha = int(20 + (i / h) * 30)
        draw.line([x, y + i, x + w, y + i], fill=(60, 80, 120, alpha))
    
    min_temp = min(temps)
    max_temp = max(temps)
    temp_range = max(max_temp - min_temp, 3)
    min_temp = min_temp - 1
    max_temp = max_temp + 1
    
    # Precip bars
    for i, p in enumerate(precips):
        if p > 25:
            bar_x = x + (i * w // 24)
            bar_h = int((p / 100) * h * 0.45)
            draw.rectangle([bar_x, y + h - bar_h, bar_x + w // 24 - 1, y + h], 
                          fill=(80, 140, 255, 40 + p))
    
    # Temp line with glow effect
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

# === MAIN IMAGE ===
W, H = 1000, 720
img = Image.new('RGB', (W, H), color='#0f0f1a')
draw = ImageDraw.Draw(img)

# Subtle gradient
for y in range(H):
    alpha = int(y / H * 15)
    draw.line([0, y, W, y], fill=(30, 30, 50, alpha))

# Fonts
try:
    font_title = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 32)
    font_city = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 24)
    font_temp = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 36)
    font_data = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 16)
    font_label = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 13)
    font_small = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 11)
except:
    font_title = font_city = font_temp = font_data = font_label = font_small = ImageFont.load_default()

# Header
title = f"Väder & Luftkvalitet • {datetime.now().strftime('%d %b')}"
title_w = draw.textlength(title, font=font_title)
draw.text(((W - title_w) / 2, 20), title, fill='white', font=font_title)

# Decorative line
draw.line([50, 60, W - 50, 60], fill='#334455', width=1)

# Data
locations = [
    {"name": "Göteborg", "lat": 57.7089, "lon": 11.9746},
    {"name": "Mölndal", "lat": 57.6561, "lon": 12.0176},
    {"name": "Rävlanda", "lat": 57.68, "lon": 12.50},
]

col_w = (W - 80) // 3
x = 40

for loc in locations:
    w = get_weather(loc['lat'], loc['lon'])
    aqi = get_air_quality(loc['lat'], loc['lon'])
    
    # Card background
    card_y = 80
    card_h = 500
    draw.rounded_rectangle([x, card_y, x + col_w - 10, card_y + card_h], radius=12, 
                          fill='#1a1a2e', outline='#2a2a4e', width=2)
    
    if not w:
        # City name at top
        city_y = card_y + 30
        city_w = draw.textlength(loc['name'], font=font_city)
        draw.text((x + col_w // 2 - city_w // 2, city_y), loc['name'], fill='white', font=font_city)
        
        # Show error message filling the rest of the card
        error_top = card_y + 70
        error_bottom = card_y + card_h - 10
        error_h = error_bottom - error_top
        
        draw.rounded_rectangle([x + 20, error_top, x + col_w - 30, error_bottom], radius=8,
                              fill='#2a1a1a', outline='#4a2a2a', width=1)
        error_lines = ["API-fel:", "Kunde inte hämta", "väder för denna", "stad"]
        total_line_h = len(error_lines) * 25
        start_y = error_top + (error_h - total_line_h) // 2
        for i, line in enumerate(error_lines):
            error_w = draw.textlength(line, font=font_data)
            draw.text((x + col_w // 2 - error_w // 2, start_y + i * 25), line, fill='#dd6666', font=font_data)
        x += col_w
        continue
    
    current = w['current']
    icon_name = get_icon_name(current['weather_code'])
    icon = weather_icons.get(icon_name)
    
    # Weather icon (above city name)
    if icon:
        img.paste(icon, (x + col_w // 2 - 32, card_y + 20), icon)
    
    # City name (below icon)
    city_y = card_y + 95
    city_w = draw.textlength(loc['name'], font=font_city)
    draw.text((x + col_w // 2 - city_w // 2, city_y), loc['name'], fill='white', font=font_city)
    
    # Big temp
    temp_y = city_y + 35
    temp_str = f"{current['temperature_2m']:.0f}°"
    temp_w = draw.textlength(temp_str, font=font_temp)
    draw.text((x + col_w // 2 - temp_w // 2, temp_y), temp_str, fill='#ff6b6b', font=font_temp)
    
    # Wind
    # Wind with icon
    wind_val = f"{current['wind_speed_10m']:.0f}"
    wind_str = f"{wind_val} km/h"
    
    # Draw wind icon next to text
    if wind_icon:
        img.paste(wind_icon, (x + col_w // 2 - 40, temp_y + 42), wind_icon)
    
    wind_w = draw.textlength(wind_str, font=font_data)
    draw.text((x + col_w // 2 - wind_w // 2 + 15, temp_y + 45), wind_str, fill='#4ecdc4', font=font_data)
    
    # === GRAPH ===
    graph_y = temp_y + 115
    graph_w = col_w - 50
    graph_h = 110
    
    draw.text((x + 20, graph_y - 20), "24h prognos", fill='#888899', font=font_label)
    
    draw.rounded_rectangle([x + 15, graph_y, x + col_w - 25, graph_y + graph_h], radius=8,
                          fill='#252540', outline='#3a3a5e', width=1)
    
    draw_temp_graph(draw, x + 20, graph_y + 10, graph_w - 10, graph_h - 15,
                   w['hourly']['temp'], w['hourly']['precip'])
    
    # Min/Max temps on graph - move away from edges
    temps = w['hourly']['temp']
    if temps:
        min_t = min(temps)
        max_t = max(temps)
        draw.text((x + 20, graph_y + 12), f"{max_t:.0f}°", fill='#ff6b6b', font=font_small)
        draw.text((x + 20, graph_y + graph_h - 18), f"{min_t:.0f}°", fill='#ff6b6b', font=font_small)
    
    for idx, label in enumerate(["00", "06", "12", "18", "24"]):
        tx = x + 20 + (idx * (graph_w - 10) // 4)
        draw.text((tx, graph_y + graph_h + 4), label, fill='#666677', font=font_small)
    
    # === AIR QUALITY ===
    aq_y = graph_y + graph_h + 40
    draw.text((x + 20, aq_y - 18), "Luftkvalitet", fill='#888899', font=font_label)
    
    # AQI card
    draw.rounded_rectangle([x + 15, aq_y, x + col_w - 25, aq_y + 120], radius=8,
                          fill='#1e1e30', outline='#3a3a5e', width=1)
    
    # AQI icon
    if aqi_icon:
        img.paste(aqi_icon, (x + col_w // 2 - 20, aq_y + 15), aqi_icon)
    
    if aqi:
        aqi_val = aqi.get('us_aqi', 0)
        aqi_status, aqi_color = get_aqi_status(aqi_val)
        
        # US AQI value - centered
        aqi_text = str(aqi_val)
        aqi_text_w = draw.textlength(aqi_text, font=font_temp)
        draw.text((x + col_w // 2 - aqi_text_w // 2, aq_y + 10), aqi_text, fill=aqi_color, font=font_temp)
        
        # Status - centered
        status_w = draw.textlength(aqi_status, font=font_data)
        draw.text((x + col_w // 2 - status_w // 2, aq_y + 50), aqi_status, fill=aqi_color, font=font_data)
        
        # PM values - centered
        pm25 = aqi.get('pm2_5', 0)
        pm10 = aqi.get('pm10', 0)
        pm_text = f"PM2.5: {pm25:.1f}  PM10: {pm10:.1f}"
        pm_w = draw.textlength(pm_text, font=font_small)
        draw.text((x + col_w // 2 - pm_w // 2, aq_y + 80), pm_text, fill='#aaaacc', font=font_small)
    else:
        no_w = draw.textlength("Ingen data", font=font_data)
        draw.text((x + col_w // 2 - no_w // 2, aq_y + 30), "Ingen data", fill='#666677', font=font_data)
    
    x += col_w

# === POLLEN (single wide row, only level > 0) ===
POLLEN_REGION = "2a2a2a2a-2a2a-4a2a-aa2a-2a2a2a303a38"  # Göteborg

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

# Get pollen and filter to only show level > 0
pollen_data = get_pollen()
today = datetime.now().strftime("%Y-%m-%d")

# Filter to only pollen with level > 0
active_pollen = []
for pollen_id, levels in pollen_data.items():
    level = levels.get(today, 0)
    if level > 0:
        active_pollen.append((pollen_id, level))

if active_pollen:
    pollen_y = 595
    pollen_h = 75
    
    # Single wide row
    draw.rounded_rectangle([20, pollen_y, W - 20, pollen_y + pollen_h], radius=10,
                          fill='#1a1a2e', outline='#2a2a4e', width=2)
    
    draw.text((40, pollen_y + 8), "🐝 Pollen", fill='white', font=font_data)
    
    # Draw each active pollen type with equal spacing
    box_w = 100
    box_spacing = 20
    total_boxes_w = len(active_pollen) * box_w + (len(active_pollen) - 1) * box_spacing
    # Center boxes in the remaining space after the label
    label_w = 100  # Approximate width of "🐝 Pollen"
    remaining_w = W - 20 - label_w - 40
    total_row_w = remaining_w
    start_x = label_w + 40 + (total_row_w - total_boxes_w) // 2
    
    px = start_x
    for pollen_id, level in active_pollen:
        pollen_name = POLLEN_NAMES.get(pollen_id, pollen_id[:8])
        level_name = POLLEN_LEVELS.get(level, "?")
        level_color = POLLEN_COLORS.get(level, "#888888")
        
        draw.rounded_rectangle([px, pollen_y + 10, px + box_w, pollen_y + 55], radius=6,
                              fill='#252540', outline=level_color, width=2)
        draw.text((px + 8, pollen_y + 14), pollen_name, fill='#aaaacc', font=font_small)
        draw.text((px + 8, pollen_y + 35), level_name, fill=level_color, font=font_small)
        
        px += box_w + box_spacing

# === DAGENS CITAT (below pollen, with proper spacing) ===
quotes = [
    '"Det finns inga dumma frågor, bara dumma svar." - Okänd',
    '"Innovation distingverar mellan en ledare och en följare." - Steve Jobs',
    '"Bästa tiden att plantera ett träd var för 20 år sedan. Nästa bästa är nu." - Kinesisk ordspråk',
    '"Framgång är inte final, misslyckande är inte dödendet." - Winston Churchill',
    '"Den enda verkliga visdomen är att veta att man inget vet." - Sokrates',
    '"Livet är vad som händer medan du gör andra planer." - John Lennon',
    '"Var dig själv, alla andra är redan tagna." - Oscar Wilde',
    '"Ingenting är omöjligt, ordet säger själv att jag är möjlig." - Audrey Hepburn',
    '"Tro inte på allt du tänker." - Okänd',
    '"En dag kommer du att vara det du tänker nu." - Okänd',
    '"Morgondagen tillhör de som förbereder sig idag." - Okänd',
    '"Små steg varje dag leder till stora förändringar." - Okänd',
]

quote = quotes[random.randint(0, len(quotes)-1)]
quote_y = pollen_y + pollen_h + 25
quote_w = draw.textlength(quote, font=font_small)
draw.text(((W - quote_w) / 2, quote_y), quote, fill='#667788', font=font_small)

# Footer
draw.text((20, H - 20), "Väder: Open-Meteo  |  Luft: Open-Meteo AQI", fill='#444455', font=font_small)

# Save at 2x resolution
img.save("/tmp/weather-report-base.png")

from PIL import Image as PILImage
base_img = PILImage.open("/tmp/weather-report-base.png")
img = base_img.resize((2000, 1440), PILImage.LANCZOS)
img.save("/tmp/weather-report.png")
print("Klar! 🌿")
