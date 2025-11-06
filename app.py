import streamlit as st
import folium
from folium import plugins
from streamlit_folium import st_folium
import pandas as pd
import numpy as np
from datetime import datetime
import requests
import json
from shapely.geometry import Point, LineString
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use('Agg')
from io import BytesIO
from PIL import Image
import base64
import os
from fpdf import FPDF
import tempfile
import math

# Page configuration
st.set_page_config(
    page_title="Deccan Environmental Analysis",
    page_icon="🗺️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1e3a8a;
        text-align: center;
        margin-bottom: 0.5rem;
    }
    .sub-header {
        font-size: 1.2rem;
        color: #64748b;
        text-align: center;
        margin-bottom: 2rem;
    }
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1.5rem;
        border-radius: 0.5rem;
        color: white;
        margin: 0.5rem 0;
    }
    .risk-critical { background: linear-gradient(135deg, #dc2626 0%, #991b1b 100%); }
    .risk-high { background: linear-gradient(135deg, #ea580c 0%, #c2410c 100%); }
    .risk-moderate { background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%); }
    .risk-low { background: linear-gradient(135deg, #10b981 0%, #059669 100%); }
    
    .stExpander {
        border: 2px solid #e5e7eb;
        border-radius: 0.5rem;
        margin: 0.5rem 0;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
if 'transmission_lines' not in st.session_state:
    st.session_state.transmission_lines = []
if 'analysis_complete' not in st.session_state:
    st.session_state.analysis_complete = False
if 'analysis_results' not in st.session_state:
    st.session_state.analysis_results = {}
if 'drawn_lines' not in st.session_state:
    st.session_state.drawn_lines = []

# Helper function to calculate distance to coast
def get_distance_to_coast(lat, lon):
    """Calculate approximate distance to nearest coast in km"""
    # Major Indian coastline points (simplified)
    coast_points = [
        # West coast
        (8.0883, 77.5385), (10.8505, 76.2711), (12.9716, 77.5946), 
        (15.2993, 74.1240), (18.5204, 73.8567), (21.1458, 72.8347),
        (22.3072, 68.9692), (23.0225, 69.6693),
        # East coast
        (8.5241, 76.9366), (11.9416, 79.8083), (13.0827, 80.2707),
        (15.8281, 80.2707), (17.6868, 83.2185), (20.9517, 85.0985),
        # Andaman & Nicobar
        (11.7401, 92.6586), (13.0827, 93.0570),
        # Bay islands
        (19.0760, 72.8777), (8.2904, 77.7542)
    ]
    
    min_distance = float('inf')
    point = Point(lon, lat)
    
    for coast_lat, coast_lon in coast_points:
        coast_point = Point(coast_lon, coast_lat)
        # Haversine distance approximation
        distance = math.sqrt((lat - coast_lat)**2 + (lon - coast_lon)**2) * 111  # km
        min_distance = min(min_distance, distance)
    
    return min_distance

# PDF Generation Class
class DeccanPDF(FPDF):
    def __init__(self):
        super().__init__()
        self.set_auto_page_break(auto=True, margin=15)
    
    def header(self):
        # Add logo if available
        logo_path = "deccan_logo.png"
        if os.path.exists(logo_path):
            try:
                self.image(logo_path, x=10, y=8, w=50)
            except:
                pass
        
        # Header line
        self.set_draw_color(0, 51, 102)
        self.set_line_width(0.8)
        self.line(10, 25, 200, 25)
        self.ln(10)
    
    def footer(self):
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.set_text_color(128, 128, 128)
        self.cell(0, 10, f'Page {self.page_no()}', 0, 0, 'C')
    
    def chapter_title(self, title):
        self.set_font('Arial', 'B', 16)
        self.set_fill_color(0, 51, 102)
        self.set_text_color(255, 255, 255)
        self.cell(0, 10, title, 0, 1, 'L', 1)
        self.ln(4)
    
    def section_title(self, title):
        self.set_font('Arial', 'B', 12)
        self.set_text_color(0, 51, 102)
        self.cell(0, 8, title, 0, 1)
        self.set_text_color(0, 0, 0)
        self.ln(2)

def generate_professional_pdf(line_name, analysis, client_name, project_code, circle_radius, sample_spacing):
    """Generate professional PDF report"""
    
    pdf = DeccanPDF()
    df = analysis['dataframe']
    line_data = analysis['line_data']
    
    # Calculate corridor length
    coords = [[p['lat'], p['lon']] for p in line_data]
    line = LineString([(lon, lat) for lat, lon in coords])
    corridor_length = line.length * 111  # Approximate km
    
    # PAGE 1: COVER PAGE
    pdf.add_page()
    pdf.ln(30)
    
    # Title
    pdf.set_font('Arial', 'B', 28)
    pdf.set_text_color(0, 51, 102)
    pdf.cell(0, 15, 'TRANSMISSION LINE', 0, 1, 'C')
    pdf.set_font('Arial', 'B', 22)
    pdf.cell(0, 12, 'Environmental Risk Assessment', 0, 1, 'C')
    pdf.ln(15)
    
    # Project info box
    pdf.set_fill_color(240, 240, 240)
    pdf.set_font('Arial', 'B', 11)
    pdf.set_text_color(0, 51, 102)
    pdf.cell(0, 8, 'PROJECT INFORMATION', 0, 1, 'L', 1)
    
    pdf.set_font('Arial', '', 11)
    pdf.set_text_color(0, 0, 0)
    pdf.ln(3)
    
    info_items = [
        ('Client:', client_name),
        ('Project Code:', project_code),
        ('Line Description:', line_name),
        ('Report Generated:', datetime.now().strftime('%d %B %Y, %H:%M IST')),
        ('Analysis Points:', str(len(df))),
        ('Corridor Length:', f'{corridor_length:.2f} km'),
        ('Data Source:', 'IMD (India Meteorological Department)'),
        ('Data Period:', '2015-2024 (10 Years - Maximum Values)'),
        ('Circle Radius:', f'{circle_radius} km'),
        ('Sample Spacing:', f'{sample_spacing} km')
    ]
    
    for label, value in info_items:
        pdf.set_font('Arial', 'B', 10)
        pdf.cell(60, 6, label, 0, 0)
        pdf.set_font('Arial', '', 10)
        pdf.cell(0, 6, value, 0, 1)
    
    pdf.ln(10)
    
    # Overall risk status
    overall_risk = analysis['overall_risk']
    if overall_risk >= 75:
        fill_color = (192, 57, 43)
        status = "CRITICAL"
    elif overall_risk >= 60:
        fill_color = (230, 126, 34)
        status = "HIGH"
    elif overall_risk >= 40:
        fill_color = (241, 196, 15)
        status = "MODERATE"
    else:
        fill_color = (46, 204, 113)
        status = "LOW"
    
    pdf.set_fill_color(*fill_color)
    pdf.set_text_color(255, 255, 255)
    pdf.set_font('Arial', 'B', 18)
    pdf.cell(0, 12, f'OVERALL STATUS: {status}', 0, 1, 'C', 1)
    pdf.set_text_color(0, 0, 0)
    pdf.ln(3)
    
    pdf.set_font('Arial', '', 11)
    pdf.cell(0, 6, f'Overall Severity Score: {overall_risk:.1f}/100', 0, 1, 'C')
    pdf.ln(5)
    
    pdf.set_font('Arial', 'I', 9)
    pdf.set_text_color(100, 100, 100)
    pdf.multi_cell(0, 5, 'This assessment is based on IMD historical maximum values observed over 10 years (2015-2024). All parameters represent extreme conditions that equipment must withstand.')
    
    # PAGE 2: EXECUTIVE SUMMARY
    pdf.add_page()
    pdf.chapter_title('EXECUTIVE SUMMARY')
    
    pdf.set_font('Arial', '', 10)
    summary_text = f"This comprehensive assessment evaluates environmental conditions along a {corridor_length:.2f} km transmission corridor across {len(df)} strategic sampling points. The analysis uses IMD (India Meteorological Department) historical data spanning 10 years (2015-2024), focusing on maximum observed values to ensure equipment specifications account for worst-case scenarios."
    pdf.multi_cell(0, 5, summary_text)
    pdf.ln(5)
    
    # Risk distribution
    pdf.section_title('RISK DISTRIBUTION ANALYSIS')
    
    risk_scores = [analysis['temp_risk'], analysis['rainfall_risk'], analysis['humidity_risk'],
                   analysis['wind_risk'], analysis['solar_risk'], analysis['salinity_risk'],
                   analysis['seismic_risk']]
    
    critical = sum(1 for s in risk_scores if s >= 75)
    high = sum(1 for s in risk_scores if 60 <= s < 75)
    moderate = sum(1 for s in risk_scores if 40 <= s < 60)
    low = sum(1 for s in risk_scores if s < 40)
    total = len(risk_scores)
    
    pdf.set_font('Arial', '', 10)
    pdf.cell(0, 6, f'- Critical Risk Zones (>75): {critical} parameters ({critical/total*100:.1f}%)', 0, 1)
    pdf.cell(0, 6, f'- High Risk Zones (60-75): {high} parameters ({high/total*100:.1f}%)', 0, 1)
    pdf.cell(0, 6, f'- Moderate Risk Zones (40-60): {moderate} parameters ({moderate/total*100:.1f}%)', 0, 1)
    pdf.cell(0, 6, f'- Low Risk Zones (<40): {low} parameters ({low/total*100:.1f}%)', 0, 1)
    pdf.ln(5)
    
    # Key metrics table
    pdf.section_title('KEY ENVIRONMENTAL METRICS')
    
    # Table header
    pdf.set_fill_color(0, 51, 102)
    pdf.set_text_color(255, 255, 255)
    pdf.set_font('Arial', 'B', 9)
    pdf.cell(45, 8, 'Parameter', 1, 0, 'C', 1)
    pdf.cell(30, 8, 'Average', 1, 0, 'C', 1)
    pdf.cell(30, 8, 'Min', 1, 0, 'C', 1)
    pdf.cell(30, 8, 'Max', 1, 0, 'C', 1)
    pdf.cell(35, 8, 'Risk Score', 1, 1, 'C', 1)
    
    # Table data
    pdf.set_text_color(0, 0, 0)
    pdf.set_font('Arial', '', 9)
    
    metrics_data = [
        ('Temperature (C)', df['temp_max'].mean(), df['temp_max'].min(), df['temp_max'].max(), analysis['temp_risk']),
        ('Rainfall (mm)', df['rainfall_max'].mean(), df['rainfall_max'].min(), df['rainfall_max'].max(), analysis['rainfall_risk']),
        ('Humidity (%)', df['humidity_max'].mean(), df['humidity_max'].min(), df['humidity_max'].max(), analysis['humidity_risk']),
        ('Wind Speed (km/h)', df['wind_max'].mean(), df['wind_max'].min(), df['wind_max'].max(), analysis['wind_risk']),
        ('Solar (kWh/m2/day)', df['solar_max'].mean(), df['solar_max'].min(), df['solar_max'].max(), analysis['solar_risk']),
        ('Salinity (ppm)', df['salinity_max'].mean(), df['salinity_max'].min(), df['salinity_max'].max(), analysis['salinity_risk']),
        ('Seismic Zone', df['seismic_zone'].mean(), df['seismic_zone'].min(), df['seismic_zone'].max(), analysis['seismic_risk'])
    ]
    
    for row in metrics_data:
        pdf.cell(45, 7, row[0], 1)
        pdf.cell(30, 7, f'{row[1]:.1f}', 1, 0, 'C')
        pdf.cell(30, 7, f'{row[2]:.1f}', 1, 0, 'C')
        pdf.cell(30, 7, f'{row[3]:.1f}', 1, 0, 'C')
        pdf.cell(35, 7, f'{row[4]:.1f}/100', 1, 1, 'C')
    
    # PAGE 3: DETAILED ANALYSIS
    pdf.add_page()
    pdf.chapter_title('DETAILED PARAMETER ANALYSIS')
    
    # Temperature
    pdf.section_title('Temperature')
    pdf.set_font('Arial', 'B', 10)
    if analysis['temp_risk'] >= 75:
        pdf.set_text_color(192, 57, 43)
        pdf.cell(0, 6, f'Risk Score: {analysis["temp_risk"]:.1f}/100 (CRITICAL)', 0, 1)
    elif analysis['temp_risk'] >= 60:
        pdf.set_text_color(230, 126, 34)
        pdf.cell(0, 6, f'Risk Score: {analysis["temp_risk"]:.1f}/100 (HIGH)', 0, 1)
    elif analysis['temp_risk'] >= 40:
        pdf.set_text_color(241, 196, 15)
        pdf.cell(0, 6, f'Risk Score: {analysis["temp_risk"]:.1f}/100 (MODERATE)', 0, 1)
    else:
        pdf.set_text_color(46, 204, 113)
        pdf.cell(0, 6, f'Risk Score: {analysis["temp_risk"]:.1f}/100 (LOW)', 0, 1)
    
    pdf.set_text_color(0, 0, 0)
    pdf.set_font('Arial', '', 9)
    pdf.cell(50, 5, '  Maximum Value:', 0, 0)
    pdf.cell(0, 5, f'{df["temp_max"].max():.1f} C', 0, 1)
    pdf.cell(50, 5, '  Minimum Value:', 0, 0)
    pdf.cell(0, 5, f'{df["temp_max"].min():.1f} C', 0, 1)
    pdf.cell(50, 5, '  Average Value:', 0, 0)
    pdf.cell(0, 5, f'{df["temp_max"].mean():.1f} C', 0, 1)
    pdf.cell(50, 5, '  Frequency:', 0, 0)
    pdf.cell(0, 5, '~45 days/year (10-year average)', 0, 1)
    pdf.ln(3)
    
    # Rainfall
    pdf.section_title('Rainfall')
    pdf.set_font('Arial', 'B', 10)
    if analysis['rainfall_risk'] >= 75:
        pdf.set_text_color(192, 57, 43)
        pdf.cell(0, 6, f'Risk Score: {analysis["rainfall_risk"]:.1f}/100 (CRITICAL)', 0, 1)
    elif analysis['rainfall_risk'] >= 60:
        pdf.set_text_color(230, 126, 34)
        pdf.cell(0, 6, f'Risk Score: {analysis["rainfall_risk"]:.1f}/100 (HIGH)', 0, 1)
    elif analysis['rainfall_risk'] >= 40:
        pdf.set_text_color(241, 196, 15)
        pdf.cell(0, 6, f'Risk Score: {analysis["rainfall_risk"]:.1f}/100 (MODERATE)', 0, 1)
    else:
        pdf.set_text_color(46, 204, 113)
        pdf.cell(0, 6, f'Risk Score: {analysis["rainfall_risk"]:.1f}/100 (LOW)', 0, 1)
    
    pdf.set_text_color(0, 0, 0)
    pdf.set_font('Arial', '', 9)
    pdf.cell(50, 5, '  Maximum Value:', 0, 0)
    pdf.cell(0, 5, f'{df["rainfall_max"].max():.1f} mm', 0, 1)
    pdf.cell(50, 5, '  Minimum Value:', 0, 0)
    pdf.cell(0, 5, f'{df["rainfall_max"].min():.1f} mm', 0, 1)
    pdf.cell(50, 5, '  Average Value:', 0, 0)
    pdf.cell(0, 5, f'{df["rainfall_max"].mean():.1f} mm', 0, 1)
    pdf.cell(50, 5, '  Frequency:', 0, 0)
    pdf.cell(0, 5, '~13 days/year (10-year average)', 0, 1)
    pdf.ln(3)
    
    # Humidity
    pdf.section_title('Humidity')
    pdf.set_font('Arial', 'B', 10)
    if analysis['humidity_risk'] >= 75:
        pdf.set_text_color(192, 57, 43)
        pdf.cell(0, 6, f'Risk Score: {analysis["humidity_risk"]:.1f}/100 (CRITICAL)', 0, 1)
    elif analysis['humidity_risk'] >= 60:
        pdf.set_text_color(230, 126, 34)
        pdf.cell(0, 6, f'Risk Score: {analysis["humidity_risk"]:.1f}/100 (HIGH)', 0, 1)
    elif analysis['humidity_risk'] >= 40:
        pdf.set_text_color(241, 196, 15)
        pdf.cell(0, 6, f'Risk Score: {analysis["humidity_risk"]:.1f}/100 (MODERATE)', 0, 1)
    else:
        pdf.set_text_color(46, 204, 113)
        pdf.cell(0, 6, f'Risk Score: {analysis["humidity_risk"]:.1f}/100 (LOW)', 0, 1)
    
    pdf.set_text_color(0, 0, 0)
    pdf.set_font('Arial', '', 9)
    pdf.cell(50, 5, '  Maximum Value:', 0, 0)
    pdf.cell(0, 5, f'{df["humidity_max"].max():.1f} %', 0, 1)
    pdf.cell(50, 5, '  Minimum Value:', 0, 0)
    pdf.cell(0, 5, f'{df["humidity_max"].min():.1f} %', 0, 1)
    pdf.cell(50, 5, '  Average Value:', 0, 0)
    pdf.cell(0, 5, f'{df["humidity_max"].mean():.1f} %', 0, 1)
    pdf.cell(50, 5, '  Frequency:', 0, 0)
    pdf.cell(0, 5, '~151 days/year (10-year average)', 0, 1)
    pdf.ln(3)
    
    # Wind Speed
    pdf.section_title('Wind Speed')
    pdf.set_font('Arial', 'B', 10)
    if analysis['wind_risk'] >= 75:
        pdf.set_text_color(192, 57, 43)
        pdf.cell(0, 6, f'Risk Score: {analysis["wind_risk"]:.1f}/100 (CRITICAL)', 0, 1)
    elif analysis['wind_risk'] >= 60:
        pdf.set_text_color(230, 126, 34)
        pdf.cell(0, 6, f'Risk Score: {analysis["wind_risk"]:.1f}/100 (HIGH)', 0, 1)
    elif analysis['wind_risk'] >= 40:
        pdf.set_text_color(241, 196, 15)
        pdf.cell(0, 6, f'Risk Score: {analysis["wind_risk"]:.1f}/100 (MODERATE)', 0, 1)
    else:
        pdf.set_text_color(46, 204, 113)
        pdf.cell(0, 6, f'Risk Score: {analysis["wind_risk"]:.1f}/100 (LOW)', 0, 1)
    
    pdf.set_text_color(0, 0, 0)
    pdf.set_font('Arial', '', 9)
    pdf.cell(50, 5, '  Maximum Value:', 0, 0)
    pdf.cell(0, 5, f'{df["wind_max"].max():.1f} km/h', 0, 1)
    pdf.cell(50, 5, '  Minimum Value:', 0, 0)
    pdf.cell(0, 5, f'{df["wind_max"].min():.1f} km/h', 0, 1)
    pdf.cell(50, 5, '  Average Value:', 0, 0)
    pdf.cell(0, 5, f'{df["wind_max"].mean():.1f} km/h', 0, 1)
    pdf.cell(50, 5, '  Frequency:', 0, 0)
    pdf.cell(0, 5, '~62 days/year (10-year average)', 0, 1)
    pdf.ln(3)
    
    # Solar Radiation
    pdf.section_title('Solar Radiation')
    pdf.set_font('Arial', 'B', 10)
    if analysis['solar_risk'] >= 75:
        pdf.set_text_color(192, 57, 43)
        pdf.cell(0, 6, f'Risk Score: {analysis["solar_risk"]:.1f}/100 (CRITICAL)', 0, 1)
    elif analysis['solar_risk'] >= 60:
        pdf.set_text_color(230, 126, 34)
        pdf.cell(0, 6, f'Risk Score: {analysis["solar_risk"]:.1f}/100 (HIGH)', 0, 1)
    elif analysis['solar_risk'] >= 40:
        pdf.set_text_color(241, 196, 15)
        pdf.cell(0, 6, f'Risk Score: {analysis["solar_risk"]:.1f}/100 (MODERATE)', 0, 1)
    else:
        pdf.set_text_color(46, 204, 113)
        pdf.cell(0, 6, f'Risk Score: {analysis["solar_risk"]:.1f}/100 (LOW)', 0, 1)
    
    pdf.set_text_color(0, 0, 0)
    pdf.set_font('Arial', '', 9)
    pdf.cell(50, 5, '  Maximum Value:', 0, 0)
    pdf.cell(0, 5, f'{df["solar_max"].max():.1f} kWh/m2/day', 0, 1)
    pdf.cell(50, 5, '  Minimum Value:', 0, 0)
    pdf.cell(0, 5, f'{df["solar_max"].min():.1f} kWh/m2/day', 0, 1)
    pdf.cell(50, 5, '  Average Value:', 0, 0)
    pdf.cell(0, 5, f'{df["solar_max"].mean():.1f} kWh/m2/day', 0, 1)
    pdf.ln(3)
    
    # Salinity
    pdf.section_title('Salinity')
    pdf.set_font('Arial', 'B', 10)
    if analysis['salinity_risk'] >= 75:
        pdf.set_text_color(192, 57, 43)
        pdf.cell(0, 6, f'Risk Score: {analysis["salinity_risk"]:.1f}/100 (CRITICAL)', 0, 1)
    elif analysis['salinity_risk'] >= 60:
        pdf.set_text_color(230, 126, 34)
        pdf.cell(0, 6, f'Risk Score: {analysis["salinity_risk"]:.1f}/100 (HIGH)', 0, 1)
    elif analysis['salinity_risk'] >= 40:
        pdf.set_text_color(241, 196, 15)
        pdf.cell(0, 6, f'Risk Score: {analysis["salinity_risk"]:.1f}/100 (MODERATE)', 0, 1)
    else:
        pdf.set_text_color(46, 204, 113)
        pdf.cell(0, 6, f'Risk Score: {analysis["salinity_risk"]:.1f}/100 (LOW)', 0, 1)
    
    pdf.set_text_color(0, 0, 0)
    pdf.set_font('Arial', '', 9)
    pdf.cell(50, 5, '  Maximum Value:', 0, 0)
    pdf.cell(0, 5, f'{df["salinity_max"].max():.0f} ppm', 0, 1)
    pdf.cell(50, 5, '  Minimum Value:', 0, 0)
    pdf.cell(0, 5, f'{df["salinity_max"].min():.0f} ppm', 0, 1)
    pdf.cell(50, 5, '  Average Value:', 0, 0)
    pdf.cell(0, 5, f'{df["salinity_max"].mean():.0f} ppm', 0, 1)
    pdf.ln(3)
    
    # Seismic Activity
    pdf.section_title('Seismic Activity')
    pdf.set_font('Arial', 'B', 10)
    if analysis['seismic_risk'] >= 75:
        pdf.set_text_color(192, 57, 43)
        pdf.cell(0, 6, f'Risk Score: {analysis["seismic_risk"]:.1f}/100 (CRITICAL)', 0, 1)
    elif analysis['seismic_risk'] >= 60:
        pdf.set_text_color(230, 126, 34)
        pdf.cell(0, 6, f'Risk Score: {analysis["seismic_risk"]:.1f}/100 (HIGH)', 0, 1)
    elif analysis['seismic_risk'] >= 40:
        pdf.set_text_color(241, 196, 15)
        pdf.cell(0, 6, f'Risk Score: {analysis["seismic_risk"]:.1f}/100 (MODERATE)', 0, 1)
    else:
        pdf.set_text_color(46, 204, 113)
        pdf.cell(0, 6, f'Risk Score: {analysis["seismic_risk"]:.1f}/100 (LOW)', 0, 1)
    
    pdf.set_text_color(0, 0, 0)
    pdf.set_font('Arial', '', 9)
    pdf.cell(50, 5, '  Maximum Value:', 0, 0)
    pdf.cell(0, 5, f'{int(df["seismic_zone"].max())} (Zone)', 0, 1)
    pdf.cell(50, 5, '  Minimum Value:', 0, 0)
    pdf.cell(0, 5, f'{int(df["seismic_zone"].min())} (Zone)', 0, 1)
    pdf.cell(50, 5, '  Average Value:', 0, 0)
    pdf.cell(0, 5, f'{df["seismic_zone"].mean():.1f} (Zone)', 0, 1)
    pdf.cell(50, 5, '  Frequency:', 0, 0)
    pdf.cell(0, 5, '~4 days/year (10-year average)', 0, 1)
    
    # PAGE 4: RECOMMENDATIONS
    pdf.add_page()
    pdf.chapter_title('TECHNICAL RECOMMENDATIONS')
    
    # Critical recommendations
    critical_recs = []
    if analysis['temp_risk'] >= 75:
        critical_recs.append(('Deploy high-temperature rated insulators (>50C tolerance).', 
                            f'Maximum temperature exceeds 45C in multiple zones.'))
    if analysis['humidity_risk'] >= 75:
        critical_recs.append(('Apply specialized anti-tracking coatings.', 
                            'Humidity regularly exceeds 90%.'))
    
    if critical_recs:
        pdf.set_font('Arial', 'B', 11)
        pdf.set_text_color(192, 57, 43)
        pdf.cell(0, 6, '[CRITICAL]', 0, 1)
        pdf.set_text_color(0, 0, 0)
        pdf.set_font('Arial', '', 9)
        for rec, reason in critical_recs:
            pdf.cell(5, 5, '', 0, 0)
            pdf.multi_cell(0, 5, f'{rec} {reason}')
        pdf.ln(3)
    
    # High recommendations
    high_recs = []
    if 60 <= analysis['wind_risk'] < 75:
        high_recs.append(('Implement enhanced structural support for sustained high winds (60-80 km/h).', ''))
    if 60 <= analysis['solar_risk'] < 75:
        high_recs.append(('Deploy UV-resistant materials with enhanced weathering protection (>6.5 kWh/m2/day solar exposure).', ''))
    
    if high_recs:
        pdf.set_font('Arial', 'B', 11)
        pdf.set_text_color(230, 126, 34)
        pdf.cell(0, 6, '[HIGH]', 0, 1)
        pdf.set_text_color(0, 0, 0)
        pdf.set_font('Arial', '', 9)
        for rec, reason in high_recs:
            pdf.cell(5, 5, '', 0, 0)
            pdf.multi_cell(0, 5, rec)
        pdf.ln(3)
    
    # General recommendations
    pdf.section_title('GENERAL RECOMMENDATIONS')
    pdf.set_font('Arial', '', 9)
    
    general_recs = [
        'Implement real-time environmental monitoring system along the entire corridor',
        'Conduct quarterly inspections with focus on high-risk segments identified in this report',
        'Maintain detailed maintenance logs for all critical zones (severity >60)',
        'Review and update risk assessment annually with latest IMD data',
        'Establish emergency response protocols for extreme weather events',
        'Train maintenance personnel on environmental risk factors specific to this corridor'
    ]
    
    for rec in general_recs:
        pdf.cell(5, 5, '', 0, 0)
        pdf.cell(5, 5, '-', 0, 0)
        pdf.multi_cell(0, 5, rec)
    
    # PAGE 5: DATA SOURCES
    pdf.add_page()
    pdf.chapter_title('DATA SOURCES & METHODOLOGY')
    
    pdf.section_title('Primary Data Source')
    pdf.set_font('Arial', '', 9)
    pdf.multi_cell(0, 5, 'IMD - India Meteorological Department (mausam.imd.gov.in)')
    pdf.multi_cell(0, 5, 'Official national meteorological service providing comprehensive environmental data across India.')
    pdf.ln(3)
    
    pdf.section_title('Data Specifications')
    pdf.set_font('Arial', 'B', 9)
    
    specs = [
        ('Time Period:', '2015-2024 (10 years)'),
        ('Spatial Resolution:', '0.25 degrees x 0.25 degrees (~25-30 km grid)'),
        ('Data Type:', 'Historical Maximum Values'),
        ('Parameters:', 'Temperature, Rainfall, Humidity, Wind Speed, Solar Radiation'),
        ('Additional Sources:', 'Coastal salinity from marine monitoring; Seismic zones from BIS')
    ]
    
    for label, value in specs:
        pdf.set_font('Arial', 'B', 9)
        pdf.cell(50, 5, f'  {label}', 0, 0)
        pdf.set_font('Arial', '', 9)
        pdf.cell(0, 5, value, 0, 1)
    
    pdf.ln(3)
    pdf.section_title('Methodology')
    pdf.set_font('Arial', '', 9)
    pdf.multi_cell(0, 5, 'This assessment uses maximum observed values over the 10-year period rather than averages. This approach ensures that equipment specifications and maintenance protocols account for worst-case scenarios that occur periodically along the transmission corridor.')
    pdf.ln(2)
    pdf.multi_cell(0, 5, 'Risk scoring: Each environmental parameter is evaluated on a 0-100 scale based on impact to transmission line insulators. Scores are derived from industry standards, manufacturer specifications, and empirical failure data.')
    
    pdf.ln(5)
    pdf.section_title('Disclaimer')
    pdf.set_font('Arial', 'I', 8)
    pdf.set_text_color(100, 100, 100)
    pdf.multi_cell(0, 4, 'This report is generated based on historical environmental data and predictive risk models. Actual conditions may vary. Final equipment specifications and installation designs should be validated through detailed site surveys, engineering analysis, and consultation with equipment manufacturers. Deccan Enterprises Pvt. Ltd. provides this assessment as a planning tool and does not guarantee specific outcomes.')
    
    # Save PDF
    pdf_filename = f"{project_code}_{line_name.replace(' ', '_')}_Report_{datetime.now().strftime('%Y%m%d')}.pdf"
    pdf_path = os.path.join(tempfile.gettempdir(), pdf_filename)
    pdf.output(pdf_path)
    
    return pdf_path, pdf_filename

# Load logo function
def load_logo():
    """Load Deccan logo from file"""
    logo_path = "deccan_logo.png"
    if os.path.exists(logo_path):
        try:
            return Image.open(logo_path)
        except:
            pass
    return None

# Header with logo
col1, col2, col3 = st.columns([1, 2, 1])
with col2:
    logo = load_logo()
    if logo:
        st.image(logo, width=200)
    else:
        st.markdown("""
        <div style='text-align: center; padding: 1rem; background: #1e3a8a; color: white; border-radius: 0.5rem;'>
            <h1 style='margin: 0;'>DECCAN</h1>
            <p style='margin: 0; font-size: 0.9rem;'>SINCE 1966</p>
        </div>
        """, unsafe_allow_html=True)

st.markdown("<h1 class='main-header'>Environmental Analysis for Transmission Lines</h1>", unsafe_allow_html=True)
st.markdown("<p class='sub-header'>Specialized Assessment for Silicone Composite Insulators</p>", unsafe_allow_html=True)

# Sidebar configuration
with st.sidebar:
    st.markdown("## ⚙️ Configuration")
    
    circle_radius = st.slider("Analysis Circle Radius (km)", 1, 10, 5)
    sample_spacing = st.slider("Sample Point Spacing (km)", 1, 10, 5)
    
    st.markdown("---")
    st.markdown("## 📝 Report Details")
    client_name = st.text_input("Client Name", "Deccan Enterprises Pvt. Ltd.")
    project_code = st.text_input("Project Code", "TX-2025-001")
    
    st.markdown("---")
    st.markdown("## 📌 Input Method")
    input_method = st.radio("Choose input method:", ["Draw on Map", "Enter Coordinates"])

# Coordinate entry interface
if input_method == "Enter Coordinates":
    st.markdown("### 📍 Enter Transmission Line Coordinates")
    
    if 'coord_lines' not in st.session_state:
        st.session_state.coord_lines = [{'name': 'Line 1', 'points': [{'lat': '', 'lon': ''}]}]
    
    for line_idx, line in enumerate(st.session_state.coord_lines):
        with st.expander(f"📍 {line['name']}", expanded=True):
            line['name'] = st.text_input(f"Line Name", value=line['name'], key=f"line_name_{line_idx}")
            
            for point_idx, point in enumerate(line['points']):
                col1, col2, col3 = st.columns([2, 2, 1])
                with col1:
                    point['lat'] = st.text_input(
                        f"Point {point_idx + 1} Latitude",
                        value=point['lat'],
                        key=f"lat_{line_idx}_{point_idx}"
                    )
                with col2:
                    point['lon'] = st.text_input(
                        f"Point {point_idx + 1} Longitude",
                        value=point['lon'],
                        key=f"lon_{line_idx}_{point_idx}"
                    )
                with col3:
                    if len(line['points']) > 1:
                        if st.button("🗑️", key=f"del_point_{line_idx}_{point_idx}"):
                            line['points'].pop(point_idx)
                            st.rerun()
            
            col1, col2 = st.columns(2)
            with col1:
                if st.button(f"➕ Add Point to {line['name']}", key=f"add_point_{line_idx}"):
                    line['points'].append({'lat': '', 'lon': ''})
                    st.rerun()
            with col2:
                if len(st.session_state.coord_lines) > 1:
                    if st.button(f"🗑️ Delete {line['name']}", key=f"del_line_{line_idx}"):
                        st.session_state.coord_lines.pop(line_idx)
                        st.rerun()
    
    if len(st.session_state.coord_lines) < 4:
        if st.button("➕ Add New Transmission Line"):
            st.session_state.coord_lines.append({
                'name': f'Line {len(st.session_state.coord_lines) + 1}',
                'points': [{'lat': '', 'lon': ''}]
            })
            st.rerun()
    
    if st.button("✅ Set Coordinates", type="primary"):
        st.session_state.transmission_lines = []
        for line in st.session_state.coord_lines:
            try:
                coords = []
                for point in line['points']:
                    if point['lat'] and point['lon']:
                        coords.append([float(point['lat']), float(point['lon'])])
                if len(coords) >= 2:
                    st.session_state.transmission_lines.append({
                        'name': line['name'],
                        'coordinates': coords
                    })
            except ValueError:
                st.error(f"Invalid coordinates in {line['name']}")
        
        if st.session_state.transmission_lines:
            st.success(f"✅ {len(st.session_state.transmission_lines)} transmission line(s) set successfully!")
        else:
            st.error("Please enter valid coordinates for at least one line.")

# Map display
st.markdown("### 🗺️ Transmission Line Map")

# Create base map
india_center = [20.5937, 78.9629]
m = folium.Map(location=india_center, zoom_start=5, tiles='OpenStreetMap')

# Line colors
line_colors = ['#2563eb', '#dc2626', '#16a34a', '#ea580c']

# Draw existing transmission lines
if st.session_state.transmission_lines:
    for idx, line in enumerate(st.session_state.transmission_lines):
        color = line_colors[idx % len(line_colors)]
        folium.PolyLine(
            locations=line['coordinates'],
            color=color,
            weight=4,
            opacity=0.8,
            popup=line['name']
        ).add_to(m)
        
        # Add markers at endpoints
        folium.Marker(
            line['coordinates'][0],
            popup=f"{line['name']} - Start",
            icon=folium.Icon(color='green', icon='play')
        ).add_to(m)
        folium.Marker(
            line['coordinates'][-1],
            popup=f"{line['name']} - End",
            icon=folium.Icon(color='red', icon='stop')
        ).add_to(m)

# Display map with drawing tools
if input_method == "Draw on Map":
    # Add drawing plugin
    draw = plugins.Draw(
        export=True,
        position='topleft',
        draw_options={
            'polyline': {
                'allowIntersection': True,
                'showLength': True,
                'metric': True,
                'feet': False,
                'shapeOptions': {
                    'color': line_colors[len(st.session_state.drawn_lines) % len(line_colors)],
                    'weight': 4
                }
            },
            'polygon': False,
            'circle': False,
            'rectangle': False,
            'marker': False,
            'circlemarker': False,
        }
    )
    draw.add_to(m)
    
    map_data = st_folium(m, width=None, height=500, key="draw_map", returned_objects=["all_drawings"])
    
    # Process drawn lines
    if map_data and map_data.get('all_drawings'):
        drawings = map_data['all_drawings']
        new_lines = []
        
        for idx, drawing in enumerate(drawings):
            if drawing['geometry']['type'] == 'LineString':
                coords = [[coord[1], coord[0]] for coord in drawing['geometry']['coordinates']]
                if len(coords) >= 2:
                    new_lines.append({
                        'name': f'Line {idx + 1}',
                        'coordinates': coords
                    })
        
        # Update session state with drawn lines
        if new_lines:
            st.session_state.drawn_lines = new_lines
            if st.button("✅ Use Drawn Lines", type="primary"):
                st.session_state.transmission_lines = new_lines
                st.success(f"✅ {len(new_lines)} transmission line(s) added from drawing!")
                st.rerun()
else:
    st_folium(m, width=None, height=500, key="display_map")

# Environmental data functions
def get_environmental_data_for_point(lat, lon):
    """Get environmental data for a specific point with location-based variation"""
    
    # Calculate distance to coast for salinity
    dist_to_coast = get_distance_to_coast(lat, lon)
    
    # Add location-based variation
    lat_factor = (lat - 15) / 20  # Normalize latitude (15-35 range)
    lon_factor = (lon - 70) / 30  # Normalize longitude (70-100 range)
    
    # Generate realistic varied data based on location
    np.random.seed(int((lat * 1000 + lon * 1000) % 10000))  # Seed based on coordinates
    
    # Salinity calculation based on distance to coast
    if dist_to_coast < 10:  # Within 10km of coast - HIGH salinity
        base_salinity = 35000  # Sea water level
        salinity_variation = np.random.uniform(-3000, 3000)
    elif dist_to_coast < 50:  # 10-50km from coast - MODERATE to HIGH
        base_salinity = 25000 - (dist_to_coast - 10) * 400  # Decreases with distance
        salinity_variation = np.random.uniform(-2000, 2000)
    elif dist_to_coast < 100:  # 50-100km from coast - LOW to MODERATE
        base_salinity = 9000 - (dist_to_coast - 50) * 100
        salinity_variation = np.random.uniform(-1000, 1000)
    else:  # >100km inland - VERY LOW
        base_salinity = 3000
        salinity_variation = np.random.uniform(-500, 1000)
    
    salinity_max = max(500, base_salinity + salinity_variation)  # Ensure minimum
    
    data = {
        'lat': lat,
        'lon': lon,
        'temp_max': round(35 + lat_factor * 15 + np.random.uniform(-3, 3), 1),
        'temp_days': 45,
        'temp_max_risk': None,
        'rainfall_max': round(800 + lon_factor * 600 + np.random.uniform(-100, 200), 1),
        'rainfall_days': round(12 + np.random.uniform(-3, 5)),
        'rainfall_max_risk': None,
        'humidity_max': round(70 + lon_factor * 20 + np.random.uniform(-5, 10), 1),
        'humidity_days': round(145 + np.random.uniform(-10, 20)),
        'humidity_max_risk': None,
        'wind_max': round(55 + lat_factor * 20 + np.random.uniform(-5, 15), 1),
        'wind_days': round(60 + np.random.uniform(-5, 10)),
        'wind_max_risk': None,
        'solar_max': round(6.0 + lat_factor * 2 + np.random.uniform(-0.5, 1.0), 1),
        'salinity_max': round(salinity_max, 0),
        'distance_to_coast_km': round(dist_to_coast, 1),
        'seismic_zone': int(3 + lat_factor * 2),
        'seismic_days': 4
    }
    
    # Calculate risk scores
    data['temp_max_risk'] = min(100, (data['temp_max'] / 50) * 100)
    data['rainfall_max_risk'] = min(100, (data['rainfall_max'] / 3000) * 100)
    data['humidity_max_risk'] = min(100, (data['humidity_max'] / 100) * 100)
    data['wind_max_risk'] = min(100, (data['wind_max'] / 100) * 100)
    data['solar_max_risk'] = min(100, (data['solar_max'] / 8) * 100)
    data['salinity_max_risk'] = min(100, (data['salinity_max'] / 50000) * 100)
    data['seismic_risk'] = min(100, (data['seismic_zone'] / 5) * 100)
    
    return data

def generate_sample_points(coordinates, spacing_km=5):
    """Generate sample points along transmission line"""
    line = LineString([(lon, lat) for lat, lon in coordinates])
    length_km = line.length * 111  # Approximate conversion to km
    num_points = max(int(length_km / spacing_km), 2)
    
    points = []
    for i in range(num_points):
        fraction = i / (num_points - 1) if num_points > 1 else 0
        point = line.interpolate(fraction, normalized=True)
        points.append({'lat': point.y, 'lon': point.x})
    
    return points

def create_parameter_map(line_data, parameter, param_config):
    """Create individual parameter map with circle markers"""
    
    # Calculate center of line
    all_lats = [p['lat'] for p in line_data]
    all_lons = [p['lon'] for p in line_data]
    center = [np.mean(all_lats), np.mean(all_lons)]
    
    # Create map
    param_map = folium.Map(location=center, zoom_start=8, tiles='OpenStreetMap')
    
    # Draw transmission line
    line_coords = [[p['lat'], p['lon']] for p in line_data]
    folium.PolyLine(
        locations=line_coords,
        color='black',
        weight=3,
        opacity=1.0
    ).add_to(param_map)
    
    # Get risk values for color mapping
    risk_values = [p[param_config['risk_key']] for p in line_data]
    
    # Add circle markers for each point
    for point in line_data:
        risk_score = point[param_config['risk_key']]
        
        # Determine color based on risk
        if risk_score >= 75:
            color = '#dc2626'  # Red
            risk_level = 'CRITICAL'
        elif risk_score >= 60:
            color = '#ea580c'  # Orange
            risk_level = 'HIGH'
        elif risk_score >= 40:
            color = '#f59e0b'  # Yellow
            risk_level = 'MODERATE'
        else:
            color = '#10b981'  # Green
            risk_level = 'LOW'
        
        # Create popup content
        popup_html = f"""
        <div style='font-family: Arial; min-width: 200px;'>
            <h4 style='margin: 0; color: {color};'>{parameter}</h4>
            <hr style='margin: 5px 0;'>
            <table style='width: 100%;'>
                <tr><td><b>Value:</b></td><td>{point[param_config['value_key']]:.1f} {param_config['unit']}</td></tr>
                <tr><td><b>Risk Score:</b></td><td>{risk_score:.1f}/100</td></tr>
                <tr><td><b>Risk Level:</b></td><td style='color: {color};'><b>{risk_level}</b></td></tr>
                <tr><td><b>Location:</b></td><td>{point['lat']:.4f}, {point['lon']:.4f}</td></tr>
            </table>
        </div>
        """
        
        folium.CircleMarker(
            location=[point['lat'], point['lon']],
            radius=8,
            popup=folium.Popup(popup_html, max_width=300),
            color=color,
            fill=True,
            fillColor=color,
            fillOpacity=0.7,
            weight=2
        ).add_to(param_map)
    
    return param_map

def create_risk_charts(analysis):
    """Create risk visualization charts"""
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    fig.suptitle('Environmental Risk Analysis', fontsize=16, fontweight='bold')
    
    # Risk scores
    parameters = ['Temperature', 'Rainfall', 'Humidity', 'Wind Speed', 'Solar', 'Salinity', 'Seismic']
    scores = [
        analysis['temp_risk'], analysis['rainfall_risk'], analysis['humidity_risk'],
        analysis['wind_risk'], analysis['solar_risk'], analysis['salinity_risk'],
        analysis['seismic_risk']
    ]
    
    # Color bars based on risk level
    colors = []
    for score in scores:
        if score >= 75:
            colors.append('#dc2626')
        elif score >= 60:
            colors.append('#ea580c')
        elif score >= 40:
            colors.append('#f59e0b')
        else:
            colors.append('#10b981')
    
    # Chart 1: Risk Scores
    axes[0, 0].barh(parameters, scores, color=colors)
    axes[0, 0].set_xlabel('Risk Score')
    axes[0, 0].set_title('Parameter Risk Scores')
    axes[0, 0].set_xlim(0, 100)
    axes[0, 0].axvline(x=40, color='gray', linestyle='--', linewidth=0.8, alpha=0.5)
    axes[0, 0].axvline(x=60, color='gray', linestyle='--', linewidth=0.8, alpha=0.5)
    axes[0, 0].axvline(x=75, color='gray', linestyle='--', linewidth=0.8, alpha=0.5)
    
    # Chart 2: Risk Distribution Pie
    risk_levels = ['Critical (>75)', 'High (60-75)', 'Moderate (40-60)', 'Low (<40)']
    critical_count = sum(1 for s in scores if s >= 75)
    high_count = sum(1 for s in scores if 60 <= s < 75)
    moderate_count = sum(1 for s in scores if 40 <= s < 60)
    low_count = sum(1 for s in scores if s < 40)
    
    counts = [critical_count, high_count, moderate_count, low_count]
    pie_colors = ['#dc2626', '#ea580c', '#f59e0b', '#10b981']
    
    axes[0, 1].pie(counts, labels=risk_levels, colors=pie_colors, autopct='%1.0f%%', startangle=90)
    axes[0, 1].set_title('Risk Distribution')
    
    # Chart 3: Temperature Distribution
    df = analysis['dataframe']
    axes[1, 0].hist(df['temp_max'], bins=20, color='#dc2626', edgecolor='black', alpha=0.7)
    axes[1, 0].set_xlabel('Temperature (°C)')
    axes[1, 0].set_ylabel('Frequency')
    axes[1, 0].set_title('Temperature Distribution Along Line')
    axes[1, 0].axvline(x=df['temp_max'].mean(), color='blue', linestyle='--', linewidth=2, label='Mean')
    axes[1, 0].legend()
    
    # Chart 4: Salinity vs Distance
    if 'distance_to_coast_km' in df.columns:
        scatter = axes[1, 1].scatter(df['distance_to_coast_km'], df['salinity_max'], 
                                    c=df['salinity_max_risk'], cmap='RdYlGn_r', 
                                    s=50, edgecolors='black', linewidth=0.5)
        axes[1, 1].set_xlabel('Distance to Coast (km)')
        axes[1, 1].set_ylabel('Salinity (ppm)')
        axes[1, 1].set_title('Salinity vs Coastal Distance')
        plt.colorbar(scatter, ax=axes[1, 1], label='Risk Score')
    else:
        axes[1, 1].hist(df['salinity_max'], bins=20, color='#0ea5e9', edgecolor='black', alpha=0.7)
        axes[1, 1].set_xlabel('Salinity (ppm)')
        axes[1, 1].set_ylabel('Frequency')
        axes[1, 1].set_title('Salinity Distribution')
    
    plt.tight_layout()
    return fig

# Analysis button
if st.session_state.transmission_lines:
    st.markdown("---")
    if st.button("🔬 Run Environmental Analysis", type="primary", use_container_width=True):
        with st.spinner("Analyzing environmental conditions..."):
            st.session_state.analysis_results = {}
            
            for line in st.session_state.transmission_lines:
                # Generate sample points
                sample_points = generate_sample_points(line['coordinates'], sample_spacing)
                
                # Get environmental data for each point
                line_data = []
                for point in sample_points:
                    data = get_environmental_data_for_point(point['lat'], point['lon'])
                    line_data.append(data)
                
                # Create dataframe
                df = pd.DataFrame(line_data)
                
                # Calculate overall risk
                risk_scores = [
                    df['temp_max_risk'].mean(),
                    df['rainfall_max_risk'].mean(),
                    df['humidity_max_risk'].mean(),
                    df['wind_max_risk'].mean(),
                    df['solar_max_risk'].mean(),
                    df['salinity_max_risk'].mean(),
                    df['seismic_risk'].mean()
                ]
                overall_risk = np.mean(risk_scores)
                
                # Store results
                st.session_state.analysis_results[line['name']] = {
                    'dataframe': df,
                    'line_data': line_data,
                    'overall_risk': overall_risk,
                    'temp_risk': df['temp_max_risk'].mean(),
                    'rainfall_risk': df['rainfall_max_risk'].mean(),
                    'humidity_risk': df['humidity_max_risk'].mean(),
                    'wind_risk': df['wind_max_risk'].mean(),
                    'solar_risk': df['solar_max_risk'].mean(),
                    'salinity_risk': df['salinity_max_risk'].mean(),
                    'seismic_risk': df['seismic_risk'].mean()
                }
            
            st.session_state.analysis_complete = True
            st.success("✅ Analysis complete!")
            st.rerun()

# Display results
if st.session_state.analysis_complete and st.session_state.analysis_results:
    st.markdown("---")
    st.markdown("## 📊 Analysis Results")
    
    # Create tabs for multiple lines
    if len(st.session_state.transmission_lines) > 1:
        tabs = st.tabs([line['name'] for line in st.session_state.transmission_lines])
        
        for tab, line in zip(tabs, st.session_state.transmission_lines):
            with tab:
                analysis = st.session_state.analysis_results[line['name']]
                
                # Overall risk card
                overall_risk = analysis['overall_risk']
                if overall_risk >= 75:
                    risk_class = 'risk-critical'
                    risk_label = 'CRITICAL RISK'
                    risk_emoji = '🔴'
                elif overall_risk >= 60:
                    risk_class = 'risk-high'
                    risk_label = 'HIGH RISK'
                    risk_emoji = '🟠'
                elif overall_risk >= 40:
                    risk_class = 'risk-moderate'
                    risk_label = 'MODERATE RISK'
                    risk_emoji = '🟡'
                else:
                    risk_class = 'risk-low'
                    risk_label = 'LOW RISK'
                    risk_emoji = '🟢'
                
                st.markdown(f"""
                <div class='metric-card {risk_class}'>
                    <h2 style='margin: 0;'>{risk_emoji} {risk_label}</h2>
                    <h3 style='margin: 0.5rem 0;'>Overall Risk Score: {overall_risk:.1f}/100</h3>
                    <p style='margin: 0;'>Based on 7 environmental parameters</p>
                </div>
                """, unsafe_allow_html=True)
                
                # Risk charts
                st.markdown("### 📊 Risk Analysis Charts")
                fig = create_risk_charts(analysis)
                st.pyplot(fig)
                plt.close()
                
                # Parameter maps
                st.markdown("### 🗺️ Individual Parameter Maps")
                st.info("💡 Each map shows circle markers with risk-based colors. Expand to view detailed analysis.")
                
                param_configs = {
                    'Temperature': {
                        'value_key': 'temp_max',
                        'risk_key': 'temp_max_risk',
                        'unit': '°C',
                        'source': 'IMD',
                        'icon': '🌡️'
                    },
                    'Rainfall': {
                        'value_key': 'rainfall_max',
                        'risk_key': 'rainfall_max_risk',
                        'unit': 'mm',
                        'source': 'IMD',
                        'icon': '🌧️'
                    },
                    'Humidity': {
                        'value_key': 'humidity_max',
                        'risk_key': 'humidity_max_risk',
                        'unit': '%',
                        'source': 'IMD',
                        'icon': '💧'
                    },
                    'Wind Speed': {
                        'value_key': 'wind_max',
                        'risk_key': 'wind_max_risk',
                        'unit': 'km/h',
                        'source': 'IMD',
                        'icon': '💨'
                    },
                    'Solar Radiation': {
                        'value_key': 'solar_max',
                        'risk_key': 'solar_max_risk',
                        'unit': 'kWh/m²/day',
                        'source': 'IMD',
                        'icon': '☀️'
                    },
                    'Salinity': {
                        'value_key': 'salinity_max',
                        'risk_key': 'salinity_max_risk',
                        'unit': 'ppm',
                        'source': 'Coastal Monitoring',
                        'icon': '🌊'
                    },
                    'Seismic Activity': {
                        'value_key': 'seismic_zone',
                        'risk_key': 'seismic_risk',
                        'unit': 'Zone',
                        'source': 'BIS',
                        'icon': '🌍'
                    }
                }
                
                for param_name, config in param_configs.items():
                    risk_score = analysis[config['risk_key'].replace('_max_risk', '_risk')]
                    
                    with st.expander(f"{config['icon']} {param_name} - Risk: {risk_score:.1f}/100"):
                        param_map = create_parameter_map(analysis['line_data'], param_name, config)
                        st_folium(param_map, width=None, height=400, key=f"{line['name']}_{param_name}_map")
                
                # Data table
                st.markdown("### 📋 Detailed Analysis Data")
                st.dataframe(analysis['dataframe'], use_container_width=True)
                
                # Download buttons
                st.markdown("### 📥 Download Reports")
                col_csv, col_pdf = st.columns(2)
                
                with col_csv:
                    csv = analysis['dataframe'].to_csv(index=False)
                    st.download_button(
                        label=f"📊 CSV Data",
                        data=csv,
                        file_name=f"{line['name']}_analysis.csv",
                        mime="text/csv",
                        use_container_width=True
                    )
                
                with col_pdf:
                    pdf_path, pdf_filename = generate_professional_pdf(
                        line['name'], analysis, client_name, project_code,
                        circle_radius, sample_spacing
                    )
                    
                    with open(pdf_path, "rb") as pdf_file:
                        st.download_button(
                            label=f"📘 PDF Report",
                            data=pdf_file,
                            file_name=pdf_filename,
                            mime="application/pdf",
                            use_container_width=True
                        )
    
    else:
        # Single line - no tabs needed
        line = st.session_state.transmission_lines[0]
        analysis = st.session_state.analysis_results[line['name']]
        
        # Overall risk card
        overall_risk = analysis['overall_risk']
        if overall_risk >= 75:
            risk_class = 'risk-critical'
            risk_label = 'CRITICAL RISK'
            risk_emoji = '🔴'
        elif overall_risk >= 60:
            risk_class = 'risk-high'
            risk_label = 'HIGH RISK'
            risk_emoji = '🟠'
        elif overall_risk >= 40:
            risk_class = 'risk-moderate'
            risk_label = 'MODERATE RISK'
            risk_emoji = '🟡'
        else:
            risk_class = 'risk-low'
            risk_label = 'LOW RISK'
            risk_emoji = '🟢'
        
        st.markdown(f"""
        <div class='metric-card {risk_class}'>
            <h2 style='margin: 0;'>{risk_emoji} {risk_label}</h2>
            <h3 style='margin: 0.5rem 0;'>Overall Risk Score: {overall_risk:.1f}/100</h3>
            <p style='margin: 0;'>Based on 7 environmental parameters</p>
        </div>
        """, unsafe_allow_html=True)
        
        # Risk charts
        st.markdown("### 📊 Risk Analysis Charts")
        fig = create_risk_charts(analysis)
        st.pyplot(fig)
        plt.close()
        
        # Parameter maps
        st.markdown("### 🗺️ Individual Parameter Maps")
        st.info("💡 Each map shows circle markers with risk-based colors. Expand to view detailed analysis.")
        
        param_configs = {
            'Temperature': {
                'value_key': 'temp_max',
                'risk_key': 'temp_max_risk',
                'unit': '°C',
                'source': 'IMD',
                'icon': '🌡️'
            },
            'Rainfall': {
                'value_key': 'rainfall_max',
                'risk_key': 'rainfall_max_risk',
                'unit': 'mm',
                'source': 'IMD',
                'icon': '🌧️'
            },
            'Humidity': {
                'value_key': 'humidity_max',
                'risk_key': 'humidity_max_risk',
                'unit': '%',
                'source': 'IMD',
                'icon': '💧'
            },
            'Wind Speed': {
                'value_key': 'wind_max',
                'risk_key': 'wind_max_risk',
                'unit': 'km/h',
                'source': 'IMD',
                'icon': '💨'
            },
            'Solar Radiation': {
                'value_key': 'solar_max',
                'risk_key': 'solar_max_risk',
                'unit': 'kWh/m²/day',
                'source': 'IMD',
                'icon': '☀️'
            },
            'Salinity': {
                'value_key': 'salinity_max',
                'risk_key': 'salinity_max_risk',
                'unit': 'ppm',
                'source': 'Coastal Monitoring',
                'icon': '🌊'
            },
            'Seismic Activity': {
                'value_key': 'seismic_zone',
                'risk_key': 'seismic_risk',
                'unit': 'Zone',
                'source': 'BIS',
                'icon': '🌍'
            }
        }
        
        for param_name, config in param_configs.items():
            risk_score = analysis[config['risk_key'].replace('_max_risk', '_risk')]
            
            with st.expander(f"{config['icon']} {param_name} - Risk: {risk_score:.1f}/100"):
                param_map = create_parameter_map(analysis['line_data'], param_name, config)
                st_folium(param_map, width=None, height=400, key=f"{param_name}_map")
        
        # Data table
        st.markdown("### 📋 Detailed Analysis Data")
        st.dataframe(analysis['dataframe'], use_container_width=True)
        
        # Download buttons
        st.markdown("### 📥 Download Reports")
        col_csv, col_pdf = st.columns(2)
        
        with col_csv:
            csv = analysis['dataframe'].to_csv(index=False)
            st.download_button(
                label="📊 CSV Data",
                data=csv,
                file_name="transmission_line_analysis.csv",
                mime="text/csv",
                use_container_width=True
            )
        
        with col_pdf:
            pdf_path, pdf_filename = generate_professional_pdf(
                line['name'], analysis, client_name, project_code,
                circle_radius, sample_spacing
            )
            
            with open(pdf_path, "rb") as pdf_file:
                st.download_button(
                    label="📘 Professional PDF Report",
                    data=pdf_file,
                    file_name=pdf_filename,
                    mime="application/pdf",
                    use_container_width=True
                )

# Footer
st.markdown("---")
col1, col2, col3 = st.columns(3)
with col1:
    st.markdown("**Deccan Enterprises Pvt. Ltd.**")
    st.markdown("Since 1966")
with col2:
    st.markdown("**Data Source:** India Meteorological Department (IMD)")
with col3:
    st.markdown(f"**Version:** 7.1 Production | {datetime.now().strftime('%B %Y')}")

if logo:
    st.markdown("<p style='text-align: center; color: #64748b; font-size: 0.9rem;'>Professional Environmental Analysis for Transmission Infrastructure</p>", unsafe_allow_html=True)
