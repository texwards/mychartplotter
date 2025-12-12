import streamlit as st
import folium
from streamlit_folium import st_folium
from geopy.distance import geodesic
from streamlit_js_eval import get_geolocation
import math
import os
import threading
import pandas as pd
from http.server import SimpleHTTPRequestHandler, HTTPServer
import datetime

# --- 1. THE NUCLEAR OPTION (Background Server) ---
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

# Initialize Session State
if 'lat' not in st.session_state: st.session_state['lat'] = 29.5500
if 'lon' not in st.session_state: st.session_state['lon'] = -94.9000
if 'route' not in st.session_state: st.session_state['route'] = [] # Planned Route
if 'track' not in st.session_state: st.session_state['track'] = [] # Actual Breadcrumbs

# --- 3. HELPER FUNCTIONS ---
def format_duration(hours):
    if math.isinf(hours) or math.isnan(hours): return "0h 0m"
    h = int(hours)
    m = int((hours - h) * 60)
    return f"{h}h {m}m"

# --- 4. SIDEBAR ---
st.sidebar.title("⚓ Galveston Nav")

# GPS & TRACKING SECTION
st.sidebar.subheader("🛰️ GPS & Tracking")

# The Toggle to Enable Recording
is_recording = st.sidebar.checkbox("🔴 Record Track", value=False, help="Enable this to leave a breadcrumb trail.")

if st.sidebar.button("📡 Get GPS Fix", type="primary"):
    loc = get_geolocation()
    if loc:
        new_lat = loc['coords']['latitude']
        new_lon = loc['coords']['longitude']
        
        # Update Position
        st.session_state['lat'] = new_lat
        st.session_state['lon'] = new_lon
        
        # RECORD BREADCRUMB (If enabled)
        if is_recording:
            # Only add if it's different from the last point (don't stack dots)
            current_point = (new_lat, new_lon)
            if not st.session_state['track'] or st.session_state['track'][-1] != current_point:
                st.session_state['track'].append(current_point)
                st.sidebar.success(f"Breadcrumb added: {len(st.session_state['track'])}")
        else:
            st.sidebar.success("GPS Locked (Not Recording)")

# Track Management
if st.session_state['track']:
    st.sidebar.markdown(f"**Track Points:** {len(st.session_state['track'])}")
    
    # Save Track Button
    track_df = pd.DataFrame(st.session_state['track'], columns=["Lat", "Lon"])
    csv = track_df.to_csv(index=False).encode('utf-8')
    st.sidebar.download_button(
        label="💾 Save Track (CSV)",
        data=csv,
        file_name=f"track_{datetime.datetime.now().strftime('%Y%m%d_%H%M')}.csv",
        mime='text/csv',
    )
    
    if st.sidebar.button("🗑️ Clear Track"):
        st.session_state['track'] = []
        st.rerun()

st.sidebar.markdown("---")
st.sidebar.subheader("📍 Trip Planner")

# Planner Controls
speed_knots = st.sidebar.slider("Planning Speed (kts)", 1, 50, 20)
col1, col2 = st.sidebar.columns(2)
if col1.button("Clear Route"):
    st.session_state['route'] = []
    st.rerun()
if col2.button("Undo Last"):
    if st.session_state['route']:
        st.session_state['route'].pop()
        st.rerun()

# --- 5. MAIN INTERFACE ---
st.title("⚓ Galveston Chartplotter")

# Initialize Map
m = folium.Map(location=[st.session_state['lat'], st.session_state['lon']], zoom_start=12, tiles=None)

# --- MAP LAYERS ---
if os.path.exists("static/tiles"):
    folium.TileLayer(
        tiles="http://localhost:8000/static/tiles/{z}/{x}/{y}.png",
        attr="Offline Charts",
        name="Offline Charts",
        overlay=False,
        control=True
    ).add_to(m)
else:
    folium.TileLayer(
        tiles="https://services.arcgisonline.com/ArcGIS/rest/services/Specialty/World_Navigation_Charts/MapServer/tile/{z}/{y}/{x}",
        attr="Esri",
        name="Online Charts",
        overlay=False
    ).add_to(m)

# --- LAYER 1: BREADCRUMB TRAIL (The History) ---
# We draw this first so it sits *under* the active route
if len(st.session_state['track']) > 1:
    folium.PolyLine(
        st.session_state['track'], 
        color="gray", 
        weight=3, 
        dash_array="5, 10", # Makes it a dashed line
        opacity=0.7,
        tooltip="Your Track"
    ).add_to(m)

# --- LAYER 2: PLANNED ROUTE (The Future) ---
route_coords = st.session_state['route']
if len(route_coords) > 0:
    folium.Marker(route_coords[0], tooltip="Start", icon=folium.Icon(color="green", icon="play")).add_to(m)
    if len(route_coords) > 1:
        folium.Marker(route_coords[-1], tooltip="End", icon=folium.Icon(color="red", icon="stop")).add_to(m)
    for point in route_coords[1:-1]:
        folium.CircleMarker(point, radius=5, color="blue", fill=True).add_to(m)
    folium.PolyLine(route_coords, color="magenta", weight=4, opacity=0.9).add_to(m)

# --- CURRENT BOAT POSITION ---
folium.Marker(
    [st.session_state['lat'], st.session_state['lon']], 
    tooltip="Current Position", 
    icon=folium.Icon(color="blue", icon="location-arrow", prefix="fa")
).add_to(m)

# --- RENDER MAP ---
map_data = st_folium(m, width=1200, height=600)

# --- CLICK LOGIC (For Planning) ---
if map_data and map_data.get("last_clicked"):
    clicked_lat = map_data["last_clicked"]["lat"]
    clicked_lon = map_data["last_clicked"]["lng"]
    new_point = (clicked_lat, clicked_lon)
    
    if not st.session_state['route'] or st.session_state['route'][-1] != new_point:
        st.session_state['route'].append(new_point)
        st.rerun()

# --- 6. TRIP STATISTICS ---
if len(st.session_state['route']) > 1:
    st.markdown("### 📋 Active Trip Plan")
    legs = []
    total_dist = 0
    for i in range(len(st.session_state['route']) - 1):
        p1 = st.session_state['route'][i]
        p2 = st.session_state['route'][i+1]
        d = geodesic(p1, p2).nm
        t = d / speed_knots if speed_knots > 0 else 0
        total_dist += d
        legs.append({"Leg": i+1, "Dist": f"{d:.2f} nm", "Time": format_duration(t)})
    
    total_time = total_dist / speed_knots if speed_knots > 0 else 0
    c1, c2, c3 = st.columns(3)
    c1.metric("Total Dist", f"{total_dist:.2f} nm")
    c2.metric("Total Time", format_duration(total_time))
    c3.metric("Waypoints", len(st.session_state['route']))
    st.dataframe(pd.DataFrame(legs), use_container_width=True)