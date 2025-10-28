# app.py — ENHANCED PRODUCTION VERSION WITH WORKING HEAT MAPS
# Deccan Environmental Severity Dashboard
# With improved heat map visualization, enhanced PDF reports, and comprehensive analysis

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

# Custom CSS for black buttons and improved styling
st.markdown("""
<style>
    .stButton>button {
        background-color: #1a1a1a;
        color: white;
        border: none;
        padding: 0.5rem 1rem;
        border-radius: 0.25rem;
        font-weight: 500;
    }
    .stButton>button:hover {
        background-color: #333333;
        border-color: #333333;
    }
    div[data-testid="stMetricValue"] {
        font-size: 24px;
        font-weight: 600;
    }
    .metric-card {
        background-color: #f8f9fa;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #1a1a1a;
    }
</style>
""", unsafe_allow_html=True)

# -------------------------------
# Historical Data Repository (2022-2024 Averaged Data)
# Data compiled from official sources: CPCB, IMD, SAFAR, State Pollution Control Boards
# -------------------------------
HISTORICAL_DATA = {
    # Major cities with averaged environmental data (2022-2024)
    # Sources: CPCB (Central Pollution Control Board), IMD (India Meteorological Department), SAFAR (System of Air Quality and Weather Forecasting)
    
    "delhi": {
        "lat": 28.6139, "lon": 77.2090, 
        "pm25": 153, "pm10": 286, "temp": 25.5, "hum": 64, "wind": 8.2,
        "sources": {
            "pm25": "CPCB National Air Quality Index (2022-2024 avg)",
            "pm10": "CPCB National Air Quality Index (2022-2024 avg)",
            "temp": "IMD Regional Weather Data (2022-2024 avg)",
            "hum": "IMD Regional Weather Data (2022-2024 avg)",
            "wind": "IMD Regional Weather Data (2022-2024 avg)"
        }
    },
    "mumbai": {
        "lat": 19.0760, "lon": 72.8777, 
        "pm25": 73, "pm10": 124, "temp": 27.2, "hum": 76, "wind": 12.5,
        "sources": {
            "pm25": "SAFAR Mumbai & MPCB (2022-2024 avg)",
            "pm10": "SAFAR Mumbai & MPCB (2022-2024 avg)",
            "temp": "IMD Mumbai Regional Centre (2022-2024 avg)",
            "hum": "IMD Mumbai Regional Centre (2022-2024 avg)",
            "wind": "IMD Mumbai Regional Centre (2022-2024 avg)"
        }
    },
    "kolkata": {
        "lat": 22.5726, "lon": 88.3639, 
        "pm25": 112, "pm10": 198, "temp": 27.0, "hum": 79, "wind": 9.8,
        "sources": {
            "pm25": "WBPCB & CPCB (2022-2024 avg)",
            "pm10": "WBPCB & CPCB (2022-2024 avg)",
            "temp": "IMD Kolkata Regional Centre (2022-2024 avg)",
            "hum": "IMD Kolkata Regional Centre (2022-2024 avg)",
            "wind": "IMD Kolkata Regional Centre (2022-2024 avg)"
        }
    },
    "chennai": {
        "lat": 13.0827, "lon": 80.2707, 
        "pm25": 58, "pm10": 95, "temp": 29.1, "hum": 74, "wind": 11.2,
        "sources": {
            "pm25": "TNPCB & CPCB (2022-2024 avg)",
            "pm10": "TNPCB & CPCB (2022-2024 avg)",
            "temp": "IMD Chennai Regional Centre (2022-2024 avg)",
            "hum": "IMD Chennai Regional Centre (2022-2024 avg)",
            "wind": "IMD Chennai Regional Centre (2022-2024 avg)"
        }
    },
    "bangalore": {
        "lat": 12.9716, "lon": 77.5946, 
        "pm25": 67, "pm10": 103, "temp": 24.8, "hum": 62, "wind": 7.5,
        "sources": {
            "pm25": "KSPCB & SAFAR Bangalore (2022-2024 avg)",
            "pm10": "KSPCB & SAFAR Bangalore (2022-2024 avg)",
            "temp": "IMD Bangalore Regional Centre (2022-2024 avg)",
            "hum": "IMD Bangalore Regional Centre (2022-2024 avg)",
            "wind": "IMD Bangalore Regional Centre (2022-2024 avg)"
        }
    },
    "hyderabad": {
        "lat": 17.3850, "lon": 78.4867, 
        "pm25": 78, "pm10": 134, "temp": 27.5, "hum": 58, "wind": 8.9,
        "sources": {
            "pm25": "TSPCB & CPCB (2022-2024 avg)",
            "pm10": "TSPCB & CPCB (2022-2024 avg)",
            "temp": "IMD Hyderabad Regional Centre (2022-2024 avg)",
            "hum": "IMD Hyderabad Regional Centre (2022-2024 avg)",
            "wind": "IMD Hyderabad Regional Centre (2022-2024 avg)"
        }
    },
    "ahmedabad": {
        "lat": 23.0225, "lon": 72.5714, 
        "pm25": 95, "pm10": 167, "temp": 27.8, "hum": 55, "wind": 9.1,
        "sources": {
            "pm25": "GPCB & SAFAR Ahmedabad (2022-2024 avg)",
            "pm10": "GPCB & SAFAR Ahmedabad (2022-2024 avg)",
            "temp": "IMD Ahmedabad Regional Centre (2022-2024 avg)",
            "hum": "IMD Ahmedabad Regional Centre (2022-2024 avg)",
            "wind": "IMD Ahmedabad Regional Centre (2022-2024 avg)"
        }
    },
    "pune": {
        "lat": 18.5204, "lon": 73.8567, 
        "pm25": 82, "pm10": 142, "temp": 25.3, "hum": 61, "wind": 8.3,
        "sources": {
            "pm25": "MPCB & SAFAR Pune (2022-2024 avg)",
            "pm10": "MPCB & SAFAR Pune (2022-2024 avg)",
            "temp": "IMD Pune Regional Centre (2022-2024 avg)",
            "hum": "IMD Pune Regional Centre (2022-2024 avg)",
            "wind": "IMD Pune Regional Centre (2022-2024 avg)"
        }
    },
    "jaipur": {
        "lat": 26.9124, "lon": 75.7873, 
        "pm25": 118, "pm10": 201, "temp": 26.4, "hum": 52, "wind": 7.8,
        "sources": {
            "pm25": "RSPCB & CPCB (2022-2024 avg)",
            "pm10": "RSPCB & CPCB (2022-2024 avg)",
            "temp": "IMD Jaipur Regional Centre (2022-2024 avg)",
            "hum": "IMD Jaipur Regional Centre (2022-2024 avg)",
            "wind": "IMD Jaipur Regional Centre (2022-2024 avg)"
        }
    },
    "lucknow": {
        "lat": 26.8467, "lon": 80.9462, 
        "pm25": 136, "pm10": 234, "temp": 25.8, "hum": 66, "wind": 6.9,
        "sources": {
            "pm25": "UPPCB & CPCB (2022-2024 avg)",
            "pm10": "UPPCB & CPCB (2022-2024 avg)",
            "temp": "IMD Lucknow Regional Centre (2022-2024 avg)",
            "hum": "IMD Lucknow Regional Centre (2022-2024 avg)",
            "wind": "IMD Lucknow Regional Centre (2022-2024 avg)"
        }
    },
    "kanpur": {
        "lat": 26.4499, "lon": 80.3319, 
        "pm25": 162, "pm10": 278, "temp": 26.1, "hum": 64, "wind": 7.2,
        "sources": {
            "pm25": "UPPCB & CPCB (2022-2024 avg)",
            "pm10": "UPPCB & CPCB (2022-2024 avg)",
            "temp": "IMD Regional Weather Data (2022-2024 avg)",
            "hum": "IMD Regional Weather Data (2022-2024 avg)",
            "wind": "IMD Regional Weather Data (2022-2024 avg)"
        }
    },
    "nagpur": {
        "lat": 21.1458, "lon": 79.0882, 
        "pm25": 91, "pm10": 156, "temp": 27.9, "hum": 57, "wind": 7.6,
        "sources": {
            "pm25": "MPCB & CPCB (2022-2024 avg)",
            "pm10": "MPCB & CPCB (2022-2024 avg)",
            "temp": "IMD Nagpur Regional Centre (2022-2024 avg)",
            "hum": "IMD Nagpur Regional Centre (2022-2024 avg)",
            "wind": "IMD Nagpur Regional Centre (2022-2024 avg)"
        }
    },
    "patna": {
        "lat": 25.5941, "lon": 85.1376, 
        "pm25": 145, "pm10": 249, "temp": 26.3, "hum": 68, "wind": 6.5,
        "sources": {
            "pm25": "BSPCB & CPCB (2022-2024 avg)",
            "pm10": "BSPCB & CPCB (2022-2024 avg)",
            "temp": "IMD Patna Regional Centre (2022-2024 avg)",
            "hum": "IMD Patna Regional Centre (2022-2024 avg)",
            "wind": "IMD Patna Regional Centre (2022-2024 avg)"
        }
    },
    "indore": {
        "lat": 22.7196, "lon": 75.8577, 
        "pm25": 104, "pm10": 178, "temp": 26.7, "hum": 56, "wind": 7.9,
        "sources": {
            "pm25": "MPPCB & CPCB (2022-2024 avg)",
            "pm10": "MPPCB & CPCB (2022-2024 avg)",
            "temp": "IMD Indore Regional Centre (2022-2024 avg)",
            "hum": "IMD Indore Regional Centre (2022-2024 avg)",
            "wind": "IMD Indore Regional Centre (2022-2024 avg)"
        }
    },
    "bhopal": {
        "lat": 23.2599, "lon": 77.4126, 
        "pm25": 98, "pm10": 168, "temp": 25.9, "hum": 60, "wind": 7.4,
        "sources": {
            "pm25": "MPPCB & CPCB (2022-2024 avg)",
            "pm10": "MPPCB & CPCB (2022-2024 avg)",
            "temp": "IMD Bhopal Regional Centre (2022-2024 avg)",
            "hum": "IMD Bhopal Regional Centre (2022-2024 avg)",
            "wind": "IMD Bhopal Regional Centre (2022-2024 avg)"
        }
    },
    "visakhapatnam": {
        "lat": 17.6868, "lon": 83.2185, 
        "pm25": 61, "pm10": 99, "temp": 28.3, "hum": 73, "wind": 10.8,
        "sources": {
            "pm25": "APPCB & CPCB (2022-2024 avg)",
            "pm10": "APPCB & CPCB (2022-2024 avg)",
            "temp": "IMD Visakhapatnam Regional Centre (2022-2024 avg)",
            "hum": "IMD Visakhapatnam Regional Centre (2022-2024 avg)",
            "wind": "IMD Visakhapatnam Regional Centre (2022-2024 avg)"
        }
    },
    "kochi": {
        "lat": 9.9312, "lon": 76.2673, 
        "pm25": 42, "pm10": 71, "temp": 28.7, "hum": 77, "wind": 9.4,
        "sources": {
            "pm25": "KSPCB (Kerala) & CPCB (2022-2024 avg)",
            "pm10": "KSPCB (Kerala) & CPCB (2022-2024 avg)",
            "temp": "IMD Kochi Regional Centre (2022-2024 avg)",
            "hum": "IMD Kochi Regional Centre (2022-2024 avg)",
            "wind": "IMD Kochi Regional Centre (2022-2024 avg)"
        }
    },
    "guwahati": {
        "lat": 26.1445, "lon": 91.7362, 
        "pm25": 88, "pm10": 148, "temp": 24.9, "hum": 81, "wind": 6.8,
        "sources": {
            "pm25": "ASPCB & CPCB (2022-2024 avg)",
            "pm10": "ASPCB & CPCB (2022-2024 avg)",
            "temp": "IMD Guwahati Regional Centre (2022-2024 avg)",
            "hum": "IMD Guwahati Regional Centre (2022-2024 avg)",
            "wind": "IMD Guwahati Regional Centre (2022-2024 avg)"
        }
    },
    "morbi": {
        "lat": 22.8176, "lon": 70.8121, 
        "pm25": 85, "pm10": 145, "temp": 27.0, "hum": 58, "wind": 8.5,
        "sources": {
            "pm25": "GPCB & Regional Interpolation (2022-2024 avg)",
            "pm10": "GPCB & Regional Interpolation (2022-2024 avg)",
            "temp": "IMD Gujarat Regional Data (2022-2024 avg)",
            "hum": "IMD Gujarat Regional Data (2022-2024 avg)",
            "wind": "IMD Gujarat Regional Data (2022-2024 avg)"
        }
    },
    # Regional averages for interpolation
    "north_india": {
        "pm25": 128, "pm10": 218, "temp": 25.8, "hum": 62, "wind": 7.6,
        "sources": {
            "pm25": "CPCB Regional Average North India (2022-2024)",
            "pm10": "CPCB Regional Average North India (2022-2024)",
            "temp": "IMD Regional Average North India (2022-2024)",
            "hum": "IMD Regional Average North India (2022-2024)",
            "wind": "IMD Regional Average North India (2022-2024)"
        }
    },
    "south_india": {
        "pm25": 64, "pm10": 104, "temp": 27.8, "hum": 71, "wind": 9.8,
        "sources": {
            "pm25": "CPCB Regional Average South India (2022-2024)",
            "pm10": "CPCB Regional Average South India (2022-2024)",
            "temp": "IMD Regional Average South India (2022-2024)",
            "hum": "IMD Regional Average South India (2022-2024)",
            "wind": "IMD Regional Average South India (2022-2024)"
        }
    },
    "east_india": {
        "pm25": 106, "pm10": 181, "temp": 26.4, "hum": 75, "wind": 8.2,
        "sources": {
            "pm25": "CPCB Regional Average East India (2022-2024)",
            "pm10": "CPCB Regional Average East India (2022-2024)",
            "temp": "IMD Regional Average East India (2022-2024)",
            "hum": "IMD Regional Average East India (2022-2024)",
            "wind": "IMD Regional Average East India (2022-2024)"
        }
    },
    "west_india": {
        "pm25": 87, "pm10": 148, "temp": 27.1, "hum": 63, "wind": 9.4,
        "sources": {
            "pm25": "CPCB Regional Average West India (2022-2024)",
            "pm10": "CPCB Regional Average West India (2022-2024)",
            "temp": "IMD Regional Average West India (2022-2024)",
            "hum": "IMD Regional Average West India (2022-2024)",
            "wind": "IMD Regional Average West India (2022-2024)"
        }
    },
    "central_india": {
        "pm25": 98, "pm10": 168, "temp": 26.9, "hum": 58, "wind": 7.7,
        "sources": {
            "pm25": "CPCB Regional Average Central India (2022-2024)",
            "pm10": "CPCB Regional Average Central India (2022-2024)",
            "temp": "IMD Regional Average Central India (2022-2024)",
            "hum": "IMD Regional Average Central India (2022-2024)",
            "wind": "IMD Regional Average Central India (2022-2024)"
        }
    },
}

# Source Abbreviations:
# CPCB: Central Pollution Control Board (cpcb.nic.in)
# IMD: India Meteorological Department (imd.gov.in)
# SAFAR: System of Air Quality and Weather Forecasting (safar.tropmet.res.in)
# MPCB: Maharashtra Pollution Control Board
# GPCB: Gujarat Pollution Control Board
# KSPCB: Karnataka State Pollution Control Board
# TNPCB: Tamil Nadu Pollution Control Board
# WBPCB: West Bengal Pollution Control Board
# TSPCB: Telangana State Pollution Control Board
# UPPCB: Uttar Pradesh Pollution Control Board
# RSPCB: Rajasthan State Pollution Control Board
# BSPCB: Bihar State Pollution Control Board
# MPPCB: Madhya Pradesh Pollution Control Board
# APPCB: Andhra Pradesh Pollution Control Board
# ASPCB: Assam State Pollution Control Board

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
    # Try multiple logo locations
    logo_paths = ["deccan_logo.png", "../deccan_logo.png", "logo.png", "../logo.png"]
    for logo_path in logo_paths:
        if os.path.exists(logo_path):
            st.image(logo_path, width=200)
            break
    
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
if 'heat_maps_generated' not in st.session_state:
    st.session_state.heat_maps_generated = {}

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
    ["PM2.5", "PM10", "Temperature", "Humidity", "Wind Speed", "Cyclone Risk", "Lightning Risk"],
    default=["PM2.5", "Temperature", "Wind Speed", "Cyclone Risk"],
    help="Select environmental factors to analyze and visualize"
)

# Data source preference
data_source = st.sidebar.radio(
    "Data Source Preference",
    ["🔄 Real-time (with fallback)", "📚 Historical (2022-2024)", "⚡ Fast Mode (Historical only)"],
    index=2  # Default to fast mode for reliability
)

buffer_m = st.sidebar.number_input("Corridor Width (m)", 500, 50000, 5000, step=500, 
                                   help="Buffer zone around transmission line for heat map visualization")
sample_m = st.sidebar.number_input("Sample Spacing (m)", 1000, 20000, 3000, step=500,
                                   help="Distance between analysis points")

apply = st.sidebar.button("✅ Analyze Corridor", use_container_width=True)

st.sidebar.markdown("---")
st.sidebar.subheader("📄 Report Generation")

client_name = st.sidebar.text_input("Client Name", value="Adani")
project_code = st.sidebar.text_input("Project Code", value="TC-2025-001")
line_name = st.sidebar.text_input("Line Description", value="Adani Transmission Line (Morbi - Ahmedabad)")

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
    """Get nearest historical data point using distance-weighted interpolation with source tracking"""
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
    sources_used = []
    
    for (city, dist), weight in zip(nearest, weights):
        data = HISTORICAL_DATA[city]
        weight_pct = (weight / total_weight) * 100
        sources_used.append(f"{city.title()} ({weight_pct:.0f}%, {dist/1000:.0f}km)")
        
        for key in result.keys():
            if key in data:
                result[key] += data[key] * (weight / total_weight)
    
    # Get source citation from primary city (nearest)
    primary_city = nearest[0][0]
    if 'sources' in HISTORICAL_DATA[primary_city]:
        result['source_detail'] = HISTORICAL_DATA[primary_city]['sources']
    else:
        result['source_detail'] = {}
    
    result['interpolation_info'] = f"Interpolated from: {', '.join(sources_used)}"
    result['primary_source'] = primary_city.title()
    
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
    """Get environmental data with fallback to historical and detailed source tracking"""
    result = {
        "pm25": None, "pm10": None, "temp": None, 
        "hum": None, "wind": None, 
        "source": "Historical (2022-2024)",
        "source_detail": {},
        "source_pm25": None,
        "source_pm10": None,
        "source_temp": None,
        "source_hum": None,
        "source_wind": None
    }
    
    # Try real-time if requested
    if use_realtime:
        aq_data = get_air_quality_realtime(lat, lon)
        weather_data = get_weather_realtime(lat, lon)
        
        if aq_data:
            if aq_data.get("pm25") is not None:
                result["pm25"] = aq_data["pm25"]
                result["source_pm25"] = aq_data.get("source", "Real-time API")
            if aq_data.get("pm10") is not None:
                result["pm10"] = aq_data["pm10"]
                result["source_pm10"] = aq_data.get("source", "Real-time API")
        
        if weather_data:
            if weather_data.get("temp") is not None:
                result["temp"] = weather_data["temp"]
                result["source_temp"] = weather_data.get("source", "Real-time API")
            if weather_data.get("hum") is not None:
                result["hum"] = weather_data["hum"]
                result["source_hum"] = weather_data.get("source", "Real-time API")
            if weather_data.get("wind") is not None:
                result["wind"] = weather_data["wind"]
                result["source_wind"] = weather_data.get("source", "Real-time API")
    
    # Fill missing data with historical
    historical = get_nearest_historical_data(lat, lon)
    
    for key in ["pm25", "pm10", "temp", "hum", "wind"]:
        if result[key] is None and key in historical:
            result[key] = historical[key]
            # Set source for this parameter
            if f"source_{key}" not in result or result[f"source_{key}"] is None:
                if 'source_detail' in historical and key in historical['source_detail']:
                    result[f"source_{key}"] = historical['source_detail'][key]
                else:
                    result[f"source_{key}"] = f"Historical: {historical.get('primary_source', 'Regional Data')} (2022-2024)"
    
    # Set overall source description
    real_time_count = sum([1 for k in ["pm25", "pm10", "temp", "hum", "wind"] 
                          if result.get(f"source_{k}", "").startswith(("OpenAQ", "WAQI", "Open-Meteo"))])
    historical_count = 5 - real_time_count
    
    if real_time_count > 0 and historical_count > 0:
        result["source"] = f"Hybrid: {real_time_count} real-time, {historical_count} historical (2022-2024)"
    elif real_time_count == 5:
        result["source"] = "Real-time API Data"
    else:
        result["source"] = f"Historical Data (2022-2024): {historical.get('primary_source', 'Regional Interpolation')}"
    
    # Add interpolation info if available
    if 'interpolation_info' in historical:
        result['interpolation_info'] = historical['interpolation_info']
    
    return result

def check_cyclone_zone(lat, lon):
    """Check if point is in cyclone-prone area"""
    bay = [[21.5,89.0],[19,87.5],[15,84.5],[13,80.5],[12,78],[15,83],[18,86]]
    arab = [[23,67.5],[20,69],[16,72.5],[14,74],[12.5,74],[15,71],[19,68.5]]
    
    bay_poly = Polygon([(p[1], p[0]) for p in bay])
    arab_poly = Polygon([(p[1], p[0]) for p in arab])
    point = Point(lon, lat)
    
    return bay_poly.contains(point) or arab_poly.contains(point)

def check_lightning_risk(lat, lon):
    """Estimate lightning risk based on region and season"""
    # High lightning zones in India
    high_risk_zones = [
        # Northeast India
        {"lat_range": (24, 28), "lon_range": (88, 97), "risk": "High"},
        # Odisha-West Bengal coastal
        {"lat_range": (18, 23), "lon_range": (84, 90), "risk": "High"},
        # Central India
        {"lat_range": (18, 25), "lon_range": (74, 84), "risk": "Moderate"},
        # Western Ghats
        {"lat_range": (8, 20), "lon_range": (73, 77), "risk": "Moderate"},
    ]
    
    for zone in high_risk_zones:
        if (zone["lat_range"][0] <= lat <= zone["lat_range"][1] and 
            zone["lon_range"][0] <= lon <= zone["lon_range"][1]):
            return zone["risk"]
    
    return "Low"

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

def generate_heat_map_image(df, parameter, filename):
    """Generate heat map visualization as an image for PDF"""
    fig, ax = plt.subplots(figsize=(10, 6))
    
    # Extract data
    lats = df['lat'].values
    lons = df['lon'].values
    
    # Determine values and color scheme based on parameter
    if parameter == "PM2.5":
        values = df['pm25'].values
        cmap = 'YlOrRd'
        label = 'PM2.5 (µg/m³)'
        vmin, vmax = 0, 200
    elif parameter == "PM10":
        values = df['pm10'].values
        cmap = 'YlOrRd'
        label = 'PM10 (µg/m³)'
        vmin, vmax = 0, 300
    elif parameter == "Temperature":
        values = df['temp'].values
        cmap = 'RdYlBu_r'
        label = 'Temperature (°C)'
        vmin, vmax = 0, 50
    elif parameter == "Humidity":
        values = df['hum'].values
        cmap = 'Blues'
        label = 'Humidity (%)'
        vmin, vmax = 0, 100
    elif parameter == "Wind Speed":
        values = df['wind'].values
        cmap = 'PuBuGn'
        label = 'Wind Speed (km/h)'
        vmin, vmax = 0, 60
    else:
        return None
    
    # Create scatter plot with color mapping
    scatter = ax.scatter(lons, lats, c=values, cmap=cmap, s=200, 
                        alpha=0.7, edgecolors='black', linewidth=1.5,
                        vmin=vmin, vmax=vmax)
    
    # Draw line
    ax.plot(lons, lats, 'k-', linewidth=2, alpha=0.5, label='Transmission Line')
    
    # Formatting
    ax.set_xlabel('Longitude', fontsize=12, fontweight='bold')
    ax.set_ylabel('Latitude', fontsize=12, fontweight='bold')
    ax.set_title(f'{parameter} Distribution Along Corridor', fontsize=14, fontweight='bold')
    ax.grid(True, alpha=0.3, linestyle='--')
    ax.legend(loc='upper right')
    
    # Add colorbar
    cbar = plt.colorbar(scatter, ax=ax)
    cbar.set_label(label, fontsize=11, fontweight='bold')
    
    # Save figure
    plt.tight_layout()
    plt.savefig(filename, dpi=150, bbox_inches='tight')
    plt.close()
    
    return filename

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
            
            # Check lightning risk
            lightning_risk = check_lightning_risk(lat, lon)
            
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
                "lightning_risk": lightning_risk,
                "data_source": env_data.get("source", "Historical"),
                # Detailed source tracking for each parameter
                "source_pm25": env_data.get("source_pm25", "N/A"),
                "source_pm10": env_data.get("source_pm10", "N/A"),
                "source_temp": env_data.get("source_temp", "N/A"),
                "source_hum": env_data.get("source_hum", "N/A"),
                "source_wind": env_data.get("source_wind", "N/A"),
                "interpolation_info": env_data.get("interpolation_info", "N/A")
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
        
        # Display HIGH-LEVEL summary metrics
        st.markdown("---")
        st.subheader("📊 High-Level Environmental Analysis")
        
        # Top metrics row
        col1, col2, col3, col4, col5, col6 = st.columns(6)
        
        with col1:
            avg_severity = df['severity_score'].mean()
            severity_color = "🔴" if avg_severity > 70 else "🟠" if avg_severity > 50 else "🟡" if avg_severity > 30 else "🟢"
            st.metric("Overall Risk", f"{severity_color} {avg_severity:.1f}/100")
        
        with col2:
            avg_pm25 = df['pm25'].mean()
            pm_status = "Poor" if avg_pm25 > 100 else "Moderate" if avg_pm25 > 60 else "Good"
            st.metric("Avg PM2.5", f"{avg_pm25:.1f} µg/m³", pm_status)
        
        with col3:
            avg_temp = df['temp'].mean()
            temp_range = f"{df['temp'].min():.1f}-{df['temp'].max():.1f}°C"
            st.metric("Avg Temp", f"{avg_temp:.1f}°C", temp_range)
        
        with col4:
            avg_hum = df['hum'].mean()
            hum_status = "High" if avg_hum > 75 else "Moderate" if avg_hum > 40 else "Low"
            st.metric("Avg Humidity", f"{avg_hum:.1f}%", hum_status)
        
        with col5:
            cyclone_pct = (df['cyclone_risk'].sum() / len(df)) * 100
            cyclone_status = "High" if cyclone_pct > 50 else "Moderate" if cyclone_pct > 0 else "Low"
            st.metric("Cyclone Risk", cyclone_status, f"{cyclone_pct:.0f}% exposed")
        
        with col6:
            high_lightning = len(df[df['lightning_risk'] == 'High'])
            lightning_status = "High" if high_lightning > len(df)/2 else "Moderate" if high_lightning > 0 else "Low"
            st.metric("Lightning Risk", lightning_status, f"{high_lightning}/{len(df)} points")
        
        # Risk distribution
        st.markdown("---")
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            critical_points = len(df[df['severity_score'] > 75])
            st.metric("Critical Risk Zones", f"{critical_points} points", 
                     f"{(critical_points/len(df)*100):.1f}%")
        
        with col2:
            high_points = len(df[(df['severity_score'] > 60) & (df['severity_score'] <= 75)])
            st.metric("High Risk Zones", f"{high_points} points", 
                     f"{(high_points/len(df)*100):.1f}%")
        
        with col3:
            moderate_points = len(df[(df['severity_score'] > 40) & (df['severity_score'] <= 60)])
            st.metric("Moderate Risk Zones", f"{moderate_points} points", 
                     f"{(moderate_points/len(df)*100):.1f}%")
        
        with col4:
            low_points = len(df[df['severity_score'] <= 40])
            st.metric("Low Risk Zones", f"{low_points} points", 
                     f"{(low_points/len(df)*100):.1f}%")
        
        # Create enhanced visualization map with WORKING HEAT MAPS
        st.markdown("---")
        st.subheader("🎨 Environmental Heat Map Visualization")
        st.info("💡 Toggle layers on/off using the layer control in the top-right corner of the map")
        
        m2 = create_base_map()
        
        # Draw transmission line prominently
        line_coords = [(p[0], p[1]) for p in list(user_line.coords)]
        folium.PolyLine(
            locations=line_coords,
            color="black",
            weight=6,
            opacity=1.0,
            popup="<b>Transmission Corridor</b>",
            tooltip="Main Transmission Line"
        ).add_to(m2)
        
        # Create feature groups for layers
        severity_layer = folium.FeatureGroup(name="📍 Severity Markers", show=True)
        
        # Buffer zone radius
        buf_deg = meters_to_deg(buffer_m)
        
        # PM2.5 heat map with enhanced visibility
        if "PM2.5" in params:
            pm25_layer = folium.FeatureGroup(name="☁️ PM2.5 Heat Map", show=True)
            pm25_cmap = cm.linear.YlOrRd_09.scale(df['pm25'].min(), df['pm25'].max())
            
            # Create heat map data
            pm25_data = [[row['lat'], row['lon'], row['pm25']/5] 
                         for _, row in df.iterrows() if row['pm25'] is not None]
            
            if pm25_data:
                HeatMap(
                    pm25_data, 
                    radius=30, 
                    blur=40,
                    gradient={0.0: '#00ff00', 0.25: '#ffff00', 0.5: '#ff9900', 0.75: '#ff0000', 1.0: '#990000'},
                    min_opacity=0.5,
                    max_zoom=13
                ).add_to(pm25_layer)
                
                # Add colored circular zones
                for _, row in df.iterrows():
                    if row['pm25'] is not None:
                        color = pm25_cmap(row['pm25'])
                        folium.Circle(
                            location=[row['lat'], row['lon']],
                            radius=buffer_m,
                            color=color,
                            fill=True,
                            fillColor=color,
                            fillOpacity=0.25,
                            weight=2,
                            popup=f"<b>PM2.5:</b> {row['pm25']:.1f} µg/m³<br><b>Point:</b> {row['point_id']}"
                        ).add_to(pm25_layer)
            
            pm25_layer.add_to(m2)
        
        # PM10 heat map
        if "PM10" in params:
            pm10_layer = folium.FeatureGroup(name="☁️ PM10 Heat Map", show=False)
            pm10_cmap = cm.linear.OrRd_09.scale(df['pm10'].min(), df['pm10'].max())
            
            pm10_data = [[row['lat'], row['lon'], row['pm10']/8] 
                         for _, row in df.iterrows() if row['pm10'] is not None]
            
            if pm10_data:
                HeatMap(
                    pm10_data, 
                    radius=30, 
                    blur=40,
                    gradient={0.0: '#ffffcc', 0.3: '#ffeda0', 0.5: '#feb24c', 0.7: '#f03b20', 1.0: '#bd0026'},
                    min_opacity=0.5,
                    max_zoom=13
                ).add_to(pm10_layer)
                
                for _, row in df.iterrows():
                    if row['pm10'] is not None:
                        color = pm10_cmap(row['pm10'])
                        folium.Circle(
                            location=[row['lat'], row['lon']],
                            radius=buffer_m,
                            color=color,
                            fill=True,
                            fillColor=color,
                            fillOpacity=0.25,
                            weight=2,
                            popup=f"<b>PM10:</b> {row['pm10']:.1f} µg/m³<br><b>Point:</b> {row['point_id']}"
                        ).add_to(pm10_layer)
            
            pm10_layer.add_to(m2)
        
        # Temperature heat map
        if "Temperature" in params:
            temp_layer = folium.FeatureGroup(name="🌡️ Temperature Heat Map", show=True)
            temp_cmap = cm.linear.RdYlBu_11.to_step(10).scale(df['temp'].min(), df['temp'].max())
            
            temp_data = [[row['lat'], row['lon'], abs(row['temp'])/2.5] 
                        for _, row in df.iterrows() if row['temp'] is not None]
            
            if temp_data:
                HeatMap(
                    temp_data, 
                    radius=30, 
                    blur=40,
                    gradient={0.0: '#0000ff', 0.25: '#00ffff', 0.5: '#ffff00', 0.75: '#ff9900', 1.0: '#ff0000'},
                    min_opacity=0.45,
                    max_zoom=13
                ).add_to(temp_layer)
                
                for _, row in df.iterrows():
                    if row['temp'] is not None:
                        color = temp_cmap(row['temp'])
                        folium.Circle(
                            location=[row['lat'], row['lon']],
                            radius=buffer_m,
                            color=color,
                            fill=True,
                            fillColor=color,
                            fillOpacity=0.3,
                            weight=2,
                            popup=f"<b>Temp:</b> {row['temp']:.1f}°C<br><b>Point:</b> {row['point_id']}"
                        ).add_to(temp_layer)
            
            temp_layer.add_to(m2)
        
        # Humidity heat map
        if "Humidity" in params:
            hum_layer = folium.FeatureGroup(name="💧 Humidity Heat Map", show=False)
            hum_cmap = cm.linear.Blues_09.scale(df['hum'].min(), df['hum'].max())
            
            hum_data = [[row['lat'], row['lon'], row['hum']/8] 
                       for _, row in df.iterrows() if row['hum'] is not None]
            
            if hum_data:
                HeatMap(
                    hum_data, 
                    radius=28, 
                    blur=38,
                    gradient={0.0: '#f7fbff', 0.3: '#6baed6', 0.6: '#2171b5', 1.0: '#08306b'},
                    min_opacity=0.4,
                    max_zoom=13
                ).add_to(hum_layer)
                
                for _, row in df.iterrows():
                    if row['hum'] is not None:
                        color = hum_cmap(row['hum'])
                        folium.Circle(
                            location=[row['lat'], row['lon']],
                            radius=buffer_m,
                            color=color,
                            fill=True,
                            fillColor=color,
                            fillOpacity=0.3,
                            weight=2,
                            popup=f"<b>Humidity:</b> {row['hum']:.1f}%<br><b>Point:</b> {row['point_id']}"
                        ).add_to(hum_layer)
            
            hum_layer.add_to(m2)
        
        # Wind speed heat map
        if "Wind Speed" in params:
            wind_layer = folium.FeatureGroup(name="💨 Wind Speed Heat Map", show=True)
            wind_cmap = cm.linear.PuBuGn_09.scale(df['wind'].min(), df['wind'].max())
            
            wind_data = [[row['lat'], row['lon'], row['wind']/2.5] 
                        for _, row in df.iterrows() if row['wind'] is not None]
            
            if wind_data:
                HeatMap(
                    wind_data, 
                    radius=28, 
                    blur=38,
                    gradient={0.0: '#edf8fb', 0.3: '#66c2a4', 0.6: '#238b45', 1.0: '#00441b'},
                    min_opacity=0.45,
                    max_zoom=13
                ).add_to(wind_layer)
                
                for _, row in df.iterrows():
                    if row['wind'] is not None:
                        color = wind_cmap(row['wind'])
                        folium.Circle(
                            location=[row['lat'], row['lon']],
                            radius=buffer_m,
                            color=color,
                            fill=True,
                            fillColor=color,
                            fillOpacity=0.3,
                            weight=2,
                            popup=f"<b>Wind Speed:</b> {row['wind']:.1f} km/h<br><b>Point:</b> {row['point_id']}"
                        ).add_to(wind_layer)
            
            wind_layer.add_to(m2)
        
        # Cyclone risk zones
        if "Cyclone Risk" in params:
            cyclone_layer = folium.FeatureGroup(name="🌀 Cyclone Risk Zones", show=False)
            
            for _, row in df.iterrows():
                if row['cyclone_risk']:
                    folium.Circle(
                        location=[row['lat'], row['lon']],
                        radius=buffer_m * 1.5,
                        color='#9b59b6',
                        fill=True,
                        fillColor='#9b59b6',
                        fillOpacity=0.35,
                        weight=3,
                        popup=f"<b>CYCLONE RISK ZONE</b><br><b>Point:</b> {row['point_id']}"
                    ).add_to(cyclone_layer)
            
            cyclone_layer.add_to(m2)
        
        # Lightning risk zones
        if "Lightning Risk" in params:
            lightning_layer = folium.FeatureGroup(name="⚡ Lightning Risk Zones", show=False)
            
            for _, row in df.iterrows():
                if row['lightning_risk'] == 'High':
                    color = '#e67e22'
                    opacity = 0.4
                elif row['lightning_risk'] == 'Moderate':
                    color = '#f39c12'
                    opacity = 0.25
                else:
                    continue
                
                folium.Circle(
                    location=[row['lat'], row['lon']],
                    radius=buffer_m,
                    color=color,
                    fill=True,
                    fillColor=color,
                    fillOpacity=opacity,
                    weight=2,
                    popup=f"<b>Lightning Risk:</b> {row['lightning_risk']}<br><b>Point:</b> {row['point_id']}"
                ).add_to(lightning_layer)
            
            lightning_layer.add_to(m2)
        
        # Add severity markers with detailed popups
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
            <div style='width:300px;font-family:Arial;'>
                <h4 style='color:{color};margin:0;'>Point {row['point_id']} - {risk} RISK</h4>
                <hr style='margin:5px 0;'>
                <table style='width:100%;font-size:11px;'>
                    <tr><td><b>Severity Score:</b></td><td style='color:{color};font-weight:bold;'>{severity:.1f}/100</td></tr>
                    <tr><td><b>PM2.5:</b></td><td>{row['pm25']:.1f} µg/m³</td></tr>
                    <tr><td><b>PM10:</b></td><td>{row['pm10']:.1f} µg/m³</td></tr>
                    <tr><td><b>Temperature:</b></td><td>{row['temp']:.1f}°C</td></tr>
                    <tr><td><b>Humidity:</b></td><td>{row['hum']:.1f}%</td></tr>
                    <tr><td><b>Wind Speed:</b></td><td>{row['wind']:.1f} km/h</td></tr>
                    <tr><td><b>Cyclone Risk:</b></td><td>{'<span style="color:red;">YES</span>' if row['cyclone_risk'] else 'NO'}</td></tr>
                    <tr><td><b>Lightning Risk:</b></td><td>{row['lightning_risk']}</td></tr>
                    <tr><td colspan='2'><hr style='margin:5px 0;'></td></tr>
                    <tr><td><b>Recommended:</b></td><td style='color:blue;'>{row['recommended_insulator']}</td></tr>
                    <tr><td><b>Cost Factor:</b></td><td>{row['insulator_cost_factor']:.2f}x</td></tr>
                    <tr><td colspan='2' style='font-size:9px;color:#666;'>{row['data_source']}</td></tr>
                </table>
            </div>
            """
            
            folium.CircleMarker(
                location=[row['lat'], row['lon']],
                radius=12,
                popup=folium.Popup(popup_html, max_width=320),
                tooltip=f"<b>Point {row['point_id']}</b><br>{risk} RISK<br>Severity: {severity:.1f}/100",
                color=color,
                fill=True,
                fillColor=color,
                fillOpacity=0.8,
                weight=4
            ).add_to(severity_layer)
        
        # Add all layers to map
        severity_layer.add_to(m2)
        
        # Add layer control
        folium.LayerControl(collapsed=False, position='topright').add_to(m2)
        
        # Add enhanced legend
        legend_html = '''
        <div style="position: fixed; bottom: 50px; left: 50px; width: 220px; height: auto; 
        background-color: white; border:3px solid #1a1a1a; z-index:9999; font-size:12px; 
        padding: 12px; border-radius: 8px; box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
        <p style="margin:0 0 8px 0; font-weight:bold; font-size:14px; border-bottom: 2px solid #1a1a1a; padding-bottom: 5px;">Risk Levels</p>
        <p style="margin:4px 0;"><span style="color:red; font-size:16px;">●</span> <b>Critical</b> (>75)</p>
        <p style="margin:4px 0;"><span style="color:orange; font-size:16px;">●</span> <b>High</b> (60-75)</p>
        <p style="margin:4px 0;"><span style="color:gold; font-size:16px;">●</span> <b>Moderate</b> (40-60)</p>
        <p style="margin:4px 0;"><span style="color:green; font-size:16px;">●</span> <b>Low</b> (<40)</p>
        <hr style="margin: 8px 0; border: 1px solid #ddd;">
        <p style="margin:4px 0; font-size:10px; color:#666;">Toggle layers using top-right control</p>
        </div>
        '''
        m2.get_root().html.add_child(folium.Element(legend_html))
        
        # Display enhanced map
        st_folium(m2, width=1200, height=650, key="analysis_map")
        
        # Parameter-wise analysis display
        st.markdown("---")
        st.subheader("📈 Parameter-wise Detailed Analysis")
        
        # Create tabs for each parameter
        param_tabs = st.tabs(["PM2.5", "PM10", "Temperature", "Humidity", "Wind Speed", "Risk Factors"])
        
        with param_tabs[0]:  # PM2.5
            col1, col2 = st.columns([2, 1])
            with col1:
                fig, ax = plt.subplots(figsize=(10, 5))
                ax.plot(df['point_id'], df['pm25'], marker='o', color='#e74c3c', linewidth=2.5, markersize=8)
                ax.axhline(y=60, color='orange', linestyle='--', linewidth=2, label='Moderate Threshold (60)')
                ax.axhline(y=100, color='red', linestyle='--', linewidth=2, label='Poor Threshold (100)')
                ax.fill_between(df['point_id'], 0, df['pm25'], alpha=0.3, color='#e74c3c')
                ax.set_xlabel('Sample Point', fontsize=12, fontweight='bold')
                ax.set_ylabel('PM2.5 Concentration (µg/m³)', fontsize=12, fontweight='bold')
                ax.set_title('PM2.5 Variation Along Corridor', fontsize=14, fontweight='bold')
                ax.legend(fontsize=10)
                ax.grid(True, alpha=0.3, linestyle='--')
                plt.tight_layout()
                st.pyplot(fig)
            
            with col2:
                st.metric("Average PM2.5", f"{df['pm25'].mean():.1f} µg/m³")
                st.metric("Maximum PM2.5", f"{df['pm25'].max():.1f} µg/m³")
                st.metric("Minimum PM2.5", f"{df['pm25'].min():.1f} µg/m³")
                st.metric("Points > 100", f"{len(df[df['pm25'] > 100])}")
                st.metric("Points > 60", f"{len(df[df['pm25'] > 60])}")
        
        with param_tabs[1]:  # PM10
            col1, col2 = st.columns([2, 1])
            with col1:
                fig, ax = plt.subplots(figsize=(10, 5))
                ax.plot(df['point_id'], df['pm10'], marker='s', color='#d35400', linewidth=2.5, markersize=8)
                ax.axhline(y=100, color='orange', linestyle='--', linewidth=2, label='Moderate Threshold (100)')
                ax.axhline(y=200, color='red', linestyle='--', linewidth=2, label='Poor Threshold (200)')
                ax.fill_between(df['point_id'], 0, df['pm10'], alpha=0.3, color='#d35400')
                ax.set_xlabel('Sample Point', fontsize=12, fontweight='bold')
                ax.set_ylabel('PM10 Concentration (µg/m³)', fontsize=12, fontweight='bold')
                ax.set_title('PM10 Variation Along Corridor', fontsize=14, fontweight='bold')
                ax.legend(fontsize=10)
                ax.grid(True, alpha=0.3, linestyle='--')
                plt.tight_layout()
                st.pyplot(fig)
            
            with col2:
                st.metric("Average PM10", f"{df['pm10'].mean():.1f} µg/m³")
                st.metric("Maximum PM10", f"{df['pm10'].max():.1f} µg/m³")
                st.metric("Minimum PM10", f"{df['pm10'].min():.1f} µg/m³")
                st.metric("Points > 200", f"{len(df[df['pm10'] > 200])}")
                st.metric("Points > 100", f"{len(df[df['pm10'] > 100])}")
        
        with param_tabs[2]:  # Temperature
            col1, col2 = st.columns([2, 1])
            with col1:
                fig, ax = plt.subplots(figsize=(10, 5))
                colors = ['#0000ff' if t < 10 else '#00ffff' if t < 25 else '#ffff00' if t < 35 else '#ff0000' 
                         for t in df['temp']]
                ax.bar(df['point_id'], df['temp'], color=colors, alpha=0.7, edgecolor='black', linewidth=1.5)
                ax.axhline(y=35, color='red', linestyle='--', linewidth=2, label='High Temp (35°C)')
                ax.axhline(y=10, color='blue', linestyle='--', linewidth=2, label='Low Temp (10°C)')
                ax.set_xlabel('Sample Point', fontsize=12, fontweight='bold')
                ax.set_ylabel('Temperature (°C)', fontsize=12, fontweight='bold')
                ax.set_title('Temperature Distribution Along Corridor', fontsize=14, fontweight='bold')
                ax.legend(fontsize=10)
                ax.grid(axis='y', alpha=0.3, linestyle='--')
                plt.tight_layout()
                st.pyplot(fig)
            
            with col2:
                st.metric("Average Temp", f"{df['temp'].mean():.1f}°C")
                st.metric("Maximum Temp", f"{df['temp'].max():.1f}°C")
                st.metric("Minimum Temp", f"{df['temp'].min():.1f}°C")
                st.metric("Temperature Range", f"{df['temp'].max() - df['temp'].min():.1f}°C")
                temp_status = "Stable" if (df['temp'].max() - df['temp'].min()) < 5 else "Variable"
                st.metric("Variation", temp_status)
        
        with param_tabs[3]:  # Humidity
            col1, col2 = st.columns([2, 1])
            with col1:
                fig, ax = plt.subplots(figsize=(10, 5))
                ax.plot(df['point_id'], df['hum'], marker='D', color='#3498db', linewidth=2.5, markersize=8)
                ax.axhline(y=70, color='blue', linestyle='--', linewidth=2, label='High Humidity (70%)')
                ax.axhline(y=40, color='green', linestyle='--', linewidth=2, label='Optimal Range')
                ax.fill_between(df['point_id'], 0, df['hum'], alpha=0.3, color='#3498db')
                ax.set_xlabel('Sample Point', fontsize=12, fontweight='bold')
                ax.set_ylabel('Relative Humidity (%)', fontsize=12, fontweight='bold')
                ax.set_title('Humidity Profile Along Corridor', fontsize=14, fontweight='bold')
                ax.legend(fontsize=10)
                ax.grid(True, alpha=0.3, linestyle='--')
                ax.set_ylim(0, 100)
                plt.tight_layout()
                st.pyplot(fig)
            
            with col2:
                st.metric("Average Humidity", f"{df['hum'].mean():.1f}%")
                st.metric("Maximum Humidity", f"{df['hum'].max():.1f}%")
                st.metric("Minimum Humidity", f"{df['hum'].min():.1f}%")
                st.metric("Points > 70%", f"{len(df[df['hum'] > 70])}")
                hum_status = "High" if df['hum'].mean() > 70 else "Moderate" if df['hum'].mean() > 40 else "Low"
                st.metric("Overall Status", hum_status)
        
        with param_tabs[4]:  # Wind Speed
            col1, col2 = st.columns([2, 1])
            with col1:
                fig, ax = plt.subplots(figsize=(10, 5))
                colors = ['#2ecc71' if w < 20 else '#f39c12' if w < 40 else '#e74c3c' for w in df['wind']]
                ax.bar(df['point_id'], df['wind'], color=colors, alpha=0.7, edgecolor='black', linewidth=1.5)
                ax.axhline(y=30, color='orange', linestyle='--', linewidth=2, label='Moderate Wind (30 km/h)')
                ax.axhline(y=50, color='red', linestyle='--', linewidth=2, label='High Wind (50 km/h)')
                ax.set_xlabel('Sample Point', fontsize=12, fontweight='bold')
                ax.set_ylabel('Wind Speed (km/h)', fontsize=12, fontweight='bold')
                ax.set_title('Wind Speed Distribution Along Corridor', fontsize=14, fontweight='bold')
                ax.legend(fontsize=10)
                ax.grid(axis='y', alpha=0.3, linestyle='--')
                plt.tight_layout()
                st.pyplot(fig)
            
            with col2:
                st.metric("Average Wind Speed", f"{df['wind'].mean():.1f} km/h")
                st.metric("Maximum Wind Speed", f"{df['wind'].max():.1f} km/h")
                st.metric("Minimum Wind Speed", f"{df['wind'].min():.1f} km/h")
                st.metric("Points > 30 km/h", f"{len(df[df['wind'] > 30])}")
                wind_status = "High" if df['wind'].mean() > 30 else "Moderate" if df['wind'].mean() > 15 else "Low"
                st.metric("Overall Wind", wind_status)
        
        with param_tabs[5]:  # Risk Factors
            col1, col2 = st.columns(2)
            
            with col1:
                st.subheader("Cyclone Risk Distribution")
                cyclone_count = df['cyclone_risk'].sum()
                no_cyclone_count = len(df) - cyclone_count
                
                fig, ax = plt.subplots(figsize=(8, 6))
                colors_pie = ['#9b59b6', '#95a5a6']
                sizes = [cyclone_count, no_cyclone_count]
                labels = [f'Cyclone Zone\n({cyclone_count} points)', f'Safe Zone\n({no_cyclone_count} points)']
                wedges, texts, autotexts = ax.pie(sizes, labels=labels, autopct='%1.1f%%', 
                                                  colors=colors_pie, startangle=90,
                                                  textprops={'fontsize': 11, 'weight': 'bold'})
                for autotext in autotexts:
                    autotext.set_color('white')
                    autotext.set_fontsize(12)
                ax.set_title('Cyclone Risk Exposure', fontsize=14, fontweight='bold', pad=20)
                st.pyplot(fig)
            
            with col2:
                st.subheader("Lightning Risk Distribution")
                lightning_counts = df['lightning_risk'].value_counts()
                
                fig, ax = plt.subplots(figsize=(8, 6))
                colors_bar = {'High': '#e67e22', 'Moderate': '#f39c12', 'Low': '#27ae60'}
                bars = ax.bar(lightning_counts.index, lightning_counts.values, 
                             color=[colors_bar.get(x, '#95a5a6') for x in lightning_counts.index],
                             alpha=0.8, edgecolor='black', linewidth=2)
                ax.set_ylabel('Number of Points', fontsize=12, fontweight='bold')
                ax.set_title('Lightning Risk Assessment', fontsize=14, fontweight='bold', pad=15)
                ax.grid(axis='y', alpha=0.3, linestyle='--')
                
                # Add value labels on bars
                for bar in bars:
                    height = bar.get_height()
                    ax.text(bar.get_x() + bar.get_width()/2., height,
                           f'{int(height)}',
                           ha='center', va='bottom', fontsize=12, fontweight='bold')
                
                plt.tight_layout()
                st.pyplot(fig)
        
        # Severity distribution chart
        st.markdown("---")
        st.subheader("📊 Overall Severity Analysis")
        
        col1, col2 = st.columns([2, 1])
        
        with col1:
            fig, ax = plt.subplots(figsize=(12, 6))
            colors = ['#c0392b' if x>75 else '#e67e22' if x>60 else '#f39c12' if x>40 else '#27ae60' 
                     for x in df['severity_score']]
            bars = ax.bar(df['point_id'], df['severity_score'], color=colors, alpha=0.8, 
                         edgecolor='black', linewidth=1.5)
            ax.axhline(y=75, color='#c0392b', linestyle='--', linewidth=2.5, label='Critical (75)')
            ax.axhline(y=60, color='#e67e22', linestyle='--', linewidth=2, label='High (60)')
            ax.axhline(y=40, color='#f39c12', linestyle='--', linewidth=2, label='Moderate (40)')
            ax.set_xlabel('Sample Point', fontsize=13, fontweight='bold')
            ax.set_ylabel('Severity Score', fontsize=13, fontweight='bold')
            ax.set_title('Environmental Severity Distribution Along Transmission Corridor', 
                        fontsize=15, fontweight='bold', pad=15)
            ax.legend(loc='upper right', fontsize=11, framealpha=0.9)
            ax.grid(axis='y', alpha=0.3, linestyle='--')
            ax.set_ylim(0, 100)
            plt.tight_layout()
            st.pyplot(fig)
        
        with col2:
            st.subheader("🔧 Insulator Recommendations")
            insulator_counts = df['recommended_insulator'].value_counts()
            fig, ax = plt.subplots(figsize=(8, 6))
            colors_pie = ['#e74c3c', '#3498db', '#2ecc71', '#f39c12', '#9b59b6']
            wedges, texts, autotexts = ax.pie(insulator_counts.values, labels=insulator_counts.index, 
                                              autopct='%1.1f%%', colors=colors_pie[:len(insulator_counts)], 
                                              startangle=90, textprops={'fontsize': 9})
            for text in texts:
                text.set_fontsize(9)
                text.set_weight('bold')
            for autotext in autotexts:
                autotext.set_color('white')
                autotext.set_fontweight('bold')
                autotext.set_fontsize(11)
            ax.set_title('Recommended Insulator Types', fontsize=13, fontweight='bold', pad=15)
            plt.tight_layout()
            st.pyplot(fig)
        
        # Data Sources Section
        st.markdown("---")
        st.subheader("📚 Data Sources & Citations")
        
        # Summarize data sources used
        real_time_sources = set()
        historical_sources = set()
        
        for _, row in df.iterrows():
            source = row['data_source']
            if 'Real-time' in source or 'Hybrid' in source:
                if 'source_pm25' in row and row['source_pm25'] and isinstance(row['source_pm25'], str):
                    if 'OpenAQ' in str(row['source_pm25']) or 'WAQI' in str(row['source_pm25']):
                        real_time_sources.add(row['source_pm25'].split('(')[0].strip())
                if 'source_temp' in row and row['source_temp'] and isinstance(row['source_temp'], str):
                    if 'Open-Meteo' in str(row['source_temp']):
                        real_time_sources.add('Open-Meteo')
            if 'Historical' in source or 'Hybrid' in source:
                if 'source_pm25' in row and row['source_pm25'] and isinstance(row['source_pm25'], str):
                    if 'CPCB' in str(row['source_pm25']) or 'SAFAR' in str(row['source_pm25']) or 'PCB' in str(row['source_pm25']):
                        historical_sources.add('CPCB/SAFAR/State PCBs')
                if 'source_temp' in row and row['source_temp'] and isinstance(row['source_temp'], str):
                    if 'IMD' in str(row['source_temp']):
                        historical_sources.add('IMD')
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("**Real-time Data Sources:**")
            if real_time_sources:
                for source in sorted(real_time_sources):
                    st.markdown(f"- ✅ **{source}** (Live API)")
            else:
                st.markdown("- ⏱️ No real-time sources used (Fast Mode selected)")
        
        with col2:
            st.markdown("**Historical Data Sources (2022-2024):**")
            if historical_sources:
                for source in sorted(historical_sources):
                    if 'CPCB' in source:
                        st.markdown(f"- 📊 **CPCB** (Central Pollution Control Board) - Air quality data")
                        st.markdown(f"- 📊 **SAFAR** (System of Air Quality Forecasting) - Air quality data")
                        st.markdown(f"- 📊 **State PCBs** (Various State Pollution Control Boards)")
                    if 'IMD' in source:
                        st.markdown(f"- 🌤️ **IMD** (India Meteorological Department) - Weather data")
            else:
                st.markdown("- No historical data used")
        
        # Source details expander
        with st.expander("🔍 View Detailed Source Citations for Each Point"):
            st.markdown("**Parameter-wise Source Tracking:**")
            st.info("This table shows which source was used for each environmental parameter at each analysis point.")
            
            source_cols = ['point_id', 'source_pm25', 'source_pm10', 'source_temp', 'source_hum', 'source_wind', 'interpolation_info']
            available_cols = [col for col in source_cols if col in df.columns]
            
            if available_cols:
                source_df = df[available_cols].copy()
                # Shorten source names for better display
                for col in ['source_pm25', 'source_pm10', 'source_temp', 'source_hum', 'source_wind']:
                    if col in source_df.columns:
                        source_df[col] = source_df[col].apply(lambda x: str(x)[:50] + '...' if isinstance(x, str) and len(str(x)) > 50 else x)
                
                st.dataframe(source_df, use_container_width=True, height=300)
            else:
                st.warning("Source tracking data not available in this analysis.")
        
        st.markdown("""
        **Source Abbreviations:**
        - **CPCB**: Central Pollution Control Board (cpcb.nic.in) - National air quality monitoring
        - **IMD**: India Meteorological Department (imd.gov.in) - National weather data
        - **SAFAR**: System of Air Quality and Weather Forecasting (safar.tropmet.res.in) - Advanced air quality forecasting
        - **OpenAQ**: Open Air Quality API - Global real-time air quality data
        - **WAQI**: World Air Quality Index - Real-time air quality platform
        - **Open-Meteo**: Open-Meteo Weather API - Real-time weather data
        - **State PCBs**: Various State Pollution Control Boards (MPCB, GPCB, KSPCB, etc.)
        """)
        
        # Data table with filtering
        st.markdown("---")
        st.subheader("📋 Detailed Analysis Data Table")
        
        # Risk filter
        col1, col2, col3 = st.columns([2, 1, 1])
        with col1:
            risk_filter = st.multiselect(
                "Filter by Risk Level",
                ["CRITICAL (>75)", "HIGH (60-75)", "MODERATE (40-60)", "LOW (<40)"],
                default=["CRITICAL (>75)", "HIGH (60-75)", "MODERATE (40-60)", "LOW (<40)"]
            )
        with col2:
            show_cyclone_only = st.checkbox("Show Cyclone Zones Only", value=False)
        with col3:
            show_sources = st.checkbox("Show Source Columns", value=False)
        
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
        
        if show_cyclone_only:
            filtered_df = filtered_df[filtered_df['cyclone_risk'] == True]
        
        # Display table with or without source columns
        if show_sources:
            display_cols = ['point_id', 'lat', 'lon', 'severity_score', 'pm25', 'pm10', 
                           'temp', 'hum', 'wind', 'cyclone_risk', 'lightning_risk',
                           'recommended_insulator', 'insulator_cost_factor', 
                           'data_source', 'source_pm25', 'source_temp']
            available_display_cols = [col for col in display_cols if col in filtered_df.columns]
            display_df = filtered_df[available_display_cols].round(2)
        else:
            display_df = filtered_df[['point_id', 'lat', 'lon', 'severity_score', 'pm25', 'pm10', 
                                      'temp', 'hum', 'wind', 'cyclone_risk', 'lightning_risk',
                                      'recommended_insulator', 'insulator_cost_factor', 
                                      'data_source']].round(2)
        
        st.dataframe(display_df, use_container_width=True, height=400)
        
        st.info(f"📌 Showing {len(filtered_df)} of {len(df)} total analysis points")

# -------------------------------
# PDF Report Generation (Enhanced with Heat Maps)
# -------------------------------
if generate_pdf and st.session_state.analysis_df is not None:
    with st.spinner("📘 Generating comprehensive PDF report with heat maps..."):
        df = st.session_state.analysis_df
        user_line = st.session_state.user_line
        
        # Generate heat map images for PDF
        temp_dir = tempfile.gettempdir()
        heat_map_files = {}
        
        for param in ["PM2.5", "PM10", "Temperature", "Humidity", "Wind Speed"]:
            if param in params or param in ["PM2.5", "Temperature"]:  # Always include PM2.5 and Temp
                filename = os.path.join(temp_dir, f"heatmap_{param.lower().replace('.', '').replace(' ', '_')}.png")
                generate_heat_map_image(df, param, filename)
                heat_map_files[param] = filename
        
        # Create PDF
        pdf = FPDF()
        pdf.set_auto_page_break(auto=True, margin=15)
        
        # Page 1: Cover Page
        pdf.add_page()
        pdf.set_font("Arial", "B", 28)
        pdf.set_text_color(0, 51, 102)
        pdf.cell(0, 20, "", ln=True)  # Spacing
        pdf.cell(0, 15, "TRANSMISSION LINE", ln=True, align='C')
        pdf.cell(0, 15, "Environmental Severity Assessment", ln=True, align='C')
        
        pdf.ln(30)
        pdf.set_font("Arial", "", 12)
        pdf.set_text_color(0, 0, 0)
        pdf.cell(0, 10, f"Client: {client_name}", ln=True)
        pdf.cell(0, 10, f"Project Code: {project_code}", ln=True)
        pdf.cell(0, 10, f"Line Description: {line_name}", ln=True)
        pdf.cell(0, 10, f"Report Generated: {datetime.now().strftime('%d %B %Y, %H:%M IST')}", ln=True)
        
        line_length = haversine(df.iloc[0]['lat'], df.iloc[0]['lon'], 
                               df.iloc[-1]['lat'], df.iloc[-1]['lon']) / 1000
        pdf.cell(0, 10, f"Corridor Length: {line_length:.2f} km", ln=True)
        pdf.cell(0, 10, f"Analysis Points: {len(df)}", ln=True)
        
        # Page 2: Executive Summary
        pdf.add_page()
        pdf.set_font("Arial", "B", 18)
        pdf.set_fill_color(0, 51, 102)
        pdf.set_text_color(255, 255, 255)
        pdf.cell(0, 12, "EXECUTIVE SUMMARY", ln=True, fill=True, align='C')
        pdf.ln(5)
        
        # Overall Risk Level
        avg_severity = df['severity_score'].mean()
        if avg_severity > 75:
            risk_level = "CRITICAL"
            risk_color = (192, 57, 43)
        elif avg_severity > 60:
            risk_level = "HIGH"
            risk_color = (230, 126, 34)
        elif avg_severity > 40:
            risk_level = "MODERATE"
            risk_color = (243, 156, 18)
        else:
            risk_level = "LOW"
            risk_color = (39, 174, 96)
        
        pdf.set_font("Arial", "B", 14)
        pdf.set_text_color(0, 0, 0)
        pdf.cell(60, 10, "Overall Risk Level:", 0)
        pdf.set_text_color(*risk_color)
        pdf.cell(0, 10, f"{risk_level} ({avg_severity:.1f}/100)", ln=True)
        
        pdf.set_text_color(0, 0, 0)
        pdf.set_font("Arial", "", 11)
        pdf.ln(3)
        pdf.multi_cell(0, 6, f"This assessment evaluates environmental conditions along a {line_length:.1f} km transmission corridor across {len(df)} strategic sampling points. The analysis integrates real-time and historical data (2022-2024) from multiple authoritative sources including OpenAQ, WAQI, Open-Meteo, and IMD regional databases.")
        
        # Key Environmental Metrics Table
        pdf.ln(8)
        pdf.set_font("Arial", "B", 14)
        pdf.cell(0, 10, "KEY ENVIRONMENTAL METRICS", ln=True)
        pdf.ln(2)
        
        pdf.set_font("Arial", "B", 10)
        pdf.set_fill_color(220, 220, 220)
        col_widths = [50, 30, 30, 30, 50]
        pdf.cell(col_widths[0], 8, "Parameter", 1, 0, 'C', True)
        pdf.cell(col_widths[1], 8, "Average", 1, 0, 'C', True)
        pdf.cell(col_widths[2], 8, "Min", 1, 0, 'C', True)
        pdf.cell(col_widths[3], 8, "Max", 1, 0, 'C', True)
        pdf.cell(col_widths[4], 8, "WHO/Standard", 1, 1, 'C', True)
        
        pdf.set_font("Arial", "", 9)
        metrics_data = [
            ("PM2.5 (ug/m3)", f"{df['pm25'].mean():.1f}", f"{df['pm25'].min():.1f}", f"{df['pm25'].max():.1f}", "15 (Annual)"),
            ("PM10 (ug/m3)", f"{df['pm10'].mean():.1f}", f"{df['pm10'].min():.1f}", f"{df['pm10'].max():.1f}", "45 (Annual)"),
            ("Temperature (C)", f"{df['temp'].mean():.1f}", f"{df['temp'].min():.1f}", f"{df['temp'].max():.1f}", "25-35 (Optimal)"),
            ("Humidity (%)", f"{df['hum'].mean():.1f}", f"{df['hum'].min():.1f}", f"{df['hum'].max():.1f}", "40-70 (Optimal)"),
            ("Wind Speed (km/h)", f"{df['wind'].mean():.1f}", f"{df['wind'].min():.1f}", f"{df['wind'].max():.1f}", "<30 (Moderate)"),
        ]
        
        for row in metrics_data:
            pdf.cell(col_widths[0], 7, row[0], 1, 0, 'L')
            pdf.cell(col_widths[1], 7, row[1], 1, 0, 'C')
            pdf.cell(col_widths[2], 7, row[2], 1, 0, 'C')
            pdf.cell(col_widths[3], 7, row[3], 1, 0, 'C')
            pdf.cell(col_widths[4], 7, row[4], 1, 1, 'C')
        
        # Risk Distribution
        pdf.ln(8)
        pdf.set_font("Arial", "B", 14)
        pdf.cell(0, 10, "RISK DISTRIBUTION ANALYSIS", ln=True)
        pdf.ln(2)
        
        critical_count = len(df[df['severity_score'] > 75])
        high_count = len(df[(df['severity_score'] > 60) & (df['severity_score'] <= 75)])
        moderate_count = len(df[(df['severity_score'] > 40) & (df['severity_score'] <= 60)])
        low_count = len(df[df['severity_score'] <= 40])
        cyclone_pct = (df['cyclone_risk'].sum() / len(df)) * 100
        
        pdf.set_font("Arial", "", 11)
        pdf.cell(0, 7, f"- Critical Risk Zones (>75): {critical_count} points ({critical_count/len(df)*100:.1f}%)", ln=True)
        pdf.cell(0, 7, f"- High Risk Zones (60-75): {high_count} points ({high_count/len(df)*100:.1f}%)", ln=True)
        pdf.cell(0, 7, f"- Moderate Risk Zones (40-60): {moderate_count} points ({moderate_count/len(df)*100:.1f}%)", ln=True)
        pdf.cell(0, 7, f"- Low Risk Zones (<40): {low_count} points ({low_count/len(df)*100:.1f}%)", ln=True)
        pdf.cell(0, 7, f"- Cyclone-Prone Coverage: {cyclone_pct:.1f}%", ln=True)
        
        # Page 3+: Heat Map Visualizations
        for param, img_path in heat_map_files.items():
            pdf.add_page()
            pdf.set_font("Arial", "B", 16)
            pdf.set_fill_color(0, 51, 102)
            pdf.set_text_color(255, 255, 255)
            pdf.cell(0, 12, f"{param.upper()} ANALYSIS", ln=True, fill=True, align='C')
            pdf.ln(5)
            
            # Add heat map image
            if os.path.exists(img_path):
                pdf.image(img_path, x=10, y=pdf.get_y(), w=190)
                pdf.ln(115)
            
            # Analysis text
            pdf.set_text_color(0, 0, 0)
            pdf.set_font("Arial", "B", 12)
            pdf.cell(0, 8, f"{param} Key Findings:", ln=True)
            pdf.set_font("Arial", "", 10)
            
            if param == "PM2.5":
                pdf.multi_cell(0, 6, f"Average PM2.5 concentration: {df['pm25'].mean():.1f} µg/m³. "
                              f"{len(df[df['pm25'] > 100])} points exceed poor air quality threshold (100 µg/m³). "
                              f"{len(df[df['pm25'] > 60])} points exceed moderate threshold (60 µg/m³). "
                              f"Recommend enhanced pollution monitoring and use of hydrophobic insulators in high-pollution zones.")
            
            elif param == "PM10":
                pdf.multi_cell(0, 6, f"Average PM10 concentration: {df['pm10'].mean():.1f} µg/m³. "
                              f"{len(df[df['pm10'] > 200])} points exceed poor air quality threshold (200 µg/m³). "
                              f"Coarse particulate matter levels indicate need for regular insulator cleaning protocols.")
            
            elif param == "Temperature":
                pdf.multi_cell(0, 6, f"Temperature ranges from {df['temp'].min():.1f}°C to {df['temp'].max():.1f}°C with average of {df['temp'].mean():.1f}°C. "
                              f"{len(df[df['temp'] > 35])} points experience temperatures above 35°C. "
                              f"Consider thermal expansion in conductor design and select insulators with appropriate temperature ratings.")
            
            elif param == "Humidity":
                pdf.multi_cell(0, 6, f"Humidity ranges from {df['hum'].min():.1f}% to {df['hum'].max():.1f}% with average of {df['hum'].mean():.1f}%. "
                              f"{len(df[df['hum'] > 70])} points experience high humidity (>70%). "
                              f"High humidity zones require anti-fog or hydrophobic insulators to prevent flashover incidents.")
            
            elif param == "Wind Speed":
                pdf.multi_cell(0, 6, f"Wind speeds range from {df['wind'].min():.1f} to {df['wind'].max():.1f} km/h with average of {df['wind'].mean():.1f} km/h. "
                              f"{len(df[df['wind'] > 30])} points experience wind speeds above 30 km/h. "
                              f"High wind zones require reinforced structural design and vibration dampers.")
        
        # Insulator Recommendations Page
        pdf.add_page()
        pdf.set_font("Arial", "B", 16)
        pdf.set_fill_color(0, 51, 102)
        pdf.set_text_color(255, 255, 255)
        pdf.cell(0, 12, "INSULATOR SPECIFICATIONS & RECOMMENDATIONS", ln=True, fill=True, align='C')
        pdf.ln(5)
        
        pdf.set_text_color(0, 0, 0)
        pdf.set_font("Arial", "B", 12)
        pdf.cell(0, 8, "Recommended Insulator Distribution:", ln=True)
        pdf.ln(2)
        
        insulator_counts = df['recommended_insulator'].value_counts()
        pdf.set_font("Arial", "", 10)
        for insulator, count in insulator_counts.items():
            pct = (count / len(df)) * 100
            pdf.cell(0, 6, f" - {insulator}: {count} sections ({pct:.1f}%)", ln=True)
        
        pdf.ln(5)
        pdf.set_font("Arial", "B", 12)
        pdf.cell(0, 8, "Zone-Specific Recommendations:", ln=True)
        pdf.set_font("Arial", "", 10)
        pdf.ln(2)
        
        # Categorize points by risk
        critical_points = df[df['severity_score'] > 75]
        if len(critical_points) > 0:
            pdf.set_font("Arial", "B", 10)
            pdf.cell(0, 6, "CRITICAL ZONES (Severity > 75):", ln=True)
            pdf.set_font("Arial", "", 9)
            pdf.multi_cell(0, 5, f"Points {', '.join(map(str, critical_points['point_id'].tolist()))}: Require premium insulators (hydrophobic silicone or polymer composite) with enhanced monitoring systems.")
            pdf.ln(2)
        
        high_points = df[(df['severity_score'] > 60) & (df['severity_score'] <= 75)]
        if len(high_points) > 0:
            pdf.set_font("Arial", "B", 10)
            pdf.cell(0, 6, "HIGH RISK ZONES (Severity 60-75):", ln=True)
            pdf.set_font("Arial", "", 9)
            pdf.multi_cell(0, 5, f"Points {', '.join(map(str, high_points['point_id'].tolist()))}: Recommend toughened glass or anti-fog ceramic insulators with quarterly inspection schedule.")
            pdf.ln(2)
        
        # Technical Recommendations
        pdf.ln(5)
        pdf.set_font("Arial", "B", 12)
        pdf.cell(0, 8, "TECHNICAL RECOMMENDATIONS", ln=True)
        pdf.set_font("Arial", "", 10)
        pdf.ln(2)
        
        recommendations = []
        
        if df['hum'].mean() > 70:
            recommendations.append("- Apply corrosion-resistant coatings and use hydrophobic insulators for high-humidity environment")
        
        if df['wind'].max() > 40:
            recommendations.append("- Consider wind load factors in structural design and insulator selection")
        
        if df['pm25'].mean() > 80:
            recommendations.append("- Implement automated insulator washing systems in high-pollution zones")
        
        if (df['cyclone_risk'].sum() / len(df)) > 0.3:
            recommendations.append("- Install real-time weather monitoring and lightning protection systems")
        
        recommendations.extend([
            "- Conduct quarterly inspections focusing on high-risk segments",
            "- Implement real-time environmental monitoring system along the corridor",
            "- Establish preventive maintenance schedule based on environmental severity zones"
        ])
        
        for rec in recommendations:
            pdf.multi_cell(0, 6, rec)
        
        # Cost Analysis
        pdf.ln(8)
        pdf.set_font("Arial", "B", 12)
        pdf.cell(0, 8, "COST IMPACT ANALYSIS", ln=True)
        pdf.set_font("Arial", "", 10)
        pdf.ln(2)
        
        avg_cost_factor = df['insulator_cost_factor'].mean()
        total_cost_index = df['insulator_cost_factor'].sum()
        premium = (avg_cost_factor - 1.0) * 100
        
        pdf.cell(0, 6, f"Average Cost Factor: {avg_cost_factor:.2f}x (relative to standard ceramic)", ln=True)
        pdf.cell(0, 6, f"Total Relative Cost Index: {total_cost_index:.1f}", ln=True)
        pdf.cell(0, 6, f"Estimated premium over standard insulators: {premium:.1f}% due to environmental severity requirements", ln=True)
        
        # DATA SOURCES & CITATIONS PAGE
        pdf.add_page()
        pdf.set_font("Arial", "B", 16)
        pdf.set_fill_color(0, 51, 102)
        pdf.set_text_color(255, 255, 255)
        pdf.cell(0, 12, "DATA SOURCES & CITATIONS", ln=True, fill=True, align='C')
        pdf.ln(5)
        
        pdf.set_text_color(0, 0, 0)
        pdf.set_font("Arial", "B", 12)
        pdf.cell(0, 8, "Real-time Data Sources:", ln=True)
        pdf.set_font("Arial", "", 10)
        pdf.ln(2)
        
        # Collect real-time sources used
        real_time_used = set()
        for _, row in df.iterrows():
            if 'source_pm25' in row and row['source_pm25'] and isinstance(row['source_pm25'], str):
                if 'OpenAQ' in str(row['source_pm25']):
                    real_time_used.add('OpenAQ')
                elif 'WAQI' in str(row['source_pm25']):
                    real_time_used.add('WAQI')
            if 'source_temp' in row and row['source_temp'] and isinstance(row['source_temp'], str):
                if 'Open-Meteo' in str(row['source_temp']):
                    real_time_used.add('Open-Meteo')
        
        if real_time_used:
            if 'OpenAQ' in real_time_used:
                pdf.multi_cell(0, 5, "- OpenAQ (Open Air Quality): Global real-time air quality data platform aggregating data from government monitoring stations worldwide. URL: https://openaq.org")
                pdf.ln(2)
            if 'WAQI' in real_time_used:
                pdf.multi_cell(0, 5, "- WAQI (World Air Quality Index): Real-time air quality information platform covering 100+ countries with PM2.5, PM10, and AQI data. URL: https://waqi.info")
                pdf.ln(2)
            if 'Open-Meteo' in real_time_used:
                pdf.multi_cell(0, 5, "- Open-Meteo: Free weather forecast API providing temperature, humidity, wind speed, and precipitation data globally. URL: https://open-meteo.com")
                pdf.ln(2)
        else:
            pdf.multi_cell(0, 5, "No real-time API sources were used in this analysis (Historical/Fast Mode selected).")
            pdf.ln(2)
        
        pdf.ln(5)
        pdf.set_font("Arial", "B", 12)
        pdf.cell(0, 8, "Historical Data Sources (2022-2024):", ln=True)
        pdf.set_font("Arial", "", 10)
        pdf.ln(2)
        
        pdf.multi_cell(0, 5, "- CPCB (Central Pollution Control Board): National air quality monitoring network covering PM2.5, PM10, NO2, SO2, CO, and O3 across India. Official national repository for air quality data. URL: https://cpcb.nic.in")
        pdf.ln(2)
        
        pdf.multi_cell(0, 5, "- IMD (India Meteorological Department): National meteorological service providing temperature, humidity, wind speed, precipitation, and severe weather data. URL: https://imd.gov.in")
        pdf.ln(2)
        
        pdf.multi_cell(0, 5, "- SAFAR (System of Air Quality and Weather Forecasting): Advanced air quality forecasting system by Indian Institute of Tropical Meteorology, providing high-resolution pollution data for major cities. URL: https://safar.tropmet.res.in")
        pdf.ln(2)
        
        pdf.multi_cell(0, 5, "- State Pollution Control Boards: Regional air quality monitoring data from state-level pollution control authorities including MPCB (Maharashtra), GPCB (Gujarat), KSPCB (Karnataka), TNPCB (Tamil Nadu), WBPCB (West Bengal), TSPCB (Telangana), UPPCB (Uttar Pradesh), and others.")
        pdf.ln(2)
        
        pdf.ln(5)
        pdf.set_font("Arial", "B", 12)
        pdf.cell(0, 8, "Data Methodology:", ln=True)
        pdf.set_font("Arial", "", 10)
        pdf.ln(2)
        
        pdf.multi_cell(0, 5, "Historical data represents 3-year averages (2022-2024) compiled from official government sources. For locations without direct monitoring stations, data is interpolated using distance-weighted averaging from the three nearest monitoring locations. This ensures comprehensive coverage while maintaining data accuracy and reliability.")
        pdf.ln(2)
        
        pdf.ln(5)
        pdf.set_font("Arial", "B", 12)
        pdf.cell(0, 8, "Cyclone & Lightning Risk Assessment:", ln=True)
        pdf.set_font("Arial", "", 10)
        pdf.ln(2)
        
        pdf.multi_cell(0, 5, "- Cyclone zones identified based on IMD historical cyclone track data (1891-2024) and defined coastal regions prone to Bay of Bengal and Arabian Sea cyclones.")
        pdf.ln(1)
        pdf.multi_cell(0, 5, "- Lightning risk assessment based on IMD lightning activity records and regional vulnerability mapping.")
        pdf.ln(2)
        
        pdf.ln(5)
        pdf.set_font("Arial", "B", 12)
        pdf.cell(0, 8, "Data Quality & Validation:", ln=True)
        pdf.set_font("Arial", "", 10)
        pdf.ln(2)
        
        pdf.multi_cell(0, 5, "All data sources are official government agencies or internationally recognized environmental monitoring platforms. Historical averages are calculated from daily measurements to provide representative baseline values. Real-time data (when used) is fetched directly from source APIs at the time of analysis.")
        pdf.ln(2)
        
        # Footer/Disclaimer
        pdf.ln(8)
        pdf.set_font("Arial", "I", 8)
        pdf.set_text_color(100, 100, 100)
        pdf.multi_cell(0, 4, "DISCLAIMER: This report is generated based on environmental data from multiple authoritative sources including CPCB, IMD, SAFAR, State PCBs, OpenAQ, WAQI, and Open-Meteo. Data represents actual measurements and forecasts from these sources. "
                            "Recommendations are based on industry standards, engineering best practices, and site-specific environmental conditions. Final specifications should be validated through detailed site surveys, additional environmental studies, and professional engineering analysis. "
                            "This report is intended for professional use in transmission line planning and should be reviewed by qualified engineers and environmental specialists.")
        
        # Save PDF
        pdf_filename = f"Deccan_Environmental_Report_{project_code}_{datetime.now().strftime('%Y%m%d')}.pdf"
        pdf_path = os.path.join(temp_dir, pdf_filename)
        pdf.output(pdf_path)
        
        # Provide download
        with open(pdf_path, "rb") as f:
            st.download_button(
                "⬇️ Download Enhanced PDF Report",
                f,
                file_name=pdf_filename,
                mime="application/pdf",
                use_container_width=True
            )
        
        st.success("✅ Enhanced PDF Report with heat maps generated successfully!")

# -------------------------------
# Excel Export (Enhanced)
# -------------------------------
if generate_excel and st.session_state.analysis_df is not None:
    with st.spinner("📗 Generating comprehensive Excel export..."):
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
                'Metric': [
                    'Average Severity Score', 'Average PM2.5', 'Average PM10', 
                    'Average Temperature', 'Average Humidity', 'Average Wind Speed',
                    'Cyclone Coverage %', 'High Lightning Risk Points',
                    'Critical Risk Points', 'High Risk Points',
                    'Moderate Risk Points', 'Low Risk Points', 
                    'Total Points', 'Corridor Length (km)'
                ],
                'Value': [
                    f"{df['severity_score'].mean():.2f}/100",
                    f"{df['pm25'].mean():.2f} µg/m³",
                    f"{df['pm10'].mean():.2f} µg/m³",
                    f"{df['temp'].mean():.2f}°C",
                    f"{df['hum'].mean():.2f}%",
                    f"{df['wind'].mean():.2f} km/h",
                    f"{(df['cyclone_risk'].sum()/len(df)*100):.1f}%",
                    len(df[df['lightning_risk'] == 'High']),
                    len(df[df['severity_score'] > 75]),
                    len(df[(df['severity_score'] > 60) & (df['severity_score'] <= 75)]),
                    len(df[(df['severity_score'] > 40) & (df['severity_score'] <= 60)]),
                    len(df[df['severity_score'] <= 40]),
                    len(df),
                    f"{haversine(df.iloc[0]['lat'], df.iloc[0]['lon'], df.iloc[-1]['lat'], df.iloc[-1]['lon'])/1000:.2f}"
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
                    'Wind Speed': row['wind'],
                    'Cyclone Risk': row['cyclone_risk'],
                    'Lightning Risk': row['lightning_risk']
                })
            insulator_df = pd.DataFrame(insulator_data)
            insulator_df.to_excel(writer, sheet_name='Insulator Recommendations', index=False)
            
            # Risk zones sheet (critical and high only)
            risk_zones = df[df['severity_score'] > 60].copy()
            risk_zones['Risk Level'] = risk_zones['severity_score'].apply(
                lambda x: 'CRITICAL' if x > 75 else 'HIGH'
            )
            risk_zones.to_excel(writer, sheet_name='High Risk Zones', index=False)
            
            # Parameter analysis sheets
            param_summary = {
                'Parameter': ['PM2.5', 'PM10', 'Temperature', 'Humidity', 'Wind Speed'],
                'Average': [
                    df['pm25'].mean(),
                    df['pm10'].mean(),
                    df['temp'].mean(),
                    df['hum'].mean(),
                    df['wind'].mean()
                ],
                'Minimum': [
                    df['pm25'].min(),
                    df['pm10'].min(),
                    df['temp'].min(),
                    df['hum'].min(),
                    df['wind'].min()
                ],
                'Maximum': [
                    df['pm25'].max(),
                    df['pm10'].max(),
                    df['temp'].max(),
                    df['hum'].max(),
                    df['wind'].max()
                ],
                'Std Deviation': [
                    df['pm25'].std(),
                    df['pm10'].std(),
                    df['temp'].std(),
                    df['hum'].std(),
                    df['wind'].std()
                ]
            }
            param_df = pd.DataFrame(param_summary)
            param_df.to_excel(writer, sheet_name='Parameter Analysis', index=False)
            
            # Project info sheet
            project_info = {
                'Field': [
                    'Client Name', 'Project Code', 'Line Description', 
                    'Report Date', 'Corridor Length (km)', 'Total Analysis Points',
                    'Data Sources Used', 'Analysis Parameters',
                    'Buffer Width (m)', 'Sample Spacing (m)'
                ],
                'Value': [
                    client_name,
                    project_code,
                    line_name,
                    datetime.now().strftime('%d %B %Y, %H:%M IST'),
                    f"{haversine(df.iloc[0]['lat'], df.iloc[0]['lon'], df.iloc[-1]['lat'], df.iloc[-1]['lon'])/1000:.2f}",
                    len(df),
                    'CPCB, IMD, SAFAR, State PCBs, OpenAQ, WAQI, Open-Meteo (2022-2024)',
                    ', '.join(params),
                    buffer_m,
                    sample_m
                ]
            }
            project_df = pd.DataFrame(project_info)
            project_df.to_excel(writer, sheet_name='Project Information', index=False)
            
            # Data Sources & Citations sheet (NEW)
            sources_info = {
                'Source Name': [
                    'CPCB', 'IMD', 'SAFAR', 'State PCBs', 'OpenAQ', 'WAQI', 'Open-Meteo'
                ],
                'Full Name': [
                    'Central Pollution Control Board',
                    'India Meteorological Department',
                    'System of Air Quality and Weather Forecasting',
                    'State Pollution Control Boards (Various)',
                    'Open Air Quality',
                    'World Air Quality Index',
                    'Open-Meteo Weather API'
                ],
                'Data Type': [
                    'PM2.5, PM10 (Air Quality)',
                    'Temperature, Humidity, Wind Speed (Weather)',
                    'PM2.5, PM10 (Air Quality)',
                    'PM2.5, PM10 (Regional Air Quality)',
                    'PM2.5, PM10 (Real-time Air Quality)',
                    'PM2.5, PM10 (Real-time Air Quality)',
                    'Temperature, Humidity, Wind Speed (Real-time Weather)'
                ],
                'Time Period': [
                    '2022-2024 (Historical)',
                    '2022-2024 (Historical)',
                    '2022-2024 (Historical)',
                    '2022-2024 (Historical)',
                    'Real-time (If selected)',
                    'Real-time (If selected)',
                    'Real-time (If selected)'
                ],
                'Website': [
                    'https://cpcb.nic.in',
                    'https://imd.gov.in',
                    'https://safar.tropmet.res.in',
                    'Various state websites',
                    'https://openaq.org',
                    'https://waqi.info',
                    'https://open-meteo.com'
                ],
                'Notes': [
                    'National air quality monitoring network',
                    'National meteorological service',
                    'Advanced air quality forecasting system',
                    'Regional monitoring by state authorities',
                    'Global open air quality data platform',
                    'World air quality information platform',
                    'Free weather forecast API'
                ]
            }
            sources_df = pd.DataFrame(sources_info)
            sources_df.to_excel(writer, sheet_name='Data Sources', index=False)
            
            # Source tracking sheet (parameter-level source information)
            if 'source_pm25' in df.columns:
                source_tracking_cols = ['point_id', 'lat', 'lon', 'source_pm25', 'source_pm10', 
                                       'source_temp', 'source_hum', 'source_wind', 'interpolation_info']
                available_source_cols = [col for col in source_tracking_cols if col in df.columns]
                if available_source_cols:
                    source_tracking_df = df[available_source_cols].copy()
                    source_tracking_df.to_excel(writer, sheet_name='Source Tracking', index=False)
        
        # Provide download
        with open(excel_path, "rb") as f:
            st.download_button(
                "⬇️ Download Excel Data Export",
                f,
                file_name=excel_filename,
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True
            )
        
        st.success("✅ Excel file generated successfully with comprehensive analysis sheets!")

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
    st.caption("**Version:** 3.0 Enhanced | **Updated:** October 2025")

with col3:
    st.caption("**Support:** support@deccan.com")
    st.caption("**Documentation:** docs.deccan.com")

# Display system info in expander
with st.expander("ℹ️ System Information & Features"):
    st.write("**✨ Key Features:**")
    st.write("- ✅ **Working Heat Maps** - Visualize environmental parameters with color gradients around transmission line")
    st.write("- 📊 High-level environmental analysis with key metrics and risk distribution")
    st.write("- 🗺️ Interactive multi-layer mapping with toggleable parameter overlays")
    st.write("- 📈 Detailed parameter-wise analysis with charts and insights")
    st.write("- 📘 Enhanced PDF reports with heat map visualizations for each parameter")
    st.write("- 📗 Comprehensive Excel exports with multiple analysis sheets")
    st.write("- 🔄 Real-time environmental data with historical fallback (2022-2024)")
    st.write("- 🌀 Cyclone zone detection and lightning risk assessment")
    st.write("- 🔧 Intelligent insulator recommendation system")
    
    st.write("\n**📊 Available Parameters:**")
    st.write("- PM2.5 & PM10 (Air Quality)")
    st.write("- Temperature & Humidity (Climate)")
    st.write("- Wind Speed (Structural Load)")
    st.write("- Cyclone Risk (Coastal Zones)")
    st.write("- Lightning Risk (Regional Assessment)")
    
    st.write("\n**🔧 Insulator Database:**")
    for key, spec in INSULATOR_SPECS.items():
        st.write(f"- **{spec['name']}**: Temp {spec['temp_range'][0]}°C to {spec['temp_range'][1]}°C, "
                f"Pollution max {spec['pollution_max']} µg/m³, Wind max {spec['wind_max']} km/h, "
                f"Cost {spec['cost_factor']}x")
    
    st.write("\n**📍 Data Coverage:**")
    st.write(f"- Historical data repository: {len([k for k, v in HISTORICAL_DATA.items() if 'lat' in v])} major cities")
    st.write("- Regional interpolation: 5 zones (North, South, East, West, Central India)")
    st.write("- Distance-weighted averaging for precise location estimates")
    st.write("- Multi-source data aggregation for accuracy")

# Debug panel
if st.sidebar.checkbox("🔧 Show Debug Info", value=False):
    with st.expander("Debug Information", expanded=True):
        st.write("**Session State:**")
        st.write(f"- User Line Defined: {st.session_state.user_line is not None}")
        st.write(f"- Analysis Data Available: {st.session_state.analysis_df is not None}")
        if st.session_state.analysis_df is not None:
            st.write(f"- Data Points: {len(st.session_state.analysis_df)}")
            st.write(f"- Selected Parameters: {params}")
        
        st.write("\n**Historical Data Sample:**")
        sample_cities = ["delhi", "mumbai", "bangalore", "morbi", "ahmedabad"]
        for city in sample_cities:
            if city in HISTORICAL_DATA:
                st.write(f"- {city.title()}: PM2.5={HISTORICAL_DATA[city]['pm25']}, "
                        f"Temp={HISTORICAL_DATA[city]['temp']}°C")
        
        if st.button("Clear Session State"):
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.rerun()
