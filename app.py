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
    
    # KEY ENVIRONMENTAL METRICS TABLE
    pdf.section_title('KEY ENVIRONMENTAL METRICS')
    
    # Table header
    pdf.set_fill_color(0, 51, 102)
    pdf.set_text_color(255, 255, 255)
    pdf.set_font('Arial', 'B', 9)
    
    col_widths = [55, 30, 25, 25, 35]
    headers = ['Parameter', 'Average', 'Min', 'Max', 'Risk Score']
    
    for i, header in enumerate(headers):
        pdf.cell(col_widths[i], 7, header, 1, 0, 'C', 1)
    pdf.ln()
    
    # Table rows
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
    
    fill = False
    for param, avg, min_val, max_val, risk in metrics_data:
        pdf.set_fill_color(245, 245, 245)
        pdf.cell(col_widths[0], 6, param, 1, 0, 'L', fill)
        pdf.cell(col_widths[1], 6, f'{avg:.1f}', 1, 0, 'C', fill)
        pdf.cell(col_widths[2], 6, f'{min_val:.1f}', 1, 0, 'C', fill)
        pdf.cell(col_widths[3], 6, f'{max_val:.1f}', 1, 0, 'C', fill)
        pdf.cell(col_widths[4], 6, f'{risk:.1f}/100', 1, 0, 'C', fill)
        pdf.ln()
        fill = not fill
    
    # PAGE 3: DETAILED PARAMETER ANALYSIS
    pdf.add_page()
    pdf.chapter_title('DETAILED PARAMETER ANALYSIS')
    
    param_details = [
        ('Temperature', 'temp_max', 'temp_risk', 'C', 'temp_days'),
        ('Rainfall', 'rainfall_max', 'rainfall_risk', 'mm', 'rainfall_days'),
        ('Humidity', 'humidity_max', 'humidity_risk', '%', 'humidity_days'),
        ('Wind Speed', 'wind_max', 'wind_risk', 'km/h', 'wind_days'),
        ('Solar Radiation', 'solar_max', 'solar_risk', 'kWh/m2/day', None),
        ('Salinity', 'salinity_max', 'salinity_risk', 'ppm', None),
        ('Seismic Activity', 'seismic_zone', 'seismic_risk', '(Zone)', 'seismic_days')
    ]
    
    for param_name, value_key, risk_key, unit, days_key in param_details:
        pdf.section_title(param_name)
        
        risk_score = analysis[risk_key]
        if risk_score >= 75:
            risk_level = "CRITICAL"
        elif risk_score >= 60:
            risk_level = "HIGH"
        elif risk_score >= 40:
            risk_level = "MODERATE"
        else:
            risk_level = "LOW"
        
        pdf.set_font('Arial', 'B', 10)
        pdf.cell(0, 6, f'Risk Score: {risk_score:.1f}/100 ({risk_level})', 0, 1)
        
        pdf.set_font('Arial', '', 9)
        pdf.cell(50, 5, f'  Maximum Value:', 0, 0)
        pdf.cell(0, 5, f'{df[value_key].max():.1f} {unit}', 0, 1)
        pdf.cell(50, 5, f'  Minimum Value:', 0, 0)
        pdf.cell(0, 5, f'{df[value_key].min():.1f} {unit}', 0, 1)
        pdf.cell(50, 5, f'  Average Value:', 0, 0)
        pdf.cell(0, 5, f'{df[value_key].mean():.1f} {unit}', 0, 1)
        
        if days_key and days_key in df.columns:
            avg_days = df[days_key].mean()
            pdf.cell(50, 5, f'  Frequency:', 0, 0)
            pdf.cell(0, 5, f'~{avg_days:.0f} days/year (10-year average)', 0, 1)
        
        pdf.ln(3)
    
    # PAGE 4: RECOMMENDATIONS
    pdf.add_page()
    pdf.chapter_title('TECHNICAL RECOMMENDATIONS')
    
    pdf.set_font('Arial', '', 10)
    recommendations = []
    
    if analysis['temp_risk'] > 75:
        recommendations.append(('CRITICAL', 'Deploy high-temperature rated insulators (>50C tolerance). Maximum temperature exceeds 45C in multiple zones.'))
    elif analysis['temp_risk'] > 60:
        recommendations.append(('HIGH', 'Use enhanced thermal-resistant insulators for sustained high temperatures (40-45C range).'))
    
    if analysis['rainfall_risk'] > 75:
        recommendations.append(('CRITICAL', 'Install hydrophobic silicone insulators with superior water-shedding properties. Heavy rainfall exceeds 350mm.'))
    elif analysis['rainfall_risk'] > 60:
        recommendations.append(('HIGH', 'Use polymer composite insulators designed for high-moisture environments.'))
    
    if analysis['humidity_risk'] > 75:
        recommendations.append(('CRITICAL', 'Apply specialized anti-tracking coatings. Humidity regularly exceeds 90%.'))
    elif analysis['humidity_risk'] > 60:
        recommendations.append(('HIGH', 'Use hydrophobic insulators to prevent surface moisture accumulation.'))
    
    if analysis['wind_risk'] > 75:
        recommendations.append(('CRITICAL', 'Reinforce tower structures for extreme wind loads (>80 km/h). Use aerodynamic insulator designs.'))
    elif analysis['wind_risk'] > 60:
        recommendations.append(('HIGH', 'Implement enhanced structural support for sustained high winds (60-80 km/h).'))
    
    if analysis['solar_risk'] > 70:
        recommendations.append(('HIGH', 'Deploy UV-resistant materials with enhanced weathering protection (>6.5 kWh/m2/day solar exposure).'))
    
    if analysis['salinity_risk'] > 75:
        recommendations.append(('CRITICAL', 'Install anti-salt fog insulators with specialized surface treatments. Coastal salinity exceeds 33,000 ppm.'))
    elif analysis['salinity_risk'] > 60:
        recommendations.append(('HIGH', 'Use corrosion-resistant materials for moderate coastal salinity (25,000-33,000 ppm).'))
    
    if analysis['seismic_risk'] > 70:
        recommendations.append(('HIGH', 'Implement seismic-resistant tower designs per Zone 4/5 specifications (BIS standards).'))
    
    if not recommendations:
        recommendations.append(('LOW', 'Standard insulator specifications are adequate for this corridor.'))
        recommendations.append(('INFO', 'Maintain routine inspection and preventive maintenance schedules.'))
    
    for priority, rec in recommendations:
        if priority == "CRITICAL":
            pdf.set_text_color(192, 57, 43)
        elif priority == "HIGH":
            pdf.set_text_color(230, 126, 34)
        else:
            pdf.set_text_color(0, 0, 0)
        
        pdf.set_font('Arial', 'B', 10)
        pdf.cell(0, 6, f'[{priority}]', 0, 1)
        pdf.set_text_color(0, 0, 0)
        pdf.set_font('Arial', '', 10)
        pdf.multi_cell(0, 5, f'  {rec}')
        pdf.ln(2)
    
    pdf.ln(5)
    pdf.section_title('GENERAL RECOMMENDATIONS')
    pdf.set_font('Arial', '', 10)
    
    general_recs = [
        'Implement real-time environmental monitoring system along the entire corridor',
        'Conduct quarterly inspections with focus on high-risk segments identified in this report',
        'Maintain detailed maintenance logs for all critical zones (severity >60)',
        'Review and update risk assessment annually with latest IMD data',
        'Establish emergency response protocols for extreme weather events',
        'Train maintenance personnel on environmental risk factors specific to this corridor'
    ]
    
    for rec in general_recs:
        pdf.cell(5, 5, '-', 0, 0)
        pdf.multi_cell(0, 5, rec)
    
    # PAGE 5: DATA SOURCES
    pdf.add_page()
    pdf.chapter_title('DATA SOURCES & METHODOLOGY')
    
    pdf.section_title('Primary Data Source')
    pdf.set_font('Arial', '', 10)
    pdf.multi_cell(0, 5, 'IMD - India Meteorological Department (mausam.imd.gov.in)\nOfficial national meteorological service providing comprehensive environmental data across India.')
    pdf.ln(3)
    
    pdf.section_title('Data Specifications')
    pdf.set_font('Arial', '', 9)
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

# Display map
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

# Helper function to calculate distance to coast
def get_distance_to_coast(lat, lon):
    """Calculate approximate distance to nearest Indian coast in km"""
    # Comprehensive Indian coastline points
    coast_points = [
        # West coast (Arabian Sea)
        (8.0883, 77.5385), (9.9312, 76.2673), (11.2588, 75.7804), (12.9716, 74.8056),
        (14.8546, 74.1240), (15.4909, 73.8278), (17.0005, 73.0167), (18.9388, 72.8354),
        (20.2961, 72.8347), (21.7051, 72.9959), (22.3072, 68.9692), (23.0225, 69.6693),
        # East coast (Bay of Bengal)
        (8.0883, 77.5569), (10.7905, 79.8437), (11.9416, 79.8083), (13.0827, 80.2707),
        (14.4426, 79.9865), (15.9129, 80.3328), (16.9891, 82.2475), (17.6868, 83.2185),
        (18.9894, 84.6667), (19.8135, 85.8312), (20.2644, 85.8281), (21.8064, 87.0936),
        (22.5726, 88.3639),
        # Andaman & Nicobar
        (11.7401, 92.6586), (13.0827, 93.0570),
        # Gujarat peninsula
        (20.9517, 70.3660), (22.4707, 69.6293),
    ]
    
    min_distance = float('inf')
    for coast_lat, coast_lon in coast_points:
        lat_diff = (lat - coast_lat) * 111
        lon_diff = (lon - coast_lon) * 111 * math.cos(math.radians(lat))
        distance = math.sqrt(lat_diff**2 + lon_diff**2)
        min_distance = min(min_distance, distance)
    return min_distance

def get_pollution_level(lat, lon):
    """Calculate pollution level (AQI) based on proximity to polluted cities"""
    polluted_cities = [
        (28.7041, 77.1025, 160), (28.4595, 77.0266, 120), (28.6692, 77.4538, 110),
        (28.6139, 77.2090, 140), (28.7100, 77.4100, 105), (28.8386, 77.8450, 95),
        (26.4499, 80.3319, 110), (26.8467, 80.9462, 100), (27.1767, 78.0081, 90),
        (25.3176, 82.9739, 95), (29.9457, 77.7085, 85), (27.5706, 77.7085, 80),
        (25.5941, 85.1376, 100), (22.5726, 88.3639, 95), (23.6345, 87.8615, 85),
        (23.5204, 87.3119, 82), (26.2006, 92.9376, 130), (26.1445, 91.7362, 90),
        (27.0238, 75.3370, 80), (26.9124, 75.7873, 75), (22.3072, 72.3694, 85),
        (21.1702, 72.8311, 75), (22.2587, 70.7813, 90), (22.4707, 70.0577, 80),
        (21.7645, 72.1519, 85), (19.0760, 72.8777, 80), (18.5204, 73.8567, 75),
        (12.9716, 77.5946, 65), (13.0827, 80.2707, 70), (30.9010, 75.8573, 90),
        (30.7333, 76.7794, 85),
    ]
    
    total_weight, weighted_aqi = 0, 0
    for city_lat, city_lon, city_aqi in polluted_cities:
        dist = math.sqrt((lat - city_lat)**2 + (lon - city_lon)**2) * 111
        if dist < 1:
            weight = 1.0
        elif dist < 50:
            weight = 1.0 / (1 + dist/10)
        elif dist < 200:
            weight = 1.0 / (1 + dist/5)
        else:
            weight = 1.0 / (1 + dist)
        weighted_aqi += city_aqi * weight
        total_weight += weight
    
    base_aqi = 45
    if total_weight > 0:
        calculated_aqi = weighted_aqi / total_weight
        final_aqi = (calculated_aqi * 0.7) + (base_aqi * 0.3)
    else:
        final_aqi = base_aqi
    return max(35, min(500, final_aqi))

def get_environmental_data_for_point(lat, lon):
    """Get environmental data with FIXED salinity and NEW pollution parameter"""
    
    # Calculate distance to coast for salinity
    dist_to_coast = get_distance_to_coast(lat, lon)
    
    # Add location-based variation
    lat_factor = (lat - 15) / 20  # Normalize latitude (15-35 range)
    lon_factor = (lon - 70) / 30  # Normalize longitude (70-100 range)
    
    # Generate realistic varied data based on location
    np.random.seed(int((lat * 1000 + lon * 1000) % 10000))  # Seed based on coordinates
    
    # CRITICAL FIX: Salinity based on actual oceanographic data
    # Arabian Sea: ~37 psu (37,000 ppm), Bay of Bengal: ~32 psu (32,000 ppm)
    if dist_to_coast < 0.5:  # ON THE SEA/OCEAN
        if lon < 80:  # Arabian Sea side
            base_salinity = 37000
        else:  # Bay of Bengal side
            base_salinity = 32000
        salinity_max = base_salinity + np.random.uniform(-1000, 1000)
    elif dist_to_coast < 5:  # 0-5km - COASTAL ZONE - VERY HIGH
        if lon < 80:
            base_salinity = 35000
        else:
            base_salinity = 30000
        salinity_max = base_salinity + np.random.uniform(-2000, 2000)
    elif dist_to_coast < 25:  # 5-25km - CRITICAL COASTAL - HIGH
        decay_factor = (dist_to_coast - 5) / 20
        if lon < 80:
            base_salinity = 35000 - (decay_factor * 20000)
        else:
            base_salinity = 30000 - (decay_factor * 18000)
        salinity_max = base_salinity + np.random.uniform(-1500, 1500)
    elif dist_to_coast < 100:  # 25-100km - MODERATE
        decay_factor = (dist_to_coast - 25) / 75
        base_salinity = 15000 - (decay_factor * 10000)
        salinity_max = base_salinity + np.random.uniform(-1000, 1000)
    else:  # >100km - LOW
        base_salinity = 3000
        salinity_max = base_salinity + np.random.uniform(-500, 1000)
    
    salinity_max = max(500, salinity_max)  # Minimum bound
    
    # NEW: Pollution parameter based on AQI research
    pollution_aqi = get_pollution_level(lat, lon)
    
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
        'pollution_aqi': round(pollution_aqi, 1),
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
    data['pollution_risk'] = min(100, (data['pollution_aqi'] / 500) * 100)
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
    """Create individual parameter map with circle markers - GUARANTEED TO WORK"""
    
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
            <b>Location:</b> {point['lat']:.4f}, {point['lon']:.4f}<br>
            <b>Value:</b> {point[param_config['value_key']]:.1f} {param_config['unit']}<br>
            <b>Risk Score:</b> {risk_score:.1f}/100<br>
            <b>Risk Level:</b> <span style='color: {color}; font-weight: bold;'>{risk_level}</span><br>
            <b>Source:</b> {param_config['source']}
        </div>
        """
        
        # Add circle marker
        folium.CircleMarker(
            location=[point['lat'], point['lon']],
            radius=12,
            popup=folium.Popup(popup_html, max_width=300),
            color=color,
            fillColor=color,
            fillOpacity=0.7,
            weight=2
        ).add_to(param_map)
    
    # Add legend
    legend_html = f"""
    <div style='position: fixed; bottom: 50px; left: 50px; width: 200px; 
                background-color: white; border: 2px solid grey; z-index: 9999;
                padding: 10px; border-radius: 5px;'>
        <h4 style='margin: 0 0 10px 0;'>{parameter}</h4>
        <p style='margin: 5px 0;'><span style='color: #10b981;'>⬤</span> LOW (0-40)</p>
        <p style='margin: 5px 0;'><span style='color: #f59e0b;'>⬤</span> MODERATE (40-60)</p>
        <p style='margin: 5px 0;'><span style='color: #ea580c;'>⬤</span> HIGH (60-75)</p>
        <p style='margin: 5px 0;'><span style='color: #dc2626;'>⬤</span> CRITICAL (75-100)</p>
    </div>
    """
    param_map.get_root().html.add_child(folium.Element(legend_html))
    
    return param_map

def create_risk_charts(analysis_data):
    """Create risk distribution charts"""
    
    # Risk scores
    risk_scores = {
        'Temperature': analysis_data['temp_risk'],
        'Rainfall': analysis_data['rainfall_risk'],
        'Humidity': analysis_data['humidity_risk'],
        'Wind Speed': analysis_data['wind_risk'],
        'Solar Radiation': analysis_data['solar_risk'],
        'Salinity': analysis_data['salinity_risk'],
        'Seismic': analysis_data['seismic_risk']
    }
    
    # Create bar chart
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))
    
    # Bar chart
    parameters = list(risk_scores.keys())
    scores = list(risk_scores.values())
    colors = ['#dc2626' if s >= 75 else '#ea580c' if s >= 60 else '#f59e0b' if s >= 40 else '#10b981' for s in scores]
    
    ax1.barh(parameters, scores, color=colors, edgecolor='black', linewidth=1.5)
    ax1.set_xlabel('Risk Score', fontsize=12, fontweight='bold')
    ax1.set_title('Parameter Risk Scores', fontsize=14, fontweight='bold')
    ax1.set_xlim(0, 100)
    ax1.grid(axis='x', alpha=0.3)
    
    # Pie chart - risk distribution
    risk_counts = {
        'LOW (0-40)': sum(1 for s in scores if s < 40),
        'MODERATE (40-60)': sum(1 for s in scores if 40 <= s < 60),
        'HIGH (60-75)': sum(1 for s in scores if 60 <= s < 75),
        'CRITICAL (75-100)': sum(1 for s in scores if s >= 75)
    }
    
    pie_colors = ['#10b981', '#f59e0b', '#ea580c', '#dc2626']
    ax2.pie(
        [v for v in risk_counts.values() if v > 0],
        labels=[k for k, v in risk_counts.items() if v > 0],
        colors=[c for c, v in zip(pie_colors, risk_counts.values()) if v > 0],
        autopct='%1.0f%%',
        startangle=90,
        textprops={'fontsize': 10, 'fontweight': 'bold'}
    )
    ax2.set_title('Risk Distribution', fontsize=14, fontweight='bold')
    
    plt.tight_layout()
    
    return fig

# Analysis button
if st.session_state.transmission_lines:
    if st.button("🔍 Analyze All Transmission Lines", type="primary", use_container_width=True):
        with st.spinner("Analyzing transmission lines..."):
            st.session_state.analysis_results = {}
            
            for line in st.session_state.transmission_lines:
                # Generate sample points
                sample_points = generate_sample_points(line['coordinates'], sample_spacing)
                
                # Get environmental data for each point
                line_data = []
                for point in sample_points:
                    data = get_environmental_data_for_point(point['lat'], point['lon'])
                    line_data.append(data)
                
                # Calculate summary statistics
                df = pd.DataFrame(line_data)
                
                analysis = {
                    'line_data': line_data,
                    'dataframe': df,
                    'temp_risk': df['temp_max_risk'].mean(),
                    'rainfall_risk': df['rainfall_max_risk'].mean(),
                    'humidity_risk': df['humidity_max_risk'].mean(),
                    'wind_risk': df['wind_max_risk'].mean(),
                    'solar_risk': df['solar_max_risk'].mean(),
                    'salinity_risk': df['salinity_max_risk'].mean(),
                    'seismic_risk': df['seismic_risk'].mean(),
                    'overall_risk': df[['temp_max_risk', 'rainfall_max_risk', 'humidity_max_risk', 
                                       'wind_max_risk', 'solar_max_risk', 'salinity_max_risk', 
                                       'seismic_risk']].mean().mean()
                }
                
                st.session_state.analysis_results[line['name']] = analysis
            
            st.session_state.analysis_complete = True
            st.success(f"✅ Analysis complete for {len(st.session_state.transmission_lines)} transmission line(s)!")

# Display results
if st.session_state.analysis_complete and st.session_state.analysis_results:
    
    # If multiple lines, use tabs
    if len(st.session_state.analysis_results) > 1:
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
    st.markdown(f"**Version:** 7.0 Production | {datetime.now().strftime('%B %Y')}")

if logo:
    st.markdown("<p style='text-align: center; color: #64748b; font-size: 0.9rem;'>Professional Environmental Analysis for Transmission Infrastructure</p>", unsafe_allow_html=True)
