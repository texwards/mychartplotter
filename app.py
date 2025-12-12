import streamlit as st
import folium
from folium.plugins import Draw
from streamlit_folium import st_folium
from geopy.distance import geodesic
from streamlit_js_eval import get_geolocation
import math
import os
import threading
import pandas as pd
from http.server import SimpleHTTPRequestHandler, HTTPServer
import json

# --- 1. BACKGROUND SERVER (Nuclear Option) ---
def start_tile_server():
    try:
        server = HTTPServer(('localhost', 8000), SimpleHTTPRequestHandler)
        server.serve_forever()
    except:
        pass

t = threading.Thread(target=start_tile_server, daemon=True)
t.start()

# --- 2. SETUP ---
st.set_page_config(page_title="Galveston Planner", page_icon="⚓", layout="wide")

if 'lat' not in st.session_state: st.session_state['lat'] = 29.5500
if 'lon' not in st.session_state: st.session_state['lon'] = -94.9000
if 'track' not in st.session_state: st.session_state['track'] = [] 

# --- 3. HELPER FUNCTIONS ---
def format_duration(hours):
    if math.isinf(hours) or math.isnan(hours): return "0h 0m"
    h = int(hours)
    m = int((hours - h) * 60)
    return f"{h}h {m}m"

# --- 4. SIDEBAR ---
st.sidebar.title("⚓ Galveston Nav")

# --- GPS TRACKING ---
st.sidebar.subheader("🚤 Active Navigation")
is_recording = st.sidebar.checkbox("🔴 Record Track", value=False)
if st.sidebar.button("📡 Get GPS Fix", type="primary"):
    loc = get_geolocation()
    if loc:
        st.session_state['lat'] = loc['coords']['latitude']
        st.session_state['lon'] = loc['coords']['longitude']
        if is_recording:
            current_point = (st.session_state['lat'], st.session_state['lon'])
            if not st.session_state['track'] or st.session_state['track'][-1] != current_point:
                st.session_state['track'].append(current_point)

if st.session_state['track']:
    st.sidebar.download_button("💾 Save Track", pd.DataFrame(st.session_state['track']).to_csv().encode('utf-8'), "track.csv", "text/csv")
    if st.sidebar.button("🗑️ Clear Track"):
        st.session_state['track'] = []
        st.rerun()

st.sidebar.markdown("---")

# --- TRIP PLANNING ---
st.sidebar.subheader("📍 Trip Planner")
speed_knots = st.sidebar.slider("Plan Speed (kts)", 1, 50, 20)
show_route = st.sidebar.checkbox("👀 Show/Edit Route", value=True)

st.sidebar.info(
    """
    **How to Edit on Chart:**
    1. Select the **Line Tool** (📉) on the map to draw.
    2. Select **Edit** (📝) to drag points.
    3. Select **Trash** (🗑️) to delete.
    """
)

# --- 5. MAP ENGINE ---
st.title("⚓ Galveston Chartplotter")

m = folium.Map(location=[st.session_state['lat'], st.session_state['lon']], zoom_start=12, tiles=None)

# Base Map Layer
if os.path.exists("static/tiles"):
    folium.TileLayer(tiles="http://localhost:8000/static/tiles/{z}/{x}/{y}.png", attr="Offline", name="Offline Charts").add_to(m)
else:
    folium.TileLayer(tiles="https://services.arcgisonline.com/ArcGIS/rest/services/Specialty/World_Navigation_Charts/MapServer/tile/{z}/{y}/{x}", attr="Esri", name="Online Charts").add_to(m)

# Draw Breadcrumb Track (Static Layer)
if len(st.session_state['track']) > 1:
    folium.PolyLine(st.session_state['track'], color="gray", weight=3, dash_array="5, 10").add_to(m)

# Current Position Marker
folium.Marker([st.session_state['lat'], st.session_state['lon']], icon=folium.Icon(color="blue", icon="location-arrow", prefix="fa")).add_to(m)

# --- THE DRAW PLUGIN (INTERACTIVE EDITING) ---
if show_route:
    draw = Draw(
        export=False,
        position="topleft",
        draw_options={
            "polyline": {
                "allowIntersection": False,
                "shapeOptions": {"color": "#ff00ff", "weight": 4} # Magenta
            },
            "polygon": False,
            "rectangle": False,
            "circle": False,
            "marker": False,
            "circlemarker": False,
        },
        edit_options={"edit": True, "remove": True}
    )
    draw.add_to(m)

# RENDER MAP
# We capture 'all_drawings' to get the route data back from the plugin
output = st_folium(m, width=1200, height=600)

# --- 6. CALCULATE ROUTE STATS FROM DRAWING ---
route_points = []

# Parse the Draw Plugin Output
if output and "all_drawings" in output and output["all_drawings"]:
    # Look for the last drawn LineString
    for feature in output["all_drawings"]:
        if feature['geometry']['type'] == 'LineString':
            # GeoJSON is [Lon, Lat], Folium needs [Lat, Lon]
            raw_coords = feature['geometry']['coordinates']
            route_points = [(c[1], c[0]) for c in raw_coords]

# Display Stats if a route exists
if route_points:
    st.markdown("### 📋 Route Data")
    
    total_dist = 0
    legs = []
    
    for i in range(len(route_points) - 1):
        p1 = route_points[i]
        p2 = route_points[i+1]
        dist = geodesic(p1, p2).nm
        total_dist += dist
        legs.append({
            "Leg": i + 1,
            "From": f"{p1[0]:.4f}, {p1[1]:.4f}",
            "To": f"{p2[0]:.4f}, {p2[1]:.4f}",
            "Distance": f"{dist:.2f} nm"
        })
        
    total_time = total_dist / speed_knots if speed_knots > 0 else 0
    
    c1, c2, c3 = st.columns(3)
    c1.metric("Total Distance", f"{total_dist:.2f} nm")
    c2.metric("Total Time", format_duration(total_time))
    c3.metric("Waypoints", len(route_points))
    
    st.dataframe(pd.DataFrame(legs), use_container_width=True)
    
elif show_route:
    st.info("👈 Use the Toolbar on the map (top-left) to Draw a Route.")