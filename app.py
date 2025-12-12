import streamlit as st
import folium
from streamlit_folium import st_folium
from geopy.distance import geodesic
from streamlit_js_eval import get_geolocation
import math
import os

# --- 1. CONFIGURATION ---
st.set_page_config(page_title="Galveston Chartplotter", page_icon="⚓", layout="wide")

# --- 2. SESSION STATE ---
if 'lat' not in st.session_state: st.session_state['lat'] = 29.5500
if 'lon' not in st.session_state: st.session_state['lon'] = -94.9000

# --- 3. HELPER FUNCTIONS ---
def calculate_bearing(lat1, lon1, lat2, lon2):
    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
    dlon = lon2 - lon1
    x = math.sin(dlon) * math.cos(lat2)
    y = math.cos(lat1) * math.sin(lat2) - (math.sin(lat1) * math.cos(lat2) * math.cos(dlon))
    initial_bearing = math.atan2(x, y)
    initial_bearing = math.degrees(initial_bearing)
    return (initial_bearing + 360) % 360

def format_duration(hours):
    if math.isinf(hours): return "N/A"
    h = int(hours)
    m = int((hours - h) * 60)
    return f"{h}h {m}m"

# --- 4. SIDEBAR ---
st.sidebar.title("⚓ Galveston Nav")

# GPS
st.sidebar.write("### 🛰️ Positioning")
if st.sidebar.button("Get GPS Location"):
    loc = get_geolocation()
    if loc:
        st.session_state['lat'] = loc['coords']['latitude']
        st.session_state['lon'] = loc['coords']['longitude']
        st.sidebar.success("GPS Locked")

st.sidebar.markdown("---")

# INPUTS
st.sidebar.subheader("📍 Start Position")
start_lat = st.sidebar.number_input("Lat", key='lat', format="%.4f")
start_lon = st.sidebar.number_input("Lon", key='lon', format="%.4f")

st.sidebar.subheader("🏁 Destination")
preset = st.sidebar.selectbox("Quick Select", [
    "Custom", "Kemah Boardwalk", "Red Fish Island", "Galveston Jetties", "Freeport"
])

if preset == "Kemah Boardwalk": d_lat, d_lon = 29.5446, -95.0224
elif preset == "Red Fish Island": d_lat, d_lon = 29.5150, -94.8850
elif preset == "Galveston Jetties": d_lat, d_lon = 29.3360, -94.7000
elif preset == "Freeport": d_lat, d_lon = 28.9430, -95.3000
else: d_lat, d_lon = 29.3013, -94.7977

dest_lat = st.sidebar.number_input("Dest Lat", value=d_lat, format="%.4f")
dest_lon = st.sidebar.number_input("Dest Lon", value=d_lon, format="%.4f")

speed_knots = st.sidebar.slider("Speed (kts)", 1, 50, 20)

# --- 5. CALCULATIONS ---
point_start = (start_lat, start_lon)
point_dest = (dest_lat, dest_lon)
dist = geodesic(point_start, point_dest).nm
bearing = calculate_bearing(start_lat, start_lon, dest_lat, dest_lon)
eta = dist / speed_knots if speed_knots > 0 else 0

# --- 6. DISPLAY ---
st.title("⚓ Galveston Bay Plotter")
c1, c2, c3, c4 = st.columns(4)
c1.metric("Distance", f"{dist:.2f} nm")
c2.metric("Heading", f"{bearing:.0f}° T")
c3.metric("ETE", format_duration(eta))
c4.metric("Speed", f"{speed_knots} kts")

# --- 7. THE CHART ENGINE ---
center_lat = (start_lat + dest_lat) / 2
center_lon = (start_lon + dest_lon) / 2

m = folium.Map(location=[center_lat, center_lon], zoom_start=12, tiles=None)

# --- LAYER 1: USACE IENC (Best for Ship Channel/Galveston) ---
# This serves high-detail channel data
folium.WmsTileLayer(
    url='https://ienc-report.usace.army.mil/arcgis/rest/services/IENC/IENC_WMS/MapServer/WMSServer',
    layers='0,1,2,3,4,5', # Requesting channel details
    name='USACE Ship Channel (Detail)',
    fmt='image/png',
    transparent=False, # Set to False to see the full chart background
    control=True
).add_to(m)

# --- LAYER 2: LOCAL TILES (Only works if folder exists) ---
# NOTE: To use this, create a folder named 'static/tiles' and put your /{z}/{x}/{y}.png files there
local_tiles_exist = os.path.exists("static/tiles")

if local_tiles_exist:
    folium.TileLayer(
        tiles="/app/static/tiles/{z}/{x}/{y}.png",
        attr="Local Charts",
        name="Downloaded Charts (Offline)",
        overlay=False,
        control=True
    ).add_to(m)
    st.sidebar.success("📂 Local Tiles Detected!")
else:
    # Fallback to World Navigation Charts
    folium.TileLayer(
        tiles="https://services.arcgisonline.com/ArcGIS/rest/services/Specialty/World_Navigation_Charts/MapServer/tile/{z}/{y}/{x}",
        attr="Esri",
        name="World Nav Charts (Backup)",
        overlay=False,
        control=True
    ).add_to(m)

# Navigation Aids (Overlay)
folium.TileLayer(
    name='Buoys & Lights',
    tiles='https://tiles.openseamap.org/seamark/{z}/{x}/{y}.png',
    attr='OpenSeaMap',
    overlay=True,
    control=True
).add_to(m)

# Course Lines
folium.Marker([start_lat, start_lon], tooltip="Start", icon=folium.Icon(color="green", icon="play")).add_to(m)
folium.Marker([dest_lat, dest_lon], tooltip="Dest", icon=folium.Icon(color="red", icon="flag")).add_to(m)
folium.PolyLine([point_start, point_dest], color="magenta", weight=4, opacity=0.8).add_to(m)

folium.LayerControl().add_to(m)
st_folium(m, width=1200, height=600)