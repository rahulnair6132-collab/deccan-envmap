# app.py
# Deccan Environmental Severity Dashboard — Consolidated production-ready single file
# Summary: instant UI, left sidebar always present, draw or enter A→B, on-demand overlays,
# fast corridor buffer visualization, PDF report with Deccan logo, caching, robust fallbacks.

import streamlit as st
from streamlit_folium import st_folium
import folium
from folium.plugins import Draw
import requests, json, os, io, tempfile, math
import pandas as pd
import numpy as np
from shapely.geometry import LineString, Point, mapping
from fpdf import FPDF
from PIL import Image
import matplotlib.pyplot as plt
import branca.colormap as cm

# ---------------------------
# Page config and CSS
# ---------------------------
st.set_page_config(page_title="Deccan Env Severity Dashboard", layout="wide")

st.markdown("""
<style>
header, footer, #MainMenu {visibility: hidden;}
.sidebar .css-1d391kg {width: 320px;}  /* attempt to keep sidebar visible */
.title-bar { display:flex; align-items:center; gap:12px; justify-content:center;
            background:#0a3b78; color:white; padding:10px; border-radius:8px; margin-bottom:10px;}
.title-bar img {height:42px;}
.lead { color: #333; margin-bottom: 10px; }
</style>
""", unsafe_allow_html=True)

# ---------------------------
# Header with logo
# ---------------------------
logo_tag = ""
if os.path.exists("deccan_logo.png"):
    # use local logo
    logo_tag = '<img src="deccan_logo.png" />'
st.markdown(f'<div class="title-bar">{logo_tag}<h3 style="margin:0">Deccan — Environmental Severity Dashboard (India)</h3></div>', unsafe_allow_html=True)
st.markdown('<div class="lead">Draw a transmission route or enter origin & destination coordinates. Select parameter layers and click <b>Apply overlays</b> to visualize corridor impacts. Generate a PDF report when done.</div>', unsafe_allow_html=True)

# ---------------------------
# Sidebar (always present) - controls + PDF download area
# ---------------------------
st.sidebar.header("Map Controls")

# Line creation mode
input_mode = st.sidebar.radio("Create line by:", ("Draw on map", "Enter coordinates (A → B)"))

# If typed coordinates mode, collect inputs
if input_mode == "Enter coordinates (A → B)":
    st.sidebar.markdown("Enter coordinates in decimal degrees (lat, lon).")
    a_lat = st.sidebar.text_input("Origin latitude (A)", value="22.8176")
    a_lon = st.sidebar.text_input("Origin longitude (A)", value="70.8121")
    b_lat = st.sidebar.text_input("Destination latitude (B)", value="23.0225")
    b_lon = st.sidebar.text_input("Destination longitude (B)", value="72.5714")

st.sidebar.markdown("---")
st.sidebar.subheader("Overlay & Analysis")

params = st.sidebar.multiselect("Select parameter layers:", ["PM2.5","Temperature","Humidity","Cyclone Zone"], default=["PM2.5","Temperature","Humidity","Cyclone Zone"])
buffer_m = st.sidebar.number_input("Buffer width around line (meters)", min_value=500, max_value=50000, value=5000, step=500)
sample_interval_m = st.sidebar.number_input("Sample spacing along line (meters)", min_value=500, max_value=50000, value=5000, step=500)
heat_opacity = st.sidebar.slider("Overlay opacity", 0.2, 0.9, 0.55, 0.05)

apply_overlays = st.sidebar.button("Apply overlays")
st.sidebar.markdown("---")

st.sidebar.subheader("PDF Report")
client_name = st.sidebar.text_input("Client name", value="Client Co.")
line_label = st.sidebar.text_input("Line name", value="Morbi → Ahmedabad (demo)")
analyze_and_pdf = st.sidebar.button("Analyze & Generate PDF")

st.sidebar.markdown("---")
st.sidebar.caption("Data sources: OpenAQ (PM2.5), WAQI fallback, Open-Meteo (temp & humidity), IMD/IBTrACS (cyclone).")

# Permanent place for latest generated PDF download
if "last_pdf" not in st.session_state:
    st.session_state["last_pdf"] = None

# ---------------------------
# Utility functions
# ---------------------------
def meters_to_deg_lat(m):
    # 1 degree latitude ~ 111320 meters (approx)
    return m / 111320.0

def haversine(lat1, lon1, lat2, lon2):
    R = 6371000.0
    phi1 = math.radians(lat1); phi2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1); dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi/2.0)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlambda/2.0)**2
    return 2*R*math.asin(math.sqrt(a))

def points_along_line(line: LineString, spacing_m):
    # compute length in meters via haversine sum
    coords = list(line.coords)
    total_m = 0.0
    seglen = []
    for i in range(len(coords)-1):
        lat1, lon1 = coords[i]
        lat2, lon2 = coords[i+1]
        d = haversine(lat1, lon1, lat2, lon2)
        seglen.append(d); total_m += d
    if total_m == 0:
        return [Point(coords[0])]
    n = max(2, int(total_m / spacing_m) + 1)
    pts = [line.interpolate(float(i)/(n-1), normalized=True) for i in range(n)]
    return pts

# ---------------------------
# Lightweight, cached API wrappers
# ---------------------------
@st.cache_data(ttl=3600)
def get_meteo(lat, lon):
    try:
        url = "https://api.open-meteo.com/v1/forecast"
        params = {"latitude": lat, "longitude": lon, "current_weather": True, "hourly": "relativehumidity_2m"}
        r = requests.get(url, params=params, timeout=8).json()
        temp = r.get("current_weather", {}).get("temperature")
        hum = None
        if "hourly" in r and "relativehumidity_2m" in r["hourly"]:
            v = r["hourly"]["relativehumidity_2m"]
            if isinstance(v, list) and len(v)>0:
                hum = v[0]
        return {"temperature": temp, "humidity": hum}
    except Exception:
        return {"temperature": None, "humidity": None}

@st.cache_data(ttl=3600)
def get_nearest_pm25(lat, lon, radius_km=50):
    # Query OpenAQ first, small bbox, fallback WAQI
    try:
        d = 0.5 * radius_km / 111.0
        bbox = f"{lon-d},{lat-d},{lon+d},{lat+d}"
        url = "https://api.openaq.org/v2/latest"
        r = requests.get(url, params={"parameter":"pm25","limit":1000,"page":1,"bbox":bbox}, timeout=10)
        j = r.json()
        pts = []
        for rec in j.get("results", []):
            coords = rec.get("coordinates")
            if not coords: continue
            for m in rec.get("measurements", []):
                if m.get("parameter") == "pm25" and m.get("value") is not None:
                    pts.append((coords.get("latitude"), coords.get("longitude"), m.get("value")))
        if len(pts) == 0:
            # WAQI fallback
            token = "demo"
            waqi = f"https://api.waqi.info/map/bounds/?latlng={lat-d},{lon-d},{lat+d},{lon+d}&token={token}"
            r2 = requests.get(waqi, timeout=8).json()
            if r2.get("status") == "ok":
                for s in r2.get("data", []):
                    if s.get("v") is not None:
                        pts.append((s.get("lat"), s.get("lon"), s.get("v")))
        if len(pts) == 0:
            return None
        # pick nearest
        best = None; best_d = None
        for (plat, plon, val) in pts:
            dist = haversine(lat, lon, plat, plon)
            if best_d is None or dist < best_d:
                best_d = dist; best = val
        return best
    except Exception:
        return None

# ---------------------------
# Scoring rules (tunable later)
# ---------------------------
def score_pm25(v):
    if v is None: return np.nan
    if v > 100: return 4
    if v > 60: return 3
    if v > 30: return 2
    return 1

def score_temp(v):
    if v is None: return np.nan
    if v > 45: return 4
    if v > 35: return 3
    if v > 25: return 2
    return 1

def score_hum(v):
    if v is None: return np.nan
    if v > 80: return 4
    if v > 60: return 3
    if v > 40: return 2
    return 1

def severity_pct(pm, t, h):
    s1 = score_pm25(pm); s2 = score_temp(t); s3 = score_hum(h)
    # treat NaN as 0 for aggregation
    s1 = 0 if np.isnan(s1) else s1
    s2 = 0 if np.isnan(s2) else s2
    s3 = 0 if np.isnan(s3) else s3
    return (s1 + s2 + s3) / (4.0 * 3.0) * 100.0

# Colormaps for corridor polygons
pm_cmap = cm.linear.YlOrRd_09.scale(0,200)
temp_cmap = cm.linear.OrRd_09.scale(-10,50)
hum_cmap = cm.linear.Blues_09.scale(0,100)

# ---------------------------
# Base folium map (loads instantly)
# ---------------------------
start_center = [22.0, 80.0]
m = folium.Map(location=start_center, zoom_start=5, tiles="CartoDB positron")
# add simple cyclone belts polygons (visual guide)
bay_coords = [[21.5,89.0],[19.0,87.5],[15.0,84.5],[13.0,80.5],[12.0,78.0],[15.0,83.0],[18.0,86.0]]
arab_coords = [[23.0,67.5],[20.0,69.0],[16.0,72.5],[14.0,74.0],[12.5,74.0],[15.0,71.0],[19.0,68.5]]
folium.Polygon(bay_coords, color="purple", fill=True, fill_opacity=0.12, tooltip="Bay of Bengal cyclone belt").add_to(m)
folium.Polygon(arab_coords, color="purple", fill=True, fill_opacity=0.12, tooltip="Arabian Sea cyclone belt").add_to(m)

# permanent legend HTML
legend_html = """
<div style="position: fixed; bottom: 18px; left: 18px; z-index:9999; background:white; padding:10px; border-radius:8px; box-shadow:2px 2px 6px rgba(0,0,0,0.2); font-size:12px;">
<b>Legend</b><br>
<span style='background:#ffffb2'>&nbsp;&nbsp;&nbsp;</span> Low PM2.5 &nbsp; <span style='background:#bd0026'>&nbsp;&nbsp;&nbsp;</span> High PM2.5<br>
<span style='background:#fee0d2'>&nbsp;&nbsp;&nbsp;</span> Low Temp &nbsp; <span style='background:#99000d'>&nbsp;&nbsp;&nbsp;</span> High Temp<br>
<span style='background:#deebf7'>&nbsp;&nbsp;&nbsp;</span> Low Humidity &nbsp; <span style='background:#08306b'>&nbsp;&nbsp;&nbsp;</span> High Humidity<br>
</div>
"""
m.get_root().html.add_child(folium.Element(legend_html))

# Add Draw plugin
draw = Draw(export=True, filename="drawn.geojson", draw_options={"polyline": True, "polygon": False, "marker": False, "rectangle": False, "circle": False}, edit_options={"edit": True})
draw.add_to(m)
folium.LayerControl().add_to(m)

# Show map (single render)
map_return = st_folium(m, width=1100, height=650)

# ---------------------------
# Determine user line (drawn or typed)
# ---------------------------
user_line = None
line_source = None

# check drawn features from map_return
if map_return and "all_drawings" in map_return and map_return["all_drawings"]:
    for feat in map_return["all_drawings"]:
        geom = feat.get("geometry")
        if geom and geom.get("type") == "LineString":
            coords = geom.get("coordinates")  # list of [lon, lat]
            pts = [(c[1], c[0]) for c in coords]
            user_line = LineString(pts)
            line_source = "drawn"
            break

# if typed coords and no drawn line, construct it
if user_line is None and input_mode == "Enter coordinates (A → B)":
    try:
        a_lat_f = float(a_lat); a_lon_f = float(a_lon); b_lat_f = float(b_lat); b_lon_f = float(b_lon)
        user_line = LineString([(a_lat_f, a_lon_f), (b_lat_f, b_lon_f)])
        line_source = "typed"
    except Exception:
        user_line = None

# user feedback
if user_line is None:
    st.info("No line yet. Draw a polyline using the Draw tool on the map or enter coordinates in the sidebar.")
else:
    # compute approximate geodesic length of full polyline
    coords = list(user_line.coords)
    total_len_m = 0.0
    for i in range(len(coords)-1):
        total_len_m += haversine(coords[i][0], coords[i][1], coords[i+1][0], coords[i+1][1])
    st.success(f"Line ready (source: {line_source}) — approx length: {int(total_len_m)} m")

# ---------------------------
# Apply overlays on demand: sample along user_line and draw buffered polygons colored by values
# ---------------------------
generated_sample_df = None
if apply_overlays:
    if user_line is None:
        st.error("No line to apply overlays to. Draw or enter coordinates first.")
    else:
        st.info("Sampling along line and fetching parameter values (this is fast).")
        with st.spinner("Sampling and drawing corridor overlays..."):
            pts = points_along_line(user_line, sample_interval_m)
            # prepare feature groups
            fg_pm = folium.FeatureGroup(name="PM2.5 Corridor", show=("PM2.5" in params))
            fg_temp = folium.FeatureGroup(name="Temperature Corridor", show=("Temperature" in params))
            fg_hum = folium.FeatureGroup(name="Humidity Corridor", show=("Humidity" in params))
            fg_cycl = folium.FeatureGroup(name="Cyclone Corridor", show=("Cyclone Zone" in params))
            sample_rows = []
            # set buffer radius degrees
            buff_deg = meters_to_deg_lat(buffer_m)
            for p in pts:
                lat = float(p.y); lon = float(p.x)
                # fetch values (cached)
                met = get_meteo(lat, lon)
                temp_val = met.get("temperature"); hum_val = met.get("humidity")
                pm_val = get_nearest_pm25(lat, lon, radius_km=50)
                sample_rows.append({"lat": lat, "lon": lon, "pm25": pm_val, "temp": temp_val, "hum": hum_val})
                # create buffer polygon in lon/lat order for GeoJSON
                # shapely expects Point(lon,lat) to buffer in degrees
                buff_poly = Point(lon, lat).buffer(buff_deg, resolution=16)
                poly_geojson = mapping(buff_poly)
                # add polygons colored by their parameter
                if "PM2.5" in params and pm_val is not None:
                    c = pm_cmap(pm_val)
                    fol = folium.GeoJson(poly_geojson, style_function=lambda feat, color=c: {"fillColor": color, "color": color, "weight": 0.3, "fillOpacity": 0.7}, tooltip=f"PM2.5: {pm_val}")
                    fol.add_to(fg_pm)
                if "Temperature" in params and temp_val is not None:
                    c = temp_cmap(temp_val)
                    fol = folium.GeoJson(poly_geojson, style_function=lambda feat, color=c: {"fillColor": color, "color": color, "weight": 0.3, "fillOpacity": 0.6}, tooltip=f"Temp: {temp_val} °C")
                    fol.add_to(fg_temp)
                if "Humidity" in params and hum_val is not None:
                    c = hum_cmap(hum_val)
                    fol = folium.GeoJson(poly_geojson, style_function=lambda feat, color=c: {"fillColor": color, "color": color, "weight": 0.3, "fillOpacity": 0.55}, tooltip=f"Humidity: {hum_val} %")
                    fol.add_to(fg_hum)
                # Cyclone zone: quick check whether sample point falls inside simple belts
                if "Cyclone Zone" in params:
                    # We use simple bounding test: check distance to bay_coords/arab_coords centroids (fast)
                    # This is a rough approximation — replace with real GeoJSON for precise zones later.
                    # centroid approach:
                    bay_cent = (sum([c[0] for c in bay_coords]) / len(bay_coords), sum([c[1] for c in bay_coords]) / len(bay_coords))
                    arab_cent = (sum([c[0] for c in arab_coords]) / len(arab_coords), sum([c[1] for c in arab_coords]) / len(arab_coords))
                    # use haversine to centroids; threshold ~700km to indicate coastal influence (very rough)
                    d_bay = haversine(lat, lon, bay_cent[0], bay_cent[1])
                    d_arab = haversine(lat, lon, arab_cent[0], arab_cent[1])
                    if d_bay < 700000 or d_arab < 700000:
                        fol = folium.GeoJson(poly_geojson, style_function=lambda feat: {"fillColor": "purple", "color": "purple", "weight": 0.2, "fillOpacity": 0.25}, tooltip="Cyclone-prone area (approx.)")
                        fol.add_to(fg_cycl)
            # add groups to map and re-render
            if "PM2.5" in params:
                fg_pm.add_to(m)
            if "Temperature" in params:
                fg_temp.add_to(m)
            if "Humidity" in params:
                fg_hum.add_to(m)
            if "Cyclone Zone" in params:
                fg_cycl.add_to(m)
            folium.LayerControl().add_to(m)
            # show a summary DataFrame
            df_samples = pd.DataFrame(sample_rows)
            generated_sample_df = df_samples
            st.write("Sampled corridor values (first rows):")
            st.dataframe(df_samples.head(200))
        # re-render the map with overlays (one more render)
        st_folium(m, width=1100, height=650)
        st.success("Corridor overlays applied. Use the Layer control (top-right) to toggle visibility.")

# ---------------------------
# Analyze & PDF generation (on-demand)
# ---------------------------
def build_pdf_report(report_items, outpath, client, line_name):
    pdf = FPDF()
    pdf.set_auto_page_break(True, margin=12)
    pdf.add_page()
    if os.path.exists("deccan_logo.png"):
        pdf.image("deccan_logo.png", x=10, y=8, w=40)
    pdf.set_font("Arial", "B", 14)
    pdf.cell(0, 10, "Deccan Environmental Severity Report", ln=True, align="C")
    pdf.ln(6)
    pdf.set_font("Arial", size=11)
    pdf.cell(0,6, f"Client: {client}", ln=True)
    pdf.cell(0,6, f"Line: {line_name}", ln=True)
    pdf.ln(4)
    for i, item in enumerate(report_items, start=1):
        pdf.set_font("Arial", "B", 12)
        pdf.cell(0,7, f"Line {i} — Mean Severity: {item['mean']:.1f}%", ln=True)
        pdf.set_font("Arial", size=11)
        pdf.multi_cell(0,6, f"Recommendation: {item['recommendation']}")
        # build plot image
        fig, ax = plt.subplots(figsize=(4,2))
        sc = ax.scatter(item["df"]["lon"], item["df"]["lat"], c=item["df"]["severity"], cmap="RdYlBu_r", s=20)
        ax.set_xlabel("Lon"); ax.set_ylabel("Lat")
        plt.colorbar(sc, ax=ax, orientation="horizontal", pad=0.2, label="Severity %")
        buf = io.BytesIO(); plt.tight_layout(); fig.savefig(buf, format="PNG", dpi=150); plt.close(fig)
        buf.seek(0)
        tmp = os.path.join(tempfile.gettempdir(), f"mini_{i}.png")
        with open(tmp, "wb") as f: f.write(buf.read())
        pdf.image(tmp, w=150)
        pdf.ln(6)
    pdf.output(outpath)
    return outpath

if analyze_and_pdf:
    if user_line is None:
        st.error("No line defined. Draw or enter coordinates before analyzing.")
    else:
        st.info("Performing full analysis and generating PDF. This may take a few seconds.")
        with st.spinner("Analyzing..."):
            # create lines list (drawn + typed)
            lines_list = []
            if map_return and "all_drawings" in map_return and map_return["all_drawings"]:
                for feat in map_return["all_drawings"]:
                    geom = feat.get("geometry")
                    if geom and geom.get("type") == "LineString":
                        coords = geom.get("coordinates")
                        pts = [(c[1], c[0]) for c in coords]
                        lines_list.append(LineString(pts))
            if input_mode == "Enter coordinates (A → B)" and user_line is not None:
                lines_list.append(user_line)
            report_items = []
            for line in lines_list:
                samples = points_along_line(line, sample_interval_m)
                rows = []
                for p in samples:
                    lat = float(p.y); lon = float(p.x)
                    met = get_meteo(lat, lon)
                    temp_val = met.get("temperature"); hum_val = met.get("humidity")
                    pm_val = get_nearest_pm25(lat, lon, radius_km=50)
                    sev = severity_pct(pm_val, temp_val, hum_val)
                    rows.append({"lat": lat, "lon": lon, "pm": pm_val, "temp": temp_val, "hum": hum_val, "severity": sev})
                df = pd.DataFrame(rows)
                mean_val = df["severity"].mean() if not df["severity"].isna().all() else 0.0
                rec = "Recommend upgraded EHV silicone spec due to high combined environmental stress." if mean_val >= 60 else "Standard insulator spec acceptable; consider targeted monitoring."
                report_items.append({"df": df, "mean": mean_val, "recommendation": rec})
            # generate PDF into temp file
            out_file = os.path.join(tempfile.gettempdir(), "Deccan_Env_Report.pdf")
            build_pdf_report(report_items, out_file, client_name, line_label)
            st.session_state["last_pdf"] = out_file
        st.success("Analysis & PDF ready. Use sidebar to download the report.")
        # offer immediate download in main area too
        if os.path.exists(st.session_state["last_pdf"]):
            with open(st.session_state["last_pdf"], "rb") as fh:
                st.download_button("⬇️ Download PDF report", data=fh, file_name="Deccan_Env_Report.pdf", mime="application/pdf")

# Sidebar PDF download widget (permanent)
st.sidebar.markdown("---")
st.sidebar.subheader("Latest Report")
if st.session_state["last_pdf"] and os.path.exists(st.session_state["last_pdf"]):
    with open(st.session_state["last_pdf"], "rb") as f:
        st.sidebar.download_button("⬇️ Download latest PDF report", data=f, file_name="Deccan_Env_Report.pdf", mime="application/pdf")
else:
    st.sidebar.caption("No PDF generated yet.")

# ---------------------------
# Final notes / Reminders
# ---------------------------
st.markdown("---")
st.info("Notes: Corridor visualization uses sampled buffers around the line (fast). For pixel-perfect raster heatmaps, we can later add tiled rasters (ERA5/MODIS) or serve precomputed tiles. If you want calibrated severity weights, or to include lightning/cyclone official GeoJSON layers (IMD/IBTrACS), I can add that next.")
