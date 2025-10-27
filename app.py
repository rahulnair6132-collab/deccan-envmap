# app.py — FINAL STABLE BUILD
# Deccan Environmental Severity Dashboard (Always-visible sidebar version)
# Rahul Nair — Deccan Enterprises Pvt. Ltd.

import streamlit as st
from streamlit_folium import st_folium
import folium
from folium.plugins import Draw
import requests, os, io, tempfile, math
import pandas as pd
import numpy as np
from shapely.geometry import LineString, Point, mapping
from fpdf import FPDF
import matplotlib.pyplot as plt
import branca.colormap as cm

# -------------------------------
# Basic Streamlit config
# -------------------------------
st.set_page_config(page_title="Deccan Env Severity Dashboard", layout="wide")

# -------------------------------
# Header and Logo
# -------------------------------
if os.path.exists("deccan_logo.png"):
    st.image("deccan_logo.png", width=150)
st.markdown(
    "<h2 style='color:#003366;text-align:center;'>Deccan — Environmental Severity Dashboard (India)</h2>",
    unsafe_allow_html=True,
)
st.write(
    "Draw or define a transmission corridor between two points. Select parameters to visualize corridor stress levels and generate client reports."
)

# -------------------------------
# Sidebar Controls
# -------------------------------
st.sidebar.header("⚙️ Map Controls")

mode = st.sidebar.radio("Create line by:", ("Draw on map", "Enter coordinates"))

if mode == "Enter coordinates":
    col1, col2 = st.sidebar.columns(2)
    with col1:
        lat1 = st.text_input("Origin Latitude", value="22.8176")
        lon1 = st.text_input("Origin Longitude", value="70.8121")
    with col2:
        lat2 = st.text_input("Destination Latitude", value="23.0225")
        lon2 = st.text_input("Destination Longitude", value="72.5714")

params = st.sidebar.multiselect(
    "Select overlays", ["PM2.5", "Temperature", "Humidity", "Cyclone Zone"],
    default=["PM2.5", "Temperature", "Humidity", "Cyclone Zone"],
)

buffer_m = st.sidebar.number_input("Buffer width (m)", 500, 50000, 5000, step=500)
sample_m = st.sidebar.number_input("Sample spacing (m)", 500, 50000, 5000, step=500)

apply = st.sidebar.button("✅ Apply Overlays")

st.sidebar.markdown("---")
st.sidebar.subheader("📄 Generate Report")

client_name = st.sidebar.text_input("Client Name", value="Client Co.")
line_name = st.sidebar.text_input("Line Name", value="Morbi → Ahmedabad (Demo)")
generate_pdf = st.sidebar.button("📘 Analyze & Generate PDF")

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
    a = (
        math.sin(dphi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    )
    return 2 * R * math.asin(math.sqrt(a))

def sample_points(line: LineString, spacing_m):
    coords = list(line.coords)
    total_m = 0
    for i in range(len(coords) - 1):
        total_m += haversine(coords[i][0], coords[i][1], coords[i + 1][0], coords[i + 1][1])
    n = max(2, int(total_m / spacing_m) + 1)
    return [line.interpolate(i / (n - 1), normalized=True) for i in range(n)]

@st.cache_data(ttl=3600)
def get_temp_hum(lat, lon):
    try:
        url = "https://api.open-meteo.com/v1/forecast"
        params = {"latitude": lat, "longitude": lon, "current_weather": True, "hourly": "relativehumidity_2m"}
        r = requests.get(url, params=params, timeout=8).json()
        t = r.get("current_weather", {}).get("temperature")
        h = None
        if "hourly" in r and "relativehumidity_2m" in r["hourly"]:
            h = r["hourly"]["relativehumidity_2m"][0]
        return {"temp": t, "hum": h}
    except:
        return {"temp": None, "hum": None}

@st.cache_data(ttl=3600)
def get_pm25(lat, lon):
    try:
        d = 0.5 / 111
        bbox = f"{lon-d},{lat-d},{lon+d},{lat+d}"
        url = "https://api.openaq.org/v2/latest"
        r = requests.get(url, params={"parameter":"pm25","bbox":bbox}, timeout=8).json()
        if r.get("results"):
            vals = [m["value"] for i in r["results"] for m in i.get("measurements",[]) if m["parameter"]=="pm25"]
            return np.mean(vals) if vals else None
        return None
    except:
        return None

# -------------------------------
# Base Map
# -------------------------------
m = folium.Map(location=[22, 80], zoom_start=5, tiles="CartoDB positron")
Draw(export=True).add_to(m)

# Add cyclone belts (static)
bay = [[21.5,89.0],[19,87.5],[15,84.5],[13,80.5],[12,78],[15,83],[18,86]]
arab = [[23,67.5],[20,69],[16,72.5],[14,74],[12.5,74],[15,71],[19,68.5]]
folium.Polygon(bay, color="purple", fill=True, fill_opacity=0.1).add_to(m)
folium.Polygon(arab, color="purple", fill=True, fill_opacity=0.1).add_to(m)

# -------------------------------
# Detect line
# -------------------------------
map_data = st_folium(m, width=900, height=600)
user_line = None

if map_data and "all_drawings" in map_data and map_data["all_drawings"]:
    for f in map_data["all_drawings"]:
        if f.get("geometry", {}).get("type") == "LineString":
            coords = [(c[1], c[0]) for c in f["geometry"]["coordinates"]]
            user_line = LineString(coords)
            break

if mode == "Enter coordinates" and user_line is None:
    try:
        user_line = LineString([(float(lat1), float(lon1)), (float(lat2), float(lon2))])
    except:
        st.warning("Invalid coordinates")

if user_line:
    st.success("Line ready. Click Apply Overlays.")
else:
    st.info("Draw a line or enter coordinates.")

# -------------------------------
# Overlays
# -------------------------------
if apply and user_line:
    with st.spinner("Fetching data and drawing corridor..."):
        pts = sample_points(user_line, sample_m)
        buf_deg = meters_to_deg(buffer_m)
        pm_cmap = cm.linear.YlOrRd_09.scale(0,200)
        temp_cmap = cm.linear.OrRd_09.scale(-10,50)
        hum_cmap = cm.linear.Blues_09.scale(0,100)
        data = []
        for p in pts:
            lat, lon = p.y, p.x
            d = get_temp_hum(lat, lon)
            t, h = d["temp"], d["hum"]
            pm = get_pm25(lat, lon)
            data.append({"lat": lat, "lon": lon, "pm25": pm, "temp": t, "hum": h})
            poly = Point(lon, lat).buffer(buf_deg)
            geo = mapping(poly)
            if "PM2.5" in params and pm is not None:
                folium.GeoJson(geo, style_function=lambda f, c=pm_cmap(pm): {"fillColor": c,"color":c,"fillOpacity":0.6}).add_to(m)
            if "Temperature" in params and t is not None:
                folium.GeoJson(geo, style_function=lambda f, c=temp_cmap(t): {"fillColor": c,"color":c,"fillOpacity":0.5}).add_to(m)
            if "Humidity" in params and h is not None:
                folium.GeoJson(geo, style_function=lambda f, c=hum_cmap(h): {"fillColor": c,"color":c,"fillOpacity":0.5}).add_to(m)
            if "Cyclone Zone" in params:
                folium.GeoJson(geo, style_function=lambda f: {"fillColor":"purple","color":"purple","fillOpacity":0.2}).add_to(m)
        st_folium(m, width=900, height=600)
        df = pd.DataFrame(data)
        st.dataframe(df)

# -------------------------------
# PDF Generation
# -------------------------------
def make_pdf(df, client, name):
    pdf = FPDF()
    pdf.add_page()
    if os.path.exists("deccan_logo.png"):
        pdf.image("deccan_logo.png", x=10, y=8, w=40)
    pdf.set_font("Arial", "B", 14)
    pdf.cell(0, 10, "Deccan Environmental Report", ln=True, align="C")
    pdf.ln(5)
    pdf.set_font("Arial", "", 11)
    pdf.cell(0, 8, f"Client: {client}", ln=True)
    pdf.cell(0, 8, f"Line: {name}", ln=True)
    pdf.ln(5)
    if not df.empty:
        pdf.cell(0, 8, f"Average Temp: {df['temp'].mean():.1f} °C", ln=True)
        pdf.cell(0, 8, f"Average Humidity: {df['hum'].mean():.1f} %", ln=True)
        pdf.cell(0, 8, f"Average PM2.5: {df['pm25'].mean():.1f}", ln=True)
    pdf.output(os.path.join(tempfile.gettempdir(), "Deccan_Report.pdf"))

if generate_pdf and user_line:
    with st.spinner("Generating PDF..."):
        pts = sample_points(user_line, sample_m)
        data = []
        for p in pts:
            lat, lon = p.y, p.x
            d = get_temp_hum(lat, lon)
            pm = get_pm25(lat, lon)
            data.append({"lat": lat, "lon": lon, "temp": d["temp"], "hum": d["hum"], "pm25": pm})
        df = pd.DataFrame(data)
        make_pdf(df, client_name, line_name)
        with open(os.path.join(tempfile.gettempdir(), "Deccan_Report.pdf"), "rb") as f:
            st.download_button("⬇️ Download PDF", f, file_name="Deccan_Report.pdf", mime="application/pdf")

st.markdown("---")
st.caption("Deccan Enterprises Pvt. Ltd. | Environmental Severity Dashboard v1.0 | Data from OpenAQ & Open-Meteo APIs")
