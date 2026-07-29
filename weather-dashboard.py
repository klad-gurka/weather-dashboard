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
import shutil
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
        weather_icons[name] = get_icon(name, 80)
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

# SMHI symbol_code (1-27) → Open-Meteo WMO weather_code mapping
SMHI_TO_WMO = {
    1: 0,    # Clear sky
    2: 1,    # Nearly clear sky
    3: 2,    # Variable cloudiness
    4: 2,    # Halfclear sky
    5: 3,    # Cloudy sky
    6: 3,    # Overcast
    7: 45,   # Fog
    8: 80,   # Light rain showers
    9: 81,   # Moderate rain showers
    10: 82,  # Heavy rain showers
    11: 95,  # Thunderstorm
    12: 80,  # Light sleet showers → treat as rain showers
    13: 81,  # Moderate sleet showers
    14: 82,  # Heavy sleet showers
    15: 85,  # Light snow showers
    16: 86,  # Moderate snow showers
    17: 86,  # Heavy snow showers
    18: 61,  # Light rain
    19: 63,  # Moderate rain
    20: 65,  # Heavy rain
    21: 95,  # Thunder
    22: 56,  # Light sleet
    23: 57,  # Moderate sleet
    24: 57,  # Heavy sleet
    25: 71,  # Light snowfall
    26: 73,  # Moderate snowfall
    27: 75,  # Heavy snowfall
}

def get_smhi(lat, lon, station_id=None):
    """Get weather forecast from SMHI, combined with observations for past hours.
    
    Returns midnight-to-midnight data: observations for past hours + forecast for future.
    station_id: SMHI metobs station ID for historical observations (optional).
    """
    url = f"https://opendata-download-metfcst.smhi.se/api/category/snow1g/version/1/geotype/point/lon/{lon}/lat/{lat}/data.json"
    try:
        data = json.loads(urllib.request.urlopen(url, timeout=10).read().decode())
        timeseries = data.get("timeSeries", [])
        if not timeseries or len(timeseries) < 2:
            return None
        
        # Current = first entry (closest to now), but prioritize observation if available
        now_data = timeseries[0]["data"]
        weather_code = SMHI_TO_WMO.get(now_data.get("symbol_code", 1), 3)
        wind_ms = now_data.get("wind_speed", 0)  # SMHI uses m/s
        
        current_hour = datetime.now().hour
        current_temp = now_data.get("air_temperature", 0)
        
        current = {
            "temperature_2m": current_temp,
            "weather_code": weather_code,
            "wind_speed_10m": wind_ms,
        }
        
        # Build midnight-to-midnight array (24 hours, local time)
        # First, get observations for past hours today
        obs_temps = {}  # {local_hour: temperature}
        
        if station_id:
            obs_url = f"https://opendata-download-metobs.smhi.se/api/version/latest/parameter/1/station/{station_id}/period/latest-day/data.json"
            try:
                obs_data = json.loads(urllib.request.urlopen(obs_url, timeout=10).read().decode())
                for v in obs_data.get("value", []):
                    from datetime import datetime as dt_mod, timezone
                    obs_dt = dt_mod.fromtimestamp(v["date"] / 1000, tz=timezone.utc)
                    local_hour = (obs_dt.hour + 2) % 24  # UTC+2 CEST
                    obs_date_str = obs_dt.strftime("%Y-%m-%d")
                    today_str = dt_mod.now(timezone.utc).strftime("%Y-%m-%d")
                    # Only use today's observations
                    if obs_date_str == today_str:
                        obs_temps[local_hour] = float(v["value"])
            except:
                pass  # If obs fail, we'll use forecast for those hours
        
        # Override current temp with observation if available
        if current_hour in obs_temps:
            current["temperature_2m"] = obs_temps[current_hour]
        
        # Build forecast lookup: {local_hour: temperature} from today's date only
        # (SMHI returns multiple days; we must filter by date to avoid tomorrow's data leaking in)
        today_date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        fcst_temps = {}
        fcst_precips = {}
        for entry in timeseries:
            t = entry["time"]
            entry_date = t[:10]  # "2026-06-13"
            if entry_date != today_date_str:
                continue  # Skip entries from other days
            fcst_hour = (int(t[11:13]) + 2) % 24  # UTC → local
            d = entry["data"]
            fcst_temps[fcst_hour] = d.get("air_temperature", 0)
            fcst_precips[fcst_hour] = d.get("probability_of_precipitation", 0)
        
        # Build midnight-to-midnight: use observation if available, else forecast
        temps = []
        precips = []
        hours = list(range(24))
        
        for h in range(24):
            if h in obs_temps and obs_temps[h] is not None:
                temps.append(obs_temps[h])
            elif h in fcst_temps:
                temps.append(fcst_temps[h])
            else:
                # Interpolate from nearest known values
                temps.append(current["temperature_2m"])
            
            # Precipitation: use forecast if available, else 0
            # (Only fill current hour from nearest forecast if missing)
            if h in fcst_precips:
                precips.append(fcst_precips[h])
            elif h == datetime.now().hour:
                # Current hour may be missing from forecast — use nearest
                found = False
                for offset in range(1, 24):
                    for nh in ((h + offset) % 24, (h - offset) % 24):
                        if nh in fcst_precips:
                            precips.append(fcst_precips[nh])
                            found = True
                            break
                    if found:
                        break
                if not found:
                    precips.append(0)
            else:
                precips.append(0)
        
        # Sync grafens current-hour-punkt med röda temp-siffran
        temps[current_hour] = current["temperature_2m"]
        
        return {
            "current": current,
            "hourly": {"temp": temps, "precip": precips, "hours": hours},
        }
    except Exception as e:
        print(f"SMHI error: {e}")
        return None

def get_weather(lat, lon, station_id=None):
    """Get weather forecast - tries SMHI first, falls back to Open-Meteo."""
    # Try SMHI first (faster, more reliable for Swedish locations)
    w = get_smhi(lat, lon, station_id)
    if w:
        return w, "smhi"
    
    # Fall back to Open-Meteo
    url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current=temperature_2m,weather_code,wind_speed_10m&hourly=temperature_2m,precipitation_probability&timezone=Europe/Stockholm&forecast_days=2"
    try:
        data = json.loads(urllib.request.urlopen(url, timeout=10).read().decode())
        return {
            'current': data['current'],
            'hourly': {
                'temp': data['hourly']['temperature_2m'][24:48],
                'precip': data['hourly']['precipitation_probability'][24:48],
            }
        }, "openmeteo"
    except:
        return None, None

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

def draw_temp_graph(draw, x, y, w, h, temps, precips, current_hour=None):
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
    
    # Precip bars — 24 uniform columns
    col_w = w / 24
    for i, p in enumerate(precips):
        if p > 25:
            bar_x = int(x + col_w * i)
            bar_w = max(1, int(x + col_w * (i + 1)) - bar_x)
            bar_h = int((p / 100) * h)
            draw.rectangle([bar_x, y + h - bar_h, bar_x + bar_w, y + h], 
                          fill=(80, 140, 255, 40 + p))
    
    # Temp line points — centered in each column
    points = []
    for i, t in enumerate(temps):
        px = int(x + col_w * (i + 0.5))
        py = y + h - int(((t - min_temp) / (max_temp - min_temp)) * h)
        points.append((px, py))
    
    if len(points) > 1:
        import math
        
        def make_thick_line(pts, thickness, color, round_joins=False):
            """Draw a thick polyline as filled rectangles per segment + optional round joints."""
            if len(pts) < 2:
                return
            t2 = thickness / 2
            
            # Draw each segment as a filled rectangle
            for i in range(len(pts) - 1):
                dx = pts[i+1][0] - pts[i][0]
                dy = pts[i+1][1] - pts[i][1]
                seg_len = math.hypot(dx, dy) or 1
                nx = -dy / seg_len * t2  # perpendicular x
                ny = dx / seg_len * t2   # perpendicular y
                
                x1, y1 = pts[i][0] + nx, pts[i][1] + ny
                x2, y2 = pts[i][0] - nx, pts[i][1] - ny
                x3, y3 = pts[i+1][0] - nx, pts[i+1][1] - ny
                x4, y4 = pts[i+1][0] + nx, pts[i+1][1] + ny
                
                draw.polygon([x1, y1, x2, y2, x3, y3, x4, y4], fill=color)
            
            # Round joints as circles at data points
            if round_joins:
                for px, py in pts:
                    draw.ellipse([px - t2, py - t2, px + t2, py + t2], fill=color)
        
        # Glow layers
        for glow in range(3, 0, -1):
            make_thick_line(points, glow * 2, (255, 107, 107, 50), round_joins=True)
        
        # Main line
        make_thick_line(points, 3, '#ff6b6b', round_joins=True)
        
        # Current hour marker + temperature label
        if current_hour is not None and 0 <= current_hour < len(points):
            cx, cy = points[current_hour]
            # Larger dot at current hour
            draw.ellipse([cx-5, cy-5, cx+5, cy+5], fill='#ff6b6b', outline='#fff', width=2)
            draw.ellipse([cx-2, cy-2, cx+2, cy+2], fill='#fff')
            # Temperature label at the point
            t_label = f"{temps[current_hour]:.0f}°"
            t_w = draw.textlength(t_label, font=font_title)
            draw.text((cx - t_w / 2, cy - 35), t_label, fill='white', font=font_title)
    
    # Horizontal grid lines for every degree — labels outside graph (to the left)
    bottom_padding = 14  # reserve space for hour labels
    for deg in range(int(min_temp), int(max_temp) + 1):
        ratio = (deg - min_temp) / (max_temp - min_temp)
        gy = y + h - int(ratio * h)
        # Skip line if it would overlap/underlap the hour numbers at the bottom
        if gy >= y + h - bottom_padding:
            continue
        # Thin line starting at graph edge (x)
        draw.line([x, gy, x + w, gy], fill='#2a2a44', width=1)
        # Label inside graph area (not outside)
        if gy < y + h - 14:
            label = f"{deg}°"
            label_w = draw.textlength(label, font=font_label)
            draw.text((x - 4 - label_w, gy - 6), label, fill='#8899aa', font=font_label)

# === FONTS ===
try:
    font_title = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 30)
    font_temp = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 36)
    font_data = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 16)
    font_label = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 13)
    font_small = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 11)
except:
    font_title = font_temp = font_data = font_label = font_small = ImageFont.load_default()

# === CITY CARD HELPER ===
def draw_city_card(name, w_data, aqi_data, date_str):
    """Draw a single city weather card, returns PIL Image."""
    CW, CH = 650, 318
    img = Image.new('RGBA', (CW, CH), color='#12121e')
    draw = ImageDraw.Draw(img)
    
    # Gradient via alpha overlay (no alpha interference with text)
    gradient = Image.new('RGBA', (CW, CH), (0, 0, 0, 0))
    gdraw = ImageDraw.Draw(gradient)
    for yp in range(CH):
        alpha = int(yp / CH * 18)
        gdraw.line([0, yp, CW, yp], fill=(0, 0, 0, alpha))
    img = Image.alpha_composite(img, gradient)
    draw = ImageDraw.Draw(img)
    
    if not w_data:
        error_w = draw.textlength("Kunde inte hämta väder", font=font_data)
        draw.text(((CW - error_w) / 2, CH / 2), "Kunde inte hämta väder", fill='#dd6666', font=font_data)
        return img
    
    current = w_data['current']
    icon_name = get_icon_name(current['weather_code'])
    icon = weather_icons.get(icon_name)
    
    # === HEADER: name/date left, temp/wind right ===
    
    draw.text((15, 8), name, fill='white', font=font_title)
    draw.text((15, 42), date_str, fill='#e6e6e6', font=font_data)
    
    temp_str = f"{min(w_data['hourly']['temp']):.0f}°–{max(w_data['hourly']['temp']):.0f}°"
    wind_val = f"{current['wind_speed_10m']:.1f}"
    wind_str = f"{wind_val} m/s"
    
    temp_w = draw.textlength(temp_str, font=font_title)
    wind_w = draw.textlength(wind_str, font=font_data)
    
    draw.text((CW - 15 - temp_w, 8), temp_str, fill='#ff6b6b', font=font_title)
    if wind_icon:
        img.paste(wind_icon, (CW - 15 - int(wind_w) - 26, 37), wind_icon)
    draw.text((CW - 15 - wind_w, 42), wind_str, fill='#4ecdc4', font=font_data)
    
    # === GRAPH ===
    graph_margin = 40
    graph_y = 65
    graph_w = CW - graph_margin - 15
    graph_h = 210
    
    current_hour = datetime.now().hour
    draw_temp_graph(draw, graph_margin + 5, graph_y + 10, graph_w - 10, graph_h - 20,
                   w_data['hourly']['temp'], w_data['hourly']['precip'], current_hour)
    
    # Hour labels — centered in each column
    label_cw = (graph_w - 10) / 24  # same column width as graph
    for idx in range(24):
        tx = graph_margin + 5 + label_cw * (idx + 0.5)
        label_str = str(idx)
        label_w = draw.textlength(label_str, font=font_small)
        label_color = 'white' if idx in (8, 12, 16, 20) else '#8899aa'
        draw.text((tx - label_w / 2, graph_y + graph_h - 5), label_str, fill=label_color, font=font_small)
    
    # Weather icon drawn on top of graph (if overlap)
    if icon:
        img.paste(icon, (CW // 2 + 95, -4), icon)
    
    # === AIR QUALITY ===
    aq_y = graph_y + graph_h + 8
    
    if aqi_data:
        aqi_val = aqi_data.get('us_aqi', 0)
        aqi_status, aqi_color = get_aqi_status(aqi_val)
        
        pm25 = aqi_data.get('pm2_5', 0)
        pm10 = aqi_data.get('pm10', 0)
        
        line = f"Luftkvalitet: {aqi_val} {aqi_status}  •  PM2.5: {pm25:.1f} µg/m³  •  PM10: {pm10:.1f} µg/m³"
        line_w = draw.textlength(line, font=font_data)
        draw.text(((CW - line_w) / 2, aq_y + 8), line, fill=aqi_color, font=font_data)
    else:
        no_w = draw.textlength("Ingen luftdata", font=font_data)
        draw.text(((CW - no_w) / 2, aq_y + 8), "Ingen luftdata", fill='#666677', font=font_data)
    
    return img


# === POLLEN CARD ===
POLLEN_REGION = "2a2a2a2a-2a2a-4a2a-aa2a-2a2a2a303a38"  # Göteborg

POLLEN_LEVELS = {0: "Inga", 1: "Låga", 2: "Låga-måttliga", 3: "Måttliga", 
                 4: "Måttliga-höga", 5: "Höga", 6: "Höga-mycket höga", 7: "Mycket höga"}

POLLEN_EMOJI = {0: "🟢", 1: "🟢", 2: "🟡", 3: "🟠",
                4: "🟠", 5: "🔴", 6: "🔴", 7: "⛔"}

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

def draw_pollen_card(active_pollen, date_str):
    """Draw pollen forecast as a standalone image."""
    PW, PH = 650, 130
    img = Image.new('RGBA', (PW, PH), color='#0f0f1a')
    draw = ImageDraw.Draw(img)
    
    for yp in range(PH):
        alpha = int(yp / PH * 15)
        draw.line([0, yp, PW, yp], fill=(30, 30, 50, alpha))
    
    draw.rounded_rectangle([10, 10, PW - 10, PH - 10], radius=10,
                          fill='#1a1a2e', outline='#2a2a4e', width=2)
    
    title = f"Pollen • {date_str}"
    title_w = draw.textlength(title, font=font_title)
    draw.text(((PW - title_w) / 2, 12), title, fill='white', font=font_title)
    
    if not active_pollen:
        no_w = draw.textlength("Inga aktiva pollen idag", font=font_data)
        draw.text(((PW - no_w) / 2, 65), "Inga aktiva pollen idag", fill='#44dd44', font=font_data)
        return img
    
    box_w = 100
    box_spacing = 15
    total_w = len(active_pollen) * box_w + (len(active_pollen) - 1) * box_spacing
    start_x = (PW - total_w) // 2
    
    px = start_x
    for pollen_id, level in active_pollen:
        pollen_name = POLLEN_NAMES.get(pollen_id, pollen_id[:8])
        level_name = POLLEN_LEVELS.get(level, "?")
        level_color = POLLEN_COLORS.get(level, "#888888")
        
        draw.rounded_rectangle([px, 48, px + box_w, 100], radius=6,
                              fill='#252540', outline=level_color, width=2)
        draw.text((px + 8, 52), pollen_name, fill='#aaaacc', font=font_small)
        draw.text((px + 8, 74), level_name, fill=level_color, font=font_small)
        
        px += box_w + box_spacing
    
    return img


# === MAIN: FETCH DATA & GENERATE IMAGES ===
weekdays = ["Måndag", "Tisdag", "Onsdag", "Torsdag", "Fredag", "Lördag", "Söndag"]
months = ["Januari", "Februari", "Mars", "April", "Maj", "Juni", "Juli", "Augusti", "September", "Oktober", "November", "December"]
now = datetime.now()
date_str = f"{weekdays[now.weekday()]} {now.day} {months[now.month - 1]}"

locations = [
    {"name": "Göteborg", "lat": 57.7089, "lon": 11.9746, "station": "71420"},
    {"name": "Mölndal", "lat": 57.6561, "lon": 12.0176, "station": "71420"},
    {"name": "Rävlanda", "lat": 57.68, "lon": 12.50, "station": "72420"},
]

# Fetch all data
city_data = []
for loc in locations:
    w, source = get_weather(loc['lat'], loc['lon'], loc.get('station'))
    aqi = get_air_quality(loc['lat'], loc['lon'])
    city_data.append((loc['name'], w, aqi))

# Fetch pollen
pollen_data = get_pollen()
today = datetime.now().strftime("%Y-%m-%d")
active_pollen = []
for pollen_id, levels in pollen_data.items():
    level = levels.get(today, 0)
    if level > 0:
        active_pollen.append((pollen_id, level))

# Generate and save city images
image_files = []
for i, (name, w, aqi) in enumerate(city_data):
    card = draw_city_card(name, w, aqi, date_str)
    path = f"/tmp/weather-{i}.png"
    card.save(path)
    image_files.append(path)

# Generate and save pollen image
pollen_card = draw_pollen_card(active_pollen, date_str)
pollen_path = "/tmp/weather-pollen.png"
pollen_card.save(pollen_path)
image_files.append(pollen_path)

# Generate pollen text file for text-based posting
pollen_txt = f"🌿 **Pollen · {date_str}**\n"
if not active_pollen:
    pollen_txt += "🟢 Inga aktiva pollen idag"
else:
    for pollen_id, level in active_pollen:
        name = POLLEN_NAMES.get(pollen_id, pollen_id[:8])
        emoji = POLLEN_EMOJI.get(level, "⚪")
        level_name = POLLEN_LEVELS.get(level, "?")
        pollen_txt += f"{emoji} **{name}**: {level_name}\n"
with open("/tmp/weather-pollen.txt", "w", encoding="utf-8") as f:
    f.write(pollen_txt.strip())

# Resize each individual image to 2x for crispness
for path in image_files:
    base = Image.open(path).convert("RGB")
    w2, h2 = base.size
    scaled = base.resize((w2 * 2, h2 * 2), Image.LANCZOS)
    scaled.save(path)

# Save first city image as legacy file for cron compatibility
if image_files:
    shutil.copyfile(image_files[0], "/tmp/weather-report.png")

print(f"Klar! 🌿 ({len(image_files)} bilder)")
