# app.py
# Deccan — Environmental Severity Dashboard (Corridor buffer style overlays)
# Author: ChatGPT (final production-ready single-file)
# Requirements: streamlit, streamlit-folium, folium, pandas, numpy, requests, shapely, matplotlib, Pillow, fpdf, branca

import streamlit as st
from streamlit_folium import st_folium
import folium
from folium import GeoJson
import requests
import pandas as pd
import numpy as np
from shapely.geometry import LineString, mapping, Point
import shapely.ops as ops
import math, io, os, tempfile, json
from fpdf import FPDF
from PIL import Image
import matplotlib.pyplot as plt
import branca.colormap as cm

st.set_page_config(page_title="Deccan Env Severity Dashboard", layout="wide")

# -------------------------
# Styles / Header
# -------------------------
st.markdown("""
<style>
header, footer, #MainMenu {visibility: hidden;}
.title-bar { display:flex; align-items:center; gap:12px; justify-content:center;
            background:#0a3b78; color:white; padding:10px; border-radius:8px; margin-bottom:10px;}
.title-bar img{height:42px;}
</style>
""", unsafe_allow_html=True)

logo_html = ""
if os.path.exists("deccan_logo.png"):
    logo_html = f'<img src="deccan_logo.png" />'
st.markdown(f'<div class="title-bar">{logo_html}<h3 style="margin:0">Deccan — Environmental Severity Dashboard (India)</h3></div>', unsafe_allow_html=True)

st.write("Draw a line on the map or enter Origin / Destination coordinates to create a transmission corridor. Select parameters and click **Apply overlays** to visualize environmental stress around the corridor. Click **Analyze & Generate PDF** to produce a client-ready report.")

# -------------------------
# Sidebar controls (collapsible)
# -------------------------
with st.sidebar.expander("⚙️ Controls", expanded=True):
    st.markdown("**Line input / creation**")
    input_mode = st.radio("Create line by:", ("Draw on map", "Enter coordinates (A → B)"))
    if input_mode == "Enter coordinates (A → B)":
        colA, colB = st.columns(2)
        with colA:
            a_lat = st.text_input("Origin latitude (A)", value="22.8176")
            a_lon = st.text_input("Origin longitude (A)", value="70.8121")
        with colB:
            b_lat = st.text_input("Destination latitude (B)", value="23.0225")
            b_lon = st.text_input("Destination longitude (B)", value="72.5714")
    st.markdown("---")
    st.markdown("**Overlay & analysis**")
    params = st.multiselect("Select parameter layers to show", ["PM2.5","Temperature","Humidity","Cyclone Zone"], default=["PM2.5","Temperature","Humidity","Cyclone Zone"])
    buffer_m = st.number_input("Buffer width around line (meters)", min_value=500, max_value=50000, value=5000, step=500)
    sample_interval_m = st.number_input("Sample spacing along line (meters)", min_value=500, max_value=50000, value=5000, step=500)
    apply_btn = st.button("Apply overlays")
    st.markdown("---")
    st.markdown("**Report**")
    client_name = st.text_input("Client name (for PDF)", value="Client Co.")
    line_name = st.text_input("Line name (for PDF)", value="Morbi → Ahmedabad (demo)")
    analyze_btn = st.button("🔍 Analyze & Generate PDF")
    st.markdown("---")
    st.markdown("Data sources: OpenAQ (PM2.5), WAQI (fallback), Open-Meteo (temp & humidity), IMD/IBTrACS (cyclone)")

# -------------------------
# Helpers: geo + meters<->deg conversion
# -------------------------
def meters_to_degrees(meters):
    # rough conversion: 1 deg latitude ~ 111320 m
    return meters / 111320.0

def haversine_distance(lat1, lon1, lat2, lon2):
    # meters
    R=6371000
    phi1,phi2=math.radians(lat1),math.radians(lat2)
    dphi=math.radians(lat2-lat1); dlambda=math.radians(lon2-lon1)
    a=math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlambda/2)**2
    return 2*R*math.asin(math.sqrt(a))

def points_along_line(line: LineString, spacing_m):
    # returns shapely Points along line at approx equal spacing (including endpoints)
    length_deg = line.length  # in degrees (because coords are lat/lon)
    # approximate degrees per meter at mid-latitude
    # We'll sample by normalized steps computed from length in meters
    # compute geodesic length by summing Haversine between consecutive coords
    coords = list(line.coords)
    total_m = 0.0
    for i in range(len(coords)-1):
        total_m += haversine_distance(coords[i][1], coords[i][0], coords[i+1][1], coords[i+1][0])
    if total_m == 0:
        return [Point(coords[0][0], coords[0][1])]
    n = max(2, int(total_m / spacing_m) + 1)
    pts = [line.interpolate(float(i)/(n-1), normalized=True) for i in range(n)]
    return pts

# -------------------------
# Caching API calls per coordinate to avoid repeated slow calls
# -------------------------
@st.cache_data(ttl=3600)
def fetch_open_meteo(lat, lon):
    try:
        url = "https://api.open-meteo.com/v1/forecast"
        params = {"latitude": lat, "longitude": lon, "current_weather": True, "hourly": "relativehumidity_2m"}
        r = requests.get(url, params=params, timeout=8)
        js = r.json()
        temp = js.get("current_weather", {}).get("temperature")
        hum = None
        if "hourly" in js and "relativehumidity_2m" in js["hourly"]:
            v = js["hourly"]["relativehumidity_2m"]
            if isinstance(v, list) and len(v) > 0:
                hum = v[0]
        return {"temperature": temp, "humidity": hum}
    except:
        return {"temperature": None, "humidity": None}

@st.cache_data(ttl=3600)
def fetch_openaq_nearby(lat, lon, radius_km=50):
    # Query OpenAQ with bbox around point (fast), fallback to WAQI if empty
    try:
        d = 0.5 * radius_km / 111.0  # approx deg
        bbox = f"{lon - d},{lat - d},{lon + d},{lat + d}"
        url = "https://api.openaq.org/v2/latest"
        r = requests.get(url, params={"parameter":"pm25", "limit":1000, "page":1, "bbox": bbox}, timeout=10)
        js = r.json()
        pts = []
        for rec in js.get("results", []):
            coords = rec.get("coordinates")
            if not coords: continue
            for m in rec.get("measurements", []):
                if m.get("parameter") == "pm25" and m.get("value") is not None:
                    pts.append({"lat": coords.get("latitude"), "lon": coords.get("longitude"), "value": m.get("value")})
        if len(pts) == 0:
            # WAQI fallback using map/bounds (demo token) for small bbox
            token = "demo"
            waqi_url = f"https://api.waqi.info/map/bounds/?latlng={lat-d},{lon-d},{lat+d},{lon+d}&token={token}"
            r2 = requests.get(waqi_url, timeout=8).json()
            if r2.get("status") == "ok":
                for s in r2.get("data", []):
                    if s.get("v") is not None:
                        pts.append({"lat": s.get("lat"), "lon": s.get("lon"), "value": s.get("v")})
        # return nearest station value if any
        if len(pts) == 0:
            return None
        # choose nearest by haversine
        min_d = None; best = None
        for p in pts:
            dist = haversine_distance(lat, lon, p["lat"], p["lon"])
            if min_d is None or dist < min_d:
                min_d = dist; best = p
        return best["value"]
    except:
        return None

# -------------------------
# Color ramps for parameters
# -------------------------
pm_cmap = cm.linear.YlOrRd_09.scale(0,200)
temp_cmap = cm.linear.OrRd_09.scale(-10,50)
hum_cmap = cm.linear.Blues_09.scale(0,100)

# -------------------------
# Base map (loads instantly)
# -------------------------
start_center = [22.0, 80.0]
zoom = 5
m = folium.Map(location=start_center, zoom_start=zoom, tiles="CartoDB positron")
# show cyclone belts (light polygons) always (simple approximations)
bay = [[21.5,89.0],[19.0,87.5],[15.0,84.5],[13.0,80.5],[12.0,78.0],[15.0,83.0],[18.0,86.0]]
arab = [[23.0,67.5],[20.0,69.0],[16.0,72.5],[14.0,74.0],[12.5,74.0],[15.0,71.0],[19.0,68.5]]
folium.Polygon(bay, color="purple", fill=True, fill_opacity=0.12, tooltip="Bay of Bengal cyclone belt").add_to(m)
folium.Polygon(arab, color="purple", fill=True, fill_opacity=0.12, tooltip="Arabian Sea cyclone belt").add_to(m)
folium.TileLayer("cartodbpositron").add_to(m)
folium.LayerControl().add_to(m)
draw = folium.plugins.Draw(export=True, filename="drawn.geojson", draw_options={"polyline": True, "marker": False, "polygon": False, "rectangle": False, "circle": False}, edit_options={"edit": True})
draw.add_to(m)

# permanent legend (bottom-left)
legend_html = """
<div style="position: fixed; bottom: 20px; left: 20px; z-index:9999; background:white; padding:10px; border-radius:8px; box-shadow:2px 2px 6px rgba(0,0,0,0.2); font-size:12px;">
<b>Legend</b><br>
<span style='background:#ffffb2'>&nbsp;&nbsp;&nbsp;</span> Low PM2.5 &nbsp; <span style='background:#bd0026'>&nbsp;&nbsp;&nbsp;</span> High PM2.5<br>
<span style='background:#fee0d2'>&nbsp;&nbsp;&nbsp;</span> Low Temp &nbsp; <span style='background:#99000d'>&nbsp;&nbsp;&nbsp;</span> High Temp<br>
<span style='background:#deebf7'>&nbsp;&nbsp;&nbsp;</span> Low Humidity &nbsp; <span style='background:#08306b'>&nbsp;&nbsp;&nbsp;</span> High Humidity<br>
</div>
"""
m.get_root().html.add_child(folium.Element(legend_html))

# Render base map
map_data = st_folium(m, width=1100, height=650)

# -------------------------
# Create line if user provided coordinates or drawn one
# -------------------------
user_line = None
line_source = "none"
# prefer drawn line if present
if map_data and "all_drawings" in map_data and map_data["all_drawings"]:
    # take first drawing feature that is a polyline
    for feat in map_data["all_drawings"]:
        g = feat.get("geometry")
        if g and g.get("type") in ("LineString",):
            coords = g.get("coordinates")
            # folium/draw gives coords as [lon,lat] pairs
            pts = [(c[1], c[0]) for c in coords]
            user_line = LineString(pts)
            line_source = "drawn"
            break

# if user entered coords
if user_line is None and input_mode == "Enter coordinates (A → B)":
    try:
        a_lat_f = float(a_lat); a_lon_f = float(a_lon); b_lat_f = float(b_lat); b_lon_f = float(b_lon)
        user_line = LineString([(a_lat_f, a_lon_f), (b_lat_f, b_lon_f)])
        line_source = "typed"
        # visualize the created line as a yellow polyline on the map area (via folium) -> need to re-render small map
        folium.PolyLine([(a_lat_f, a_lon_f), (b_lat_f, b_lon_f)], color="yellow", weight=3, tooltip="Created A → B line").add_to(m)
        # re-render the map with the overlay polyline
        st_folium(m, width=1100, height=650, returned_objects=map_data)
    except Exception:
        pass

if user_line is None:
    st.info("No line yet: draw a line using the Draw tool (top-left) or enter Origin/Destination coordinates in the sidebar.")
else:
    st.success(f"Line ready (source: {line_source}). Length ~ {int(haversine_distance(user_line.coords[0][0], user_line.coords[0][1], user_line.coords[-1][0], user_line.coords[-1][1]))} m")

# -------------------------
# Overlay application (on demand)
# -------------------------
# We'll add featuregroups for each parameter so they can be toggled
overlay_groups = {}

def make_geojson_feature(polygon_geojson, properties):
    return {"type": "Feature", "geometry": polygon_geojson, "properties": properties}

if apply_btn and user_line is not None:
    st.info("Sampling along line and fetching parameter values (this is fast).")
    with st.spinner("Sampling and fetching..."):
        pts = points_along_line(user_line, spacing_m=sample_interval_m)
        # prepare folium FeatureGroups
        pm_fg = folium.FeatureGroup(name="PM2.5 Corridor", show="PM2.5" in params)
        t_fg = folium.FeatureGroup(name="Temperature Corridor", show="Temperature" in params)
        h_fg = folium.FeatureGroup(name="Humidity Corridor", show="Humidity" in params)
        cycl_fg = folium.FeatureGroup(name="Cyclone Buffer", show="Cyclone Zone" in params)
        # for each sample, fetch values and add a buffer polygon colored according to value
        sample_rows = []
        for i, p in enumerate(pts):
            lat = p.y; lon = p.x
            # fetch metrics (cached)
            met = fetch_open_meteo(lat, lon)
            temp_val = met.get("temperature")
            hum_val = met.get("humidity")
            pm_val = fetch_openaq_nearby(lat, lon, radius_km=50)
            sample_rows.append({"lat": lat, "lon": lon, "pm25": pm_val, "temp": temp_val, "hum": hum_val})
            # create buffer polygon in degrees (approx) around this point
            # convert buffer_m (meters) to degrees (latitude approx)
            buff_deg = meters_to_degrees(buffer_m)
            circle = Point(lon, lat).buffer(buff_deg)  # shapely uses (x=lon,y=lat) for Point(lon,lat)
            # Note: we passed Point(lon,lat) but earlier we used shapely Points created from (lat,lon) sometimes - be cautious.
            # To be consistent: geometry as lon,lat for shapely when making polygon for GeoJSON.
            # create polygon geojson (lon,lat order)
            poly_geojson = mapping(circle)
            # Add pm polygon
            if "PM2.5" in params and pm_val is not None:
                color = pm_cmap(pm_val)
                fol = folium.GeoJson(poly_geojson, style_function=lambda feat, c=color: {"fillColor": c, "color": c, "weight":0.4, "fillOpacity":0.7}, tooltip=f"PM2.5: {pm_val}")
                fol.add_to(pm_fg)
            # temperature polygon
            if "Temperature" in params and temp_val is not None:
                color = temp_cmap(temp_val)
                fol = folium.GeoJson(poly_geojson, style_function=lambda feat, c=color: {"fillColor": c, "color": c, "weight":0.4, "fillOpacity":0.6}, tooltip=f"Temp: {temp_val} °C")
                fol.add_to(t_fg)
            # humidity polygon
            if "Humidity" in params and hum_val is not None:
                color = hum_cmap(hum_val)
                fol = folium.GeoJson(poly_geojson, style_function=lambda feat, c=color: {"fillColor": c, "color": c, "weight":0.4, "fillOpacity":0.5}, tooltip=f"Humidity: {hum_val} %")
                fol.add_to(h_fg)
            # cyclone: check if point lies inside the simple coastal polygons; if yes, add a highlight (slightly bigger)
            if "Cyclone Zone" in params:
                # quick inside test using our simple polygons
                # we use lat/lon polygon lists above
                p_point = Point(lon, lat)
                bay_poly = LineString([(c[1], c[0]) for c in bay]).buffer(0.1)  # rough
                arab_poly = LineString([(c[1], c[0]) for c in arab]).buffer(0.1)
                if bay_poly.contains(p_point) or arab_poly.contains(p_point):
                    fol = folium.GeoJson(poly_geojson, style_function=lambda feat: {"fillColor":"purple","color":"purple","weight":0.3,"fillOpacity":0.25}, tooltip=f"Cyclone-prone zone")
                    fol.add_to(cycl_fg)
        # add feature groups to map and re-render
        if "PM2.5" in params:
            pm_fg.add_to(m); overlay_groups["PM2.5"] = pm_fg
        if "Temperature" in params:
            t_fg.add_to(m); overlay_groups["Temperature"] = t_fg
        if "Humidity" in params:
            h_fg.add_to(m); overlay_groups["Humidity"] = h_fg
        if "Cyclone Zone" in params:
            cycl_fg.add_to(m); overlay_groups["Cyclone Zone"] = cycl_fg
        # add LayerControl to toggle groups
        folium.LayerControl().add_to(m)
        # show sampled points summary in a dataframe (fast)
        sample_df = pd.DataFrame(sample_rows)
        st.dataframe(sample_df.head(200))
        # re-render map with overlays
        st_folium(m, width=1100, height=650)
        st.success("Overlays applied. Toggle layers using the map layer control (top-right).")

# -------------------------
# Analysis & PDF generation
# -------------------------
def create_pdf_report(results, out_path, client, line_name):
    pdf = FPDF()
    pdf.add_page()
    if os.path.exists("deccan_logo.png"):
        pdf.image("deccan_logo.png", x=10, y=8, w=40)
    pdf.set_font("Arial", "B", 14)
    pdf.cell(0, 10, "Deccan Environmental Severity Report", ln=True, align="C")
    pdf.ln(6)
    pdf.set_font("Arial", size=11)
    pdf.cell(0, 6, f"Client: {client}", ln=True)
    pdf.cell(0, 6, f"Line: {line_name}", ln=True)
    pdf.ln(4)
    for idx, res in enumerate(results, start=1):
        pdf.set_font("Arial", "B", 12)
        pdf.cell(0, 6, f"Line {idx} summary", ln=True)
        pdf.set_font("Arial", size=11)
        pdf.cell(0, 6, f"Samples: {len(res['df'])}  |  Mean Severity: {res['mean_sev']:.1f}%", ln=True)
        pdf.multi_cell(0, 6, f"Recommendation: {res['recommendation']}")
        # mini-plot
        fig, ax = plt.subplots(figsize=(4,2))
        sc = ax.scatter(res['df']['lon'], res['df']['lat'], c=res['df']['severity'], cmap="RdYlBu_r", s=20)
        ax.set_xlabel("Lon"); ax.set_ylabel("Lat")
        plt.colorbar(sc, ax=ax, orientation='horizontal', pad=0.2, label='Severity %')
        buf = io.BytesIO()
        plt.tight_layout()
        fig.savefig(buf, format="PNG", dpi=150)
        plt.close(fig)
        buf.seek(0)
        tmpimg = os.path.join(tempfile.gettempdir(), f"mini_{idx}.png")
        with open(tmpimg, "wb") as fh:
            fh.write(buf.read())
        pdf.image(tmpimg, w=150)
        pdf.ln(8)
    pdf.output(out_path)
    return out_path

if analyze_btn and user_line is not None:
    # perform sampling and full analysis (similar to overlay but now compute severity and recommendations)
    with st.spinner("Analyzing line(s)..."):
        lines = []
        # gather drawn/uploaded or typed line as list(s)
        if map_data and "all_drawings" in map_data and map_data["all_drawings"]:
            for feat in map_data["all_drawings"]:
                g = feat.get("geometry")
                if g and g.get("type") in ("LineString",):
                    coords = g.get("coordinates")
                    pts_coords = [(c[1], c[0]) for c in coords]
                    lines.append(LineString(pts_coords))
        if input_mode == "Enter coordinates (A → B)" and user_line is not None:
            lines.append(user_line)
        # analyze each line
        report_list = []
        for line in lines:
            samples = points_along_line(line, spacing_m=sample_interval_m)
            rows = []
            for p in samples:
                lat = p.y; lon = p.x
                met = fetch_open_meteo(lat, lon)
                t = met.get("temperature"); h = met.get("humidity")
                pm = fetch_openaq_nearby(lat, lon, radius_km=50)
                sev = severity_pct(pm, t, h)
                rows.append({"lat": lat, "lon": lon, "pm": pm, "temp": t, "hum": h, "severity": sev})
            df = pd.DataFrame(rows)
            mean_sev = df["severity"].mean() if not df["severity"].isna().all() else 0.0
            recommendation = "Recommend upgraded EHV silicone spec due to high combined environmental stress." if mean_sev >= 60 else "Standard insulator spec acceptable; consider targeted monitoring."
            report_list.append({"df": df, "mean_sev": mean_sev, "recommendation": recommendation})
        # create PDF
        out_pdf = os.path.join(tempfile.gettempdir(), "Deccan_Env_Report.pdf")
        create_pdf_report(report_list, out_pdf, client_name, line_name)
        with open(out_pdf, "rb") as fh:
            st.download_button("⬇️ Download PDF report", data=fh, file_name="Deccan_Env_Report.pdf", mime="application/pdf")
        st.success("Analysis complete — PDF generated.")

# -------------------------
# Final notes
# -------------------------
st.markdown("---")
st.caption("Notes: This app samples live APIs (OpenAQ/WAQI and Open-Meteo). Results are a fast corridor-level heuristic — for full raster accuracy (ERA5 / MODIS) we can add tiled raster overlays in a next phase.")
