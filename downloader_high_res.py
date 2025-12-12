import os
import requests
import math
import time
import random

# --- CONFIGURATION ---
# Zoom 14 & 15 (High Detail)
ZOOM_LEVELS = [11,12,13,14, 15,16] 

# Galveston Bay Area
bbox = [29.2000, -95.0500, 29.7000, -94.6000]

# SOURCE: World Imagery (Satellite)
# This is the only free server guaranteed to have Zoom 15+ data
TILE_URL = "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"

OUTPUT_DIR = "static/tiles"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
}

def deg2num(lat_deg, lon_deg, zoom):
    lat_rad = math.radians(lat_deg)
    n = 2.0 ** zoom
    xtile = int((lon_deg + 180.0) / 360.0 * n)
    ytile = int((1.0 - math.asinh(math.tan(lat_rad)) / math.pi) / 2.0 * n)
    return (xtile, ytile)

def download_tiles():
    if not os.path.exists(OUTPUT_DIR): os.makedirs(OUTPUT_DIR)
        
    print("🚀 Starting Satellite Download (Zoom 14 & 15)...")
    print("⚠️ This overrides the 'Not Available' charts with real photos.")

    for z in ZOOM_LEVELS:
        x_min, y_max = deg2num(bbox[0], bbox[1], z)
        x_max, y_min = deg2num(bbox[2], bbox[3], z)
        
        total = (x_max - x_min + 1) * (y_max - y_min + 1)
        print(f"\nZoom {z}: Downloading {total} tiles...")
        
        count = 0
        for x in range(x_min, x_max + 1):
            for y in range(y_min, y_max + 1):
                dir_path = f"{OUTPUT_DIR}/{z}/{x}"
                if not os.path.exists(dir_path): os.makedirs(dir_path)
                
                file_path = f"{dir_path}/{y}.png"
                url = TILE_URL.format(z=z, x=x, y=y)
                
                try:
                    # Download regardless of if it exists (to overwrite the gray error tiles)
                    r = requests.get(url, headers=HEADERS, timeout=5)
                    
                    if r.status_code == 200:
                        with open(file_path, 'wb') as f:
                            f.write(r.content)
                        count += 1
                        if count % 100 == 0: print(f"  Saved {count}...")
                        time.sleep(random.uniform(0.05, 0.1))
                except Exception as e:
                    print(f"Error: {e}")

    print("✅ Download Complete. Restart your App!")

if __name__ == "__main__":
    download_tiles()