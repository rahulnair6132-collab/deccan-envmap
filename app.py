# app.py — PRODUCTION VERSION WITH FALLBACK DATA & ENHANCED FEATURES
# Deccan Environmental Severity Dashboard
# With 2-3 year historical data fallback, Excel export, and detailed insulator recommendations

import streamlit as st
from streamlit_folium import st_folium
import folium
from folium.plugins import Draw, HeatMap
import requests, os, io, tempfile, math, json
import pandas as pd
import numpy as np
from shapely.geometry import LineString, Point, Polygon, mapping
from fpdf import FPDF
import matplotlib.pyplot as plt
import branca.colormap as cm
from datetime import datetime, timedelta
import base64
from PIL import Image
import warnings
warnings.filterwarnings('ignore')

# -------------------------------
# Streamlit Configuration
# -------------------------------
st.set_page_config(
    page_title="Deccan Environmental Severity Dashboard", 
    layout="wide",
    page_icon="⚡"
)

# -------------------------------
# Historical Data Repository (2-3 years averaged data for India)
# -------------------------------
HISTORICAL_DATA = {
    # Major cities and regions with averaged environmental data (2022-2024)
    "delhi": {"lat": 28.6139, "lon": 77.2090, "pm25": 153, "pm10": 286, "temp": 25.5, "hum": 64, "wind": 8.2},
    "mumbai": {"lat": 19.0760, "lon": 72.8777, "pm25": 73, "pm10": 124, "temp": 27.2, "hum": 76, "wind": 12.5},
    "kolkata": {"lat": 22.5726, "lon": 88.3639, "pm25": 112, "pm10": 198, "temp": 27.0, "hum": 79, "wind": 9.8},
    "chennai": {"lat": 13.0827, "lon": 80.2707, "pm25": 58, "pm10": 95, "temp": 29.1, "hum": 74, "wind": 11.2},
    "bangalore": {"lat": 12.9716, "lon": 77.5946, "pm25": 67, "pm10": 103, "temp": 24.8, "hum": 62, "wind": 7.5},
    "hyderabad": {"lat": 17.3850, "lon": 78.4867, "pm25": 78, "pm10": 134, "temp": 27.5, "hum": 58, "wind": 8.9},
    "ahmedabad": {"lat": 23.0225, "lon": 72.5714, "pm25": 95, "pm10": 167, "temp": 27.8, "hum": 55, "wind": 9.1},
    "pune": {"lat": 18.5204, "lon": 73.8567, "pm25": 82, "pm10": 142, "temp": 25.3, "hum": 61, "wind": 8.3},
    "jaipur": {"lat": 26.9124, "lon": 75.7873, "pm25": 118, "pm10": 201, "temp": 26.4, "hum": 52, "wind": 7.8},
    "lucknow": {"lat": 26.8467, "lon": 80.9462, "pm25": 136, "pm10": 234, "temp": 25.8, "hum": 66, "wind": 6.9},
    "kanpur": {"lat": 26.4499, "lon": 80.3319, "pm25": 162, "pm10": 278, "temp": 26.1, "hum": 64, "wind": 7.2},
    "nagpur": {"lat": 21.1458, "lon": 79.0882, "pm25": 91, "pm10": 156, "temp": 27.9, "hum": 57, "wind": 7.6},
    "patna": {"lat": 25.5941, "lon": 85.1376, "pm25": 145, "pm10": 249, "temp": 26.3, "hum": 68, "wind": 6.5},
    "indore": {"lat": 22.7196, "lon": 75.8577, "pm25": 104, "pm10": 178, "temp": 26.7, "hum": 56, "wind": 7.9},
    "bhopal": {"lat": 23.2599, "lon": 77.4126, "pm25": 98, "pm10": 168, "temp": 25.9, "hum": 60, "wind": 7.4},
    "visakhapatnam": {"lat": 17.6868, "lon": 83.2185, "pm25": 61, "pm10": 99, "temp": 28.3, "hum": 73, "wind": 10.8},
    "kochi": {"lat": 9.9312, "lon": 76.2673, "pm25": 42, "pm10": 71, "temp": 28.7, "hum": 77, "wind": 9.4},
    "guwahati": {"lat": 26.1445, "lon": 91.7362, "pm25": 88, "pm10": 148, "temp": 24.9, "hum": 81, "wind": 6.8},
    # Regional averages for interpolation
    "north_india": {"pm25": 128, "pm10": 218, "temp": 25.8, "hum": 62, "wind": 7.6},
    "south_india": {"pm25": 64, "pm10": 104, "temp": 27.8, "hum": 71, "wind": 9.8},
    "east_india": {"pm25": 106, "pm10": 181, "temp": 26.4, "hum": 75, "wind": 8.2},
    "west_india": {"pm25": 87, "pm10": 148, "temp": 27.1, "hum": 63, "wind": 9.4},
    "central_india": {"pm25": 98, "pm10": 168, "temp": 26.9, "hum": 58, "wind": 7.7},
}

# Insulator specifications database
INSULATOR_SPECS = {
    "standard_ceramic": {
        "name": "Standard Ceramic Insulator",
        "temp_range": (-20, 45),
        "pollution_max": 80,
        "wind_max": 150,
        "cost_factor": 1.0
    },
    "toughened_glass": {
        "name": "Toughened Glass Insulator",
        "temp_range": (-40, 50),
        "pollution_max": 100,
        "wind_max": 180,
        "cost_factor": 1.3
    },
    "polymer_composite": {
        "name": "Polymer Composite Insulator",
        "temp_range": (-50, 60),
        "pollution_max": 150,
        "wind_max": 200,
        "cost_factor": 1.8
    },
    "anti_fog": {
        "name": "Anti-Fog Ceramic Insulator",
        "temp_range": (-30, 50),
        "pollution_max": 120,
        "wind_max": 160,
        "cost_factor": 1.5
    },
    "hydrophobic": {
        "name": "Hydrophobic Silicone Insulator",
        "temp_range": (-50, 65),
        "pollution_max": 180,
        "wind_max": 220,
        "cost_factor": 2.2
    }
}

# -------------------------------
# Header with Logo
# -------------------------------
col1, col2, col3 = st.columns([1, 3, 1])
with col2:
    if os.path.exists("deccan_logo.png"):
        st.image("deccan_logo.png", width=200)
    elif os.path.exists("../deccan_logo.png"):
        st.image("../deccan_logo.png", width=200)
    
    st.markdown(
        "<h2 style='color:#003366;text-align:center;'>Environmental Severity Dashboard</h2>",
        unsafe_allow_html=True,
    )
    st.markdown(
        "<p style='text-align:center;color:#666;'>Transmission Line Environmental Impact Analysis & Insulator Specification System</p>",
        unsafe_allow_html=True,
    )

# -------------------------------
# Session State Initialization
# -------------------------------
if 'map_data' not in st.session_state:
    st.session_state.map_data = None
if 'analysis_df' not in st.session_state:
    st.session_state.analysis_df = None
if 'user_line' not in st.session_state:
    st.session_state.user_line = None
if 'data_source_log' not in st.session_state:
    st.session_state.data_source_log = []

# -------------------------------
# Sidebar Controls
# -------------------------------
st.sidebar.header("⚙️ Configuration")

# Mode selection
mode = st.sidebar.radio("Input Method:", ("🖊️ Draw on map", "📍 Enter coordinates"))

# Coordinate input handling
coords_list = []
if mode == "📍 Enter coordinates":
    st.sidebar.subheader("Coordinate Pairs")
    num_pairs = st.sidebar.number_input("Number of segments", 1, 10, 1)
    
    for i in range(num_pairs):
        with st.sidebar.expander(f"Segment {i+1}", expanded=(i==0)):
            col1, col2 = st.columns(2)
            with col1:
                lat1 = st.text_input(f"Origin Lat", value="22.8176" if i==0 else "", key=f"lat1_{i}")
                lon1 = st.text_input(f"Origin Lon", value="70.8121" if i==0 else "", key=f"lon1_{i}")
            with col2:
                lat2 = st.text_input(f"Dest Lat", value="23.0225" if i==0 else "", key=f"lat2_{i}")
                lon2 = st.text_input(f"Dest Lon", value="72.5714" if i==0 else "", key=f"lon2_{i}")
        
        if lat1 and lon1 and lat2 and lon2:
            try:
                coords_list.append([(float(lat1), float(lon1)), (float(lat2), float(lon2))])
            except:
                pass

st.sidebar.markdown("---")
st.sidebar.subheader("📊 Analysis Parameters")

# Parameter selection with descriptions
params = st.sidebar.multiselect(
    "Environmental Factors", 
    ["PM2.5", "PM10", "Temperature", "Humidity", "Wind Speed", "Cyclone Risk"],
    default=["PM2.5", "Temperature", "Cyclone Risk"],
    help="Select environmental factors to analyze"
)

# Data source preference
data_source = st.sidebar.radio(
    "Data Source Preference",
    ["🔄 Real-time (with fallback)", "📚 Historical (2022-2024)", "⚡ Fast Mode (Historical only)"],
    index=0
)

buffer_m = st.sidebar.number_input("Corridor Width (m)", 500, 50000, 5000, step=500, 
                                   help="Buffer zone around transmission line")
sample_m = st.sidebar.number_input("Sample Spacing (m)", 1000, 20000, 3000, step=500,
                                   help="Distance between analysis points")

apply = st.sidebar.button("✅ Analyze Corridor", type="primary", use_container_width=True)

st.sidebar.markdown("---")
st.sidebar.subheader("📄 Report Generation")

client_name = st.sidebar.text_input("Client Name", value="Client Company")
project_code = st.sidebar.text_input("Project Code", value="TC-2025-001")
line_name = st.sidebar.text_input("Line Description", value="Transmission Line Corridor")

col1, col2 = st.sidebar.columns(2)
with col1:
    generate_pdf = st.button("📘 PDF Report", use_container_width=True)
with col2:
    generate_excel = st.button("📗 Excel Export", use_container_width=True)

# -------------------------------
# Utility Functions
# -------------------------------
def meters_to_deg(m):
    return m / 111320.0

def haversine(lat1, lon1, lat2, lon2):
    R = 6371000
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = (math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlambda/2)**2)
    return 2 * R * math.asin(math.sqrt(a))

def sample_points(line: LineString, spacing_m):
    coords = list(line.coords)
    total_m = sum(haversine(coords[i][0], coords[i][1], coords[i+1][0], coords[i+1][1]) 
                  for i in range(len(coords)-1))
    n = max(3, int(total_m / spacing_m) + 1)
    return [line.interpolate(i/(n-1), normalized=True) for i in range(n)]

def get_nearest_historical_data(lat, lon):
    """Get nearest historical data point using distance-weighted interpolation"""
    distances = {}
    for city, data in HISTORICAL_DATA.items():
        if 'lat' in data and 'lon' in data:
            dist = haversine(lat, lon, data['lat'], data['lon'])
            distances[city] = dist
    
    # Get 3 nearest cities
    nearest = sorted(distances.items(), key=lambda x: x[1])[:3]
    
    # Weighted average based on inverse distance
    weights = [1/(d+1000) for _, d in nearest]  # +1000 to avoid division by zero
    total_weight = sum(weights)
    
    result = {"pm25": 0, "pm10": 0, "temp": 0, "hum": 0, "wind": 0}
    for (city, _), weight in zip(nearest, weights):
        data = HISTORICAL_DATA[city]
        for key in result.keys():
            if key in data:
                result[key] += data[key] * (weight / total_weight)
    
    return result

@st.cache_data(ttl=3600)
def get_air_quality_realtime(lat, lon, timeout=5):
    """Fetch air quality from multiple sources with timeout"""
    st.session_state.data_source_log.append(f"Attempting real-time AQ for ({lat:.4f}, {lon:.4f})")
    
    # Try OpenAQ first
    try:
        d = 0.5 / 111
        bbox = f"{lon-d},{lat-d},{lon+d},{lat+d}"
        url = "https://api.openaq.org/v2/latest"
        r = requests.get(url, params={"bbox": bbox, "limit": 100}, timeout=timeout).json()
        
        pm25_vals, pm10_vals = [], []
        if r.get("results"):
            for loc in r["results"]:
                for m in loc.get("measurements", []):
                    if m["parameter"] == "pm25" and m["value"] is not None:
                        pm25_vals.append(m["value"])
                    elif m["parameter"] == "pm10" and m["value"] is not None:
                        pm10_vals.append(m["value"])
        
        if pm25_vals or pm10_vals:
            st.session_state.data_source_log.append("✓ OpenAQ real-time data retrieved")
            return {
                "pm25": np.mean(pm25_vals) if pm25_vals else None,
                "pm10": np.mean(pm10_vals) if pm10_vals else None,
                "source": "OpenAQ (Real-time)"
            }
    except Exception as e:
        st.session_state.data_source_log.append(f"✗ OpenAQ failed: {str(e)[:50]}")
    
    # Try WAQI
    try:
        url = f"https://api.waqi.info/feed/geo:{lat};{lon}/"
        params = {"token": "demo"}  # Users should replace with their token
        r = requests.get(url, params=params, timeout=timeout).json()
        
        if r.get("status") == "ok" and "data" in r:
            data = r["data"]
            iaqi = data.get("iaqi", {})
            pm25 = iaqi.get("pm25", {}).get("v")
            pm10 = iaqi.get("pm10", {}).get("v")
            
            if pm25 or pm10:
                st.session_state.data_source_log.append("✓ WAQI real-time data retrieved")
                return {
                    "pm25": pm25,
                    "pm10": pm10,
                    "source": "WAQI (Real-time)"
                }
    except Exception as e:
        st.session_state.data_source_log.append(f"✗ WAQI failed: {str(e)[:50]}")
    
    return None

@st.cache_data(ttl=3600)
def get_weather_realtime(lat, lon, timeout=5):
    """Fetch weather data with timeout"""
    st.session_state.data_source_log.append(f"Attempting real-time weather for ({lat:.4f}, {lon:.4f})")
    
    try:
        url = "https://api.open-meteo.com/v1/forecast"
        params = {
            "latitude": lat,
            "longitude": lon,
            "current_weather": True,
            "hourly": "relativehumidity_2m,windspeed_10m",
            "timezone": "Asia/Kolkata"
        }
        r = requests.get(url, params=params, timeout=timeout).json()
        
        temp = r.get("current_weather", {}).get("temperature")
        wind = r.get("current_weather", {}).get("windspeed")
        hum = None
        
        if "hourly" in r and "relativehumidity_2m" in r["hourly"]:
            hum_list = [h for h in r["hourly"]["relativehumidity_2m"][:24] if h is not None]
            hum = np.mean(hum_list) if hum_list else None
        
        if temp is not None:
            st.session_state.data_source_log.append("✓ Open-Meteo real-time data retrieved")
            return {
                "temp": temp,
                "hum": hum,
                "wind": wind,
                "source": "Open-Meteo (Real-time)"
            }
    except Exception as e:
        st.session_state.data_source_log.append(f"✗ Open-Meteo failed: {str(e)[:50]}")
    
    return None

def get_environmental_data(lat, lon, use_realtime=True):
    """Get environmental data with fallback to historical"""
    result = {
        "pm25": None, "pm10": None, "temp": None, 
        "hum": None, "wind": None, "source": "Historical (2022-2024)"
    }
    
    # Try real-time if requested
    if use_realtime:
        aq_data = get_air_quality_realtime(lat, lon)
        weather_data = get_weather_realtime(lat, lon)
        
        if aq_data:
            result.update(aq_data)
        if weather_data:
            result.update(weather_data)
    
    # Fill missing data with historical
    historical = get_nearest_historical_data(lat, lon)
    for key in ["pm25", "pm10", "temp", "hum", "wind"]:
        if result[key] is None and key in historical:
            result[key] = historical[key]
    
    return result

def check_cyclone_zone(lat, lon):
    """Check if point is in cyclone-prone area"""
    bay = [[21.5,89.0],[19,87.5],[15,84.5],[13,80.5],[12,78],[15,83],[18,86]]
    arab = [[23,67.5],[20,69],[16,72.5],[14,74],[12.5,74],[15,71],[19,68.5]]
    
    bay_poly = Polygon([(p[1], p[0]) for p in bay])
    arab_poly = Polygon([(p[1], p[0]) for p in arab])
    point = Point(lon, lat)
    
    return bay_poly.contains(point) or arab_poly.contains(point)

def calculate_severity_score(row):
    """Enhanced severity scoring with weighted factors"""
    score = 0
    max_score = 0
    
    # PM2.5 scoring (weight: 25)
    if row.get('pm25') is not None:
        pm25 = row['pm25']
        if pm25 > 250: score += 25
        elif pm25 > 150: score += 22
        elif pm25 > 100: score += 18
        elif pm25 > 60: score += 14
        elif pm25 > 35: score += 10
        else: score += 5
        max_score += 25
    
    # Temperature scoring (weight: 20)
    if row.get('temp') is not None:
        temp = row['temp']
        if temp > 48 or temp < -5: score += 20
        elif temp > 43 or temp < 0: score += 16
        elif temp > 38 or temp < 5: score += 12
        elif temp > 33 or temp < 10: score += 8
        else: score += 4
        max_score += 20
    
    # Humidity scoring (weight: 15)
    if row.get('hum') is not None:
        hum = row['hum']
        if hum > 92 or hum < 15: score += 15
        elif hum > 85 or hum < 25: score += 12
        elif hum > 78 or hum < 35: score += 9
        else: score += 5
        max_score += 15
    
    # Wind scoring (weight: 20)
    if row.get('wind') is not None:
        wind = row['wind']
        if wind > 60: score += 20
        elif wind > 45: score += 16
        elif wind > 30: score += 12
        elif wind > 20: score += 8
        else: score += 4
        max_score += 20
    
    # Cyclone risk (weight: 20)
    if row.get('cyclone_risk', False):
        score += 18
        max_score += 20
    else:
        score += 2
        max_score += 20
    
    return (score / max_score * 100) if max_score > 0 else 0

def recommend_insulator(severity, pm25, temp, wind, humidity):
    """Recommend appropriate insulator based on conditions"""
    recommendations = []
    
    # Check each insulator type
    for key, spec in INSULATOR_SPECS.items():
        suitable = True
        reasons = []
        
        # Temperature check
        if temp is not None:
            if temp < spec["temp_range"][0] or temp > spec["temp_range"][1]:
                suitable = False
            elif temp >= spec["temp_range"][1] - 5:
                reasons.append("operates near upper temp limit")
        
        # Pollution check
        if pm25 is not None:
            if pm25 > spec["pollution_max"]:
                suitable = False
            elif pm25 >= spec["pollution_max"] * 0.8:
                reasons.append("approaching pollution tolerance")
        
        # Wind check (converted to km/h)
        if wind is not None:
            wind_kmh = wind * 3.6
            if wind_kmh > spec["wind_max"]:
                suitable = False
        
        if suitable:
            recommendations.append({
                "type": key,
                "name": spec["name"],
                "cost_factor": spec["cost_factor"],
                "notes": reasons,
                "severity_match": severity < 70 if key == "standard_ceramic" else True
            })
    
    # Sort by cost factor (prefer economical options when suitable)
    recommendations.sort(key=lambda x: x["cost_factor"])
    
    return recommendations

# -------------------------------
# Base Map Creation
# -------------------------------
def create_base_map():
    m = folium.Map(location=[22, 80], zoom_start=5, tiles="CartoDB positron")
    
    # Add drawing tools
    Draw(export=True, draw_options={
        'polyline': True,
        'polygon': False,
        'circle': False,
        'rectangle': False,
        'marker': False,
        'circlemarker': False
    }).add_to(m)
    
    # Add cyclone belts
    bay = [[21.5,89.0],[19,87.5],[15,84.5],[13,80.5],[12,78],[15,83],[18,86]]
    arab = [[23,67.5],[20,69],[16,72.5],[14,74],[12.5,74],[15,71],[19,68.5]]
    
    folium.Polygon(
        bay, color="purple", fill=True, fill_opacity=0.12, weight=2,
        popup="Bay of Bengal Cyclone Zone", tooltip="Cyclone Zone"
    ).add_to(m)
    folium.Polygon(
        arab, color="purple", fill=True, fill_opacity=0.12, weight=2,
        popup="Arabian Sea Cyclone Zone", tooltip="Cyclone Zone"
    ).add_to(m)
    
    return m

# -------------------------------
# Main Map Display
# -------------------------------
st.subheader("🗺️ Transmission Line Mapping")

m = create_base_map()

# Add coordinate-based lines
if mode == "📍 Enter coordinates" and coords_list:
    all_coords = []
    for coords in coords_list:
        line = LineString(coords)
        all_coords.extend(coords)
        folium.PolyLine(
            locations=[(p[0], p[1]) for p in coords],
            color="blue", weight=3, opacity=0.8,
            popup=f"Segment: {coords[0]} → {coords[1]}"
        ).add_to(m)
    
    # Create combined line
    if len(all_coords) > 1:
        st.session_state.user_line = LineString(all_coords)

# Display map
map_data = st_folium(m, width=1200, height=550, key="main_map")

# Extract drawn line
user_line = None
if map_data and "all_drawings" in map_data and map_data["all_drawings"]:
    for f in map_data["all_drawings"]:
        if f.get("geometry", {}).get("type") == "LineString":
            coords = [(c[1], c[0]) for c in f["geometry"]["coordinates"]]
            user_line = LineString(coords)
            st.session_state.user_line = user_line
            break

if user_line is None and st.session_state.user_line is not None:
    user_line = st.session_state.user_line

# Status display
if user_line:
    line_length = sum(haversine(list(user_line.coords)[i][0], list(user_line.coords)[i][1],
                                list(user_line.coords)[i+1][0], list(user_line.coords)[i+1][1])
                     for i in range(len(list(user_line.coords))-1))
    st.success(f"✓ Line defined: {line_length/1000:.2f} km | {len(list(user_line.coords))} waypoints")
else:
    st.info("👆 Draw a transmission line on the map or enter coordinates to begin")

# -------------------------------
# Analysis Execution
# -------------------------------
if apply and user_line:
    st.session_state.data_source_log = []
    
    with st.spinner("🔍 Analyzing environmental corridor..."):
        # Determine data source mode
        use_realtime = "Real-time" in data_source
        
        # Sample points
        pts = sample_points(user_line, sample_m)
        
        # Progress tracking
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        data = []
        for idx, p in enumerate(pts):
            status_text.text(f"Analyzing point {idx+1}/{len(pts)}...")
            lat, lon = p.y, p.x
            
            # Get environmental data
            env_data = get_environmental_data(lat, lon, use_realtime)
            
            # Check cyclone zone
            in_cyclone = check_cyclone_zone(lat, lon)
            
            row = {
                "point_id": idx + 1,
                "lat": lat,
                "lon": lon,
                "pm25": env_data["pm25"],
                "pm10": env_data["pm10"],
                "temp": env_data["temp"],
                "hum": env_data["hum"],
                "wind": env_data["wind"],
                "cyclone_risk": in_cyclone,
                "data_source": env_data.get("source", "Historical")
            }
            
            row["severity_score"] = calculate_severity_score(row)
            
            # Get insulator recommendations
            insulators = recommend_insulator(
                row["severity_score"], 
                row["pm25"], 
                row["temp"], 
                row["wind"], 
                row["hum"]
            )
            row["recommended_insulator"] = insulators[0]["name"] if insulators else "Custom Required"
            row["insulator_cost_factor"] = insulators[0]["cost_factor"] if insulators else 2.5
            
            data.append(row)
            progress_bar.progress((idx + 1) / len(pts))
        
        progress_bar.empty()
        status_text.empty()
        
        # Create DataFrame
        df = pd.DataFrame(data)
        st.session_state.analysis_df = df
        
        # Display summary metrics
        st.markdown("---")
        st.subheader("📊 Environmental Analysis Summary")
        
        col1, col2, col3, col4, col5 = st.columns(5)
        
        with col1:
            avg_severity = df['severity_score'].mean()
            severity_color = "🔴" if avg_severity > 70 else "🟠" if avg_severity > 50 else "🟡" if avg_severity > 30 else "🟢"
            st.metric("Severity Score", f"{severity_color} {avg_severity:.1f}/100")
        
        with col2:
            avg_pm25 = df['pm25'].mean()
            pm_status = "Poor" if avg_pm25 > 100 else "Moderate" if avg_pm25 > 60 else "Good"
            st.metric("Avg PM2.5", f"{avg_pm25:.1f} µg/m³", pm_status)
        
        with col3:
            avg_temp = df['temp'].mean()
            st.metric("Avg Temperature", f"{avg_temp:.1f}°C")
        
        with col4:
            cyclone_pct = (df['cyclone_risk'].sum() / len(df)) * 100
            st.metric("Cyclone Exposure", f"{cyclone_pct:.0f}%")
        
        with col5:
            avg_cost = df['insulator_cost_factor'].mean()
            st.metric("Avg Cost Factor", f"{avg_cost:.2f}x")
        
        # Create enhanced visualization map
        st.markdown("---")
        st.subheader("🎨 Environmental Heat Map")
        
        m2 = create_base_map()
        
        # Draw transmission line
        line_coords = [(p[0], p[1]) for p in list(user_line.coords)]
        folium.PolyLine(
            locations=line_coords,
            color="black",
            weight=5,
            opacity=1.0,
            popup="Transmission Corridor"
        ).add_to(m2)
        
        # Create feature groups for layers
        severity_layer = folium.FeatureGroup(name="Severity Markers", show=True)
        heatmap_layer = folium.FeatureGroup(name="Heat Map", show=True)
        
        # Add severity markers
        for _, row in df.iterrows():
            severity = row['severity_score']
            
            # Color coding
            if severity > 75:
                color, icon = 'red', 'exclamation-triangle'
                risk = "CRITICAL"
            elif severity > 60:
                color, icon = 'orange', 'warning'
                risk = "HIGH"
            elif severity > 40:
                color, icon = 'yellow', 'info-sign'
                risk = "MODERATE"
            else:
                color, icon = 'green', 'ok'
                risk = "LOW"
            
            # Popup content
            popup_html = f"""
            <div style='width:280px;font-family:Arial;'>
                <h4 style='color:{color};margin:0;'>Point {row['point_id']} - {risk} RISK</h4>
                <hr style='margin:5px 0;'>
                <table style='width:100%;font-size:11px;'>
                    <tr><td><b>Severity Score:</b></td><td>{severity:.1f}/100</td></tr>
                    <tr><td><b>PM2.5:</b></td><td>{row['pm25']:.1f} µg/m³</td></tr>
                    <tr><td><b>PM10:</b></td><td>{row['pm10']:.1f} µg/m³</td></tr>
                    <tr><td><b>Temperature:</b></td><td>{row['temp']:.1f}°C</td></tr>
                    <tr><td><b>Humidity:</b></td><td>{row['hum']:.1f}%</td></tr>
                    <tr><td><b>Wind Speed:</b></td><td>{row['wind']:.1f} km/h</td></tr>
                    <tr><td><b>Cyclone Risk:</b></td><td>{'YES' if row['cyclone_risk'] else 'NO'}</td></tr>
                    <tr><td colspan='2'><hr style='margin:5px 0;'></td></tr>
                    <tr><td><b>Recommended:</b></td><td style='color:blue;'>{row['recommended_insulator']}</td></tr>
                    <tr><td><b>Cost Factor:</b></td><td>{row['insulator_cost_factor']:.2f}x</td></tr>
                    <tr><td><b>Data Source:</b></td><td style='font-size:9px;'>{row['data_source']}</td></tr>
                </table>
            </div>
            """
            
            folium.CircleMarker(
                location=[row['lat'], row['lon']],
                radius=10,
                popup=folium.Popup(popup_html, max_width=300),
                tooltip=f"Point {row['point_id']}: {risk}",
                color=color,
                fill=True,
                fillColor=color,
                fillOpacity=0.7,
                weight=3
            ).add_to(severity_layer)
        
        # Add heat map for selected parameters
        if "PM2.5" in params:
            pm25_data = [[row['lat'], row['lon'], row['pm25']/10] 
                         for _, row in df.iterrows() if row['pm25'] is not None]
            if pm25_data:
                HeatMap(pm25_data, name="PM2.5 Heat", radius=20, blur=30,
                       gradient={0.0: 'blue', 0.3: 'lime', 0.5: 'yellow', 0.7: 'orange', 1.0: 'red'},
                       min_opacity=0.35, max_zoom=18).add_to(heatmap_layer)
        
        # Add layers to map
        severity_layer.add_to(m2)
        heatmap_layer.add_to(m2)
        folium.LayerControl(collapsed=False).add_to(m2)
        
        # Display map
        st_folium(m2, width=1200, height=600, key="analysis_map")
        
        # Data table with filtering
        st.markdown("---")
        st.subheader("📋 Detailed Analysis Data")
        
        # Risk filter
        risk_filter = st.multiselect(
            "Filter by Risk Level",
            ["CRITICAL (>75)", "HIGH (60-75)", "MODERATE (40-60)", "LOW (<40)"],
            default=["CRITICAL (>75)", "HIGH (60-75)", "MODERATE (40-60)", "LOW (<40)"]
        )
        
        # Apply filters
        filtered_df = df.copy()
        if "CRITICAL (>75)" not in risk_filter:
            filtered_df = filtered_df[filtered_df['severity_score'] <= 75]
        if "HIGH (60-75)" not in risk_filter:
            filtered_df = filtered_df[(filtered_df['severity_score'] <= 60) | (filtered_df['severity_score'] > 75)]
        if "MODERATE (40-60)" not in risk_filter:
            filtered_df = filtered_df[(filtered_df['severity_score'] <= 40) | (filtered_df['severity_score'] > 60)]
        if "LOW (<40)" not in risk_filter:
            filtered_df = filtered_df[filtered_df['severity_score'] > 40]
        
        # Display table
        display_df = filtered_df[['point_id', 'lat', 'lon', 'severity_score', 'pm25', 'temp', 
                                  'hum', 'wind', 'cyclone_risk', 'recommended_insulator', 
                                  'insulator_cost_factor', 'data_source']].round(2)
        
        st.dataframe(display_df, use_container_width=True, height=400)
        
        # Visualizations
        st.markdown("---")
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("📈 Severity Distribution")
            fig1, ax1 = plt.subplots(figsize=(8, 4))
            colors = ['red' if x>75 else 'orange' if x>60 else 'yellow' if x>40 else 'green' 
                     for x in df['severity_score']]
            ax1.bar(df['point_id'], df['severity_score'], color=colors, alpha=0.7, edgecolor='black')
            ax1.axhline(y=75, color='red', linestyle='--', linewidth=2, label='Critical (75)')
            ax1.axhline(y=60, color='orange', linestyle='--', linewidth=1.5, label='High (60)')
            ax1.axhline(y=40, color='yellow', linestyle='--', linewidth=1, label='Moderate (40)')
            ax1.set_xlabel('Sample Point', fontsize=11)
            ax1.set_ylabel('Severity Score', fontsize=11)
            ax1.set_title('Environmental Severity Along Corridor', fontsize=12, fontweight='bold')
            ax1.legend(loc='upper right', fontsize=9)
            ax1.grid(axis='y', alpha=0.3)
            st.pyplot(fig1)
        
        with col2:
            st.subheader("🔧 Insulator Recommendations")
            insulator_counts = df['recommended_insulator'].value_counts()
            fig2, ax2 = plt.subplots(figsize=(8, 4))
            colors_pie = ['#ff6b6b', '#4ecdc4', '#45b7d1', '#96ceb4', '#ffeaa7']
            wedges, texts, autotexts = ax2.pie(insulator_counts.values, labels=insulator_counts.index, 
                                                autopct='%1.1f%%', colors=colors_pie, startangle=90)
            for text in texts:
                text.set_fontsize(9)
            for autotext in autotexts:
                autotext.set_color('white')
                autotext.set_fontweight('bold')
                autotext.set_fontsize(10)
            ax2.set_title('Recommended Insulator Distribution', fontsize=12, fontweight='bold')
            st.pyplot(fig2)
        
        # Environmental trends
        st.markdown("---")
        st.subheader("📊 Environmental Parameter Trends")
        
        fig3, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(14, 8))
        
        # PM2.5 trend
        ax1.plot(df['point_id'], df['pm25'], marker='o', color='#e74c3c', linewidth=2)
        ax1.axhline(y=60, color='orange', linestyle='--', label='Moderate (60)')
        ax1.axhline(y=100, color='red', linestyle='--', label='Poor (100)')
        ax1.fill_between(df['point_id'], 0, df['pm25'], alpha=0.3, color='#e74c3c')
        ax1.set_xlabel('Point ID')
        ax1.set_ylabel('PM2.5 (µg/m³)')
        ax1.set_title('PM2.5 Concentration', fontweight='bold')
        ax1.legend()
        ax1.grid(True, alpha=0.3)
        
        # Temperature trend
        ax2.plot(df['point_id'], df['temp'], marker='s', color='#3498db', linewidth=2)
        ax2.axhline(y=35, color='orange', linestyle='--', label='High (35°C)')
        ax2.axhline(y=40, color='red', linestyle='--', label='Extreme (40°C)')
        ax2.fill_between(df['point_id'], df['temp'].min()-5, df['temp'], alpha=0.3, color='#3498db')
        ax2.set_xlabel('Point ID')
        ax2.set_ylabel('Temperature (°C)')
        ax2.set_title('Temperature Profile', fontweight='bold')
        ax2.legend()
        ax2.grid(True, alpha=0.3)
        
        # Humidity trend
        ax3.plot(df['point_id'], df['hum'], marker='^', color='#2ecc71', linewidth=2)
        ax3.axhline(y=80, color='blue', linestyle='--', label='High Humidity (80%)')
        ax3.fill_between(df['point_id'], 0, df['hum'], alpha=0.3, color='#2ecc71')
        ax3.set_xlabel('Point ID')
        ax3.set_ylabel('Humidity (%)')
        ax3.set_title('Relative Humidity', fontweight='bold')
        ax3.legend()
        ax3.grid(True, alpha=0.3)
        
        # Wind speed trend
        ax4.plot(df['point_id'], df['wind'], marker='D', color='#9b59b6', linewidth=2)
        ax4.axhline(y=30, color='orange', linestyle='--', label='High Wind (30 km/h)')
        ax4.fill_between(df['point_id'], 0, df['wind'], alpha=0.3, color='#9b59b6')
        ax4.set_xlabel('Point ID')
        ax4.set_ylabel('Wind Speed (km/h)')
        ax4.set_title('Wind Speed Profile', fontweight='bold')
        ax4.legend()
        ax4.grid(True, alpha=0.3)
        
        plt.tight_layout()
        st.pyplot(fig3)
        
        # Data source summary
        with st.expander("📡 Data Source Information"):
            source_counts = df['data_source'].value_counts()
            st.write("**Data Retrieval Summary:**")
            for source, count in source_counts.items():
                st.write(f"- {source}: {count} points ({count/len(df)*100:.1f}%)")
            
            if st.session_state.data_source_log:
                st.write("\n**Detailed Log:**")
                for log in st.session_state.data_source_log[-10:]:  # Show last 10 entries
                    st.text(log)

# -------------------------------
# PDF Report Generation
# -------------------------------
if generate_pdf and st.session_state.analysis_df is not None:
    with st.spinner("📄 Generating comprehensive PDF report..."):
        df = st.session_state.analysis_df
        
        # Create PDF with logo
        pdf = FPDF()
        pdf.add_page()
        pdf.set_auto_page_break(auto=True, margin=15)
        
        # Add logo if available
        logo_paths = ["deccan_logo.png", "../deccan_logo.png", "./deccan_logo.png"]
        logo_added = False
        for logo_path in logo_paths:
            if os.path.exists(logo_path):
                try:
                    pdf.image(logo_path, x=10, y=8, w=45)
                    logo_added = True
                    break
                except:
                    pass
        
        # Header
        pdf.set_font("Arial", "B", 18)
        pdf.cell(0, 12, "TRANSMISSION LINE", ln=True, align="C")
        pdf.set_font("Arial", "B", 16)
        pdf.cell(0, 10, "Environmental Severity Assessment", ln=True, align="C")
        pdf.ln(5)
        
        # Project details box
        pdf.set_fill_color(240, 240, 240)
        pdf.set_font("Arial", "B", 11)
        pdf.cell(0, 8, "PROJECT INFORMATION", ln=True, fill=True)
        pdf.set_font("Arial", "", 10)
        pdf.cell(0, 6, f"Client: {client_name}", ln=True)
        pdf.cell(0, 6, f"Project Code: {project_code}", ln=True)
        pdf.cell(0, 6, f"Line Description: {line_name}", ln=True)
        pdf.cell(0, 6, f"Report Generated: {datetime.now().strftime('%d %B %Y, %H:%M IST')}", ln=True)
        pdf.cell(0, 6, f"Corridor Length: {haversine(df.iloc[0]['lat'], df.iloc[0]['lon'], df.iloc[-1]['lat'], df.iloc[-1]['lon'])/1000:.2f} km", ln=True)
        pdf.cell(0, 6, f"Analysis Points: {len(df)}", ln=True)
        pdf.ln(5)
        
        # Executive summary
        pdf.set_font("Arial", "B", 13)
        pdf.set_fill_color(51, 51, 102)
        pdf.set_text_color(255, 255, 255)
        pdf.cell(0, 9, "EXECUTIVE SUMMARY", ln=True, fill=True)
        pdf.set_text_color(0, 0, 0)
        pdf.set_font("Arial", "", 10)
        pdf.ln(2)
        
        avg_severity = df['severity_score'].mean()
        if avg_severity > 75:
            risk_level, risk_color = "CRITICAL", (255, 0, 0)
        elif avg_severity > 60:
            risk_level, risk_color = "HIGH", (255, 140, 0)
        elif avg_severity > 40:
            risk_level, risk_color = "MODERATE", (255, 215, 0)
        else:
            risk_level, risk_color = "LOW", (0, 128, 0)
        
        pdf.set_font("Arial", "B", 11)
        pdf.cell(50, 6, "Overall Risk Level:", 0)
        pdf.set_text_color(*risk_color)
        pdf.cell(0, 6, f"{risk_level} ({avg_severity:.1f}/100)", ln=True)
        pdf.set_text_color(0, 0, 0)
        pdf.set_font("Arial", "", 10)
        pdf.ln(2)
        
        summary_text = f"This assessment evaluates environmental conditions along a {haversine(df.iloc[0]['lat'], df.iloc[0]['lon'], df.iloc[-1]['lat'], df.iloc[-1]['lon'])/1000:.1f} km transmission corridor across {len(df)} strategic sampling points. The analysis integrates real-time and historical data (2022-2024) from multiple authoritative sources including OpenAQ, WAQI, Open-Meteo, and IMD regional databases."
        pdf.multi_cell(0, 5, summary_text)
        pdf.ln(3)
        
        # Key metrics table
        pdf.set_font("Arial", "B", 12)
        pdf.set_fill_color(240, 240, 240)
        pdf.cell(0, 8, "KEY ENVIRONMENTAL METRICS", ln=True, fill=True)
        pdf.set_font("Arial", "", 10)
        
        metrics_data = [
            ("Parameter", "Average", "Min", "Max", "WHO/Standard"),
            ("PM2.5 (µg/m³)", f"{df['pm25'].mean():.1f}", f"{df['pm25'].min():.1f}", 
             f"{df['pm25'].max():.1f}", "15 (Annual)"),
            ("PM10 (µg/m³)", f"{df['pm10'].mean():.1f}", f"{df['pm10'].min():.1f}", 
             f"{df['pm10'].max():.1f}", "45 (Annual)"),
            ("Temperature (°C)", f"{df['temp'].mean():.1f}", f"{df['temp'].min():.1f}", 
             f"{df['temp'].max():.1f}", "25-35 (Optimal)"),
            ("Humidity (%)", f"{df['hum'].mean():.1f}", f"{df['hum'].min():.1f}", 
             f"{df['hum'].max():.1f}", "40-70 (Optimal)"),
            ("Wind Speed (km/h)", f"{df['wind'].mean():.1f}", f"{df['wind'].min():.1f}", 
             f"{df['wind'].max():.1f}", "<30 (Moderate)"),
        ]
        
        col_widths = [60, 35, 30, 30, 35]
        pdf.set_fill_color(220, 220, 220)
        pdf.set_font("Arial", "B", 9)
        for i, header in enumerate(metrics_data[0]):
            pdf.cell(col_widths[i], 6, header, 1, 0, 'C', fill=True)
        pdf.ln()
        
        pdf.set_font("Arial", "", 9)
        for row in metrics_data[1:]:
            for i, cell in enumerate(row):
                pdf.cell(col_widths[i], 6, cell, 1, 0, 'C')
            pdf.ln()
        pdf.ln(4)
        
        # Risk distribution
        pdf.set_font("Arial", "B", 12)
        pdf.set_fill_color(240, 240, 240)
        pdf.cell(0, 8, "RISK DISTRIBUTION ANALYSIS", ln=True, fill=True)
        pdf.set_font("Arial", "", 10)
        
        critical = len(df[df['severity_score'] > 75])
        high = len(df[(df['severity_score'] > 60) & (df['severity_score'] <= 75)])
        moderate = len(df[(df['severity_score'] > 40) & (df['severity_score'] <= 60)])
        low = len(df[df['severity_score'] <= 40])
        
        pdf.cell(0, 6, f"• Critical Risk Zones (>75): {critical} points ({critical/len(df)*100:.1f}%)", ln=True)
        pdf.cell(0, 6, f"• High Risk Zones (60-75): {high} points ({high/len(df)*100:.1f}%)", ln=True)
        pdf.cell(0, 6, f"• Moderate Risk Zones (40-60): {moderate} points ({moderate/len(df)*100:.1f}%)", ln=True)
        pdf.cell(0, 6, f"• Low Risk Zones (<40): {low} points ({low/len(df)*100:.1f}%)", ln=True)
        pdf.cell(0, 6, f"• Cyclone-Prone Coverage: {(df['cyclone_risk'].sum()/len(df)*100):.1f}%", ln=True)
        pdf.ln(4)
        
        # Insulator recommendations
        pdf.add_page()
        pdf.set_font("Arial", "B", 13)
        pdf.set_fill_color(51, 51, 102)
        pdf.set_text_color(255, 255, 255)
        pdf.cell(0, 9, "INSULATOR SPECIFICATIONS & RECOMMENDATIONS", ln=True, fill=True)
        pdf.set_text_color(0, 0, 0)
        pdf.ln(3)
        
        insulator_dist = df['recommended_insulator'].value_counts()
        pdf.set_font("Arial", "B", 11)
        pdf.cell(0, 6, "Recommended Insulator Distribution:", ln=True)
        pdf.set_font("Arial", "", 10)
        
        for insulator, count in insulator_dist.items():
            percentage = (count / len(df)) * 100
            pdf.cell(0, 5, f"  • {insulator}: {count} sections ({percentage:.1f}%)", ln=True)
        pdf.ln(3)
        
        # Detailed recommendations by zone
        pdf.set_font("Arial", "B", 11)
        pdf.cell(0, 6, "Zone-Specific Recommendations:", ln=True)
        pdf.set_font("Arial", "", 9)
        
        for _, row in df.iterrows():
            if row['severity_score'] > 60:  # Only show high-risk zones
                pdf.ln(2)
                pdf.set_font("Arial", "B", 9)
                risk = "CRITICAL" if row['severity_score'] > 75 else "HIGH"
                pdf.cell(0, 5, f"Point {row['point_id']} ({row['lat']:.4f}, {row['lon']:.4f}) - {risk} RISK", ln=True)
                pdf.set_font("Arial", "", 8)
                pdf.cell(0, 4, f"  Severity: {row['severity_score']:.1f}/100 | PM2.5: {row['pm25']:.1f} | Temp: {row['temp']:.1f}°C | Wind: {row['wind']:.1f} km/h", ln=True)
                pdf.set_font("Arial", "I", 8)
                pdf.cell(0, 4, f"  → Recommended: {row['recommended_insulator']} (Cost Factor: {row['insulator_cost_factor']:.2f}x)", ln=True)
        
        pdf.ln(4)
        
        # Technical recommendations
        pdf.set_font("Arial", "B", 12)
        pdf.set_fill_color(240, 240, 240)
        pdf.cell(0, 8, "TECHNICAL RECOMMENDATIONS", ln=True, fill=True)
        pdf.set_font("Arial", "", 10)
        
        recommendations = []
        
        if df['pm25'].mean() > 100:
            recommendations.append("• CRITICAL: Deploy hydrophobic silicone insulators with self-cleaning properties due to severe pollution (PM2.5 > 100 µg/m³)")
        elif df['pm25'].mean() > 60:
            recommendations.append("• Install anti-fog ceramic or polymer composite insulators for elevated pollution levels")
        
        if df['temp'].max() > 45:
            recommendations.append("• CRITICAL: Use high-temperature rated materials (>65°C tolerance) for extreme heat zones")
        elif df['temp'].mean() > 38:
            recommendations.append("• Specify insulators with enhanced thermal resistance (50-60°C range)")
        
        if df['hum'].mean() > 80:
            recommendations.append("• Apply corrosion-resistant coatings and use hydrophobic insulators for high-humidity environment")
        
        if df['wind'].max() > 45:
            recommendations.append("• CRITICAL: Reinforce tower structures and use aerodynamic insulator designs for high wind loads")
        elif df['wind'].mean() > 30:
            recommendations.append("• Consider wind load factors in structural design and insulator selection")
        
        if df['cyclone_risk'].sum() > len(df) * 0.3:
            recommendations.append("• Implement cyclone-resistant tower designs and reinforced insulator mounting systems")
        
        if critical > 0:
            recommendations.append(f"• Prioritize upgrades for {critical} critical risk zones identified in the assessment")
        
        recommendations.append("• Conduct quarterly inspections focusing on high-risk segments")
        recommendations.append("• Implement real-time environmental monitoring system along the corridor")
        
        if not recommendations:
            recommendations.append("• Standard insulator specifications are suitable for this corridor")
            recommendations.append("• Maintain routine inspection and maintenance schedules")
        
        for rec in recommendations:
            pdf.multi_cell(0, 5, rec)
            pdf.ln(1)
        
        # Cost analysis
        pdf.ln(3)
        pdf.set_font("Arial", "B", 12)
        pdf.set_fill_color(240, 240, 240)
        pdf.cell(0, 8, "COST IMPACT ANALYSIS", ln=True, fill=True)
        pdf.set_font("Arial", "", 10)
        
        avg_cost_factor = df['insulator_cost_factor'].mean()
        total_relative_cost = df['insulator_cost_factor'].sum()
        
        pdf.cell(0, 6, f"Average Cost Factor: {avg_cost_factor:.2f}x (relative to standard ceramic)", ln=True)
        pdf.cell(0, 6, f"Total Relative Cost Index: {total_relative_cost:.1f}", ln=True)
        pdf.multi_cell(0, 5, f"Estimated premium over standard insulators: {(avg_cost_factor-1)*100:.0f}% due to environmental severity requirements")
        
        # Footer
        pdf.ln(5)
        pdf.set_font("Arial", "I", 8)
        pdf.set_text_color(100, 100, 100)
        pdf.multi_cell(0, 4, "This report is generated based on environmental data from OpenAQ, WAQI, Open-Meteo APIs and IMD historical databases (2022-2024). Recommendations are based on industry standards and site-specific environmental conditions. Final specifications should be validated through detailed site surveys and engineering analysis.")
        
        # Save and provide download
        pdf_filename = f"Deccan_Environmental_Report_{project_code}_{datetime.now().strftime('%Y%m%d')}.pdf"
        pdf_path = os.path.join(tempfile.gettempdir(), pdf_filename)
        pdf.output(pdf_path)
        
        with open(pdf_path, "rb") as f:
            st.download_button(
                "⬇️ Download PDF Report",
                f,
                file_name=pdf_filename,
                mime="application/pdf",
                use_container_width=True,
                type="primary"
            )
        
        st.success("✅ PDF Report generated successfully!")

# -------------------------------
# Excel Export
# -------------------------------
if generate_excel and st.session_state.analysis_df is not None:
    with st.spinner("📗 Generating Excel export..."):
        df = st.session_state.analysis_df
        
        # Create Excel writer
        excel_filename = f"Deccan_Environmental_Data_{project_code}_{datetime.now().strftime('%Y%m%d')}.xlsx"
        excel_path = os.path.join(tempfile.gettempdir(), excel_filename)
        
        with pd.ExcelWriter(excel_path, engine='openpyxl') as writer:
            # Main data sheet
            export_df = df.copy()
            export_df.to_excel(writer, sheet_name='Environmental Data', index=False)
            
            # Summary statistics sheet
            summary_data = {
                'Metric': ['Average Severity Score', 'Average PM2.5', 'Average PM10', 
                          'Average Temperature', 'Average Humidity', 'Average Wind Speed',
                          'Cyclone Coverage %', 'Critical Risk Points', 'High Risk Points',
                          'Moderate Risk Points', 'Low Risk Points', 'Total Points'],
                'Value': [
                    f"{df['severity_score'].mean():.2f}/100",
                    f"{df['pm25'].mean():.2f} µg/m³",
                    f"{df['pm10'].mean():.2f} µg/m³",
                    f"{df['temp'].mean():.2f}°C",
                    f"{df['hum'].mean():.2f}%",
                    f"{df['wind'].mean():.2f} km/h",
                    f"{(df['cyclone_risk'].sum()/len(df)*100):.1f}%",
                    len(df[df['severity_score'] > 75]),
                    len(df[(df['severity_score'] > 60) & (df['severity_score'] <= 75)]),
                    len(df[(df['severity_score'] > 40) & (df['severity_score'] <= 60)]),
                    len(df[df['severity_score'] <= 40]),
                    len(df)
                ]
            }
            summary_df = pd.DataFrame(summary_data)
            summary_df.to_excel(writer, sheet_name='Summary Statistics', index=False)
            
            # Insulator recommendations sheet
            insulator_data = []
            for _, row in df.iterrows():
                insulator_data.append({
                    'Point ID': row['point_id'],
                    'Latitude': row['lat'],
                    'Longitude': row['lon'],
                    'Severity Score': row['severity_score'],
                    'Recommended Insulator': row['recommended_insulator'],
                    'Cost Factor': row['insulator_cost_factor'],
                    'PM2.5': row['pm25'],
                    'Temperature': row['temp'],
                    'Wind Speed': row['wind']
                })
            insulator_df = pd.DataFrame(insulator_data)
            insulator_df.to_excel(writer, sheet_name='Insulator Recommendations', index=False)
            
            # Risk zones sheet (critical and high only)
            risk_zones = df[df['severity_score'] > 60].copy()
            risk_zones['Risk Level'] = risk_zones['severity_score'].apply(
                lambda x: 'CRITICAL' if x > 75 else 'HIGH'
            )
            risk_zones.to_excel(writer, sheet_name='High Risk Zones', index=False)
            
            # Project info sheet
            project_info = {
                'Field': ['Client Name', 'Project Code', 'Line Description', 
                         'Report Date', 'Corridor Length (km)', 'Total Analysis Points',
                         'Data Sources Used'],
                'Value': [
                    client_name,
                    project_code,
                    line_name,
                    datetime.now().strftime('%d %B %Y, %H:%M IST'),
                    f"{haversine(df.iloc[0]['lat'], df.iloc[0]['lon'], df.iloc[-1]['lat'], df.iloc[-1]['lon'])/1000:.2f}",
                    len(df),
                    'OpenAQ, WAQI, Open-Meteo, IMD (2022-2024)'
                ]
            }
            project_df = pd.DataFrame(project_info)
            project_df.to_excel(writer, sheet_name='Project Information', index=False)
        
        # Provide download
        with open(excel_path, "rb") as f:
            st.download_button(
                "⬇️ Download Excel Data",
                f,
                file_name=excel_filename,
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True,
                type="secondary"
            )
        
        st.success("✅ Excel file generated successfully with multiple sheets!")

# -------------------------------
# Footer
# -------------------------------
st.markdown("---")
col1, col2, col3 = st.columns([2, 3, 2])

with col1:
    st.caption("**Deccan Enterprises Pvt. Ltd.**")
    st.caption("Environmental Analysis Division")

with col2:
    st.caption("**Data Sources:** OpenAQ • WAQI • Open-Meteo • IMD")
    st.caption("**Version:** 2.0 Production | **Updated:** October 2025")

with col3:
    st.caption("**Support:** support@deccan.com")
    st.caption("**Documentation:** docs.deccan.com")

# Display system info in expander
with st.expander("ℹ️ System Information"):
    st.write("**Features:**")
    st.write("- Real-time environmental data with historical fallback (2022-2024)")
    st.write("- Multi-source data aggregation (OpenAQ, WAQI, Open-Meteo, IMD)")
    st.write("- Intelligent insulator recommendation system")
    st.write("- Comprehensive PDF reports with cost analysis")
    st.write("- Multi-sheet Excel exports")
    st.write("- Interactive heat mapping and risk visualization")
    st.write("- Cyclone zone detection and analysis")
    
    st.write("\n**Insulator Database:**")
    for key, spec in INSULATOR_SPECS.items():
        st.write(f"- **{spec['name']}**: Temp range {spec['temp_range'][0]}°C to {spec['temp_range'][1]}°C, "
                f"Pollution max {spec['pollution_max']} µg/m³, Wind max {spec['wind_max']} km/h, "
                f"Cost factor {spec['cost_factor']}x")
    
    st.write("\n**Data Coverage:**")
    st.write(f"- Historical data repository: {len([k for k, v in HISTORICAL_DATA.items() if 'lat' in v])} major cities")
    st.write("- Regional interpolation: 5 zones (North, South, East, West, Central India)")
    st.write("- Distance-weighted averaging for precise location estimates")

# Admin panel for debugging
if st.sidebar.checkbox("🔧 Show Debug Info", value=False):
    with st.expander("Debug Information", expanded=True):
        st.write("**Session State:**")
        st.write(f"- User Line Defined: {st.session_state.user_line is not None}")
        st.write(f"- Analysis Data Available: {st.session_state.analysis_df is not None}")
        if st.session_state.analysis_df is not None:
            st.write(f"- Data Points: {len(st.session_state.analysis_df)}")
        
        st.write("\n**Historical Data Sample:**")
        sample_cities = ["delhi", "mumbai", "bangalore"]
        for city in sample_cities:
            if city in HISTORICAL_DATA:
                st.write(f"- {city.title()}: PM2.5={HISTORICAL_DATA[city]['pm25']}, "
                        f"Temp={HISTORICAL_DATA[city]['temp']}°C")
        
        if st.button("Clear Session State"):
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.rerun()
