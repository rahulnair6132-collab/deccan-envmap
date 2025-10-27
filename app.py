# (Full app.py code START)
import streamlit as st
from streamlit_folium import st_folium
import folium
from folium.plugins import HeatMap, Draw
import requests
import pandas as pd
import numpy as np
import json
from shapely.geometry import LineString, shape, Point
import branca.colormap as cm

st.set_page_config(page_title="Deccan Env Severity Dashboard", layout="wide")

st.title("Deccan — Environmental Severity Dashboard (India)")
st.markdown("Interactive heatmap overlays (PM2.5, Temperature, Humidity) + multi-line severity sampling. Upload cyclone GeoJSON to overlay cyclone-prone zones.")

# -------------------------
# User controls (sidebar)
# -------------------------
st.sidebar.header("Map Controls")
params = st.sidebar.multiselect("Select parameters to show as heatmap:", ["PM2.5","Temperature","Humidity"], default=["PM2.5","Temperature","Humidity"])
st.sidebar.markdown("---")
region_center = st.sidebar.selectbox("Default map zoom/region:", ["India (All)", "Gujarat (Demo)"], index=0)

st.sidebar.markdown("**Line tools**")
st.sidebar.markdown("You can: (A) draw lines on the map (Draw tool), (B) upload KML/GeoJSON lines, (C) upload CSV with start/end coords.")
uploaded_lines = st.sidebar.file_uploader("Upload GeoJSON/KML of transmission lines (optional)", type=["geojson","json","kml","kmz"])
uploaded_cyclone = st.sidebar.file_uploader("Upload Cyclone zones GeoJSON/KML (optional)", type=["geojson","json","kml","kmz"])

# Sampling resolution along a line (km)
sample_km = st.sidebar.number_input("Sample interval along a drawn line (km)", min_value=1, max_value=50, value=10)

st.sidebar.markdown("---")
st.sidebar.markdown("Data sources: OpenAQ (PM2.5), Open-Meteo (Temperature & Humidity).")

# -------------------------
# Map initialization
# -------------------------
if region_center == "India (All)":
    m_center = [22.0, 80.0]
    zoom = 5
else:
    m_center = [23.0, 71.5]  # Gujarat area
    zoom = 7

m = folium.Map(location=m_center, zoom_start=zoom, tiles="CartoDB positron")

# Layer groups
pm_layer = folium.FeatureGroup(name="PM2.5 Heatmap", show="PM2.5" in params)
temp_layer = folium.FeatureGroup(name="Temperature Heatmap", show="Temperature" in params)
hum_layer = folium.FeatureGroup(name="Humidity Heatmap", show="Humidity" in params)
cyclone_layer = folium.FeatureGroup(name="Cyclone Zones", show=False)
lines_layer = folium.FeatureGroup(name="Transmission Lines", show=True)

# -------------------------
# Helper functions
# -------------------------
def fetch_openaq_pm25(bounds=None, limit=1000):
    base = "https://api.openaq.org/v2/latest"
    params = {"parameter":"pm25", "limit":10000, "page":1}
    if bounds:
        params["bbox"] = ",".join(map(str,bounds))
    try:
        r = requests.get(base, params=params, timeout=20)
        data = r.json()
        pts = []
        for rec in data.get("results", []):
            for mrec in rec.get("measurements", []):
                if mrec.get("parameter") == "pm25" and mrec.get("value") is not None:
                    coords = rec.get("coordinates")
                    if coords:
                        lat = coords.get("latitude")
                        lon = coords.get("longitude")
                        val = mrec.get("value")
                        pts.append([lat, lon, val])
        return pd.DataFrame(pts, columns=["lat","lon","value"])
    except Exception as e:
        st.error(f"OpenAQ fetch error: {e}")
        return pd.DataFrame(columns=["lat","lon","value"])

def fetch_open_meteo_many(points):
    rows = []
    for lat, lon in points:
        try:
            url = "https://api.open-meteo.com/v1/forecast"
            params = {"latitude":lat, "longitude":lon, "current_weather":True, "hourly":"temperature_2m,relativehumidity_2m"}
            r = requests.get(url, params=params, timeout=10)
            j = r.json()
            temp = None
            hum = None
            if "current_weather" in j and j["current_weather"]:
                temp = j["current_weather"].get("temperature")
            if "hourly" in j and "relativehumidity_2m" in j["hourly"]:
                hum_vals = j["hourly"]["relativehumidity_2m"]
                if isinstance(hum_vals, list) and len(hum_vals)>0:
                    hum = hum_vals[0]
            rows.append({"lat":lat,"lon":lon,"temperature":temp,"humidity":hum})
        except Exception as e:
            rows.append({"lat":lat,"lon":lon,"temperature":None,"humidity":None})
    return pd.DataFrame(rows)

def idw_grid(points_df, value_col="value", bbox=[68,6,97,36], grid_res=0.5, power=2):
    if points_df.empty:
        return None, None
    min_lon, min_lat, max_lon, max_lat = bbox
    xs = np.arange(min_lon, max_lon, grid_res)
    ys = np.arange(min_lat, max_lat, grid_res)
    grid = np.zeros((len(ys), len(xs)))
    pts = points_df[[ "lon","lat", value_col]].dropna().values
    if len(pts)==0:
        return None, None
    for i, y in enumerate(ys):
        for j, x in enumerate(xs):
            dists = np.sqrt((pts[:,0]-x)**2 + (pts[:,1]-y)**2)
            if np.any(dists==0):
                grid[i,j] = pts[dists==0,2][0]
            else:
                weights = 1.0 / (dists**power)
                grid[i,j] = np.sum(weights * pts[:,2]) / np.sum(weights)
    return grid, (min_lon, min_lat, max_lon, max_lat)

def add_image_overlay_from_grid(m, grid, bbox, colormap, name, opacity=0.6):
    """
    Convert numeric grid into an RGBA image using colormap and overlay on folium map.
    Fixed version: saves PNG to disk to avoid JSON serialization issue on Streamlit Cloud.
    """
    import matplotlib.pyplot as plt
    from PIL import Image
    import io, os, base64, tempfile

    if grid is None:
        return
    g = np.nan_to_num(grid, nan=0.0)
    vmin, vmax = np.nanmin(g), np.nanmax(g)
    if vmax == vmin:
        vmax = vmin + 1.0
    norm = (g - vmin) / (vmax - vmin)
    cmap = plt.get_cmap(colormap)
    rgba = (cmap(norm) * 255).astype(np.uint8)
    img = Image.fromarray(rgba)

    # Save to a temporary file instead of BytesIO
    tmp_dir = tempfile.gettempdir()
    tmp_path = os.path.join(tmp_dir, f"{name.replace(' ','_')}.png")
    img.save(tmp_path)

    min_lon, min_lat, max_lon, max_lat = bbox
    img_overlay = folium.raster_layers.ImageOverlay(
        name=name,
        image=tmp_path,
        bounds=[[min_lat, min_lon], [max_lat, max_lon]],
        opacity=opacity,
        interactive=True,
        cross_origin=False,
        zindex=1,
    )
    img_overlay.add_to(m)
    return (vmin, vmax)

    import matplotlib.pyplot as plt
    from PIL import Image
    if grid is None:
        return
    g = grid.copy()
    g = np.nan_to_num(g, nan=0.0)
    vmin = np.nanmin(g)
    vmax = np.nanmax(g)
    if vmax==vmin:
        vmax = vmin+1.0
    norm = (g - vmin) / (vmax - vmin)
    cmap = plt.get_cmap(colormap)
    rgba = cmap(norm)
    img = (rgba * 255).astype(np.uint8)
    pil = Image.fromarray(img)
    import io
    bio = io.BytesIO()
    pil.save(bio, format="PNG")
    bio.seek(0)
    min_lon, min_lat, max_lon, max_lat = bbox
    img_overlay = folium.raster_layers.ImageOverlay(bio, bounds=[[min_lat, min_lon],[max_lat, max_lon]], opacity=opacity, name=name, interactive=True, cross_origin=False, zindex=1)
    img_overlay.add_to(m)
    return (vmin, vmax)

# -------------------------
# Prepare base heatmap points
# -------------------------
st.info("Loading live station/point data (OpenAQ & Open-Meteo). This may take up to 20 seconds depending on network.")

india_bbox = [68.0, 6.0, 97.0, 36.0]

pm_df = pd.DataFrame(columns=["lat","lon","value"])
if "PM2.5" in params:
    pm_df = fetch_openaq_pm25(bounds=india_bbox)
    if pm_df.empty:
        st.warning("No PM2.5 station data found from OpenAQ for the bounding region.")
    else:
        st.success(f"Loaded {len(pm_df)} PM2.5 stations.")

temp_df = pd.DataFrame()
hum_df = pd.DataFrame()
if ("Temperature" in params) or ("Humidity" in params):
    lats = np.linspace(8.0, 33.0, 9)
    lons = np.linspace(68.0, 92.0, 13)
    sample_points = [(float(lat), float(lon)) for lat in np.linspace(8.0,33.0,9) for lon in np.linspace(68.0,92.0,13)]
    sample_points = sample_points[::3]
    om_df = fetch_open_meteo_many([(p[0], p[1]) for p in sample_points])
    if not om_df.empty:
        if "Temperature" in params:
            temp_df = om_df[["lat","lon","temperature"]].dropna()
            temp_df = temp_df.rename(columns={"temperature":"value"})
        if "Humidity" in params:
            hum_df = om_df[["lat","lon","humidity"]].dropna()
            hum_df = hum_df.rename(columns={"humidity":"value"})

# -------------------------
# Build heatmaps & overlays
# -------------------------
if not pm_df.empty and "PM2.5" in params:
    heat_data = pm_df[["lat","lon","value"]].values.tolist()
    HeatMap([[r[0],r[1], r[2]] for r in heat_data], name="PM2.5 Heatmap", min_opacity=0.3, radius=20, blur=15, max_zoom=6).add_to(pm_layer)
    try:
        vmin = pm_df["value"].min()
        vmax = pm_df["value"].max()
        col = cm.linear.YlOrRd_09.scale(vmin, vmax)
        col.caption = "PM2.5 (µg/m³)"
        m.add_child(col)
    except:
        pass

if not temp_df.empty and "Temperature" in params:
    grid, bbox = idw_grid(temp_df.rename(columns={"lat":"lat","lon":"lon","value":"value"}).rename(columns={"lon":"lon","lat":"lat"})[["lon","lat","value"]], value_col="value", bbox=india_bbox, grid_res=0.5, power=2)
    if grid is not None:
        add_image_overlay_from_grid(temp_layer, grid, bbox, colormap="hot", name="Temperature Overlay", opacity=0.5)
        try:
            tmin = temp_df["value"].min(); tmax = temp_df["value"].max()
            colt = cm.linear.OrRd_09.scale(tmin, tmax)
            colt.caption = "Temperature (°C)"
            m.add_child(colt)
        except:
            pass

if not hum_df.empty and "Humidity" in params:
    grid_h, bbox_h = idw_grid(hum_df[["lon","lat","value"]], value_col="value", bbox=india_bbox, grid_res=0.5, power=2)
    if grid_h is not None:
        add_image_overlay_from_grid(hum_layer, grid_h, bbox_h, colormap="Blues", name="Humidity Overlay", opacity=0.5)
        try:
            hmin = hum_df["value"].min(); hmax = hum_df["value"].max()
            colh = cm.linear.Blues_09.scale(hmin, hmax)
            colh.caption = "Relative Humidity (%)"
            m.add_child(colh)
        except:
            pass

# -------------------------
# Cyclone overlay (user upload)
# -------------------------
if uploaded_cyclone is not None:
    try:
        bytes_data = uploaded_cyclone.read()
        try:
            gj = json.loads(bytes_data.decode("utf-8"))
            folium.GeoJson(gj, name="Cyclone Zones", style_function=lambda x: {"fillColor":"purple","color":"purple","weight":1,"fillOpacity":0.2}).add_to(cyclone_layer)
        except Exception:
            with open("tmp_cyclone.kml","wb") as f:
                f.write(bytes_data)
            folium.Kml("tmp_cyclone.kml", name="Cyclone Zones").add_to(cyclone_layer)
        st.success("Cyclone zones uploaded and added as a layer.")
    except Exception as e:
        st.error(f"Could not load cyclone file: {e}")

# -------------------------
# Load uploaded transmission lines (if provided)
# -------------------------
uploaded_lines_geojson = None
if uploaded_lines is not None:
    try:
        data = uploaded_lines.read()
        try:
            gj = json.loads(data.decode("utf-8"))
            uploaded_lines_geojson = gj
            folium.GeoJson(gj, name="Uploaded Lines").add_to(lines_layer)
            st.success("Uploaded lines added to map.")
        except Exception:
            with open("tmp_lines.kml","wb") as f:
                f.write(data)
            folium.Kml("tmp_lines.kml", name="Uploaded Lines").add_to(lines_layer)
            st.success("Uploaded KML lines added to map.")
    except Exception as e:
        st.error(f"Could not load uploaded lines: {e}")

# -------------------------
# Add demo line if no upload and show uploaded polygons
# -------------------------
demo_line_coords = [(22.8176,70.8121),(23.0225,72.5714)]
folium.PolyLine(locations=[(c[0],c[1]) for c in demo_line_coords], color="yellow", weight=3, tooltip="Morbi → Ahmedabad (demo)").add_to(lines_layer)

# -------------------------
# Add layers & control
# -------------------------
pm_layer.add_to(m)
temp_layer.add_to(m)
hum_layer.add_to(m)
cyclone_layer.add_to(m)
lines_layer.add_to(m)
folium.LayerControl().add_to(m)

draw = Draw(export=True, filename='drawn.geojson', draw_options={'polyline': True, 'polygon': False, 'marker': False, 'circle': False, 'rectangle': False}, edit_options={'edit': True})
draw.add_to(m)

st_data = st_folium(m, width=1100, height=700)

st.sidebar.markdown("---")
st.sidebar.header("Analyze drawn lines")
if st_data and "all_drawings" in st_data and st_data["all_drawings"]:
    st.sidebar.success("Detected drawn features on the map. Click 'Analyze drawn lines' to sample values along them.")
    if st.sidebar.button("Analyze drawn lines"):
        for feat in st_data["all_drawings"]:
            try:
                geom = feat["geometry"]
                line = shape(geom)
                length_deg = line.length
                num_samples = max(2, int(line.length / 0.1))
                pts = [line.interpolate(float(i)/num_samples, normalized=True) for i in range(num_samples+1)]
                samp_rows = []
                for p in pts:
                    lat = p.y; lon = p.x
                    row = {"lat":lat, "lon":lon}
                    if not pm_df.empty:
                        dists = np.sqrt((pm_df["lat"]-lat)**2 + (pm_df["lon"]-lon)**2)
                        idx = dists.idxmin()
                        row["pm25"] = float(pm_df.loc[idx,"value"])
                    try:
                        url = "https://api.open-meteo.com/v1/forecast"
                        pr = {"latitude":lat, "longitude":lon, "current_weather":True, "hourly":"relativehumidity_2m"}
                        rr = requests.get(url, params=pr, timeout=8).json()
                        if "current_weather" in rr and rr["current_weather"]:
                            row["temperature"] = rr["current_weather"].get("temperature")
                        if "hourly" in rr and "relativehumidity_2m" in rr["hourly"]:
                            row["humidity"] = rr["hourly"]["relativehumidity_2m"][0]
                    except:
                        row["temperature"]=None; row["humidity"]=None
                    samp_rows.append(row)
                sdf = pd.DataFrame(samp_rows)
                st.write("Sampled values along drawn line:")
                st.dataframe(sdf.head(20))
                def score_val(val, param):
                    if val is None:
                        return np.nan
                    if param == "pm25":
                        if val>100: return 4
                        if val>60: return 3
                        if val>30: return 2
                        return 1
                    if param == "humidity":
                        if val>80: return 4
                        if val>60: return 3
                        if val>40: return 2
                        return 1
                    if param == "temperature":
                        if val>45: return 4
                        if val>35: return 3
                        if val>25: return 2
                        return 1
                sdf["pm25_score"] = sdf["pm25"].apply(lambda x: score_val(x,"pm25"))
                sdf["hum_score"] = sdf["humidity"].apply(lambda x: score_val(x,"humidity"))
                sdf["temp_score"] = sdf["temperature"].apply(lambda x: score_val(x,"temperature"))
                sdf["sum_scores"] = sdf[["pm25_score","hum_score","temp_score"]].sum(axis=1, skipna=True)
                max_score = 4 * 3
                sdf["severity_pct"] = (sdf["sum_scores"]/max_score)*100
                st.write("Severity summary along this line:")
                st.dataframe(sdf.describe())
                mean_severity = sdf["severity_pct"].mean()
                st.success(f"Average Severity along drawn line ≈ {mean_severity:.1f}%")
            except Exception as e:
                st.error(f"Could not analyze drawn feature: {e}")

if uploaded_lines_geojson is not None:
    if st.sidebar.button("Analyze uploaded lines"):
        try:
            gj = uploaded_lines_geojson
            for feature in gj.get("features", []):
                geom = feature.get("geometry")
                if geom.get("type") in ["LineString","MultiLineString"]:
                    line = shape(geom)
                    num_samples = max(2, int(line.length / 0.1))
                    pts = [line.interpolate(float(i)/num_samples, normalized=True) for i in range(num_samples+1)]
                    samp_rows = []
                    for p in pts:
                        lat = p.y; lon = p.x
                        row = {"lat":lat,"lon":lon}
                        if not pm_df.empty:
                            dists = np.sqrt((pm_df["lat"]-lat)**2 + (pm_df["lon"]-lon)**2)
                            idx = dists.idxmin()
                            row["pm25"] = float(pm_df.loc[idx,"value"])
                        try:
                            url = "https://api.open-meteo.com/v1/forecast"
                            pr = {"latitude":lat, "longitude":lon, "current_weather":True, "hourly":"relativehumidity_2m"}
                            rr = requests.get(url, params=pr, timeout=8).json()
                            if "current_weather" in rr and rr["current_weather"]:
                                row["temperature"] = rr["current_weather"].get("temperature")
                            if "hourly" in rr and "relativehumidity_2m" in rr["hourly"]:
                                row["humidity"] = rr["hourly"]["relativehumidity_2m"][0]
                        except:
                            row["temperature"]=None; row["humidity"]=None
                        samp_rows.append(row)
                    s_df = pd.DataFrame(samp_rows)
                    st.write("Uploaded line sampled values (first rows):")
                    st.dataframe(s_df.head(20))
                    s_df["pm25_score"] = s_df["pm25"].apply(lambda x: score_val(x,"pm25"))
                    s_df["hum_score"] = s_df["humidity"].apply(lambda x: score_val(x,"humidity"))
                    s_df["temp_score"] = s_df["temperature"].apply(lambda x: score_val(x,"temperature"))
                    s_df["sum_scores"] = s_df[["pm25_score","hum_score","temp_score"]].sum(axis=1, skipna=True)
                    s_df["severity_pct"] = (s_df["sum_scores"]/(4*3))*100
                    st.success(f"Uploaded line average severity ≈ {s_df['severity_pct'].mean():.1f}%")
        except Exception as e:
            st.error(f"Error analyzing uploaded lines: {e}")

st.markdown("---")
st.markdown("Notes: For higher-resolution raster heatmaps (ERA5/MODIS), we can add raster processing and produce tiled overlays. Cyclone zones should be loaded as GeoJSON/KML from authoritative sources (IMD/IBTrACS).")
# (Full app.py code END)
