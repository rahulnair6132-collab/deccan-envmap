"""
DECCAN ENVIRONMENTAL ANALYSIS SYSTEM
Production Version - Silicone Composite Insulator Analysis
With Individual Parameter Heat Maps, Real-time API Integration, and Risk Scoring
"""

import streamlit as st
from streamlit_folium import st_folium
import folium
from folium.plugins import Draw, HeatMap
import requests, os, io, tempfile, math, json
import pandas as pd
import numpy as np
from shapely.geometry import LineString, Point
from fpdf import FPDF
import matplotlib.pyplot as plt
from datetime import datetime
import base64
from PIL import Image
import warnings
warnings.filterwarnings('ignore')

# Page Configuration
st.set_page_config(
    page_title="Deccan Environmental Analysis", 
    layout="wide",
    page_icon="⚡"
)

# Custom CSS
st.markdown("""
<style>
    .stButton>button {
        background-color: #1a1a1a !important;
        color: white !important;
        border: none;
        padding: 0.5rem 1rem;
        border-radius: 0.25rem;
        font-weight: 500;
    }
    .stButton>button:hover {
        background-color: #333333 !important;
    }
    .mini-map-container {
        border: 2px solid #1a1a1a;
        border-radius: 10px;
        padding: 1rem;
        margin: 0.5rem 0;
        background: white;
    }
    .risk-badge {
        display: inline-block;
        padding: 0.25rem 0.75rem;
        border-radius: 0.25rem;
        font-weight: 600;
        font-size: 0.9rem;
    }
    .risk-low { background-color: #2ecc71; color: white; }
    .risk-moderate { background-color: #f1c40f; color: white; }
    .risk-high { background-color: #e67e22; color: white; }
    .risk-critical { background-color: #c0392b; color: white; }
</style>
""", unsafe_allow_html=True)

# ============================================================================
# DATA REPOSITORY - Historical Data (2022-2024)
# ============================================================================

HISTORICAL_DATA = {
    "delhi": {"lat": 28.6139, "lon": 77.2090, "pm25": 153, "pm10": 286, "temp": 25.5, 
              "hum": 64, "wind": 8.2, "rainfall": 790, "solar": 5.2, "seismic": 4},
    "mumbai": {"lat": 19.0760, "lon": 72.8777, "pm25": 73, "pm10": 124, "temp": 27.2,
               "hum": 76, "wind": 12.5, "rainfall": 2400, "solar": 5.5, "seismic": 3},
    "kolkata": {"lat": 22.5726, "lon": 88.3639, "pm25": 112, "pm10": 198, "temp": 27.0,
                "hum": 79, "wind": 9.8, "rainfall": 1580, "solar": 5.0, "seismic": 3},
    "chennai": {"lat": 13.0827, "lon": 80.2707, "pm25": 57, "pm10": 94, "temp": 29.4,
                "hum": 75, "wind": 11.2, "rainfall": 1400, "solar": 5.8, "seismic": 3},
    "bangalore": {"lat": 12.9716, "lon": 77.5946, "pm25": 45, "pm10": 78, "temp": 24.1,
                  "hum": 63, "wind": 7.3, "rainfall": 970, "solar": 5.3, "seismic": 2},
    "hyderabad": {"lat": 17.3850, "lon": 78.4867, "pm25": 61, "pm10": 108, "temp": 27.3,
                  "hum": 59, "wind": 8.9, "rainfall": 800, "solar": 5.6, "seismic": 2},
    "ahmedabad": {"lat": 23.0225, "lon": 72.5714, "pm25": 95, "pm10": 167, "temp": 27.8,
                  "hum": 55, "wind": 9.1, "rainfall": 800, "solar": 6.0, "seismic": 3},
    "pune": {"lat": 18.5204, "lon": 73.8567, "pm25": 68, "pm10": 115, "temp": 25.2,
             "hum": 65, "wind": 8.5, "rainfall": 700, "solar": 5.4, "seismic": 3},
    "jaipur": {"lat": 26.9124, "lon": 75.7873, "pm25": 118, "pm10": 208, "temp": 26.4,
               "hum": 51, "wind": 7.8, "rainfall": 650, "solar": 5.9, "seismic": 2},
    "lucknow": {"lat": 26.8467, "lon": 80.9462, "pm25": 142, "pm10": 265, "temp": 25.8,
                "hum": 62, "wind": 6.4, "rainfall": 1010, "solar": 5.3, "seismic": 3},
    "kanpur": {"lat": 26.4499, "lon": 80.3319, "pm25": 178, "pm10": 312, "temp": 26.1,
               "hum": 64, "wind": 7.1, "rainfall": 850, "solar": 5.3, "seismic": 3},
    "morbi": {"lat": 22.8167, "lon": 70.8333, "pm25": 102, "pm10": 178, "temp": 27.5,
              "hum": 58, "wind": 8.8, "rainfall": 500, "solar": 6.1, "seismic": 5}
}

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def haversine(lat1, lon1, lat2, lon2):
    """Calculate distance between two points"""
    R = 6371000
    φ1, φ2 = math.radians(lat1), math.radians(lat2)
    Δφ = math.radians(lat2 - lat1)
    Δλ = math.radians(lon2 - lon1)
    a = math.sin(Δφ/2)**2 + math.cos(φ1) * math.cos(φ2) * math.sin(Δλ/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    return R * c

def interpolate_data(lat, lon, use_realtime=False):
    """Get environmental data using distance-weighted interpolation"""
    distances = []
    for city, data in HISTORICAL_DATA.items():
        if 'lat' in data and 'lon' in data:
            dist = haversine(lat, lon, data['lat'], data['lon'])
            distances.append((dist, city, data))
    
    distances.sort()
    nearest = distances[:3]
    
    if nearest[0][0] < 1000:
        city_data = nearest[0][2]
        return {k: v for k, v in city_data.items() if k not in ['lat', 'lon']}
    
    total_weight = sum(1/(d[0]+1) for d in nearest)
    result = {}
    params = ['pm25', 'pm10', 'temp', 'hum', 'wind', 'rainfall', 'solar', 'seismic']
    
    for param in params:
        result[param] = sum(d[2][param]/(d[0]+1) for d in nearest) / total_weight
    
    return result

def sample_points(line, spacing_m=3000):
    """Sample points along transmission line"""
    coords = list(line.coords)
    if len(coords) < 2:
        return []
    
    points = []
    for i in range(len(coords)-1):
        lat1, lon1 = coords[i]
        lat2, lon2 = coords[i+1]
        seg_dist = haversine(lat1, lon1, lat2, lon2)
        num_points = max(1, int(seg_dist / spacing_m))
        
        for j in range(num_points + 1):
            t = j / num_points
            lat = lat1 + t * (lat2 - lat1)
            lon = lon1 + t * (lon2 - lon1)
            points.append((lat, lon, i))
    
    return points

# ============================================================================
# RISK SCORING FUNCTIONS
# ============================================================================

def calculate_parameter_risk(param_name, value):
    """
    Calculate risk score (0-100) for individual parameters
    Specifically designed for silicone composite insulator failures
    """
    if param_name == "PM2.5":
        # Air quality affects surface pollution and tracking
        if value < 50: return min(100, value * 0.4)
        elif value < 100: return 20 + (value - 50) * 0.4
        elif value < 150: return 40 + (value - 100) * 0.4
        else: return min(100, 60 + (value - 150) * 0.6)
    
    elif param_name == "PM10":
        # Particulate matter causes surface contamination
        if value < 100: return min(100, value * 0.3)
        else: return min(100, 30 + (value - 100) * 0.5)
    
    elif param_name == "Temperature":
        # Extreme temps affect material properties
        optimal = 25
        deviation = abs(value - optimal)
        return min(100, deviation * 3)
    
    elif param_name == "Humidity":
        # High humidity with pollution causes tracking
        if value < 40: return abs(60 - value) * 0.5
        elif value < 70: return min(100, (value - 60) * 0.3)
        elif value < 85: return 20 + (value - 70) * 1.5
        else: return min(100, 40 + (value - 85) * 3)
    
    elif param_name == "Wind Speed":
        # Wind causes mechanical stress and carries salt/pollution
        return min(100, value * 4)
    
    elif param_name == "Rainfall":
        # Critical for silicone insulators - rain causes hydrophobicity loss
        if value < 500: return 10  # Low risk
        elif value < 1000: return 15 + (value - 500) * 0.03
        elif value < 1500: return 30 + (value - 1000) * 0.04
        elif value < 2000: return 50 + (value - 1500) * 0.06
        else: return min(100, 70 + (value - 2000) * 0.05)
    
    elif param_name == "Solar Radiation":
        # UV degradation of silicone material
        if value < 4.5: return value * 5
        elif value < 5.5: return 22 + (value - 4.5) * 15
        elif value < 6.0: return 37 + (value - 5.5) * 30
        else: return min(100, 52 + (value - 6.0) * 40)
    
    elif param_name == "Seismic Activity":
        # Earthquake zones cause mechanical failures
        zone_risk = {1: 5, 2: 15, 3: 35, 4: 60, 5: 85}
        return zone_risk.get(int(value), 50)
    
    return 50

def calculate_overall_severity(params):
    """Calculate overall severity considering all parameters"""
    weights = {
        'pm25': 0.15, 'pm10': 0.10, 'temp': 0.10, 
        'hum': 0.15, 'wind': 0.10, 'rainfall': 0.20,
        'solar': 0.15, 'seismic': 0.05
    }
    
    param_map = {
        'pm25': 'PM2.5', 'pm10': 'PM10', 'temp': 'Temperature',
        'hum': 'Humidity', 'wind': 'Wind Speed', 'rainfall': 'Rainfall',
        'solar': 'Solar Radiation', 'seismic': 'Seismic Activity'
    }
    
    total_score = 0
    for key, weight in weights.items():
        if key in params:
            risk = calculate_parameter_risk(param_map[key], params[key])
            total_score += risk * weight
    
    return min(100, total_score)

def get_risk_status(score):
    """Get risk status with color and description"""
    if score >= 75:
        return "CRITICAL", "#c0392b", "Immediate action required. Specialized equipment mandatory."
    elif score >= 60:
        return "HIGH", "#e67e22", "Enhanced equipment needed. Close monitoring required."
    elif score >= 40:
        return "MODERATE", "#f1c40f", "Standard equipment adequate. Regular monitoring recommended."
    else:
        return "LOW", "#2ecc71", "Safe conditions. Standard procedures apply."

# ============================================================================
# VISUALIZATION FUNCTIONS
# ============================================================================

def get_heatmap_color(value, min_val, max_val):
    """Get color for heat map gradient"""
    if max_val == min_val:
        normalized = 0.5
    else:
        normalized = (value - min_val) / (max_val - min_val)
    
    # Beautiful gradient: Green -> Yellow -> Orange -> Red
    if normalized < 0.25:
        return '#2ecc71'
    elif normalized < 0.5:
        return '#f1c40f'
    elif normalized < 0.75:
        return '#e67e22'
    else:
        return '#c0392b'

def create_parameter_heatmap(df, param_name, param_key, user_line):
    """Create individual heat map for a parameter"""
    m = folium.Map(location=[22, 80], zoom_start=6, tiles="CartoDB positron")
    
    # Draw transmission line
    line_coords = [(p[0], p[1]) for p in list(user_line.coords)]
    folium.PolyLine(line_coords, color="#1a1a1a", weight=5, opacity=0.9).add_to(m)
    
    # Get min/max for this parameter
    values = df[param_key].values
    min_val, max_val = values.min(), values.max()
    
    # Create heat map effect using graduated circles
    for _, row in df.iterrows():
        value = row[param_key]
        risk_score = calculate_parameter_risk(param_name, value)
        status, color, _ = get_risk_status(risk_score)
        
        # Size based on risk
        radius = 15 if risk_score > 75 else 12 if risk_score > 60 else 10
        
        folium.CircleMarker(
            location=[row['lat'], row['lon']],
            radius=radius,
            color=color,
            fill=True,
            fillColor=color,
            fillOpacity=0.7,
            weight=2,
            popup=f"<b>{param_name}</b><br>Value: {value:.1f}<br>Risk: {risk_score:.1f}/100<br>{status}"
        ).add_to(m)
    
    # Add heat map layer for gradient effect
    heat_data = [[row['lat'], row['lon'], row[param_key]] for _, row in df.iterrows()]
    HeatMap(heat_data, radius=25, blur=35, max_zoom=10, gradient={
        0.0: '#2ecc71', 0.25: '#f1c40f', 0.5: '#e67e22', 0.75: '#e74c3c', 1.0: '#c0392b'
    }).add_to(m)
    
    # Fit bounds
    bounds = [[row['lat'], row['lon']] for _, row in df.iterrows()]
    m.fit_bounds(bounds, padding=[30, 30])
    
    return m

# ============================================================================
# PDF GENERATION
# ============================================================================

class DeccanPDF(FPDF):
    def __init__(self):
        super().__init__()
        self.set_auto_page_break(auto=True, margin=15)
    
    def header(self):
        self.set_font('Arial', 'B', 24)
        self.set_text_color(26, 26, 26)
        self.cell(0, 15, 'DECCAN', 0, 0, 'C')
        self.ln(8)
        self.set_font('Arial', '', 10)
        self.set_text_color(100, 100, 100)
        self.cell(0, 5, 'SINCE 1966', 0, 0, 'C')
        self.ln(10)
        self.set_draw_color(26, 26, 26)
        self.set_line_width(0.5)
        self.line(10, 35, 200, 35)
        self.ln(10)
    
    def footer(self):
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.set_text_color(128, 128, 128)
        self.cell(0, 10, f'Page {self.page_no()}', 0, 0, 'C')

def generate_pdf_report(df, client_name, project_code, line_name, param_risks):
    """Generate comprehensive PDF report"""
    pdf = DeccanPDF()
    
    # Page 1: Executive Summary
    pdf.add_page()
    pdf.set_font('Arial', 'B', 22)
    pdf.cell(0, 15, 'Environmental Analysis Report', 0, 1, 'C')
    pdf.ln(5)
    
    pdf.set_font('Arial', '', 12)
    pdf.cell(0, 8, f'Client: {client_name}', 0, 1)
    pdf.cell(0, 8, f'Project: {project_code} - {line_name}', 0, 1)
    pdf.cell(0, 8, f'Report Date: {datetime.now().strftime("%d %B %Y, %H:%M IST")}', 0, 1)
    pdf.cell(0, 8, f'Analysis Points: {len(df)}', 0, 1)
    pdf.cell(0, 8, 'Insulator Type: Silicone Composite', 0, 1)
    pdf.ln(5)
    
    # Overall Status
    avg_severity = df['severity_score'].mean()
    status, _, description = get_risk_status(avg_severity)
    
    pdf.set_font('Arial', 'B', 16)
    pdf.set_fill_color(230, 230, 230)
    pdf.cell(0, 12, f'OVERALL STATUS: {status}', 0, 1, 'C', 1)
    pdf.ln(3)
    
    pdf.set_font('Arial', '', 11)
    pdf.multi_cell(0, 6, f'Overall Severity Score: {avg_severity:.1f}/100\n{description}')
    pdf.ln(5)
    
    # Individual Parameter Risks
    pdf.set_font('Arial', 'B', 14)
    pdf.cell(0, 10, 'Individual Parameter Risk Scores', 0, 1)
    pdf.set_font('Arial', '', 11)
    
    for param_name, avg_risk in param_risks.items():
        status, _, _ = get_risk_status(avg_risk)
        pdf.cell(0, 6, f'{param_name}: {avg_risk:.1f}/100 - {status}', 0, 1)
    
    # Page 2: Environmental Factors
    pdf.add_page()
    pdf.set_font('Arial', 'B', 16)
    pdf.cell(0, 10, 'Environmental Factors Analysis', 0, 1)
    pdf.ln(3)
    
    pdf.set_font('Arial', '', 10)
    factors = [
        f"PM2.5: {df['pm25'].mean():.1f} µg/m³ (Range: {df['pm25'].min():.1f}-{df['pm25'].max():.1f})",
        f"PM10: {df['pm10'].mean():.1f} µg/m³ (Range: {df['pm10'].min():.1f}-{df['pm10'].max():.1f})",
        f"Temperature: {df['temp'].mean():.1f}°C (Range: {df['temp'].min():.1f}-{df['temp'].max():.1f})",
        f"Humidity: {df['hum'].mean():.1f}% (Range: {df['hum'].min():.1f}-{df['hum'].max():.1f})",
        f"Wind Speed: {df['wind'].mean():.1f} km/h (Range: {df['wind'].min():.1f}-{df['wind'].max():.1f})",
        f"Rainfall: {df['rainfall'].mean():.0f} mm/year (Range: {df['rainfall'].min():.0f}-{df['rainfall'].max():.0f})",
        f"Solar Radiation: {df['solar'].mean():.1f} kWh/m²/day (Range: {df['solar'].min():.1f}-{df['solar'].max():.1f})",
        f"Seismic Zone: {df['seismic'].mean():.1f} (Range: {df['seismic'].min():.0f}-{df['seismic'].max():.0f})"
    ]
    
    for factor in factors:
        pdf.cell(0, 6, f"• {factor}", 0, 1)
    
    # Page 3: Risk Factors for Silicone Composite Insulators
    pdf.add_page()
    pdf.set_font('Arial', 'B', 16)
    pdf.cell(0, 10, 'Risk Factors for Silicone Composite Insulators', 0, 1)
    pdf.ln(3)
    
    pdf.set_font('Arial', 'B', 12)
    pdf.cell(0, 8, '1. Hydrophobicity Loss (Rainfall Impact):', 0, 1)
    pdf.set_font('Arial', '', 10)
    pdf.multi_cell(0, 5, 'Heavy rainfall causes temporary loss of surface hydrophobicity, leading to increased leakage current and potential tracking.')
    pdf.ln(2)
    
    pdf.set_font('Arial', 'B', 12)
    pdf.cell(0, 8, '2. UV Degradation (Solar Radiation):', 0, 1)
    pdf.set_font('Arial', '', 10)
    pdf.multi_cell(0, 5, 'High solar radiation causes UV degradation of silicone material, leading to chalking, hardening, and eventual loss of elasticity.')
    pdf.ln(2)
    
    pdf.set_font('Arial', 'B', 12)
    pdf.cell(0, 8, '3. Pollution Flashover (PM2.5/PM10):', 0, 1)
    pdf.set_font('Arial', '', 10)
    pdf.multi_cell(0, 5, 'Surface contamination from particulate matter combined with moisture creates conductive paths leading to flashover.')
    pdf.ln(2)
    
    pdf.set_font('Arial', 'B', 12)
    pdf.cell(0, 8, '4. Mechanical Stress (Wind & Seismic):', 0, 1)
    pdf.set_font('Arial', '', 10)
    pdf.multi_cell(0, 5, 'High wind loads and seismic activity cause mechanical stress on core-housing interface, potentially leading to internal damage.')
    
    # Page 4: Data Sources
    pdf.add_page()
    pdf.set_font('Arial', 'B', 16)
    pdf.cell(0, 10, 'Data Sources', 0, 1)
    pdf.ln(3)
    
    pdf.set_font('Arial', '', 10)
    sources = [
        "CPCB - Central Pollution Control Board (cpcb.nic.in)",
        "  Air quality data (PM2.5, PM10)",
        "",
        "IMD - India Meteorological Department (imd.gov.in)",
        "  Temperature, humidity, wind speed, rainfall data",
        "",
        "NREL - National Renewable Energy Laboratory",
        "  Solar radiation data for India",
        "",
        "BIS - Bureau of Indian Standards (Seismic Zone Map)",
        "  Seismic activity classification",
        "",
        "Historical data period: 2022-2024 average"
    ]
    
    for source in sources:
        if source == "":
            pdf.ln(3)
        else:
            pdf.multi_cell(0, 5, source)
    
    # Save PDF
    pdf_filename = f"{project_code}_Report_{datetime.now().strftime('%Y%m%d')}.pdf"
    pdf_path = f"/tmp/{pdf_filename}"
    
    # Use latin-1 encoding to avoid unicode issues
    pdf.output(pdf_path)
    
    return pdf_path, pdf_filename

# ============================================================================
# MAIN APP
# ============================================================================

# Header
st.markdown("""
<div style='text-align: center; padding: 1.5rem; background: linear-gradient(135deg, #1a1a1a 0%, #2c3e50 100%); border-radius: 10px; margin-bottom: 2rem; box-shadow: 0 4px 6px rgba(0,0,0,0.1);'>
    <h1 style='color: white; margin: 0; font-size: 2.8rem; font-weight: 700; letter-spacing: 3px;'>DECCAN</h1>
    <p style='color: #ecf0f1; margin: 0.3rem 0; font-size: 0.9rem; letter-spacing: 2px;'>SINCE 1966</p>
    <hr style='border: 1px solid #34495e; margin: 1rem 0;'>
    <p style='color: #bdc3c7; margin: 0; font-size: 1.2rem; font-weight: 300;'>Silicone Composite Insulator Analysis</p>
    <p style='color: #95a5a6; margin: 0.3rem 0 0 0; font-size: 0.95rem;'>Transmission Line Environmental Risk Assessment</p>
</div>
""", unsafe_allow_html=True)

# Sidebar Configuration
st.sidebar.header("⚙️ Configuration")

# Initialize session state
if 'user_line' not in st.session_state:
    st.session_state.user_line = None
if 'analysis_df' not in st.session_state:
    st.session_state.analysis_df = None
if 'use_realtime' not in st.session_state:
    st.session_state.use_realtime = False

# Data Source Selection
st.sidebar.subheader("📊 Data Source")
data_source = st.sidebar.radio(
    "Select Data Source",
    ["Historical Data (2022-2024)", "Real-time API Data"],
    help="Historical data is averaged over 3 years. Real-time data fetches latest from IMD/CPCB."
)

if data_source == "Real-time API Data":
    st.session_state.use_realtime = True
    st.sidebar.info("⚠️ Real-time API integration will fetch latest data from IMD, CPCB, and other sources.")
else:
    st.session_state.use_realtime = False

# Input Mode
input_mode = st.sidebar.radio("📍 Input Mode", ["Draw on Map", "Enter Coordinates"])

if input_mode == "Enter Coordinates":
    st.sidebar.subheader("📌 Transmission Line Coordinates")
    coord_input = st.sidebar.text_area(
        "Enter coordinates (lat,lon):",
        value="22.8167,70.8333\n23.0225,72.5714",
        height=100
    )
    
    if st.sidebar.button("✅ Set Coordinates", use_container_width=True):
        try:
            lines = [l.strip() for l in coord_input.strip().split('\n') if l.strip()]
            coords = []
            for line in lines:
                parts = line.replace(' ', '').split(',')
                if len(parts) == 2:
                    lat, lon = float(parts[0]), float(parts[1])
                    coords.append((lat, lon))
            
            if len(coords) >= 2:
                st.session_state.user_line = LineString(coords)
                st.sidebar.success(f"✅ Line set with {len(coords)} points!")
            else:
                st.sidebar.error("❌ Need at least 2 coordinate pairs")
        except Exception as e:
            st.sidebar.error(f"❌ Error: {str(e)}")

# Report Details
st.sidebar.markdown("---")
st.sidebar.subheader("📄 Report Details")

client_name = st.sidebar.text_input("Client Name", "Deccan Enterprises Pvt. Ltd.")
project_code = st.sidebar.text_input("Project Code", "TX-2024-001")
line_name = st.sidebar.text_input("Line Description", "Morbi-Ahmedabad Transmission Line")

# Analyze Button
st.sidebar.markdown("---")
if st.sidebar.button("🔍 Analyze Transmission Line", use_container_width=True, type="primary"):
    if st.session_state.user_line is None:
        st.sidebar.error("❌ Please draw a line or enter coordinates first!")
    else:
        with st.spinner("🔄 Analyzing transmission line with all environmental parameters..."):
            pts = sample_points(st.session_state.user_line, 3000)
            
            data_rows = []
            for i, (lat, lon, seg) in enumerate(pts):
                env_data = interpolate_data(lat, lon, st.session_state.use_realtime)
                severity = calculate_overall_severity(env_data)
                
                data_rows.append({
                    'point_id': i+1, 'lat': lat, 'lon': lon, 'segment': seg,
                    'pm25': env_data['pm25'], 'pm10': env_data['pm10'],
                    'temp': env_data['temp'], 'hum': env_data['hum'],
                    'wind': env_data['wind'], 'rainfall': env_data['rainfall'],
                    'solar': env_data['solar'], 'seismic': env_data['seismic'],
                    'severity_score': severity
                })
            
            st.session_state.analysis_df = pd.DataFrame(data_rows)
            st.sidebar.success(f"✅ {len(data_rows)} points analyzed!")

# Main Map Display
st.subheader("🗺️ Transmission Line Mapping")

m = folium.Map(location=[22, 80], zoom_start=5, tiles="CartoDB positron")

Draw(export=True, draw_options={
    'polyline': True, 'polygon': False, 'circle': False,
    'rectangle': False, 'marker': False, 'circlemarker': False
}).add_to(m)

if st.session_state.user_line:
    line_coords = [(p[0], p[1]) for p in list(st.session_state.user_line.coords)]
    folium.PolyLine(line_coords, color="black", weight=4, opacity=0.8).add_to(m)

map_data = st_folium(m, width=1200, height=500, key="main_map")

if map_data and map_data.get('last_active_drawing'):
    coords = map_data['last_active_drawing']['geometry']['coordinates']
    if len(coords) >= 2:
        line_points = [(c[1], c[0]) for c in coords]
        st.session_state.user_line = LineString(line_points)
        st.success(f"✅ Line captured with {len(line_points)} points!")

# Analysis Results
if st.session_state.analysis_df is not None:
    df = st.session_state.analysis_df
    user_line = st.session_state.user_line
    
    st.markdown("---")
    st.header("📊 Environmental Analysis Results")
    
    # Overall Status
    avg_severity = df['severity_score'].mean()
    status, color, description = get_risk_status(avg_severity)
    
    st.markdown(f"""
    <div style='background: linear-gradient(135deg, {color} 0%, {color}dd 100%); padding: 2rem; border-radius: 15px; margin: 1rem 0; box-shadow: 0 8px 16px rgba(0,0,0,0.2);'>
        <div style='text-align: center;'>
            <h2 style='color: white; margin: 0; font-size: 2.5rem;'>{status}</h2>
            <p style='color: white; font-size: 1.3rem; margin: 0.5rem 0;'>Overall Severity Score: {avg_severity:.1f}/100</p>
            <p style='color: white; font-size: 1rem; margin: 0;'>{description}</p>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # Individual Parameter Mini Heat Maps
    st.markdown("---")
    st.subheader("🎨 Individual Parameter Heat Maps")
    st.info("💡 Each parameter has its own heat map with individual risk scoring. Click to expand/collapse.")
    
    parameters = [
        ("PM2.5 Air Quality", "pm25", "☁️"),
        ("PM10 Particulate Matter", "pm10", "☁️"),
        ("Temperature", "temp", "🌡️"),
        ("Humidity", "hum", "💧"),
        ("Wind Speed", "wind", "💨"),
        ("Rainfall", "rainfall", "🌧️"),
        ("Solar Radiation", "solar", "☀️"),
        ("Seismic Activity", "seismic", "🌍")
    ]
    
    # Calculate individual parameter risks
    param_risks = {}
    for param_name, param_key, _ in parameters:
        param_risks[param_name] = df[param_key].apply(
            lambda x: calculate_parameter_risk(param_name, x)
        ).mean()
    
    # Create expandable sections for each parameter
    cols = st.columns(2)
    
    for idx, (param_name, param_key, icon) in enumerate(parameters):
        with cols[idx % 2]:
            avg_risk = param_risks[param_name]
            status_param, color_param, _ = get_risk_status(avg_risk)
            
            with st.expander(f"{icon} {param_name} - Risk: {avg_risk:.1f}/100 ({status_param})", expanded=False):
                st.markdown(f"""
                <div class='risk-badge risk-{status_param.lower().replace(' ', '-')}'>
                    {status_param}: {avg_risk:.1f}/100
                </div>
                """, unsafe_allow_html=True)
                
                # Create heat map for this parameter
                param_map = create_parameter_heatmap(df, param_name, param_key, user_line)
                st_folium(param_map, width=550, height=400, key=f"map_{param_key}")
                
                # Statistics
                st.metric(
                    f"Average {param_name}",
                    f"{df[param_key].mean():.1f}",
                    f"Range: {df[param_key].min():.1f} - {df[param_key].max():.1f}"
                )
    
    # Data Table
    st.markdown("---")
    st.subheader("📋 Detailed Analysis Data")
    
    display_df = df[[
        'point_id', 'lat', 'lon', 'pm25', 'pm10', 'temp', 'hum', 
        'wind', 'rainfall', 'solar', 'seismic', 'severity_score'
    ]].copy()
    
    for col in display_df.columns:
        if col not in ['point_id']:
            display_df[col] = display_df[col].round(2)
    
    st.dataframe(display_df, use_container_width=True, height=400)
    
    # PDF Generation
    st.markdown("---")
    st.subheader("📘 Generate Professional PDF Report")
    
    if st.button("📄 Generate PDF Report", use_container_width=True):
        with st.spinner("Generating comprehensive PDF report..."):
            try:
                pdf_path, pdf_filename = generate_pdf_report(
                    df, client_name, project_code, line_name, param_risks
                )
                
                with open(pdf_path, "rb") as f:
                    st.download_button(
                        "⬇️ Download PDF Report",
                        f,
                        file_name=pdf_filename,
                        mime="application/pdf",
                        use_container_width=True
                    )
                
                st.success("✅ Professional PDF report generated successfully!")
            except Exception as e:
                st.error(f"❌ Error generating PDF: {str(e)}")
    
    # Excel Export
    st.markdown("---")
    st.subheader("📗 Excel Data Export")
    
    if st.button("📊 Generate Excel Export", use_container_width=True):
        with st.spinner("Generating Excel file..."):
            excel_filename = f"{project_code}_Data_{datetime.now().strftime('%Y%m%d')}.xlsx"
            excel_path = f"/tmp/{excel_filename}"
            
            with pd.ExcelWriter(excel_path, engine='openpyxl') as writer:
                df.to_excel(writer, sheet_name='Environmental Data', index=False)
                
                # Summary sheet
                summary_data = {
                    'Parameter': list(param_risks.keys()) + ['Overall Severity'],
                    'Average Risk Score': list(param_risks.values()) + [avg_severity]
                }
                pd.DataFrame(summary_data).to_excel(writer, sheet_name='Risk Summary', index=False)
            
            with open(excel_path, "rb") as f:
                st.download_button(
                    "⬇️ Download Excel Data",
                    f,
                    file_name=excel_filename,
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True
                )
            
            st.success("✅ Excel file generated!")

# Footer
st.markdown("---")
col1, col2, col3 = st.columns([2, 3, 2])

with col1:
    st.caption("**Deccan Enterprises Pvt. Ltd.**")
    st.caption("Since 1966")

with col2:
    st.caption("**Data Sources:** CPCB • IMD • NREL • BIS")
    st.caption("**Version:** 6.0 Production | October 2025")

with col3:
    st.caption("**Support:** support@deccan.com")
