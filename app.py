import streamlit as st
import folium
from streamlit_folium import st_folium
from geopy.distance import geodesic
from streamlit_js_eval import get_geolocation
import math
import os

# --- 1. SETUP ---
st.set_page_config(page_title="Galveston Chartplotter", page_icon="⚓", layout="wide")

if 'lat' not in st.session_state: st.session_state['lat'] = 29.5500
if 'lon' not in st.session_state: st.session_state['lon'] = -94.9000

# --- 2. SIDEBAR ---
st.sidebar.title("⚓ Galveston Nav")

# GPS Button
if st.sidebar.button("📡 Get GPS Fix"):
    loc = get_geolocation()
    if loc:
        st.session_state['lat'] = loc['coords']['latitude']
        st.session_state['lon'] = loc['coords']['longitude']
        st.sidebar.success("GPS Locked")

st.sidebar.markdown("---")
# Quick Jump Presets
preset = st.sidebar.selectbox("Jump To:", ["Galveston Bay", "Ship Channel (Red Fish)", "The Jetties", "Offshore"])
if preset == "Galveston Bay": c_lat, c_lon = 29.55, -94.90
elif preset == "Ship Channel (Red Fish)": c_lat, c_lon = 29.515, -94.885
elif preset == "The Jetties": c_lat, c_lon = 29.336, -94.700
elif preset == "Offshore": c_lat, c_lon = 29.100, -94.600
else: c_lat, c_lon = 29.55, -94.90

# --- 3. MAP ENGINE ---
st.title("⚓ Galveston Chartplotter Pro")

m = folium.Map(location=[st.session_state['lat'], st.session_state['lon']], zoom_start=12, tiles=None)

# CHECK FOR OFFLINE TILES
# The path must be relative to where the command is run
offline_path = "static/tiles"
has_offline = os.path.exists(offline_path)

if has_offline:
    # --- OFFLINE MODE ---
    # Streamlit serves the 'static' folder at '/app/static/'
    folium.TileLayer(
        tiles="app/static/tiles/{z}/{x}/{y}.png",  # <--- CHANGED THIS LINE
        attr="Offline Charts",
        name="⚠️ OFFLINE CHARTS (Local)",
        overlay=False,
        control=True
    ).add_to(m)
    st.success(f"📂 Offline Charts Loaded from {offline_path}")
else:
    # --- ONLINE MODE (The High-Detail Feed) ---
    # 1. World Nav Charts (Base Paper Look)
    folium.TileLayer(
        tiles="https://services.arcgisonline.com/ArcGIS/rest/services/Specialty/World_Navigation_Charts/MapServer/tile/{z}/{y}/{x}",
        attr="Esri / NOAA",
        name="Nautical Charts (Paper Style)",
        overlay=False,
        control=True
    ).add_to(m)

    # 2. NOAA Raster Replacement (The "Official" Look)
    folium.WmsTileLayer(
        url='https://gis.charttools.noaa.gov/arcgis/rest/services/MCS/NOAAChartDisplay/MapServer/exts/MaritimeChartService/MapServer',
        layers='0,1,2,3',
        name='NOAA Official (WMS)',
        fmt='image/png',
        transparent=True,
        overlay=True,
        control=True
    ).add_to(m)

# 3. Satellite Hybrid (Always good to have)
folium.TileLayer(
    tiles="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
    attr="Esri",
    name="Satellite Photo",
    overlay=False,
    control=True
).add_to(m)

# Add Marker
folium.Marker(
    [st.session_state['lat'], st.session_state['lon']], 
    icon=folium.Icon(color="red", icon="ship", prefix="fa")
).add_to(m)

folium.LayerControl().add_to(m)
st_folium(m, width=1200, height=700)