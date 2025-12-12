import os
import requests
import math
import time
import random

# --- CONFIGURATION ---
# Galveston Bay Area
# Zoom 14 is the "Sweet Spot" for navigation details (Depths, Markers)
ZOOM_LEVELS = [14] 
bbox = [29.2000, -95.0500, 29.7000, -94.6000]

# SOURCE: NOAA ECDIS (The Official Electronic Chart Display)
# We use the 'export' function to generate tiles on the fly
BASE_URL = "https://gis.charttools.noaa.gov/arcgis/rest/services/MCS/ENCOnline/MapServer/export"

OUTPUT_DIR = "static/tiles"

# Headers to look like a browser
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
}

# --- MATH HELPER: Tile -> Web Mercator Bounding Box ---
def tile_to_bbox(x, y, z):
    e = 20037508.3427892
    limit = e
    size = 2 * e
    
    # Calculate bounds of the tile in Web Mercator meters
    res = size / (2 ** z)
    x0 = -e + x * res
    y0 = e - (y * res) # Top of tile
    x1 = x0 + res
    y1 = y0 - res      # Bottom of tile
    
    return f"{x0},{y1},{x1},{y0}" # Left, Bottom, Right, Top

def deg2num(lat_deg, lon_deg, zoom):
    lat_rad = math.radians(lat_deg)
    n = 2.0 ** zoom
    xtile = int((lon_deg + 180.0) / 360.0 * n)
    ytile = int((1.0 - math.asinh(math.tan(lat_rad)) / math.pi) / 2.0 * n)
    return (xtile, ytile)

def download_tiles():
    if not os.path.exists(OUTPUT_DIR): os.makedirs(OUTPUT_DIR)
        
    print("🚀 Starting NOAA Chart Generator...")
    print("⚠️  This is slower than before because NOAA has to draw each tile.")

    for z in ZOOM_LEVELS:
        x_min, y_max = deg2num(bbox[0], bbox[1], z)
        x_max, y_min = deg2num(bbox[2], bbox[3], z)
        
        total = (x_max - x_min + 1) * (y_max - y_min + 1)
        print(f"\nZoom {z}: Generating {total} chart tiles...")
        
        count = 0
        for x in range(x_min, x_max + 1):
            for y in range(y_min, y_max + 1):
                dir_path = f"{OUTPUT_DIR}/{z}/{x}"
                if not os.path.exists(dir_path): os.makedirs(dir_path)
                
                file_path = f"{dir_path}/{y}.png"
                
                # Calculate the BBOX for this specific tile
                bbox_str = tile_to_bbox(x, y, z)
                
                # Construct the Magic WMS URL
                # layers=show:0-7 asks for ALL chart details (Depth, Lights, Buoys)
                params = (
                    f"?bbox={bbox_str}&bboxSR=3857&layers=show:0,1,2,3,4,5,6,7"
                    f"&size=256,256&imageSR=3857&format=png&f=image&transparent=false"
                )
                url = BASE_URL + params
                
                try:
                    # Request the image
                    r = requests.get(url, headers=HEADERS, timeout=10)
                    
                    if r.status_code == 200:
                        with open(file_path, 'wb') as f:
                            f.write(r.content)
                        
                        count += 1
                        if count % 20 == 0: print(f"  Generated {count} tiles...")
                        
                        # Be polite to NOAA servers
                        time.sleep(0.2)
                    else:
                        print(f"❌ Error {r.status_code}")
                        
                except Exception as e:
                    print(f"Error: {e}")

    print("✅ Charts Generated. These are REAL nautical charts!")

if __name__ == "__main__":
    download_tiles()