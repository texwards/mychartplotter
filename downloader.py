import os
import requests
import math

# --- CONFIGURATION ---
# Galveston Bay Area (Zoom 12 is good for general bay, 14 for detail)
ZOOM_LEVELS = [11, 12, 13] 
# Bounding Box for Galveston Bay [South, West, North, East]
bbox = [29.2000, -95.0500, 29.7000, -94.6000]

# The "Paper Chart" Source (ArcGIS Navigation Charts)
TILE_URL = "https://services.arcgisonline.com/ArcGIS/rest/services/Specialty/World_Navigation_Charts/MapServer/tile/{z}/{y}/{x}"

OUTPUT_DIR = "static/tiles"

def deg2num(lat_deg, lon_deg, zoom):
    lat_rad = math.radians(lat_deg)
    n = 2.0 ** zoom
    xtile = int((lon_deg + 180.0) / 360.0 * n)
    ytile = int((1.0 - math.asinh(math.tan(lat_rad)) / math.pi) / 2.0 * n)
    return (xtile, ytile)

def download_tiles():
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)

    print(f"🚀 Starting download for Galveston Bay...")
    
    for z in ZOOM_LEVELS:
        x_min, y_max = deg2num(bbox[0], bbox[1], z) # South-West
        x_max, y_min = deg2num(bbox[2], bbox[3], z) # North-East
        
        total_tiles = (x_max - x_min + 1) * (y_max - y_min + 1)
        print(f"Zoom {z}: Downloading {total_tiles} tiles...")
        
        count = 0
        for x in range(x_min, x_max + 1):
            for y in range(y_min, y_max + 1):
                # Create directory structure: static/tiles/z/x/
                dir_path = f"{OUTPUT_DIR}/{z}/{x}"
                if not os.path.exists(dir_path):
                    os.makedirs(dir_path)
                
                file_path = f"{dir_path}/{y}.png"
                
                # Skip if already exists
                if os.path.exists(file_path):
                    continue
                
                url = TILE_URL.format(z=z, x=x, y=y)
                try:
                    response = requests.get(url, timeout=10)
                    if response.status_code == 200:
                        with open(file_path, 'wb') as f:
                            f.write(response.content)
                        count += 1
                        if count % 50 == 0: print(f"  Saved {count} tiles...")
                except Exception as e:
                    print(f"  Error on {url}")

    print("✅ Download Complete! You can now run the App in Offline Mode.")

if __name__ == "__main__":
    download_tiles()