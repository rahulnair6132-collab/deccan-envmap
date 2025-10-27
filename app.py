# app.py
# Deccan Environmental Severity Dashboard — Production edition
# Includes: interactive map, multi-line analysis, PDF report with logo & mini-map
# Save deccan_logo.png in the same repo.

import streamlit as st
from streamlit_folium import st_folium
import folium
from folium.plugins import HeatMap, Draw
import requests
import pandas as pd
import numpy as np
from shapely.geometry import shape, LineString, Point
import matplotlib.pyplot as plt
from PIL import Image
import tempfile, os, io
from fpdf import FPDF
import branca.colormap as cm
import matplotlib
matplotlib.use("Agg")

# ---------------------------
# Basic page setup + CSS
# ---------------------------
st.set_page_config(page_title="Deccan Env Severity Dashboard", layout="wide")
st.markdown(
    """
    <style>
    header {visibility: hidden;}
    footer {visibility: hidden;}
    #MainMenu {visibility: hidden;}
    .stApp { background-color: #f7fbff; }
    .title-bar { display:flex; align-items:center; justify-content:center; background:#0a3b78; color:white; padding:10px; border-radius:8px; }
    .title-bar img { height:42px; margin-right:12px; }
    </style>
    """,
    unsafe_allow_html=True,
)

# Top header with logo (logo file must be in repo as deccan_logo.png)
with st.container():
    col1, col2, col3 = st.columns([1, 10, 1])
    with col2:
        logo_html = ""
        if os.path.exists("deccan_logo.png"):
            logo_html = '<img src="deccan_logo.png" style="height:42px;margin-right:12px"/>'
        st.markdown(f'<div class="title-bar">{logo_html}<h3 style="margin:0;">Deccan Environmental Severity Dashboard (India)</h3></div>', unsafe_allow_html=True)
    st.write("Interactive heatmap overlays + multi-line severity analysis for insulator impacts. Draw lines or upload your transmission routes, then click **Analyze lines** to generate a PDF report.")

# ---------------------------
# Sidebar controls
# ---------------------------
st.sidebar.header("Map Controls")
params = st.sidebar.multiselect("Select overlays:", ["PM2.5", "Temperature", "Humidity"], default=["PM2.5", "Temperature", "Humidity"])
region_center = st.sidebar.selectbox("Default region:", ["India", "Gujarat (Demo)"], index=0)
uploaded_lines = st.sidebar.file_uploader("Upload transmission lines (GeoJSON/KML)", type=["geojson", "json", "kml", "kmz"])
uploaded_cyclone = st.sidebar.file_uploader("Upload cyclone zones (GeoJSON/KML)", type=["geojson", "json", "kml", "kmz"])
sample_km = st.sidebar.number_input("Sampling interval (meters) along line (approx):", min_value=100, max_value=50000, value=5000, step=100)
st.sidebar.markdown("---")
st.sidebar.info("Data sources: OpenAQ (PM2.5) with WAQI fallback, Open-Meteo (temperature & humidity), IMD/IBTrACS (cyclone polygons)")

# ---------------------------
# Helper functions (data fetch + processing)
# ---------------------------
def fetch_openaq_pm25(bounds=[68,6,97,36]):
    """Fetch PM2.5 from OpenAQ. If empty, fallback to WAQI demo map API."""
    try:
        base = "https://api.openaq.org/v2/latest"
        params = {"parameter":"pm25","limit":10000}
        # OpenAQ bbox format if needed (minLon,minLat,maxLon,maxLat) - but we'll skip to fetch all and filter
        r = requests.get(base, params=params, timeout=12)
        j = r.json()
        pts = []
        for rec in j.get("results", []):
            coords = rec.get("coordinates")
            if not coords:
                continue
            for m in rec.get("measurements", []):
                if m.get("parameter") == "pm25" and m.get("value") is not None:
                    lat = coords.get("latitude"); lon = coords.get("longitude")
                    # filter bounds
                    if bounds[0] <= lon <= bounds[2] and bounds[1] <= lat <= bounds[3]:
                        pts.append([lat, lon, m.get("value")])
        df = pd.DataFrame(pts, columns=["lat","lon","value"])
        if df.empty:
            # WAQI fallback (demo token)
            token = "demo"
            waqi_url = f"https://api.waqi.info/map/bounds/?latlng={bounds[1]},{bounds[0]},{bounds[3]},{bounds[2]}&token={token}"
            r2 = requests.get(waqi_url, timeout=10).json()
            pts2 = []
            if r2.get("status") == "ok":
                for d in r2.get("data", []):
                    v = d.get("v")
                    if v is None: continue
                    pts2.append([d.get("lat"), d.get("lon"), v])
            df = pd.DataFrame(pts2, columns=["lat","lon","value"])
        return df
    except Exception as e:
        st.warning(f"Air fetch failed, using placeholders: {e}")
        return pd.DataFrame({"lat":[19.0,22.0,26.0],"lon":[72.8,77.2,88.3],"value":[80,65,95]})

def fetch_open_meteo_for_points(points):
    """Given list of (lat,lon) return dataframe with temperature and humidity (current)."""
    rows=[]
    for lat,lon in points:
        try:
            url="https://api.open-meteo.com/v1/forecast"
            params={"latitude":lat,"longitude":lon,"current_weather":True,"hourly":"relativehumidity_2m"}
            r = requests.get(url, params=params, timeout=8).json()
            temp = r.get("current_weather",{}).get("temperature")
            hum = None
            if "hourly" in r and "relativehumidity_2m" in r["hourly"]:
                hourly = r["hourly"]["relativehumidity_2m"]
                if isinstance(hourly, list) and len(hourly)>0:
                    hum = hourly[0]
            rows.append({"lat":lat,"lon":lon,"temperature":temp,"humidity":hum})
        except:
            rows.append({"lat":lat,"lon":lon,"temperature":None,"humidity":None})
    return pd.DataFrame(rows)

def idw_interpolate(df, valcol="value", bbox=[68,6,97,36], res_deg=0.5, power=2):
    """IDW interpolation to grid (coarse) — returns numpy grid and bbox."""
    if df.empty: return None, None
    min_lon, min_lat, max_lon, max_lat = bbox
    xs = np.arange(min_lon, max_lon, res_deg)
    ys = np.arange(min_lat, max_lat, res_deg)
    grid = np.zeros((len(ys), len(xs)))
    pts = df[["lon","lat",valcol]].dropna().values
    if len(pts) == 0: return None, None
    for i,y in enumerate(ys):
        for j,x in enumerate(xs):
            d = np.sqrt((pts[:,0]-x)**2 + (pts[:,1]-y)**2)
            if np.any(d==0):
                grid[i,j] = pts[d==0,2][0]
            else:
                w = 1.0/(d**power)
                grid[i,j] = np.sum(w*pts[:,2]) / np.sum(w)
    return grid, (min_lon,min_lat,max_lon,max_lat)

def add_grid_overlay(m, grid, bbox, cmap_name="hot", name="Overlay", opacity=0.5):
    """Convert grid to PNG, add ImageOverlay. Uses temp file to avoid serialization error."""
    if grid is None:
        return
    g = np.nan_to_num(grid, nan=0.0)
    vmin, vmax = np.nanmin(g), np.nanmax(g)
    if vmax == vmin:
        vmax = vmin + 1.0
    norm = (g - vmin) / (vmax - vmin)
    cmap = plt.get_cmap(cmap_name)
    rgba = (cmap(norm) * 255).astype(np.uint8)
    img = Image.fromarray(rgba)
    tmpfile = os.path.join(tempfile.gettempdir(), f"{name.replace(' ','_')}.png")
    img.save(tmpfile)
    min_lon, min_lat, max_lon, max_lat = bbox
    folium.raster_layers.ImageOverlay(tmpfile, bounds=[[min_lat, min_lon],[max_lat, max_lon]], opacity=opacity, name=name).add_to(m)

# Scoring rules (example)
def score_pm25(v):
    if v is None: return np.nan
    if v > 100: return 4
    if v > 60: return 3
    if v > 30: return 2
    return 1

def score_humidity(v):
    if v is None: return np.nan
    if v > 80: return 4
    if v > 60: return 3
    if v > 40: return 2
    return 1

def score_temperature(v):
    if v is None: return np.nan
    if v > 45: return 4
    if v > 35: return 3
    if v > 25: return 2
    return 1

def severity_pct_row(pm, hum, temp):
    scores = []
    for val,fn in [(pm,score_pm25),(hum,score_humidity),(temp,score_temperature)]:
        s = fn(val)
        scores.append(s if np.isfinite(s) else 0)
    total = sum(scores)
    max_total = 4 * 3
    pct = (total / max_total) * 100
    return pct

# ---------------------------
# Prepare base data (safe startup)
# ---------------------------
india_bbox = [68,6,97,36]
st.info("Loading background data (this is quick).")
pm_df = fetch_openaq_pm25(india_bbox)  # may fallback to WAQI or placeholders

# coarse sample grid for meteodata
lat_grid = np.linspace(8,33,9)
lon_grid = np.linspace(68,92,13)
sample_points = [(float(lat), float(lon)) for lat in lat_grid for lon in lon_grid][::3]
meteo_df = fetch_open_meteo_for_points(sample_points)
temp_df = meteo_df[["lat","lon","temperature"]].dropna().rename(columns={"temperature":"value"})
hum_df = meteo_df[["lat","lon","humidity"]].dropna().rename(columns={"humidity":"value"})

# ---------------------------
# Build Folium map and overlays
# ---------------------------
if region_center == "India":
    m_center = [22.0, 80.0]; zoom = 5
else:
    m_center = [23.0, 71.5]; zoom = 7
m = folium.Map(location=m_center, zoom_start=zoom, tiles="CartoDB positron")

# built-in cyclone zones (coastal belts)
cyclone_zones = [
    {"name":"Bay of Bengal","coords":[[21.5,89.0],[19.0,87.5],[15.0,84.5],[13.0,80.5],[12.0,78.0],[15.0,83.0],[18.0,86.0],[21.5,89.0]]},
    {"name":"Arabian Sea","coords":[[23.0,67.5],[20.0,69.0],[16.0,72.5],[14.0,74.0],[12.5,74.0],[15.0,71.0],[19.0,68.5],[23.0,67.5]]}
]
for cz in cyclone_zones:
    folium.Polygon(cz["coords"], color="purple", fill=True, fill_opacity=0.22, tooltip=cz["name"], name="Cyclone Zones").add_to(m)

# Add heat/overlay layers based on params
if "PM2.5" in params and not pm_df.empty:
    HeatMap(pm_df[["lat","lon","value"]].values.tolist(), radius=18, blur=12, min_opacity=0.3, name="PM2.5").add_to(m)
    try:
        cm1 = cm.linear.YlOrRd_09.scale(pm_df["value"].min(), pm_df["value"].max())
        cm1.caption = "PM2.5 (µg/m³)"
        m.add_child(cm1)
    except: pass

if "Temperature" in params and not temp_df.empty:
    grid_t, bbox_t = idw_interpolate(temp_df, "value", india_bbox, res_deg=0.5)
    add_grid_overlay(m, grid_t, bbox_t, cmap_name="hot", name="Temperature")

if "Humidity" in params and not hum_df.empty:
    grid_h, bbox_h = idw_interpolate(hum_df, "value", india_bbox, res_deg=0.5)
    add_grid_overlay(m, grid_h, bbox_h, cmap_name="Blues", name="Humidity")

# Demo line as default (Morbi -> Ahmedabad)
folium.PolyLine([(22.8176,70.8121),(23.0225,72.5714)], color="yellow", weight=3, tooltip="Morbi → Ahmedabad (demo)").add_to(m)

Draw(export=True, filename="drawn.geojson").add_to(m)
folium.LayerControl().add_to(m)

# Static legend & data sources box (bottom-left)
legend_html = """
<div style="position: fixed; bottom: 18px; left: 18px; z-index:9999; background:white; padding:10px; border-radius:8px; box-shadow:2px 2px 6px rgba(0,0,0,0.2); font-size:12px;">
<b>Legend</b><br>
<span style='display:inline-block;width:12px;height:12px;background:#ffffb2;margin-right:6px;'></span> Low PM2.5 &nbsp;
<span style='display:inline-block;width:12px;height:12px;background:#bd0026;margin-left:8px;margin-right:6px;'></span> High PM2.5<br>
<span style='display:inline-block;width:12px;height:12px;background:#fee0d2;margin-right:6px;'></span> Low Temp &nbsp;
<span style='display:inline-block;width:12px;height:12px;background:#99000d;margin-left:8px;margin-right:6px;'></span> High Temp<br>
<span style='display:inline-block;width:12px;height:12px;background:#deebf7;margin-right:6px;'></span> Low Humidity &nbsp;
<span style='display:inline-block;width:12px;height:12px;background:#08306b;margin-left:8px;margin-right:6px;'></span> High Humidity<br><br>
<b>Data Sources:</b><br>OpenAQ, WAQI, Open-Meteo, IMD, IBTrACS
</div>
"""
m.get_root().html.add_child(folium.Element(legend_html))

# Render the folium map in Streamlit
st_map = st_folium(m, width=1100, height=700)

# ---------------------------
# Line analysis & PDF generation
# ---------------------------
st.markdown("---")
st.header("Analyze drawn/uploaded transmission lines")

# Helper: sample along a shapely LineString at roughly every N meters (approx)
def sample_line_points(line_geom: LineString, interval_meters=5000):
    # approximate degrees per meter (latitude approx): 1 deg ≈ 111km => 1 meter ≈ 9e-6 deg
    # We'll sample using normalized distance steps
    length = line_geom.length
    # number of samples: at least 2, at most 200
    n_samples = max(2, min(200, int(length / (interval_meters * 9e-6))))
    pts = [line_geom.interpolate(float(i)/(n_samples-1), normalized=True) for i in range(n_samples)]
    return pts

# Collect lines: from drawn features (st_map) and uploaded file
lines_to_analyze = []

# drawn features
if st_map and "all_drawings" in st_map and st_map["all_drawings"]:
    for feat in st_map["all_drawings"]:
        try:
            geom = feat.get("geometry")
            if not geom: continue
            ls = shape(geom)
            if ls.geom_type in ("LineString","MultiLineString"):
                lines_to_analyze.append({"source":"drawn","geom":ls})
        except:
            pass

# uploaded file
if uploaded_lines is not None:
    try:
        data = uploaded_lines.read()
        try:
            gj = json.loads(data.decode("utf-8"))
            for f in gj.get("features", []):
                geom = f.get("geometry")
                if geom:
                    ls = shape(geom)
                    if ls.geom_type in ("LineString","MultiLineString"):
                        lines_to_analyze.append({"source":"uploaded","geom":ls, "properties": f.get("properties", {})})
        except Exception:
            # try writing temp file and let folium parse; skip for analysis
            pass
    except Exception as e:
        st.warning(f"Could not parse uploaded lines: {e}")

if len(lines_to_analyze) == 0:
    st.info("Draw a line on the map (Draw tool) or upload a GeoJSON/KML of lines to analyze.")
else:
    st.success(f"{len(lines_to_analyze)} line(s) ready for analysis.")

if st.button("🔍 Analyze lines and generate PDF report"):
    overall_report = []
    # for each line: sample, fetch nearest PM2.5 & open-meteo, compute severity
    for idx, item in enumerate(lines_to_analyze, start=1):
        line_geom = item["geom"]
        pts = sample_line_points(line_geom, interval_meters=sample_km)
        samples = []
        for p in pts:
            lat = p.y; lon = p.x
            # PM2.5: nearest station from pm_df
            pm_val = None
            if not pm_df.empty:
                try:
                    dists = np.sqrt((pm_df["lat"]-lat)**2 + (pm_df["lon"]-lon)**2)
                    nearest = pm_df.iloc[dists.idxmin()]
                    pm_val = float(nearest["value"])
                except:
                    pm_val = None
            # Meteo: Open-Meteo single-point call
            temp_val = None; hum_val = None
            try:
                url="https://api.open-meteo.com/v1/forecast"
                params={"latitude":lat,"longitude":lon,"current_weather":True,"hourly":"relativehumidity_2m"}
                r = requests.get(url, params=params, timeout=8).json()
                temp_val = r.get("current_weather",{}).get("temperature")
                if "hourly" in r and "relativehumidity_2m" in r["hourly"]:
                    hr = r["hourly"]["relativehumidity_2m"]
                    if isinstance(hr,list) and len(hr)>0:
                        hum_val = hr[0]
            except:
                pass
            sev = severity_pct_row(pm_val, hum_val, temp_val)
            samples.append({"lat":lat,"lon":lon,"pm25":pm_val,"temperature":temp_val,"humidity":hum_val,"severity_pct":sev})
        df_samp = pd.DataFrame(samples)
        mean_sev = df_samp["severity_pct"].mean()
        recommendation = "Recommend upgraded EHV silicone spec (improved hydrophobicity & higher creepage) due to high combined environmental stress." if mean_sev>=60 else "Standard spec acceptable; consider targeted monitoring."
        report_item = {
            "line_index": idx,
            "n_samples": len(df_samp),
            "mean_severity_pct": float(mean_sev if not np.isnan(mean_sev) else 0.0),
            "recommendation": recommendation,
            "samples_df": df_samp
        }
        overall_report.append(report_item)

    # Create PDF with logo, summary table, and a mini-map scatter plot for first line (as example)
    def create_report_pdf(report_items, out_path):
        pdf = FPDF()
        pdf.set_auto_page_break(auto=True, margin=15)
        pdf.add_page()
        # logo
        if os.path.exists("deccan_logo.png"):
            pdf.image("deccan_logo.png", x=10, y=8, w=40)
        pdf.set_font("Arial", "B", 14)
        pdf.cell(0, 10, "Deccan Environmental Severity Report", ln=True, align="C")
        pdf.ln(4)
        pdf.set_font("Arial", size=11)
        pdf.multi_cell(0, 6, "This report summarizes environmental stress factors sampled along provided transmission line(s). Values are sampled from monitoring networks and meteorological APIs. Severity is computed as an aggregate index across PM2.5, Temperature and Humidity.")
        pdf.ln(4)
        for item in report_items:
            pdf.set_font("Arial", "B", 12)
            pdf.cell(0,8, f"Line #{item['line_index']} — Samples: {item['n_samples']} — Mean Severity: {item['mean_severity_pct']:.1f}%", ln=True)
            pdf.set_font("Arial", size=11)
            pdf.multi_cell(0,6, f"Recommendation: {item['recommendation']}")
            # add a small table of first 6 sampled rows
            pdf.ln(2)
            pdf.set_font("Arial","B",10)
            pdf.cell(40,6,"Lat",border=1)
            pdf.cell(40,6,"Lon",border=1)
            pdf.cell(30,6,"PM2.5",border=1)
            pdf.cell(30,6,"Temp (°C)",border=1)
            pdf.cell(30,6,"Hum (%)",border=1)
            pdf.ln()
            pdf.set_font("Arial","",9)
            for _, r in item["samples_df"].head(6).iterrows():
                pdf.cell(40,6, f"{r['lat']:.4f}", border=1)
                pdf.cell(40,6, f"{r['lon']:.4f}", border=1)
                pdf.cell(30,6, f"{r['pm25'] if pd.notna(r['pm25']) else 'NA'}",border=1)
                pdf.cell(30,6, f"{r['temperature'] if pd.notna(r['temperature']) else 'NA'}",border=1)
                pdf.cell(30,6, f"{r['humidity'] if pd.notna(r['humidity']) else 'NA'}",border=1)
                pdf.ln()
            pdf.ln(6)
            # mini-plot for this line: scatter colored by severity
            fig, ax = plt.subplots(figsize=(4,2.2))
            sc = ax.scatter(item["samples_df"]["lon"], item["samples_df"]["lat"], c=item["samples_df"]["severity_pct"], cmap="RdYlBu_r", s=30)
            ax.set_xlabel("Lon"); ax.set_ylabel("Lat")
            ax.set_title(f"Severity along line #{item['line_index']}")
            ax.grid(False)
            cbar = plt.colorbar(sc, ax=ax, orientation='horizontal', pad=0.2)
            cbar.set_label("Severity %")
            buf = io.BytesIO()
            plt.tight_layout()
            fig.savefig(buf, format="PNG", dpi=150)
            plt.close(fig)
            buf.seek(0)
            # save to temp file and put into pdf
            tmpimg = os.path.join(tempfile.gettempdir(), f"line_{item['line_index']}_mini.png")
            with open(tmpimg, "wb") as fh:
                fh.write(buf.read())
            pdf.image(tmpimg, w=150)
            pdf.ln(8)
        pdf_out = out_path
        pdf.output(pdf_out)
        return pdf_out

    out_pdf = os.path.join(tempfile.gettempdir(), "Deccan_Env_Severity_Report.pdf")
    create_report_pdf(overall_report, out_pdf)

    # Present report summary + download button
    st.success("Analysis complete — PDF report generated.")
    with open(out_pdf, "rb") as f:
        st.download_button("⬇️ Download PDF Report", data=f, file_name="Deccan_Env_Severity_Report.pdf", mime="application/pdf")

    # Also show table for quick review (first line)
    st.subheader("First line sample summary (first 50 rows)")
    st.dataframe(overall_report[0]["samples_df"].reset_index(drop=True).head(50))

st.info("Notes: Severity scoring is a heuristic example (Low->1 ... VeryHigh->4). For production, we can calibrate weights per parameter and include historical rasters (ERA5/MODIS) for higher spatial accuracy.")
