import streamlit as st
import folium
from streamlit_folium import st_folium
from geopy.distance import geodesic
import math

# --- 1. SETUP & CONFIGURATION ---
st.set_page_config(page_title="Pocket Chartplotter Pro", page_icon="⚓", layout="wide")

# Helper Function: Calculate Bearing between two points
def calculate_bearing(lat1, lon1, lat2, lon2):
    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
    dlon = lon2 - lon1
    x = math.sin(dlon) * math.cos(lat2)
    y = math.cos(lat1) * math.sin(lat2) - (math.sin(lat1) * math.cos(lat2) * math.cos(dlon))
    initial_bearing = math.atan2(x, y)
    initial_bearing = math.degrees(initial_bearing)
    compass_bearing = (initial_bearing + 360) % 360
    return compass_bearing

# Helper Function: Format Decimal Hours to Hr/Min
def format_duration(hours):
    if math.isinf(hours): return "N/A"
    h = int(hours)
    m = int((hours - h) * 60)
    return f"{h}h {m}m"

# --- 2. SIDEBAR: NAVIGATION CONTROLS ---
st.sidebar.title("🧭 Nav Station")

# Section A: Vessel Settings (NEW!)
st.sidebar.subheader("⛵ Vessel Settings")
speed_knots = st.sidebar.slider("Boat Speed (knots)", min_value=1, max_value=60, value=20)

# Section B: Current Position
st.sidebar.markdown("---")
st.sidebar.subheader("📍 Start / Current Position")
start_lat = st.sidebar.number_input("Start Latitude", value=25.7617, format="%.4f")
start_lon = st.sidebar.number_input("Start Longitude", value=-80.1918, format="%.4f")

# Section C: Waypoint
st.sidebar.subheader("🏁 Destination / Waypoint")
preset = st.sidebar.selectbox("Quick Select", ["Custom", "Bimini, Bahamas", "Key West, FL", "Havana, Cuba"])

if preset == "Bimini, Bahamas":
    def_lat, def_lon = 25.7256, -79.2972
elif preset == "Key West, FL":
    def_lat, def_lon = 24.5551, -81.7800
elif preset == "Havana, Cuba":
    def_lat, def_lon = 23.1136, -82.3666
else:
    def_lat, def_lon = 25.7743, -80.1303 

dest_lat = st.sidebar.number_input("Dest Latitude", value=def_lat, format="%.4f")
dest_lon = st.sidebar.number_input("Dest Longitude", value=def_lon, format="%.4f")

# --- 3. CALCULATIONS ---
point_start = (start_lat, start_lon)
point_dest = (dest_lat, dest_lon)

# Distance & Bearing
distance_nm = geodesic(point_start, point_dest).nm
bearing = calculate_bearing(start_lat, start_lon, dest_lat, dest_lon)

# Time Calculation (Avoid division by zero)
if speed_knots > 0:
    time_hours = distance_nm / speed_knots
    time_str = format_duration(time_hours)
else:
    time_str = "Inf"

# --- 4. DASHBOARD (Metrics) ---
st.title("⚓ Pocket Chartplotter Pro")

# Custom CSS to make metrics pop
st.markdown("""
<style>
div[data-testid="stMetricValue"] { font-size: 24px; }
</style>
""", unsafe_allow_html=True)

m1, m2, m3, m4 = st.columns(4)
m1.metric("Distance", f"{distance_nm:.2f} nm")
m2.metric("Heading", f"{bearing:.0f}° True")
m3.metric("Est. Time Enroute", time_str) # Dynamic ETA
m4.metric("Target Speed", f"{speed_knots} kts")

# --- 5. MAP VISUALIZATION ---
# Center map
center_lat = (start_lat + dest_lat) / 2
center_lon = (start_lon + dest_lon) / 2

m = folium.Map(location=[center_lat, center_lon], zoom_start=8)

# Boat Icon
folium.Marker(
    [start_lat, start_lon], 
    popup="You are here", 
    tooltip="Start",
    icon=folium.Icon(color="blue", icon="location-arrow", prefix="fa")
).add_to(m)

# Destination Icon
folium.Marker(
    [dest_lat, dest_lon], 
    popup=f"Target: {preset}", 
    tooltip="Waypoint",
    icon=folium.Icon(color="red", icon="flag", prefix="fa")
).add_to(m)

# Course Line
folium.PolyLine(
    locations=[point_start, point_dest],
    color="red",
    weight=3,
    opacity=0.7,
    dash_array='10',
    tooltip=f"Course: {bearing:.0f}°"
).add_to(m)

st_folium(m, width=1200, height=500)