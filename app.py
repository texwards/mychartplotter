import streamlit as st
import folium
from streamlit_folium import st_folium
from geopy.distance import geodesic
from streamlit_js_eval import get_geolocation
import math

# --- 1. SETUP & CONFIGURATION ---
st.set_page_config(page_title="Galveston Chartplotter", page_icon="⚓", layout="wide")

# --- 2. SESSION STATE SETUP (Crucial for GPS) ---
# We use session_state to let the GPS button overwrite the manual inputs
if 'lat' not in st.session_state:
    st.session_state['lat'] = 29.5500 # Default: Galveston Bay
if 'lon' not in st.session_state:
    st.session_state['lon'] = -94.9000

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
st.sidebar.title("🧭 Galveston Nav")

# GPS BUTTON
st.sidebar.write("### 🛰️ Positioning")
loc = get_geolocation()

# If the button returned data, update our session state variables
if loc:
    st.session_state['lat'] = loc['coords']['latitude']
    st.session_state['lon'] = loc['coords']['longitude']
    st.sidebar.success(f"GPS Locked: {loc['coords']['latitude']:.4f}, {loc['coords']['longitude']:.4f}")

st.sidebar.markdown("---")

# MANUAL INPUTS (Linked to Session State)
st.sidebar.subheader("📍 Start Position")
start_lat = st.sidebar.number_input("Latitude", key='lat', format="%.4f")
start_lon = st.sidebar.number_input("Longitude", key='lon', format="%.4f")

# DESTINATION INPUTS
st.sidebar.subheader("🏁 Destination")
preset = st.sidebar.selectbox("Quick Select", [
    "Custom", 
    "Kemah Boardwalk", 
    "Red Fish Island", 
    "Galveston Jetties",
    "Freeport"
])

# Galveston-Specific Defaults
if preset == "Kemah Boardwalk":
    d_lat, d_lon = 29.5446, -95.0224
elif preset == "Red Fish Island":
    d_lat, d_lon = 29.5150, -94.8850
elif preset == "Galveston Jetties":
    d_lat, d_lon = 29.3360, -94.7000
elif preset == "Freeport":
    d_lat, d_lon = 28.9430, -95.3000
else:
    d_lat, d_lon = 29.3013, -94.7977 # Galveston default

dest_lat = st.sidebar.number_input("Dest Latitude", value=d_lat, format="%.4f")
dest_lon = st.sidebar.number_input("Dest Longitude", value=d_lon, format="%.4f")

# VESSEL SETTINGS
st.sidebar.markdown("---")
speed_knots = st.sidebar.slider("Speed (kts)", 1, 50, 15)

# --- 5. CALCULATIONS ---
point_start = (start_lat, start_lon)
point_dest = (dest_lat, dest_lon)
dist = geodesic(point_start, point_dest).nm
bearing = calculate_bearing(start_lat, start_lon, dest_lat, dest_lon)
eta = dist / speed_knots if speed_knots > 0 else 0

# --- 6. DISPLAY ---
st.title("⚓ Galveston Bay Plotter")

# Dashboard
c1, c2, c3, c4 = st.columns(4)
c1.metric("Distance", f"{dist:.2f} nm")
c2.metric("Heading", f"{bearing:.0f}° T")
c3.metric("ETE", format_duration(eta))
c4.metric("Speed", f"{speed_knots} kts")

# Map
center_lat = (start_lat + dest_lat) / 2
center_lon = (start_lon + dest_lon) / 2

m = folium.Map(location=[center_lat, center_lon], zoom_start=10)

# Start Marker (Green for Start)
folium.Marker([start_lat, start_lon], tooltip="Start", icon=folium.Icon(color="green", icon="play")).add_to(m)
# End Marker (Red for Dest)
folium.Marker([dest_lat, dest_lon], tooltip="Dest", icon=folium.Icon(color="red", icon="flag")).add_to(m)
# Line
folium.PolyLine([point_start, point_dest], color="blue", weight=3, opacity=0.8, dash_array='5').add_to(m)

st_folium(m, width=1200, height=500)