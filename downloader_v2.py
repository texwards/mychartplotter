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
import time
from datetime import datetime
from http.server import SimpleHTTPRequestHandler, HTTPServer

# --- 1. SERVER & SHARED MEMORY ---
def start_tile_server():
    try:
        server = HTTPServer(('localhost', 8000), SimpleHTTPRequestHandler)
        server.serve_forever()
    except:
        pass

if 'server_started' not in st.session_state:
    t = threading.Thread(target=start_tile_server, daemon=True)
    t.start()
    st.session_state['server_started'] = True

@st.cache_resource
def get_shared_fleet():
    # Stores User Locations: {'Callsign': {'lat':..., 'lon':...}}
    return {}

@st.cache_resource
def get_shared_messages():
    # Stores Voice Notes: [{'from': 'Maverick', 'to': 'All', 'time': '12:00', 'audio': bytes}]
    return []

# --- 2. SETUP & STATE ---
st.set_page_config(page_title="EZChartplotter", page_icon="⚓", layout="wide")

# Persistent Settings
if 'user_callsign' not in st.session_state: st.session_state['user_callsign'] = ""
if 'pref_speed' not in st.session_state: st.session_state['pref_speed'] = 20
if 'pref_privacy' not in st.session_state: st.session_state['pref_privacy'] = "Public"
if 'pref_allowed' not in st.session_state: st.session_state['pref_allowed'] = []

# Navigation State
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

# --- 4. PAGE: SETTINGS ---
def show_settings():
    st.title("⚙️ User Settings")
    
    with st.container(border=True):
        st.subheader("👤 Identity")
        st.session_state['user_callsign'] = st.text_input(
            "My Callsign (Username)", 
            value=st.session_state['user_callsign']
        ).strip()
    
    col1, col2 = st.columns(2)
    with col1:
        with st.container(border=True):
            st.subheader("🛡️ Privacy")
            privacy_mode = st.radio("Visibility", ["Public", "Private (Only Whitelist)", "Hidden"], index=["Public", "Private (Only Whitelist)", "Hidden"].index(st.session_state['pref_privacy']))
            st.session_state['pref_privacy'] = privacy_mode
            if privacy_mode == "Private (Only Whitelist)":
                current_list = ", ".join(st.session_state['pref_allowed'])
                allowed = st.text_area("Allowed Users (Comma separated)", value=current_list)
                st.session_state['pref_allowed'] = [x.strip() for x in allowed.split(",") if x.strip()]

    with col2:
        with st.container(border=True):
            st.subheader("🚤 Defaults")
            st.session_state['pref_speed'] = st.number_input("Default Speed (kts)", 1, 100, st.session_state['pref_speed'])

    st.success("Settings Saved!")

# --- 5. PAGE: CHARTPLOTTER ---
def show_chartplotter():
    st.title(f"⚓ EZChartplotter")
    
    # --- SIDEBAR: COMMS (VOICE) ---
    st.sidebar.subheader("🎙️ Fleet Comms (PTT)")
    
    # 1. Target Selector
    comms_mode = st.sidebar.radio("Send To:", ["All Fleet", "Private"], horizontal=True, label_visibility="collapsed")
    
    target_recipient = "All"
    if comms_mode == "Private":
        target_recipient = st.sidebar.text_input("Recipient Callsign", placeholder="e.g. Goose").strip()
    else:
        st.sidebar.caption("📢 Broadcasting to everyone.")

    # 2. The Microphone
    audio_value = st.audio_input("Hold to Talk")
    
    # 3. Save Logic (With Privacy Routing)
    if audio_value:
        messages = get_shared_messages()
        sender = st.session_state['user_callsign'] if st.session_state['user_callsign'] else "Unknown"
        timestamp = datetime.now().strftime("%H:%M")
        
        # Deduplication check
        is_duplicate = False
        if messages and messages[-1]['audio'] == audio_value:
            is_duplicate = True
        
        if not is_duplicate:
            # SAVE MESSAGE WITH 'TO' FIELD
            new_msg = {
                'from': sender, 
                'to': target_recipient, # 'All' or specific name
                'time': timestamp, 
                'audio': audio_value
            }
            messages.append(new_msg)
            # Keep history short
            if len(messages) > 15: messages.pop(0)
            
            if target_recipient == "All":
                st.toast(f"Broadcast sent!", icon="📡")
            else:
                st.toast(f"Private message sent to {target_recipient}", icon="🔒")
    
    # 4. Display Messages (With Filtering)
    messages = get_shared_messages()
    my_name = st.session_state['user_callsign']
    
    with st.sidebar.expander("🔊 Recent Messages", expanded=True):
        if not messages:
            st.caption("No recent chatter.")
        else:
            # Show newest first
            for msg in reversed(messages):
                # FILTERING LOGIC: Who gets to see this?
                # 1. It is Public ('All')
                # 2. It is sent TO me
                # 3. It is sent BY me (so I see my own history)
                is_visible = False
                
                if msg['to'] == 'All':
                    is_visible = True
                    label = f"**{msg['from']}** ({msg['time']})"
                elif msg['to'] == my_name:
                    is_visible = True
                    label = f"🔒 **{msg['from']}** (Direct) ({msg['time']})"
                elif msg['from'] == my_name:
                    is_visible = True
                    label = f"🔒 **To: {msg['to']}** ({msg['time']})"
                
                if is_visible:
                    if msg['to'] != 'All':
                        st.markdown(f":red[{label}]") # Highlight private msgs in red
                    else:
                        st.markdown(label)
                    st.audio(msg['audio'])
                    st.divider()
        
        if st.button("🔄 Refresh Comms"):
            st.rerun()

    st.sidebar.markdown("---")

    # --- SIDEBAR: NAV & TRACKER ---
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
            
            # Broadcast Location
            if st.session_state['user_callsign']:
                fleet = get_shared_fleet()
                if st.session_state['pref_privacy'] == "Hidden":
                    if st.session_state['user_callsign'] in fleet: del fleet[st.session_state['user_callsign']]
                else:
                    fleet[st.session_state['user_callsign']] = {
                        "lat": st.session_state['lat'], "lon": st.session_state['lon'], 
                        "last_seen": time.time(), "privacy": st.session_state['pref_privacy'], 
                        "allowed": st.session_state['pref_allowed']
                    }

    # Fleet Watch Logic
    st.sidebar.markdown("---")
    st.sidebar.subheader("🔭 Fleet Watch")
    friend_input = st.sidebar.text_input("Find Friend")
    active_friends = []
    
    if friend_input:
        fleet = get_shared_fleet()
        if friend_input in fleet:
            data = fleet[friend_input]
            can_see = False
            if data['privacy'] == "Public": can_see = True
            elif data['privacy'] == "Private (Only Whitelist)" and st.session_state['user_callsign'] in data['allowed']: can_see = True
            
            if can_see:
                active_friends.append((friend_input, data))
                st.sidebar.success(f"Tracking **{friend_input}**")
            else:
                st.sidebar.error("⛔ Private")
        else:
            st.sidebar.warning("Offline")

    # --- MAP LAYERS ---
    m = folium.Map(location=[st.session_state['lat'], st.session_state['lon']], zoom_start=14, tiles=None)

    if os.path.exists("static/tiles"):
        folium.TileLayer(tiles="http://localhost:8000/static/tiles/{z}/{x}/{y}.png", attr="Offline", name="Offline Charts (Local)", min_zoom=10, max_zoom=16).add_to(m)
    folium.TileLayer(tiles="https://services.arcgisonline.com/ArcGIS/rest/services/Specialty/World_Navigation_Charts/MapServer/tile/{z}/{y}/{x}", attr="Esri", name="Online Paper Charts").add_to(m)
    folium.WmsTileLayer(url='https://gis.charttools.noaa.gov/arcgis/rest/services/MCS/ENCOnline/MapServer/WMSServer', layers='0,1,2,3,4,5,6,7', name='NOAA Overlay', fmt='image/png', transparent=True, overlay=True, show=True).add_to(m)

    # Tracks
    if len(st.session_state['track']) > 1:
        folium.PolyLine(st.session_state['track'], color="gray", weight=3, dash_array="5, 10").add_to(m)

    # Routes
    show_routes = st.sidebar.toggle("Show Routes", True)
    drawn_routes = folium.FeatureGroup(name="Planned Routes")
    
    if show_routes and st.session_state['polylines']:
        for i, feat in enumerate(st.session_state['polylines']):
            raw_coords = feat['geometry']['coordinates']
            lat_lon_path = [(c[1], c[0]) for c in raw_coords]
            
            if str(i) not in st.session_state['route_speeds']: st.session_state['route_speeds'][str(i)] = st.session_state['pref_speed']
            leg_speed = st.session_state['route_speeds'][str(i)]
            
            line = folium.PolyLine(lat_lon_path, color="magenta", weight=5, opacity=0.8)
            folium.Popup(get_stats_html(lat_lon_path, leg_speed, i+1), max_width=250).add_to(line)
            line.add_to(drawn_routes)
    drawn_routes.add_to(m)

    draw = Draw(
        export=False, position="topleft",
        draw_options={"polyline": {"shapeOptions": {"color": "#ff00ff", "weight": 5}}, "polygon": False, "rectangle": False, "circle": False, "marker": False, "circlemarker": False},
        edit_options={"edit": False, "remove": False}
    )
    draw.add_to(m)

    # Markers
    folium.Marker([st.session_state['lat'], st.session_state['lon']], popup=f"<b>ME</b><br>{st.session_state['user_callsign']}", icon=folium.Icon(color="blue", icon="location-arrow", prefix="fa")).add_to(m)
    for name, data in active_friends:
        folium.Marker([data['lat'], data['lon']], popup=f"<b>{name}</b><br>{datetime.fromtimestamp(data['last_seen']).strftime('%H:%M')}", icon=folium.Icon(color="orange", icon="ship", prefix="fa")).add_to(m)

    folium.LayerControl().add_to(m)
    output = st_folium(m, width=1200, height=600)

    if output and "all_drawings" in output:
        if output["all_drawings"] != st.session_state['polylines']:
            st.session_state['polylines'] = output["all_drawings"]
            st.rerun()

    # Speed Editor
    if st.session_state['polylines']:
        st.markdown("### 📋 Speed Editor")
        table_data = []
        for i, feat in enumerate(st.session_state['polylines']):
            coords = [(c[1], c[0]) for c in feat['geometry']['coordinates']]
            seg_dist = sum([geodesic(coords[j], coords[j+1]).nm for j in range(len(coords)-1)])
            speed = st.session_state['route_speeds'].get(str(i), st.session_state['pref_speed'])
            time = seg_dist / speed if speed > 0 else 0
            table_data.append({"Leg ID": i+1, "Dist": round(seg_dist, 2), "Speed (kts)": int(speed), "Time": format_duration(time)})
        
        edited = st.data_editor(pd.DataFrame(table_data), use_container_width=True, num_rows="dynamic", key="editor")
        
        if len(edited) < len(st.session_state['polylines']):
            rem_idx = [row["Leg ID"] - 1 for i, row in edited.iterrows()]
            st.session_state['polylines'] = [st.session_state['polylines'][i] for i in rem_idx]
            st.rerun()

        change = False
        for idx, row in edited.iterrows():
            if st.session_state['route_speeds'].get(str(idx)) != row["Speed (kts)"]:
                st.session_state['route_speeds'][str(idx)] = row["Speed (kts)"]
                change = True
        if change: st.rerun()

# --- 6. ROUTER ---
page = st.sidebar.radio("Menu", ["🗺️ Chartplotter", "⚙️ Settings"])
if page == "🗺️ Chartplotter": show_chartplotter()
elif page == "⚙️ Settings": show_settings()