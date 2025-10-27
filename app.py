# app.py
# Deccan Environmental Severity Dashboard (Production Build)
# Author: Rahul Nair — Deccan Enterprises Pvt. Ltd.

import streamlit as st
from streamlit_folium import st_folium
import folium
from folium.plugins import HeatMap, Draw
import requests
import pandas as pd
import numpy as np
from shapely.geometry import shape, LineString
from PIL import Image
import tempfile, os, io, json
from fpdf import FPDF
import branca.colormap as cm
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use("Agg")

# -------------------------------------------------------------------
# PAGE CONFIG + STYLES
# -------------------------------------------------------------------
st.set_page_config(page_title="Deccan Env Severity Dashboard", layout="wide")

st.markdown("""
<style>
header, footer, #MainMenu {visibility: hidden;}
.stApp {background-color: #f7fbff;}
.title-bar {
    display: flex; align-items: center; justify-content: center;
    background: #0a3b78; color: white;
    padding: 10px; border-radius: 8px; margin-bottom: 8px;
}
.title-bar img {height: 42px; margin-right: 12px;}
</style>
""", unsafe_allow_html=True)

# -------------------------------------------------------------------
# HEADER WITH LOGO
# -------------------------------------------------------------------
with st.container():
    col1, col2, col3 = st.columns([1, 10, 1])
    with col2:
        logo_html = ""
        if os.path.exists("deccan_logo.png"):
            logo_html = '<img src="deccan_logo.png" />'
        st.markdown(
            f'<div class="title-bar">{logo_html}<h3>Environmental Severity Dashboard (India)</h3></div>',
            unsafe_allow_html=True
        )
    st.write("Visualize environmental stress (PM₂.₅, temperature, humidity, cyclones) "
             "across transmission routes. Draw or upload lines to analyze stress and generate client reports.")

# -------------------------------------------------------------------
# SIDEBAR CONTROLS
# -------------------------------------------------------------------
st.sidebar.header("Map Controls")
params = st.sidebar.multiselect(
    "Select overlays:",
    ["PM2.5", "Temperature", "Humidity"],
    default=["PM2.5", "Temperature", "Humidity"]
)
region_center = st.sidebar.selectbox("Default region:", ["India", "Gujarat (Demo)"], index=0)
uploaded_lines = st.sidebar.file_uploader("Upload transmission lines (GeoJSON/KML)", type=["geojson","json","kml"])
sample_km = st.sidebar.number_input("Sampling interval (meters):", 1000, 50000, 5000, step=1000)
heat_opacity = st.sidebar.slider("Heat overlay opacity", 0.2, 0.8, 0.5, 0.05)
st.sidebar.markdown("---")
st.sidebar.info("Data: OpenAQ / WAQI / Open-Meteo / IMD / IBTrACS")

# -------------------------------------------------------------------
# FETCH FUNCTIONS
# -------------------------------------------------------------------
def fetch_openaq_pm25(bounds=[68,6,97,36]):
    """Fetch PM2.5 from OpenAQ, fallback WAQI."""
    try:
        base = "https://api.openaq.org/v2/latest"
        r = requests.get(base, params={"parameter":"pm25","limit":10000}, timeout=12).json()
        pts = []
        for rec in r.get("results", []):
            coords = rec.get("coordinates")
            if not coords: continue
            for m in rec.get("measurements", []):
                if m.get("parameter")=="pm25":
                    lat, lon = coords.get("latitude"), coords.get("longitude")
                    if bounds[0]<=lon<=bounds[2] and bounds[1]<=lat<=bounds[3]:
                        pts.append([lat, lon, m.get("value")])
        df = pd.DataFrame(pts, columns=["lat","lon","value"])
        if df.empty:
            token="demo"
            url=f"https://api.waqi.info/map/bounds/?latlng={bounds[1]},{bounds[0]},{bounds[3]},{bounds[2]}&token={token}"
            w = requests.get(url, timeout=10).json()
            if w.get("status")=="ok":
                pts=[[d["lat"],d["lon"],d["v"]] for d in w.get("data",[]) if d.get("v")]
                df=pd.DataFrame(pts,columns=["lat","lon","value"])
        return df
    except Exception as e:
        st.warning(f"Air data unavailable: {e}")
        return pd.DataFrame()

def fetch_open_meteo_points(points):
    rows=[]
    for lat,lon in points:
        try:
            r=requests.get(
                "https://api.open-meteo.com/v1/forecast",
                params={"latitude":lat,"longitude":lon,"current_weather":True,"hourly":"relativehumidity_2m"},
                timeout=8
            ).json()
            t=r.get("current_weather",{}).get("temperature")
            h=None
            if "hourly" in r and "relativehumidity_2m" in r["hourly"]:
                h=r["hourly"]["relativehumidity_2m"][0]
            rows.append({"lat":lat,"lon":lon,"temperature":t,"humidity":h})
        except:
            pass
    return pd.DataFrame(rows)

def idw_interpolate(df, valcol, bbox=[68,6,97,36], res_deg=0.5):
    if df.empty: return None, None
    min_lon, min_lat, max_lon, max_lat = bbox
    xs = np.arange(min_lon, max_lon, res_deg)
    ys = np.arange(min_lat, max_lat, res_deg)
    grid = np.zeros((len(ys), len(xs)))
    pts = df[["lon","lat",valcol]].dropna().values
    for i,y in enumerate(ys):
        for j,x in enumerate(xs):
            d=np.sqrt((pts[:,0]-x)**2+(pts[:,1]-y)**2)
            if np.any(d==0): grid[i,j]=pts[d==0,2][0]; continue
            w=1/(d**2)
            grid[i,j]=np.sum(w*pts[:,2])/np.sum(w)
    return grid, (min_lon,min_lat,max_lon,max_lat)

# -------------------------------------------------------------------
# FIXED HEATMAP OVERLAY (transparent background)
# -------------------------------------------------------------------
def add_grid_overlay(m, grid, bbox, cmap_name="hot", name="Overlay", opacity=0.5):
    """Add transparent heat overlay (no shaded box)."""
    if grid is None: return
    g=np.nan_to_num(grid,nan=0.0)
    vmin,vmax=np.nanmin(g),np.nanmax(g)
    if vmax==vmin: vmax=vmin+1
    norm=(g-vmin)/(vmax-vmin)
    cmap=plt.get_cmap(cmap_name)
    rgba=(cmap(norm)*255).astype(np.uint8)
    threshold=0.05  # low value cutoff
    rgba[...,3]=(norm>threshold).astype(np.uint8)*255
    img=Image.fromarray(rgba,"RGBA")
    tmp=os.path.join(tempfile.gettempdir(),f"{name}.png")
    img.save(tmp)
    min_lon,min_lat,max_lon,max_lat=bbox
    folium.raster_layers.ImageOverlay(
        tmp,bounds=[[min_lat,min_lon],[max_lat,max_lon]],opacity=opacity,name=name
    ).add_to(m)

# -------------------------------------------------------------------
# SCORING RULES
# -------------------------------------------------------------------
def score_pm25(v): return 4 if v>100 else 3 if v>60 else 2 if v>30 else 1
def score_temp(v): return 4 if v>45 else 3 if v>35 else 2 if v>25 else 1
def score_hum(v): return 4 if v>80 else 3 if v>60 else 2 if v>40 else 1

def severity_pct(pm, t, h):
    scores=[score_pm25(pm),score_temp(t),score_hum(h)]
    return (sum(scores)/(4*3))*100

# -------------------------------------------------------------------
# LOAD DATA
# -------------------------------------------------------------------
st.info("Loading base data...")
bbox=[68,6,97,36]
pm_df=fetch_openaq_pm25(bbox)
pts=[(lat,lon) for lat in np.linspace(8,33,9) for lon in np.linspace(68,92,13)][::3]
meteo=fetch_open_meteo_points(pts)
t_df=meteo[["lat","lon","temperature"]].dropna().rename(columns={"temperature":"value"})
h_df=meteo[["lat","lon","humidity"]].dropna().rename(columns={"humidity":"value"})

# -------------------------------------------------------------------
# BUILD MAP
# -------------------------------------------------------------------
center=[22,80] if region_center=="India" else [23,71.5]
zoom=5 if region_center=="India" else 7
m=folium.Map(location=center,zoom_start=zoom,tiles="CartoDB positron")

# Cyclone belts
zones=[
    {"name":"Bay of Bengal","coords":[[21.5,89],[19,87.5],[15,84.5],[13,80.5],[12,78],[15,83],[18,86],[21.5,89]]},
    {"name":"Arabian Sea","coords":[[23,67.5],[20,69],[16,72.5],[14,74],[12.5,74],[15,71],[19,68.5],[23,67.5]]}
]
for z in zones:
    folium.Polygon(z["coords"],color="purple",fill=True,fill_opacity=0.25,tooltip=z["name"]).add_to(m)

# Overlays
if "PM2.5" in params and not pm_df.empty:
    HeatMap(pm_df[["lat","lon","value"]].values.tolist(),radius=18,blur=12,min_opacity=0.3,name="PM2.5").add_to(m)
if "Temperature" in params and not t_df.empty:
    g,b=idw_interpolate(t_df,"value",bbox)
    add_grid_overlay(m,g,b,"hot","Temperature",opacity=heat_opacity)
if "Humidity" in params and not h_df.empty:
    g,b=idw_interpolate(h_df,"value",bbox)
    add_grid_overlay(m,g,b,"Blues","Humidity",opacity=heat_opacity)

folium.PolyLine([(22.8176,70.8121),(23.0225,72.5714)],color="yellow",weight=3,tooltip="Morbi → Ahmedabad").add_to(m)
Draw(export=True).add_to(m)
folium.LayerControl().add_to(m)

# Legend box
legend_html = """
<div style='position:fixed;bottom:20px;left:20px;z-index:9999;background:white;padding:10px;
border-radius:8px;box-shadow:2px 2px 6px rgba(0,0,0,0.2);font-size:12px;'>
<b>Legend</b><br>
<span style='background:#ffffb2;'>&nbsp;&nbsp;&nbsp;</span> Low PM₂.₅ &nbsp;
<span style='background:#bd0026;'>&nbsp;&nbsp;&nbsp;</span> High PM₂.₅<br>
<span style='background:#fee0d2;'>&nbsp;&nbsp;&nbsp;</span> Low Temp &nbsp;
<span style='background:#99000d;'>&nbsp;&nbsp;&nbsp;</span> High Temp<br>
<span style='background:#deebf7;'>&nbsp;&nbsp;&nbsp;</span> Low Humidity &nbsp;
<span style='background:#08306b;'>&nbsp;&nbsp;&nbsp;</span> High Humidity<br><br>
<b>Data Sources:</b><br>OpenAQ, WAQI, Open-Meteo, IMD, IBTrACS
</div>
"""
m.get_root().html.add_child(folium.Element(legend_html))

st_map=st_folium(m,width=1100,height=700)

# -------------------------------------------------------------------
# ANALYSIS + PDF
# -------------------------------------------------------------------
st.markdown("---")
st.header("Analyze drawn/uploaded transmission lines")

def sample_line(line:LineString, interval=5000):
    n=max(2,min(200,int(line.length/(interval*9e-6))))
    return [line.interpolate(i/(n-1),normalized=True) for i in range(n)]

lines=[]
if st_map and "all_drawings" in st_map and st_map["all_drawings"]:
    for feat in st_map["all_drawings"]:
        try:
            geom=feat.get("geometry")
            if geom: lines.append(shape(geom))
        except: pass

if uploaded_lines:
    try:
        gj=json.loads(uploaded_lines.read().decode("utf-8"))
        for f in gj.get("features",[]):
            g=f.get("geometry")
            if g: lines.append(shape(g))
    except: pass

if not lines:
    st.info("Draw or upload a line to analyze.")
else:
    st.success(f"{len(lines)} line(s) ready for analysis.")
    if st.button("🔍 Analyze and Generate PDF Report"):
        results=[]
        for idx,line in enumerate(lines,1):
            pts=sample_line(line,sample_km)
            rows=[]
            for p in pts:
                lat,lon=p.y,p.x
                pm=None
                if not pm_df.empty:
                    d=np.sqrt((pm_df["lat"]-lat)**2+(pm_df["lon"]-lon)**2)
                    pm=float(pm_df.iloc[d.idxmin()]["value"])
                t=h=None
                try:
                    j=requests.get("https://api.open-meteo.com/v1/forecast",
                        params={"latitude":lat,"longitude":lon,"current_weather":True,"hourly":"relativehumidity_2m"},
                        timeout=8).json()
                    t=j.get("current_weather",{}).get("temperature")
                    if "hourly" in j and "relativehumidity_2m" in j["hourly"]:
                        h=j["hourly"]["relativehumidity_2m"][0]
                except: pass
                rows.append({"lat":lat,"lon":lon,"pm":pm,"temp":t,"hum":h,"severity":severity_pct(pm,t,h)})
            df=pd.DataFrame(rows)
            mean=df["severity"].mean()
            rec="Recommend upgraded EHV silicone spec due to high stress." if mean>=60 else "Standard spec sufficient; periodic checks advised."
            results.append({"idx":idx,"mean":mean,"rec":rec,"df":df})

        # --- PDF generation ---
        pdf=FPDF(); pdf.add_page()
        if os.path.exists("deccan_logo.png"): pdf.image("deccan_logo.png",10,8,40)
        pdf.set_font("Arial","B",14)
        pdf.cell(0,10,"Deccan Environmental Severity Report",ln=True,align="C")
        pdf.ln(6); pdf.set_font("Arial",size=11)
        pdf.multi_cell(0,6,"This report analyzes environmental stress (PM₂.₅, temperature, humidity) along transmission lines. "
                           "Severity is computed as a normalized index (0-100%).")
        for r in results:
            pdf.ln(4)
            pdf.set_font("Arial","B",12)
            pdf.cell(0,8,f"Line #{r['idx']}  |  Avg Severity: {r['mean']:.1f}%",ln=True)
            pdf.set_font("Arial",size=11)
            pdf.multi_cell(0,6,f"Recommendation: {r['rec']}")
            # plot mini scatter
            fig,ax=plt.subplots(figsize=(4,2.2))
            sc=ax.scatter(r["df"]["lon"],r["df"]["lat"],c=r["df"]["severity"],cmap="RdYlBu_r",s=25)
            ax.set_xlabel("Longitude"); ax.set_ylabel("Latitude")
            plt.colorbar(sc,ax=ax,orientation="horizontal",pad=0.2,label="Severity %")
            buf=io.BytesIO(); plt.tight_layout(); fig.savefig(buf,format="PNG",dpi=150); plt.close(fig); buf.seek(0)
            tmp=os.path.join(tempfile.gettempdir(),f"map_{r['idx']}.png")
            open(tmp,"wb").write(buf.read()); pdf.image(tmp,w=150); pdf.ln(8)
        out=os.path.join(tempfile.gettempdir(),"Deccan_Env_Report.pdf")
        pdf.output(out)
        with open(out,"rb") as f:
            st.download_button("⬇️ Download PDF Report",data=f,file_name="Deccan_Env_Report.pdf",mime="application/pdf")
        st.success("Report generated successfully ✅")
