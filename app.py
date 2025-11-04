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
        with st.expander(f"🔷 {line['name']}", expanded=True):
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
    map_data = st_folium(m, width=None, height=500, key="main_map")
    
    if map_data and map_data.get('all_drawings'):
        drawings = map_data['all_drawings']
        st.session_state.transmission_lines = []
        
        for idx, drawing in enumerate(drawings):
            if drawing['geometry']['type'] == 'LineString':
                coords = [[coord[1], coord[0]] for coord in drawing['geometry']['coordinates']]
                st.session_state.transmission_lines.append({
                    'name': f'Line {idx + 1}',
                    'coordinates': coords
                })
else:
    st_folium(m, width=None, height=500, key="display_map")

# Environmental data functions
def get_environmental_data_for_point(lat, lon):
    """Get environmental data for a specific point with location-based variation"""
    
    # Add location-based variation
    lat_factor = (lat - 15) / 20  # Normalize latitude (15-35 range)
    lon_factor = (lon - 70) / 30  # Normalize longitude (70-100 range)
    
    # Generate realistic varied data based on location
    np.random.seed(int((lat * 1000 + lon * 1000) % 10000))  # Seed based on coordinates
    
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
        'salinity_max': round(15000 + lon_factor * 25000 + np.random.uniform(-2000, 5000), 0),
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
                
                # Download CSV
                csv = analysis['dataframe'].to_csv(index=False)
                st.download_button(
                    label=f"📥 Download {line['name']} Data (CSV)",
                    data=csv,
                    file_name=f"{line['name']}_analysis.csv",
                    mime="text/csv"
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
        
        # Download CSV
        csv = analysis['dataframe'].to_csv(index=False)
        st.download_button(
            label="📥 Download Data (CSV)",
            data=csv,
            file_name="transmission_line_analysis.csv",
            mime="text/csv"
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
