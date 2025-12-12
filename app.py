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

# --- 1. BACKGROUND TILE SERVER ---
def start_tile_server():
    try:
        # Serves the project folder on Port 8000
        server = HTTPServer(('localhost', 8000), SimpleHTTPRequestHandler)
        server.serve_forever()
    except:
        pass

t = threading.Thread(target=start_tile_server, daemon=True)
t.start()

# --- 2. SETUP & STATE ---
st.set_page_config(page_title="Galveston Planner", page_icon="⚓", layout="wide")

if 'lat' not in st.session_state: st.session_state['lat'] = 29.5500
if 'lon' not in st.session_state: st.session_state['lon'] = -94.9000
if 'track' not in st.session_state: st.session_state['track'] = [] 
if 'polylines' not in st.session_state: st.session_state['polylines'] = []
if 'route_speeds' not in st.session_state: st.session_state['route_speeds'] = {}

# --- 3. HELPER FUNCTIONS ---
def format_duration(hours):
    if math.isinf(hours) or math.isnan(hours): return "0h 0m"
    h = int(hours)
    m = int((hours - h) * 60)
    return f"{h}h {m}m"

def get_stats_html(coords, speed_kts, leg_id):
    total_nm = 0
    for i in range(len(coords) - 1):
        total_nm += geodesic(coords[i], coords[i+1]).nm
    time_hrs = total_nm / speed_kts if speed_kts > 0 else 0
    return f"""
    <div style="font-family: sans-serif; min-width: 160px;">
        <h5 style="margin:0; color: #0044cc;">⚓ Leg #{leg_id}</h5>
        <hr style="margin: 5px 0;">
        <b>Dist:</b> {total_nm:.2f} nm<br>
        <b>Speed:</b> {speed_kts} kts<br>
        <b>Time:</b> {format_duration(time_hrs)}
    </div>
    """

# --- 4. SIDEBAR ---
st.sidebar.title("⚓ Galveston Nav")
st.sidebar.subheader("Active Navigation")
is_recording = st.sidebar.checkbox("🔴 Record Track", value=False)
if st.sidebar.button("📡 Get GPS Fix", type="primary"):
    loc = get_geolocation()
    if loc:
        st.session_state['lat'] = loc['coords']['latitude']
        st.session_state['lon'] = loc['coords']['longitude']
        if is_recording:
            current = (st.session_state['lat'], st.session_state['lon'])
            if not st.session_state['track'] or st.session_state['track'][-1] != current:
                st.session_state['track'].append(current)

if st.session_state['track']:
    st.sidebar.download_button("💾 Save Track", pd.DataFrame(st.session_state['track']).to_csv().encode('utf-8'), "track.csv", "text/csv")
    if st.sidebar.button("🗑️ Clear Track"):
        st.session_state['track'] = []
        st.rerun()

st.sidebar.markdown("---")
st.sidebar.subheader("Trip Planner")
default_speed = st.sidebar.slider("Default Speed (kts)", 1, 60, 20)
show_routes = st.sidebar.toggle("👀 Show Routes", value=True)
if st.sidebar.button("🗑️ Delete All Routes"):
    st.session_state['polylines'] = []
    st.session_state['route_speeds'] = {}
    st.rerun()

# --- 5. MAP ENGINE ---
st.title("⚓ Galveston Chartplotter Pro")

# START AT ZOOM 14 to see markers immediately
m = folium.Map(location=[st.session_state['lat'], st.session_state['lon']], zoom_start=14, tiles=None)

# --- BASE LAYERS ---

# 1. Offline Charts (FIXED URL)
if os.path.exists("static/tiles"):
    folium.TileLayer(
        # REMOVED '/app/' -> This was causing the 404s
        tiles="http://localhost:8000/static/tiles/{z}/{x}/{y}.png", 
        attr="Offline", 
        name="Offline Charts (Local)",
        min_zoom=12,
        max_zoom=16
    ).add_to(m)

# 2. Online Backup
folium.TileLayer(
    tiles="https://services.arcgisonline.com/ArcGIS/rest/services/Specialty/World_Navigation_Charts/MapServer/tile/{z}/{y}/{x}", 
    attr="Esri", 
    name="Online Paper Charts"
).add_to(m)

# 3. NOAA Overlay (Needs Internet)
folium.WmsTileLayer(
    url='https://gis.charttools.noaa.gov/arcgis/rest/services/MCS/ENCOnline/MapServer/WMSServer',
    layers='0,1,2,3,4,5,6,7',
    name='NOAA Markers Overlay',
    fmt='image/png',
    transparent=True,
    overlay=True,
    show=True
).add_to(m)

# Track
if len(st.session_state['track']) > 1:
    folium.PolyLine(st.session_state['track'], color="gray", weight=3, dash_array="5, 10").add_to(m)

# Routes
drawn_routes = folium.FeatureGroup(name="Planned Routes")
if show_routes and st.session_state['polylines']:
    for i, feat in enumerate(st.session_state['polylines']):
        raw_coords = feat['geometry']['coordinates']
        lat_lon_path = [(c[1], c[0]) for c in raw_coords]
        if str(i) not in st.session_state['route_speeds']: st.session_state['route_speeds'][str(i)] = default_speed
        leg_speed = st.session_state['route_speeds'][str(i)]
        line = folium.PolyLine(lat_lon_path, color="magenta", weight=5, opacity=0.8)
        folium.Popup(get_stats_html(lat_lon_path, leg_speed, i+1), max_width=250).add_to(line)
        line.add_to(drawn_routes)
drawn_routes.add_to(m)

# Draw Plugin
draw = Draw(
    export=False, position="topleft",
    draw_options={"polyline": {"shapeOptions": {"color": "#ff00ff", "weight": 5}}, "polygon": False, "rectangle": False, "circle": False, "marker": False, "circlemarker": False},
    edit_options={"edit": False, "remove": False}
)
draw.add_to(m)

folium.Marker([st.session_state['lat'], st.session_state['lon']], icon=folium.Icon(color="blue", icon="location-arrow", prefix="fa")).add_to(m)

folium.LayerControl().add_to(m)
output = st_folium(m, width=1200, height=600)

if output and "all_drawings" in output:
    if output["all_drawings"] != st.session_state['polylines']:
        st.session_state['polylines'] = output["all_drawings"]
        st.rerun()

# --- TABLE ---
if st.session_state['polylines']:
    st.markdown("### 📋 Speed Editor")
    table_data = []
    total_dist = 0
    total_time = 0
    for i, feat in enumerate(st.session_state['polylines']):
        coords = [(c[1], c[0]) for c in feat['geometry']['coordinates']]
        seg_dist = 0
        for j in range(len(coords)-1): seg_dist += geodesic(coords[j], coords[j+1]).nm
        speed = st.session_state['route_speeds'].get(str(i), default_speed)
        time = seg_dist / speed if speed > 0 else 0
        total_dist += seg_dist
        total_time += time
        table_data.append({"Leg ID": i+1, "Dist (nm)": round(seg_dist, 2), "Speed (kts)": int(speed), "Est Time": format_duration(time)})
    
    edited_df = st.data_editor(
        pd.DataFrame(table_data),
        column_config={"Leg ID": st.column_config.NumberColumn(disabled=True), "Dist (nm)": st.column_config.NumberColumn(disabled=True), "Est Time": st.column_config.TextColumn(disabled=True), "Speed (kts)": st.column_config.NumberColumn(min_value=1, max_value=100)},
        use_container_width=True, num_rows="dynamic", key="editor"
    )
    
    if len(edited_df) < len(st.session_state['polylines']):
        rem_idx = [row["Leg ID"] - 1 for i, row in edited_df.iterrows()]
        st.session_state['polylines'] = [st.session_state['polylines'][i] for i in rem_idx]
        st.rerun()

    change = False
    for idx, row in edited_df.iterrows():
        if st.session_state['route_speeds'].get(str(idx)) != row["Speed (kts)"]:
            st.session_state['route_speeds'][str(idx)] = row["Speed (kts)"]
            change = True
    if change: st.rerun()
    
    st.divider()
    c1, c2, c3 = st.columns(3)
    c1.metric("Total Dist", f"{total_dist:.2f} nm")
    c2.metric("Total Time", format_duration(total_time))
    c3.metric("Total Legs", len(st.session_state['polylines']))