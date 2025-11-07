import streamlit as st
import folium
from folium import plugins
from streamlit_folium import st_folium
import numpy as np
import math
from datetime import datetime
import io
import matplotlib.pyplot as plt
import base64

# ReportLab imports
try:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.lib.enums import TA_CENTER, TA_LEFT
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, Image as RLImage
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False
    st.warning("ReportLab not available. PDF generation will be disabled.")

# Page config
st.set_page_config(page_title="Deccan Environmental Analysis", layout="wide", page_icon="🌍")

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        color: #1f77b4;
        text-align: center;
        padding: 1rem 0;
        font-weight: bold;
    }
    .sub-header {
        font-size: 1.5rem;
        color: #2c3e50;
        margin-top: 1rem;
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 2rem;
    }
    .risk-box {
        padding: 1rem;
        border-radius: 10px;
        margin: 0.5rem 0;
        text-align: center;
    }
    .risk-critical { background-color: #ff4444; color: white; }
    .risk-high { background-color: #ff8800; color: white; }
    .risk-moderate { background-color: #ffbb33; color: black; }
    .risk-low { background-color: #00C851; color: white; }
</style>
""", unsafe_allow_html=True)

# Initialize session state
if 'transmission_lines' not in st.session_state:
    st.session_state.transmission_lines = []
if 'drawn_lines' not in st.session_state:
    st.session_state.drawn_lines = []
if 'use_drawn_lines' not in st.session_state:
    st.session_state.use_drawn_lines = False

def get_risk_color(value, thresholds):
    """Determine risk color based on value and thresholds"""
    if value >= thresholds['critical']:
        return 'red'
    elif value >= thresholds['high']:
        return 'orange'
    elif value >= thresholds['moderate']:
        return 'yellow'
    return 'green'

def get_risk_level(value, thresholds):
    """Get risk level text"""
    if value >= thresholds['critical']:
        return 'Critical'
    elif value >= thresholds['high']:
        return 'High'
    elif value >= thresholds['moderate']:
        return 'Moderate'
    return 'Low'

# Comprehensive Indian coastline points (100+ points for accurate coastal detection)
INDIAN_COASTLINE_POINTS = [
    # Gujarat Coast (Gulf of Khambhat and Kutch)
    (23.0225, 72.5714), (22.4707, 69.6293), (22.8046, 70.0779), (23.0216, 70.1001),
    (22.7500, 69.5000), (22.5000, 69.3000), (22.3000, 69.1000), (22.1000, 68.9000),
    (21.9000, 68.8000), (21.7000, 68.7500), (21.5000, 68.8000), (21.3000, 69.0000),
    (21.1000, 69.2000), (21.0000, 69.4000), (20.9171, 70.3667), (20.8000, 70.5000),
    (20.7000, 70.7000), (20.6000, 70.9000), (20.7000, 71.1000), (20.9000, 71.3000),
    (21.1000, 71.5000), (21.3000, 71.7000), (21.5000, 71.9000), (21.7000, 72.0000),
    (21.9000, 72.1000), (22.1000, 72.2000), (22.3000, 72.3000), (22.5000, 72.4000),
    (22.7000, 72.5000), (22.9000, 72.6000), (23.1000, 72.7000),
    
    # Maharashtra Coast
    (18.9388, 72.8354), (18.5000, 72.9000), (18.0000, 73.0000), (17.5000, 73.1000),
    (17.0000, 73.3000), (16.5000, 73.5000), (16.0000, 73.7000), (15.8486, 73.8170),
    (15.5000, 74.0000), (15.3000, 74.1000),
    
    # Goa Coast
    (15.2993, 73.8278), (15.4000, 73.8000), (15.5000, 73.7500),
    
    # Karnataka Coast
    (14.8000, 74.1000), (14.5000, 74.3000), (14.0000, 74.5000), (13.5000, 74.7000),
    (13.0000, 74.8000), (12.9141, 74.8560),
    
    # Kerala Coast  
    (12.5000, 74.9000), (12.0000, 75.0000), (11.5000, 75.3000), (11.2588, 75.7804),
    (11.0000, 75.8000), (10.5000, 76.0000), (10.0000, 76.2000), (9.5000, 76.3000),
    (9.0000, 76.5000), (8.7379, 76.7419), (8.5000, 76.9000), (8.0883, 77.5385),
    
    # Tamil Nadu Coast (West & South)
    (8.0000, 77.6000), (8.0806, 77.5418), (8.1000, 77.7000), (8.2000, 78.0000),
    (8.5000, 78.1000), (8.7000, 78.1500), (9.0000, 78.2000), (9.2812, 78.1137),
    (9.5000, 78.3000), (9.9252, 78.1198), (10.0000, 78.5000), (10.5000, 79.0000),
    (10.7867, 79.8380), (11.0000, 79.8000), (11.5000, 79.7000),
    
    # Tamil Nadu Coast (East)
    (12.0000, 79.8000), (12.5000, 80.0000), (12.8000, 80.2000), (13.0827, 80.2707),
    (13.3000, 80.3000), (13.5000, 80.2000), (13.6000, 80.2500),
    
    # Andhra Pradesh Coast
    (14.0000, 80.2000), (14.5000, 80.0000), (15.0000, 80.1000), (15.5000, 80.3000),
    (15.8281, 80.2707), (16.0000, 80.4000), (16.5000, 80.6000), (17.0000, 80.8000),
    (17.6868, 83.2185), (17.5000, 82.5000), (17.8000, 83.0000), (18.0000, 83.3000),
    (18.5000, 83.8000), (18.9894, 84.2806),
    
    # Odisha Coast
    (19.3000, 84.8000), (19.5000, 85.0000), (19.8083, 85.8314), (20.0000, 86.0000),
    (20.2644, 85.8330), (20.5000, 86.1000), (20.9517, 87.0846), (21.0000, 87.2000),
    (21.5000, 87.5000),
    
    # West Bengal Coast
    (21.6417, 87.8667), (21.7000, 88.0000), (21.8000, 88.2000), (22.0000, 88.3000),
    (22.3000, 88.5000), (22.5725, 88.3639),
    
    # Additional points along major gulfs and bays
    (22.0000, 70.0000), (21.5000, 70.5000), (21.0000, 71.0000), (20.5000, 71.5000),
    (20.0000, 72.0000), (19.5000, 72.5000), (19.0000, 72.8000), (18.5000, 73.0000),
]

def get_distance_to_coast(lat, lon):
    """Calculate minimum distance to Indian coastline using comprehensive coastal points"""
    min_distance = float('inf')
    
    for coast_lat, coast_lon in INDIAN_COASTLINE_POINTS:
        # Haversine formula for distance
        dlat = math.radians(lat - coast_lat)
        dlon = math.radians(lon - coast_lon)
        a = math.sin(dlat/2)**2 + math.cos(math.radians(lat)) * math.cos(math.radians(coast_lat)) * math.sin(dlon/2)**2
        c = 2 * math.asin(math.sqrt(a))
        distance = 6371 * c  # Earth's radius in km
        
        min_distance = min(min_distance, distance)
    
    return min_distance

def get_environmental_data_for_point(lat, lon):
    """Generate realistic environmental data for a point with CRITICAL salinity near coast/sea"""
    # Use coordinates as seed for reproducible randomness
    np.random.seed(int((lat * 1000 + lon * 1000) % 10000))
    
    # Normalize coordinates (India bounds: lat 8-36, lon 68-97)
    lat_norm = (lat - 8) / 28  # 0 to 1
    lon_norm = (lon - 68) / 29  # 0 to 1
    
    # Gujarat-specific detection
    is_gujarat = (20.0 <= lat <= 24.7) and (68.0 <= lon <= 74.5)
    
    # Calculate distance to coast for CRITICAL salinity calculation
    distance_to_coast = get_distance_to_coast(lat, lon)
    
    # SALINITY - CRITICAL NEAR COAST/SEA (0-40,000 ppm)
    # Arabian Sea: ~37 psu (37,000 ppm), Bay of Bengal: ~32 psu (32,000 ppm)
    if distance_to_coast < 2:  # 0-2 km: ON THE SEA or IMMEDIATE COAST
        base_salinity = 37000 + np.random.randint(-2000, 2000)  # 35,000-39,000 ppm
    elif distance_to_coast < 10:  # 2-10 km: VERY CLOSE TO COAST
        base_salinity = 36000 + np.random.randint(-2000, 1000)  # 34,000-37,000 ppm
    elif distance_to_coast < 25:  # 10-25 km: COASTAL INFLUENCE ZONE
        decay = (distance_to_coast - 10) / 15  # 0 to 1
        base_salinity = 36000 - (decay * 11000) + np.random.randint(-1000, 1000)  # 25,000-36,000 ppm
    elif distance_to_coast < 75:  # 25-75 km: HIGH SALINITY ZONE
        decay = (distance_to_coast - 25) / 50  # 0 to 1
        base_salinity = 25000 - (decay * 13000) + np.random.randint(-1000, 1000)  # 12,000-25,000 ppm
    elif distance_to_coast < 150:  # 75-150 km: MODERATE ZONE
        decay = (distance_to_coast - 75) / 75  # 0 to 1
        base_salinity = 12000 - (decay * 7000) + np.random.randint(-500, 500)  # 5,000-12,000 ppm
    elif distance_to_coast < 250:  # 150-250 km: LOW INFLUENCE
        decay = (distance_to_coast - 150) / 100  # 0 to 1
        base_salinity = 5000 - (decay * 2000) + np.random.randint(-300, 300)  # 3,000-5,000 ppm
    else:  # > 250 km: INLAND
        base_salinity = 3000 + np.random.randint(-500, 1000)  # 2,500-4,000 ppm
    
    # Gujarat gets additional salinity boost (industrial + coastal)
    if is_gujarat:
        base_salinity += 7000
    
    salinity_ppm = max(2500, min(40000, base_salinity))
    
    # TEMPERATURE (25-50°C) - Northern areas hotter
    base_temp = 35 + (lat_norm * 15)  # 35-50°C
    if is_gujarat:
        base_temp += 3  # Gujarat summer boost
    temperature = base_temp + np.random.randint(-3, 3)
    temperature = max(25, min(50, temperature))
    
    # RAINFALL (200-3000mm) - Eastern and coastal areas get more
    base_rainfall = 800 + (lon_norm * 600) + (distance_to_coast < 50) * 400
    rainfall = base_rainfall + np.random.randint(-100, 200)
    rainfall = max(200, min(3000, rainfall))
    
    # HUMIDITY (40-95%) - Coastal and eastern areas more humid
    base_humidity = 70 + (lon_norm * 20) + (distance_to_coast < 50) * 10
    if is_gujarat:
        base_humidity += 8  # Coastal humidity boost
    humidity = base_humidity + np.random.randint(-5, 10)
    humidity = max(40, min(95, humidity))
    
    # WIND SPEED (20-120 km/h) - Higher in northern plains
    base_wind = 55 + (lat_norm * 20)
    wind_speed = base_wind + np.random.randint(-5, 15)
    wind_speed = max(20, min(120, wind_speed))
    
    # SOLAR RADIATION (3-9 kWh/m²/day) - Higher in north and arid areas
    base_solar = 6.0 + (lat_norm * 2)
    if is_gujarat:
        base_solar += 0.5  # High solar in Gujarat
    solar = base_solar + np.random.uniform(-0.5, 1.0)
    solar = max(3.0, min(9.0, solar))
    
    # SEISMIC ZONE (1-5) - Northern (Himalayan) areas higher
    seismic_base = 3 + (lat_norm * 2)
    seismic_zone = int(min(5, max(1, seismic_base)))
    
    # POLLUTION (AQI 50-120) - MEDIUM TO HIGH ONLY
    # Major polluted cities in India with typical AQI
    polluted_cities = [
        (28.7041, 77.1025, 90),   # Delhi NCR
        (28.6139, 77.2090, 88),   # New Delhi
        (28.4595, 77.0266, 92),   # Gurgaon
        (28.6692, 77.4538, 85),   # Noida
        (28.8386, 77.0426, 87),   # Rohini
        (26.4499, 80.3319, 80),   # Kanpur
        (28.4089, 77.3178, 83),   # Faridabad
        (25.4358, 81.8463, 78),   # Prayagraj
        (25.3176, 82.9739, 76),   # Varanasi
        (26.8467, 80.9462, 75),   # Lucknow
        (23.0225, 72.5714, 72),   # Ahmedabad
        (21.1702, 72.8311, 68),   # Surat
        (22.5726, 88.3639, 73),   # Kolkata
        (22.7196, 75.8577, 70),   # Indore
        (23.2599, 77.4126, 69),   # Bhopal
        (26.9124, 75.7873, 71),   # Jaipur
        (19.0760, 72.8777, 68),   # Mumbai
        (18.5204, 73.8567, 67),   # Pune
        (21.1458, 79.0882, 70),   # Nagpur
        (17.3850, 78.4867, 69),   # Hyderabad
        (13.0827, 80.2707, 66),   # Chennai
        (12.9716, 77.5946, 65),   # Bangalore
        (11.0168, 76.9558, 62),   # Coimbatore
        (22.2587, 70.7813, 75),   # Morbi (Gujarat ceramic hub)
        (23.0300, 72.5800, 74),   # Mehsana
        (22.3072, 73.1812, 72),   # Vadodara
        (21.7645, 72.1519, 70),   # Bharuch
        (23.1645, 69.6669, 68),   # Bhuj
        (20.5937, 78.9629, 67),   # India center
    ]
    
    # Calculate weighted AQI based on distance to polluted cities
    total_weight = 0
    weighted_aqi = 0
    
    for city_lat, city_lon, city_aqi in polluted_cities:
        distance = math.sqrt((lat - city_lat)**2 + (lon - city_lon)**2)
        if distance < 5:  # Within 5 degrees (~550km)
            weight = 1 / (distance + 0.1)**2  # Inverse square distance weighting
            weighted_aqi += city_aqi * weight
            total_weight += weight
    
    if total_weight > 0:
        calculated_aqi = weighted_aqi / total_weight
    else:
        calculated_aqi = 55  # Rural baseline (medium)
    
    # Blend with medium baseline and add Gujarat industrial boost
    base_aqi = calculated_aqi * 0.7 + 60 * 0.3  # Blend with medium baseline
    if is_gujarat:
        base_aqi += 15  # Industrial pollution boost
    
    # Final AQI: 50-120 range (Medium to High only)
    pollution_aqi = base_aqi + np.random.randint(-8, 12)
    pollution_aqi = max(50, min(120, pollution_aqi))
    
    return {
        'temperature': round(temperature, 1),
        'rainfall': round(rainfall, 1),
        'humidity': round(humidity, 1),
        'wind_speed': round(wind_speed, 1),
        'solar_radiation': round(solar, 1),
        'salinity_ppm': round(salinity_ppm, 0),
        'seismic_zone': seismic_zone,
        'pollution_aqi': round(pollution_aqi, 0),
        'distance_to_coast': round(distance_to_coast, 1)
    }

def calculate_risk_score(value, param_type):
    """Calculate risk score (0-100) based on parameter type and value"""
    thresholds = {
        'temperature': {'min': 25, 'max': 50, 'critical': 45, 'high': 40, 'moderate': 35},
        'rainfall': {'min': 200, 'max': 3000, 'critical': 2500, 'high': 2000, 'moderate': 1500},
        'humidity': {'min': 40, 'max': 95, 'critical': 85, 'high': 75, 'moderate': 65},
        'wind_speed': {'min': 20, 'max': 120, 'critical': 100, 'high': 80, 'moderate': 60},
        'solar_radiation': {'min': 3, 'max': 9, 'critical': 8, 'high': 7, 'moderate': 6},
        'salinity_ppm': {'min': 2500, 'max': 40000, 'critical': 30000, 'high': 20000, 'moderate': 10000},
        'seismic_zone': {'min': 1, 'max': 5, 'critical': 5, 'high': 4, 'moderate': 3},
        'pollution_aqi': {'min': 50, 'max': 120, 'critical': 100, 'high': 80, 'moderate': 60}
    }
    
    if param_type not in thresholds:
        return 50
    
    t = thresholds[param_type]
    normalized = ((value - t['min']) / (t['max'] - t['min'])) * 100
    return max(0, min(100, normalized))

def analyze_transmission_line(coords, line_name):
    """Analyze environmental parameters along transmission line"""
    analysis_results = []
    
    for i in range(len(coords)):
        lat, lon = coords[i]
        env_data = get_environmental_data_for_point(lat, lon)
        
        # Calculate risk scores for each parameter
        temp_risk = calculate_risk_score(env_data['temperature'], 'temperature')
        rainfall_risk = calculate_risk_score(env_data['rainfall'], 'rainfall')
        humidity_risk = calculate_risk_score(env_data['humidity'], 'humidity')
        wind_risk = calculate_risk_score(env_data['wind_speed'], 'wind_speed')
        solar_risk = calculate_risk_score(env_data['solar_radiation'], 'solar_radiation')
        salinity_risk = calculate_risk_score(env_data['salinity_ppm'], 'salinity_ppm')
        seismic_risk = (env_data['seismic_zone'] - 1) * 25  # Zone 1=0, Zone 5=100
        pollution_risk = calculate_risk_score(env_data['pollution_aqi'], 'pollution_aqi')
        
        # Calculate overall risk (weighted average)
        overall_risk = (
            temp_risk * 0.15 +
            rainfall_risk * 0.10 +
            humidity_risk * 0.15 +
            wind_risk * 0.15 +
            solar_risk * 0.10 +
            salinity_risk * 0.20 +  # Highest weight
            seismic_risk * 0.10 +
            pollution_risk * 0.05
        )
        
        analysis_results.append({
            'point_index': i + 1,
            'lat': lat,
            'lon': lon,
            'temperature': env_data['temperature'],
            'temp_risk': temp_risk,
            'rainfall': env_data['rainfall'],
            'rainfall_risk': rainfall_risk,
            'humidity': env_data['humidity'],
            'humidity_risk': humidity_risk,
            'wind_speed': env_data['wind_speed'],
            'wind_risk': wind_risk,
            'solar_radiation': env_data['solar_radiation'],
            'solar_risk': solar_risk,
            'salinity_ppm': env_data['salinity_ppm'],
            'salinity_risk': salinity_risk,
            'seismic_zone': env_data['seismic_zone'],
            'seismic_risk': seismic_risk,
            'pollution_aqi': env_data['pollution_aqi'],
            'pollution_risk': pollution_risk,
            'distance_to_coast': env_data['distance_to_coast'],
            'overall_risk': overall_risk
        })
    
    return analysis_results

def create_risk_charts(analysis_results):
    """Create comprehensive and appealing risk visualization charts"""
    # Extract data
    points = [r['point_index'] for r in analysis_results]
    temp_risks = [r['temp_risk'] for r in analysis_results]
    rainfall_risks = [r['rainfall_risk'] for r in analysis_results]
    humidity_risks = [r['humidity_risk'] for r in analysis_results]
    wind_risks = [r['wind_risk'] for r in analysis_results]
    solar_risks = [r['solar_risk'] for r in analysis_results]
    salinity_risks = [r['salinity_risk'] for r in analysis_results]
    seismic_risks = [r['seismic_risk'] for r in analysis_results]
    pollution_risks = [r['pollution_risk'] for r in analysis_results]
    overall_risks = [r['overall_risk'] for r in analysis_results]
    
    # Color scheme
    colors_palette = ['#FF6B6B', '#4ECDC4', '#45B7D1', '#FFA07A', '#98D8C8', '#F7DC6F', '#BB8FCE', '#85C1E2']
    
    # Create figure with multiple subplots
    fig = plt.figure(figsize=(20, 16))
    
    # 1. Overall Risk Distribution Along Line (Line Plot with Fill)
    ax1 = plt.subplot(3, 3, 1)
    ax1.plot(points, overall_risks, linewidth=3, color='#E74C3C', marker='o', markersize=8, label='Overall Risk')
    ax1.fill_between(points, overall_risks, alpha=0.3, color='#E74C3C')
    ax1.axhline(y=75, color='red', linestyle='--', alpha=0.5, label='Critical (75)')
    ax1.axhline(y=50, color='orange', linestyle='--', alpha=0.5, label='High (50)')
    ax1.axhline(y=25, color='yellow', linestyle='--', alpha=0.5, label='Moderate (25)')
    ax1.set_xlabel('Point Along Line', fontsize=12, fontweight='bold')
    ax1.set_ylabel('Risk Score', fontsize=12, fontweight='bold')
    ax1.set_title('Overall Risk Distribution', fontsize=14, fontweight='bold', pad=15)
    ax1.grid(True, alpha=0.3, linestyle='--')
    ax1.legend(loc='upper right', fontsize=9)
    ax1.set_ylim([0, 100])
    
    # 2. Risk Category Pie Chart
    ax2 = plt.subplot(3, 3, 2)
    risk_categories = {'Critical (75-100)': 0, 'High (50-75)': 0, 'Moderate (25-50)': 0, 'Low (0-25)': 0}
    for risk in overall_risks:
        if risk >= 75:
            risk_categories['Critical (75-100)'] += 1
        elif risk >= 50:
            risk_categories['High (50-75)'] += 1
        elif risk >= 25:
            risk_categories['Moderate (25-50)'] += 1
        else:
            risk_categories['Low (0-25)'] += 1
    
    colors_pie = ['#E74C3C', '#F39C12', '#F4D03F', '#52BE80']
    wedges, texts, autotexts = ax2.pie(risk_categories.values(), labels=risk_categories.keys(), 
                                        autopct='%1.1f%%', colors=colors_pie, startangle=90,
                                        textprops={'fontsize': 11, 'weight': 'bold'})
    ax2.set_title('Risk Category Distribution', fontsize=14, fontweight='bold', pad=15)
    
    # 3. Parameter Comparison Bar Chart
    ax3 = plt.subplot(3, 3, 3)
    avg_risks = {
        'Temp': np.mean(temp_risks),
        'Rain': np.mean(rainfall_risks),
        'Humid': np.mean(humidity_risks),
        'Wind': np.mean(wind_risks),
        'Solar': np.mean(solar_risks),
        'Salin': np.mean(salinity_risks),
        'Seism': np.mean(seismic_risks),
        'Pollut': np.mean(pollution_risks)
    }
    bars = ax3.bar(avg_risks.keys(), avg_risks.values(), color=colors_palette, edgecolor='black', linewidth=1.5)
    ax3.set_ylabel('Average Risk Score', fontsize=12, fontweight='bold')
    ax3.set_title('Average Risk by Parameter', fontsize=14, fontweight='bold', pad=15)
    ax3.grid(True, axis='y', alpha=0.3, linestyle='--')
    ax3.set_ylim([0, 100])
    for bar in bars:
        height = bar.get_height()
        ax3.text(bar.get_x() + bar.get_width()/2., height,
                f'{height:.1f}', ha='center', va='bottom', fontsize=10, fontweight='bold')
    
    # 4. Heatmap of All Parameters Along Line
    ax4 = plt.subplot(3, 3, 4)
    risk_matrix = np.array([
        temp_risks, rainfall_risks, humidity_risks, wind_risks,
        solar_risks, salinity_risks, seismic_risks, pollution_risks
    ])
    im = ax4.imshow(risk_matrix, cmap='RdYlGn_r', aspect='auto', vmin=0, vmax=100)
    ax4.set_yticks(range(8))
    ax4.set_yticklabels(['Temp', 'Rain', 'Humid', 'Wind', 'Solar', 'Salin', 'Seism', 'Pollut'], fontsize=11)
    ax4.set_xlabel('Point Along Line', fontsize=12, fontweight='bold')
    ax4.set_title('Risk Heatmap (All Parameters)', fontsize=14, fontweight='bold', pad=15)
    plt.colorbar(im, ax=ax4, label='Risk Score')
    
    # 5. Salinity Risk Detailed View
    ax5 = plt.subplot(3, 3, 5)
    ax5.plot(points, salinity_risks, linewidth=3, color='#3498DB', marker='s', markersize=8)
    ax5.fill_between(points, salinity_risks, alpha=0.3, color='#3498DB')
    ax5.axhline(y=75, color='red', linestyle='--', alpha=0.5)
    ax5.axhline(y=50, color='orange', linestyle='--', alpha=0.5)
    ax5.set_xlabel('Point Along Line', fontsize=12, fontweight='bold')
    ax5.set_ylabel('Salinity Risk Score', fontsize=12, fontweight='bold')
    ax5.set_title('Salinity Risk (Critical for Insulators)', fontsize=14, fontweight='bold', pad=15)
    ax5.grid(True, alpha=0.3, linestyle='--')
    ax5.set_ylim([0, 100])
    
    # 6. Statistical Distribution Box Plot
    ax6 = plt.subplot(3, 3, 6)
    risk_data = [temp_risks, rainfall_risks, humidity_risks, wind_risks, 
                 solar_risks, salinity_risks, seismic_risks, pollution_risks]
    bp = ax6.boxplot(risk_data, labels=['Temp', 'Rain', 'Humid', 'Wind', 'Solar', 'Salin', 'Seism', 'Pollut'],
                     patch_artist=True, notch=True, showmeans=True)
    for patch, color in zip(bp['boxes'], colors_palette):
        patch.set_facecolor(color)
        patch.set_alpha(0.7)
    ax6.set_ylabel('Risk Score', fontsize=12, fontweight='bold')
    ax6.set_title('Risk Distribution Statistics', fontsize=14, fontweight='bold', pad=15)
    ax6.grid(True, axis='y', alpha=0.3, linestyle='--')
    ax6.set_ylim([0, 100])
    
    # 7. Multi-Parameter Line Plot
    ax7 = plt.subplot(3, 3, 7)
    ax7.plot(points, temp_risks, label='Temperature', linewidth=2, marker='o', color=colors_palette[0])
    ax7.plot(points, humidity_risks, label='Humidity', linewidth=2, marker='s', color=colors_palette[1])
    ax7.plot(points, salinity_risks, label='Salinity', linewidth=2, marker='^', color=colors_palette[2])
    ax7.plot(points, pollution_risks, label='Pollution', linewidth=2, marker='d', color=colors_palette[3])
    ax7.set_xlabel('Point Along Line', fontsize=12, fontweight='bold')
    ax7.set_ylabel('Risk Score', fontsize=12, fontweight='bold')
    ax7.set_title('Key Parameter Trends', fontsize=14, fontweight='bold', pad=15)
    ax7.legend(loc='best', fontsize=10)
    ax7.grid(True, alpha=0.3, linestyle='--')
    ax7.set_ylim([0, 100])
    
    # 8. Risk Scatter Plot (Overall vs Salinity)
    ax8 = plt.subplot(3, 3, 8)
    scatter = ax8.scatter(salinity_risks, overall_risks, c=points, cmap='viridis', 
                         s=150, alpha=0.7, edgecolors='black', linewidth=1.5)
    ax8.set_xlabel('Salinity Risk', fontsize=12, fontweight='bold')
    ax8.set_ylabel('Overall Risk', fontsize=12, fontweight='bold')
    ax8.set_title('Salinity vs Overall Risk Correlation', fontsize=14, fontweight='bold', pad=15)
    ax8.grid(True, alpha=0.3, linestyle='--')
    plt.colorbar(scatter, ax=ax8, label='Point Number')
    
    # 9. Summary Statistics Table
    ax9 = plt.subplot(3, 3, 9)
    ax9.axis('off')
    summary_data = [
        ['Parameter', 'Min', 'Max', 'Avg', 'StdDev'],
        ['Temperature', f'{min(temp_risks):.1f}', f'{max(temp_risks):.1f}', f'{np.mean(temp_risks):.1f}', f'{np.std(temp_risks):.1f}'],
        ['Rainfall', f'{min(rainfall_risks):.1f}', f'{max(rainfall_risks):.1f}', f'{np.mean(rainfall_risks):.1f}', f'{np.std(rainfall_risks):.1f}'],
        ['Humidity', f'{min(humidity_risks):.1f}', f'{max(humidity_risks):.1f}', f'{np.mean(humidity_risks):.1f}', f'{np.std(humidity_risks):.1f}'],
        ['Wind', f'{min(wind_risks):.1f}', f'{max(wind_risks):.1f}', f'{np.mean(wind_risks):.1f}', f'{np.std(wind_risks):.1f}'],
        ['Solar', f'{min(solar_risks):.1f}', f'{max(solar_risks):.1f}', f'{np.mean(solar_risks):.1f}', f'{np.std(solar_risks):.1f}'],
        ['Salinity', f'{min(salinity_risks):.1f}', f'{max(salinity_risks):.1f}', f'{np.mean(salinity_risks):.1f}', f'{np.std(salinity_risks):.1f}'],
        ['Seismic', f'{min(seismic_risks):.1f}', f'{max(seismic_risks):.1f}', f'{np.mean(seismic_risks):.1f}', f'{np.std(seismic_risks):.1f}'],
        ['Pollution', f'{min(pollution_risks):.1f}', f'{max(pollution_risks):.1f}', f'{np.mean(pollution_risks):.1f}', f'{np.std(pollution_risks):.1f}'],
        ['Overall', f'{min(overall_risks):.1f}', f'{max(overall_risks):.1f}', f'{np.mean(overall_risks):.1f}', f'{np.std(overall_risks):.1f}']
    ]
    
    table = ax9.table(cellText=summary_data, cellLoc='center', loc='center',
                     colWidths=[0.25, 0.15, 0.15, 0.15, 0.15])
    table.auto_set_font_size(False)
    table.set_fontsize(10)
    table.scale(1, 2.5)
    
    # Style header row
    for i in range(5):
        table[(0, i)].set_facecolor('#34495E')
        table[(0, i)].set_text_props(weight='bold', color='white')
    
    # Alternate row colors
    for i in range(1, len(summary_data)):
        for j in range(5):
            if i % 2 == 0:
                table[(i, j)].set_facecolor('#ECF0F1')
            else:
                table[(i, j)].set_facecolor('#FFFFFF')
    
    ax9.set_title('Statistical Summary', fontsize=14, fontweight='bold', pad=15)
    
    plt.tight_layout(pad=3.0)
    return fig

def create_map_with_analysis(transmission_lines):
    """Create folium map with transmission lines and analysis"""
    # Calculate center of all lines
    all_coords = []
    for line in transmission_lines:
        all_coords.extend(line['coords'])
    
    if not all_coords:
        center_lat, center_lon = 20.5937, 78.9629  # Center of India
    else:
        center_lat = sum(c[0] for c in all_coords) / len(all_coords)
        center_lon = sum(c[1] for c in all_coords) / len(all_coords)
    
    # Create map
    m = folium.Map(
        location=[center_lat, center_lon],
        zoom_start=6,
        tiles='OpenStreetMap',
        control_scale=True
    )
    
    # Add drawing tools
    draw = plugins.Draw(
        draw_options={
            'polyline': {
                'allowIntersection': False,
                'shapeOptions': {
                    'color': '#0000FF',
                    'weight': 4,
                    'opacity': 0.8
                }
            },
            'polygon': False,
            'rectangle': False,
            'circle': False,
            'marker': False,
            'circlemarker': False
        },
        edit_options={'edit': False}
    )
    draw.add_to(m)
    
    # Color palette for multiple lines
    colors = ['blue', 'red', 'green', 'orange', 'purple', 'darkred', 'darkblue', 'darkgreen']
    
    # Plot each transmission line
    for idx, line in enumerate(transmission_lines):
        line_color = colors[idx % len(colors)]
        coords = line['coords']
        line_name = line['name']
        
        # Draw the line
        folium.PolyLine(
            coords,
            color=line_color,
            weight=4,
            opacity=0.8,
            popup=f"<b>{line_name}</b><br>Points: {len(coords)}",
            tooltip=line_name
        ).add_to(m)
        
        # Add markers at each analysis point
        analysis = line.get('analysis', [])
        for point_data in analysis:
            # Determine marker color based on overall risk
            risk = point_data['overall_risk']
            if risk >= 75:
                marker_color = 'red'
                risk_level = 'Critical'
            elif risk >= 50:
                marker_color = 'orange'
                risk_level = 'High'
            elif risk >= 25:
                marker_color = 'yellow'
                risk_level = 'Moderate'
            else:
                marker_color = 'green'
                risk_level = 'Low'
            
            # Create detailed popup
            popup_html = f"""
            <div style="font-family: Arial; min-width: 250px;">
                <h4 style="margin: 0 0 10px 0; color: {marker_color};">{line_name} - Point {point_data['point_index']}</h4>
                <table style="width: 100%; font-size: 12px;">
                    <tr><td><b>Overall Risk:</b></td><td style="color: {marker_color};"><b>{risk:.1f} ({risk_level})</b></td></tr>
                    <tr><td colspan="2"><hr style="margin: 5px 0;"></td></tr>
                    <tr><td><b>Temperature:</b></td><td>{point_data['temperature']}°C ({point_data['temp_risk']:.1f})</td></tr>
                    <tr><td><b>Rainfall:</b></td><td>{point_data['rainfall']}mm ({point_data['rainfall_risk']:.1f})</td></tr>
                    <tr><td><b>Humidity:</b></td><td>{point_data['humidity']}% ({point_data['humidity_risk']:.1f})</td></tr>
                    <tr><td><b>Wind Speed:</b></td><td>{point_data['wind_speed']} km/h ({point_data['wind_risk']:.1f})</td></tr>
                    <tr><td><b>Solar Rad:</b></td><td>{point_data['solar_radiation']} kWh/m²/day ({point_data['solar_risk']:.1f})</td></tr>
                    <tr><td><b>Salinity:</b></td><td>{point_data['salinity_ppm']} ppm ({point_data['salinity_risk']:.1f})</td></tr>
                    <tr><td><b>Seismic Zone:</b></td><td>Zone {point_data['seismic_zone']} ({point_data['seismic_risk']:.1f})</td></tr>
                    <tr><td><b>Pollution (AQI):</b></td><td>{point_data['pollution_aqi']} ({point_data['pollution_risk']:.1f})</td></tr>
                    <tr><td><b>Coast Dist:</b></td><td>{point_data['distance_to_coast']:.1f} km</td></tr>
                </table>
            </div>
            """
            
            folium.CircleMarker(
                location=[point_data['lat'], point_data['lon']],
                radius=8,
                popup=folium.Popup(popup_html, max_width=300),
                color='black',
                fillColor=marker_color,
                fillOpacity=0.9,
                weight=2
            ).add_to(m)
    
    # Add legend
    legend_html = '''
    <div style="position: fixed; 
                bottom: 50px; right: 50px; 
                border:2px solid grey; z-index:9999; 
                background-color:white;
                padding: 10px;
                font-size: 14px;
                font-family: Arial;">
        <p style="margin: 0; font-weight: bold;">Risk Levels</p>
        <p style="margin: 5px 0;"><span style="color: red;">●</span> Critical (75-100)</p>
        <p style="margin: 5px 0;"><span style="color: orange;">●</span> High (50-75)</p>
        <p style="margin: 5px 0;"><span style="color: yellow;">●</span> Moderate (25-50)</p>
        <p style="margin: 5px 0;"><span style="color: green;">●</span> Low (0-25)</p>
    </div>
    '''
    m.get_root().html.add_child(folium.Element(legend_html))
    
    return m

def create_parameter_maps(analysis_results, line_name, line_color):
    """Create individual parameter maps"""
    if not analysis_results:
        return {}
    
    # Calculate center
    center_lat = sum(r['lat'] for r in analysis_results) / len(analysis_results)
    center_lon = sum(r['lon'] for r in analysis_results) / len(analysis_results)
    
    # Parameter configurations
    param_configs = {
        'Temperature (°C) 🌡️': {
            'values': [r['temperature'] for r in analysis_results],
            'risks': [r['temp_risk'] for r in analysis_results],
            'unit': '°C',
            'thresholds': {'critical': 45, 'high': 40, 'moderate': 35}
        },
        'Rainfall (mm) 🌧️': {
            'values': [r['rainfall'] for r in analysis_results],
            'risks': [r['rainfall_risk'] for r in analysis_results],
            'unit': 'mm',
            'thresholds': {'critical': 2500, 'high': 2000, 'moderate': 1500}
        },
        'Humidity (%) 💧': {
            'values': [r['humidity'] for r in analysis_results],
            'risks': [r['humidity_risk'] for r in analysis_results],
            'unit': '%',
            'thresholds': {'critical': 85, 'high': 75, 'moderate': 65}
        },
        'Wind Speed (km/h) 💨': {
            'values': [r['wind_speed'] for r in analysis_results],
            'risks': [r['wind_risk'] for r in analysis_results],
            'unit': 'km/h',
            'thresholds': {'critical': 100, 'high': 80, 'moderate': 60}
        },
        'Solar Radiation (kWh/m²/day) ☀️': {
            'values': [r['solar_radiation'] for r in analysis_results],
            'risks': [r['solar_risk'] for r in analysis_results],
            'unit': 'kWh/m²/day',
            'thresholds': {'critical': 8, 'high': 7, 'moderate': 6}
        },
        'Salinity (ppm) 🌊': {
            'values': [r['salinity_ppm'] for r in analysis_results],
            'risks': [r['salinity_risk'] for r in analysis_results],
            'unit': 'ppm',
            'thresholds': {'critical': 30000, 'high': 20000, 'moderate': 10000}
        },
        'Seismic Zone ⚠️': {
            'values': [r['seismic_zone'] for r in analysis_results],
            'risks': [r['seismic_risk'] for r in analysis_results],
            'unit': 'Zone',
            'thresholds': {'critical': 5, 'high': 4, 'moderate': 3}
        },
        'Pollution (AQI) 🏭': {
            'values': [r['pollution_aqi'] for r in analysis_results],
            'risks': [r['pollution_risk'] for r in analysis_results],
            'unit': 'AQI',
            'thresholds': {'critical': 100, 'high': 80, 'moderate': 60}
        }
    }
    
    maps = {}
    
    for param_name, config in param_configs.items():
        m = folium.Map(
            location=[center_lat, center_lon],
            zoom_start=7,
            tiles='OpenStreetMap'
        )
        
        # Draw line
        coords = [[r['lat'], r['lon']] for r in analysis_results]
        folium.PolyLine(
            coords,
            color=line_color,
            weight=3,
            opacity=0.7
        ).add_to(m)
        
        # Add markers
        for i, result in enumerate(analysis_results):
            value = config['values'][i]
            risk = config['risks'][i]
            
            # Determine color
            if value >= config['thresholds']['critical']:
                marker_color = 'red'
                risk_level = 'Critical'
            elif value >= config['thresholds']['high']:
                marker_color = 'orange'
                risk_level = 'High'
            elif value >= config['thresholds']['moderate']:
                marker_color = 'yellow'
                risk_level = 'Moderate'
            else:
                marker_color = 'green'
                risk_level = 'Low'
            
            popup_html = f"""
            <div style="font-family: Arial;">
                <h4 style="margin: 0;">{line_name} - Point {i+1}</h4>
                <p style="margin: 5px 0;"><b>{param_name.split('(')[0]}:</b> {value} {config['unit']}</p>
                <p style="margin: 5px 0;"><b>Risk Score:</b> {risk:.1f}</p>
                <p style="margin: 5px 0; color: {marker_color};"><b>Level:</b> {risk_level}</p>
            </div>
            """
            
            folium.CircleMarker(
                location=[result['lat'], result['lon']],
                radius=6,
                popup=folium.Popup(popup_html, max_width=250),
                color='black',
                fillColor=marker_color,
                fillOpacity=0.9,
                weight=2
            ).add_to(m)
        
        maps[param_name] = m
    
    return maps

def generate_pdf_report(transmission_lines):
    """Generate comprehensive PDF report"""
    if not REPORTLAB_AVAILABLE:
        st.error("ReportLab is not available. Cannot generate PDF report.")
        return None
    
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=0.5*inch, bottomMargin=0.5*inch)
    story = []
    styles = getSampleStyleSheet()
    
    # Custom styles
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Title'],
        fontSize=24,
        textColor=colors.HexColor('#1f77b4'),
        spaceAfter=30,
        alignment=TA_CENTER,
        fontName='Helvetica-Bold'
    )
    
    heading_style = ParagraphStyle(
        'CustomHeading',
        parent=styles['Heading1'],
        fontSize=16,
        textColor=colors.HexColor('#2c3e50'),
        spaceAfter=12,
        spaceBefore=12,
        fontName='Helvetica-Bold'
    )
    
    # Title
    story.append(Paragraph("Transmission Line Environmental Analysis Report", title_style))
    story.append(Paragraph(f"Generated on: {datetime.now().strftime('%B %d, %Y at %H:%M')}", styles['Normal']))
    story.append(Spacer(1, 0.3*inch))
    
    # Add logo
    try:
        logo_path = "logo.png"
        logo = RLImage(logo_path, width=2*inch, height=1*inch)
        story.append(logo)
        story.append(Spacer(1, 0.2*inch))
    except:
        pass
    
    # For each transmission line
    for idx, line in enumerate(transmission_lines):
        if idx > 0:
            story.append(PageBreak())
        
        line_name = line['name']
        analysis = line['analysis']
        
        # Line header
        story.append(Paragraph(f"Transmission Line: {line_name}", heading_style))
        story.append(Paragraph(f"Total Analysis Points: {len(analysis)}", styles['Normal']))
        story.append(Spacer(1, 0.2*inch))
        
        # Calculate average risks
        avg_overall = np.mean([r['overall_risk'] for r in analysis])
        avg_salinity = np.mean([r['salinity_risk'] for r in analysis])
        avg_temp = np.mean([r['temp_risk'] for r in analysis])
        
        # Summary table
        summary_data = [
            ['Parameter', 'Average Risk', 'Risk Level'],
            ['Overall Risk', f'{avg_overall:.1f}', get_risk_level(avg_overall, {'critical': 75, 'high': 50, 'moderate': 25})],
            ['Salinity', f'{avg_salinity:.1f}', get_risk_level(avg_salinity, {'critical': 75, 'high': 50, 'moderate': 25})],
            ['Temperature', f'{avg_temp:.1f}', get_risk_level(avg_temp, {'critical': 75, 'high': 50, 'moderate': 25})]
        ]
        
        summary_table = Table(summary_data, colWidths=[2.5*inch, 1.5*inch, 1.5*inch])
        summary_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        
        story.append(summary_table)
        story.append(Spacer(1, 0.3*inch))
        
        # Detailed analysis table
        story.append(Paragraph("Detailed Point Analysis", heading_style))
        
        # Create detailed table (first 10 points)
        detail_data = [['Point', 'Temp (°C)', 'Humidity (%)', 'Salinity (ppm)', 'Pollution (AQI)', 'Overall Risk']]
        for i, result in enumerate(analysis[:10]):  # Limit to first 10 points
            detail_data.append([
                str(result['point_index']),
                f"{result['temperature']:.1f}",
                f"{result['humidity']:.1f}",
                f"{result['salinity_ppm']:.0f}",
                f"{result['pollution_aqi']:.0f}",
                f"{result['overall_risk']:.1f}"
            ])
        
        detail_table = Table(detail_data, colWidths=[0.8*inch, 1.2*inch, 1.2*inch, 1.4*inch, 1.3*inch, 1.3*inch])
        detail_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1f77b4')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
            ('BACKGROUND', (0, 1), (-1, -1), colors.white),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey)
        ]))
        
        story.append(detail_table)
        
        # Add risk charts
        story.append(Spacer(1, 0.3*inch))
        story.append(Paragraph("Risk Analysis Charts", heading_style))
        
        fig = create_risk_charts(analysis)
        img_buffer = io.BytesIO()
        fig.savefig(img_buffer, format='png', dpi=150, bbox_inches='tight')
        img_buffer.seek(0)
        plt.close(fig)
        
        chart_image = RLImage(img_buffer, width=7*inch, height=5.5*inch)
        story.append(chart_image)
    
    # Build PDF
    doc.build(story)
    buffer.seek(0)
    return buffer

# Main app
st.markdown('<h1 class="main-header">🌍 Deccan Environmental Analysis System</h1>', unsafe_allow_html=True)

# Add Clear Coordinates button at the top
col1, col2, col3 = st.columns([1, 2, 1])
with col2:
    if st.button("🗑️ Clear All Coordinates & Reset", type="primary", use_container_width=True):
        st.session_state.transmission_lines = []
        st.session_state.drawn_lines = []
        st.session_state.use_drawn_lines = False
        st.rerun()

st.markdown("---")

# Input methods
input_method = st.radio(
    "Select Input Method:",
    ["Enter Coordinates Manually", "Draw on Map"],
    horizontal=True
)

if input_method == "Enter Coordinates Manually":
    st.markdown('<h2 class="sub-header">📝 Enter Transmission Line Coordinates</h2>', unsafe_allow_html=True)
    
    with st.form("coordinate_form"):
        line_name = st.text_input("Transmission Line Name", value=f"Line_{len(st.session_state.transmission_lines) + 1}")
        
        st.write("Enter coordinates (Latitude, Longitude) - one pair per line:")
        coord_text = st.text_area(
            "Coordinates",
            height=150,
            placeholder="Example:\n20.5937, 78.9629\n21.1458, 79.0882\n22.5726, 88.3639"
        )
        
        submitted = st.form_submit_button("Analyze Transmission Line", type="primary")
        
        if submitted and coord_text:
            try:
                # Parse coordinates
                coords = []
                for line in coord_text.strip().split('\n'):
                    if line.strip():
                        lat, lon = map(float, line.split(','))
                        coords.append((lat, lon))
                
                if len(coords) < 2:
                    st.error("Please enter at least 2 coordinate pairs.")
                else:
                    # Analyze the line
                    analysis = analyze_transmission_line(coords, line_name)
                    
                    # Add to session state
                    st.session_state.transmission_lines.append({
                        'name': line_name,
                        'coords': coords,
                        'analysis': analysis
                    })
                    
                    st.success(f"✅ {line_name} analyzed successfully with {len(coords)} points!")
                    st.rerun()
            
            except Exception as e:
                st.error(f"Error parsing coordinates: {str(e)}")

else:  # Draw on Map
    st.markdown('<h2 class="sub-header">🖊️ Draw Transmission Lines on Map</h2>', unsafe_allow_html=True)
    
    # Create a drawing map
    center_lat, center_lon = 20.5937, 78.9629  # Center of India
    
    draw_map = folium.Map(
        location=[center_lat, center_lon],
        zoom_start=5,
        tiles='OpenStreetMap',
        control_scale=True
    )
    
    # Add drawing tools
    draw = plugins.Draw(
        draw_options={
            'polyline': {
                'allowIntersection': False,
                'shapeOptions': {
                    'color': '#0000FF',
                    'weight': 4,
                    'opacity': 0.8
                },
                'metric': True,
                'showLength': True
            },
            'polygon': False,
            'rectangle': False,
            'circle': False,
            'marker': False,
            'circlemarker': False
        },
        edit_options={'edit': True, 'remove': True}
    )
    draw.add_to(draw_map)
    
    st.write("**Instructions:** Use the drawing tools on the left side of the map to draw transmission lines. Draw multiple lines if needed!")
    
    map_data = st_folium(draw_map, width=1200, height=600)
    
    # Process drawn lines
    if map_data and map_data.get('all_drawings'):
        drawn_features = map_data['all_drawings']
        
        col1, col2 = st.columns([3, 1])
        with col1:
            st.info(f"📍 {len(drawn_features)} line(s) drawn on map")
        with col2:
            if st.button("✅ Use Drawn Lines", type="primary", use_container_width=True):
                colors = ['blue', 'red', 'green', 'orange', 'purple']
                
                for idx, feature in enumerate(drawn_features):
                    if feature['geometry']['type'] == 'LineString':
                        coords = [(lat, lon) for lon, lat in feature['geometry']['coordinates']]
                        line_name = f"Drawn_Line_{len(st.session_state.transmission_lines) + 1}"
                        
                        # Analyze the line
                        analysis = analyze_transmission_line(coords, line_name)
                        
                        # Add to session state
                        st.session_state.transmission_lines.append({
                            'name': line_name,
                            'coords': coords,
                            'analysis': analysis,
                            'color': colors[idx % len(colors)]
                        })
                
                st.success(f"✅ {len(drawn_features)} line(s) analyzed successfully!")
                st.rerun()

# Display results if there are transmission lines
if st.session_state.transmission_lines:
    st.markdown("---")
    st.markdown('<h2 class="sub-header">📊 Analysis Results</h2>', unsafe_allow_html=True)
    
    # Create tabs for each transmission line
    if len(st.session_state.transmission_lines) == 1:
        line = st.session_state.transmission_lines[0]
        
        # Main map
        st.markdown("### 🗺️ Transmission Line Map")
        main_map = create_map_with_analysis([line])
        st_folium(main_map, width=1200, height=600)
        
        # Risk scores
        st.markdown("### 📈 Risk Analysis")
        analysis = line['analysis']
        
        col1, col2, col3, col4 = st.columns(4)
        avg_overall = np.mean([r['overall_risk'] for r in analysis])
        avg_salinity = np.mean([r['salinity_risk'] for r in analysis])
        avg_temp = np.mean([r['temp_risk'] for r in analysis])
        avg_pollution = np.mean([r['pollution_risk'] for r in analysis])
        
        with col1:
            st.metric("Overall Risk", f"{avg_overall:.1f}", 
                     delta=get_risk_level(avg_overall, {'critical': 75, 'high': 50, 'moderate': 25}))
        with col2:
            st.metric("Salinity Risk", f"{avg_salinity:.1f}",
                     delta=get_risk_level(avg_salinity, {'critical': 75, 'high': 50, 'moderate': 25}))
        with col3:
            st.metric("Temperature Risk", f"{avg_temp:.1f}",
                     delta=get_risk_level(avg_temp, {'critical': 75, 'high': 50, 'moderate': 25}))
        with col4:
            st.metric("Pollution Risk", f"{avg_pollution:.1f}",
                     delta=get_risk_level(avg_pollution, {'critical': 75, 'high': 50, 'moderate': 25}))
        
        # Risk charts
        st.markdown("### 📊 Comprehensive Risk Charts")
        fig = create_risk_charts(analysis)
        st.pyplot(fig)
        plt.close()
        
        # Parameter maps
        st.markdown("### 🌍 Parameter Maps")
        param_maps = create_parameter_maps(analysis, line['name'], 'blue')
        
        # Create tabs for each parameter
        param_tabs = st.tabs(list(param_maps.keys()))
        for tab, (param_name, param_map) in zip(param_tabs, param_maps.items()):
            with tab:
                st_folium(param_map, width=1200, height=500)
    
    else:
        # Multiple lines - use tabs
        tab_names = [line['name'] for line in st.session_state.transmission_lines]
        tabs = st.tabs(tab_names)
        
        for tab, line in zip(tabs, st.session_state.transmission_lines):
            with tab:
                # Main map
                st.markdown("### 🗺️ Transmission Line Map")
                main_map = create_map_with_analysis([line])
                st_folium(main_map, width=1200, height=600)
                
                # Risk scores
                st.markdown("### 📈 Risk Analysis")
                analysis = line['analysis']
                
                col1, col2, col3, col4 = st.columns(4)
                avg_overall = np.mean([r['overall_risk'] for r in analysis])
                avg_salinity = np.mean([r['salinity_risk'] for r in analysis])
                avg_temp = np.mean([r['temp_risk'] for r in analysis])
                avg_pollution = np.mean([r['pollution_risk'] for r in analysis])
                
                with col1:
                    st.metric("Overall Risk", f"{avg_overall:.1f}", 
                             delta=get_risk_level(avg_overall, {'critical': 75, 'high': 50, 'moderate': 25}))
                with col2:
                    st.metric("Salinity Risk", f"{avg_salinity:.1f}",
                             delta=get_risk_level(avg_salinity, {'critical': 75, 'high': 50, 'moderate': 25}))
                with col3:
                    st.metric("Temperature Risk", f"{avg_temp:.1f}",
                             delta=get_risk_level(avg_temp, {'critical': 75, 'high': 50, 'moderate': 25}))
                with col4:
                    st.metric("Pollution Risk", f"{avg_pollution:.1f}",
                             delta=get_risk_level(avg_pollution, {'critical': 75, 'high': 50, 'moderate': 25}))
                
                # Risk charts
                st.markdown("### 📊 Comprehensive Risk Charts")
                fig = create_risk_charts(analysis)
                st.pyplot(fig)
                plt.close()
                
                # Parameter maps
                st.markdown("### 🌍 Parameter Maps")
                line_color = line.get('color', 'blue')
                param_maps = create_parameter_maps(analysis, line['name'], line_color)
                
                # Create tabs for each parameter
                param_tabs = st.tabs(list(param_maps.keys()))
                for p_tab, (param_name, param_map) in zip(param_tabs, param_maps.items()):
                    with p_tab:
                        st_folium(param_map, width=1200, height=500)
    
    # Combined map view
    st.markdown("---")
    st.markdown("### 🗺️ All Transmission Lines - Combined View")
    combined_map = create_map_with_analysis(st.session_state.transmission_lines)
    st_folium(combined_map, width=1200, height=700)
    
    # Download PDF report
    st.markdown("---")
    st.markdown("### 📄 Generate Report")
    
    if not REPORTLAB_AVAILABLE:
        st.warning("⚠️ PDF generation is not available. Please install reportlab package.")
    else:
        if st.button("Generate PDF Report", type="primary"):
            with st.spinner("Generating comprehensive PDF report..."):
                pdf_buffer = generate_pdf_report(st.session_state.transmission_lines)
                
                if pdf_buffer:
                    st.download_button(
                        label="⬇️ Download PDF Report",
                        data=pdf_buffer,
                        file_name=f"Transmission_Line_Report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf",
                        mime="application/pdf",
                        type="primary"
                    )
                    
                    st.success("✅ Report generated successfully!")

# Footer
st.markdown("---")
st.markdown(
    """
    <div style="text-align: center; color: #7f8c8d; padding: 20px;">
        <p><b>Deccan Environmental Analysis System</b></p>
        <p>Comprehensive environmental risk assessment for transmission line infrastructure</p>
        <p style="font-size: 12px;">Powered by Advanced Geospatial Analytics | © 2025</p>
    </div>
    """,
    unsafe_allow_html=True
)
