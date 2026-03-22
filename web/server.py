import os
import sqlite3
import shutil # Moved to the top!
import json
import subprocess
from datetime import datetime, timedelta
from typing import List
from fastapi import FastAPI, File, UploadFile
from fastapi.responses import FileResponse, JSONResponse
import uvicorn
from pydantic import BaseModel

# ==========================================
# 1. BULLETPROOF PATH RESOLUTION
# ==========================================
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(CURRENT_DIR)

DB_PATH = os.path.join(ROOT_DIR, "data", "void_stats.db")
TEMPLATE_PATH = os.path.join(CURRENT_DIR, "templates", "index.html")
# NEW: Define the path for the files page
FILES_TEMPLATE_PATH = os.path.join(CURRENT_DIR, "templates", "files.html") 
ABOUT_TEMPLATE_PATH = os.path.join(CURRENT_DIR, "templates", "about.html")
SETTINGS_PATH = os.path.join(ROOT_DIR, "data", "settings.json")
# NEW: Define the path to the music folder
MUSIC_DIR = os.path.expanduser("~/Music")
os.makedirs(MUSIC_DIR, exist_ok=True) # Ensure it exists

app = FastAPI()

def get_db_connection():
    """Helper to open a read-only-friendly connection to SQLite."""
    conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row 
    return conn

# ==========================================
# 2. WEB ROUTES
# ==========================================

@app.get("/")
def serve_dashboard():
    """Serves the Bento Box HTML dashboard."""
    if not os.path.exists(TEMPLATE_PATH):
        return {"error": "Dashboard UI not found. Check web/templates/index.html"}
    return FileResponse(TEMPLATE_PATH)

@app.get("/files")
def serve_files_page():
    """Serves the Drag and Drop File Manager UI."""
    if not os.path.exists(FILES_TEMPLATE_PATH):
        return {"error": "Files UI not found. Check web/templates/files.html"}
    return FileResponse(FILES_TEMPLATE_PATH)
@app.get("/about")
def serve_about_page():
    """Serves the About and Settings UI."""
    if not os.path.exists(ABOUT_TEMPLATE_PATH):
        return {"error": "About UI not found. Check web/templates/about.html"}
    return FileResponse(ABOUT_TEMPLATE_PATH)
# ==========================================
# 3. FILE MANAGER API ROUTES
# ==========================================

@app.get("/api/files")
def list_music_files():
    """Reads the ~/Music directory and returns all audio files."""
    files_list = []
    allowed_exts = ('.mp3', '.flac', '.wav', '.m4a', '.ogg')
    
    for filename in os.listdir(MUSIC_DIR):
        if filename.lower().endswith(allowed_exts):
            file_path = os.path.join(MUSIC_DIR, filename)
            size_mb = round(os.path.getsize(file_path) / (1024 * 1024), 1)
            files_list.append({"name": filename, "size": f"{size_mb} MB"})
            
    files_list.sort(key=lambda x: x['name'].lower())
    return {"files": files_list}

@app.post("/api/files")
async def upload_music_files(files: List[UploadFile] = File(...)):
    """Receives uploaded files and saves them to ~/Music."""
    allowed_exts = ('.mp3', '.flac', '.wav', '.m4a', '.ogg')
    uploaded_count = 0
    
    for file in files:
        if file.filename.lower().endswith(allowed_exts):
            file_path = os.path.join(MUSIC_DIR, file.filename)
            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
            uploaded_count += 1
            
    return {"message": f"Successfully uploaded {uploaded_count} files."}

@app.delete("/api/files/{filename}")
def delete_music_file(filename: str):
    """Deletes a specific file from ~/Music."""
    if "/" in filename or "\\" in filename or ".." in filename:
        return JSONResponse(status_code=400, content={"error": "Invalid filename."})
        
    file_path = os.path.join(MUSIC_DIR, filename)
    if os.path.exists(file_path):
        os.remove(file_path)
        return {"message": "Deleted successfully."}
    return JSONResponse(status_code=404, content={"error": "File not found."})

@app.get("/api/stats/tracking")
def get_tracking_stats(timeframe: str = "All-Time"):
    if not os.path.exists(DB_PATH):
        return {"value": 0}

    now = datetime.now()
    cutoff = 0
    if timeframe == "Week":
        cutoff = (now - timedelta(days=7)).timestamp()
    elif timeframe == "Month":
        cutoff = (now - timedelta(days=30)).timestamp()
        
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT SUM(duration_listened) as total_seconds 
            FROM listening_history 
            WHERE timestamp >= ? AND skipped = 0
        """, (cutoff,))
        result = cursor.fetchone()
        conn.close()
        
        total_seconds = result['total_seconds'] if result['total_seconds'] else 0
        total_minutes = round(total_seconds / 60)
        return {"value": total_minutes} 
    except sqlite3.Error as e:
        print(f"[API Error] Tracking: {e}")
        return {"value": 0}

@app.get("/api/stats/topsong")
def get_top_song(timeframe: str = "All-Time"):
    if not os.path.exists(DB_PATH):
        return {"title": "No Data", "artist": "Start listening!", "plays": 0}

    now = datetime.now()
    cutoff = 0
    if timeframe == "Week":
        cutoff = (now - timedelta(days=7)).timestamp()
    elif timeframe == "Month":
        cutoff = (now - timedelta(days=30)).timestamp()

    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT track_name, artist_name, COUNT(*) as play_count 
            FROM listening_history 
            WHERE timestamp >= ? AND skipped = 0
            GROUP BY track_name, artist_name 
            ORDER BY play_count DESC 
            LIMIT 1
        """, (cutoff,))
        result = cursor.fetchone()
        conn.close()
        
        if result:
            return {"title": result['track_name'], "artist": result['artist_name'], "plays": result['play_count']}
        return {"title": "No Data", "artist": "Start listening!", "plays": 0}
    except sqlite3.Error as e:
        print(f"[API Error] Top Song: {e}")
        return {"title": "Error", "artist": "Check DB", "plays": 0}

@app.get("/api/stats/topartists")
def get_top_artists(timeframe: str = "Month"):
    if not os.path.exists(DB_PATH):
        return {"artists": []}
        
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        now = datetime.now()
        cutoff = 0
        time_span_days = 30
        
        if timeframe == "Week":
            cutoff = (now - timedelta(days=7)).timestamp()
            time_span_days = 7
        elif timeframe == "Month":
            cutoff = (now - timedelta(days=30)).timestamp()
            time_span_days = 30
        else:
            cursor.execute("SELECT MIN(timestamp) as first_play FROM listening_history")
            first_play = cursor.fetchone()['first_play']
            cutoff = first_play if first_play else (now - timedelta(days=1)).timestamp()
            time_span_days = (now.timestamp() - cutoff) / 86400
            if time_span_days < 1: time_span_days = 1 
            
        cursor.execute("""
            SELECT artist_name, COUNT(*) as play_count 
            FROM listening_history 
            WHERE timestamp >= ? AND skipped = 0
            GROUP BY artist_name 
            ORDER BY play_count DESC LIMIT 3
        """, (cutoff,))
        
        top_artists = cursor.fetchall()
        results = []
        bucket_size_seconds = (time_span_days * 24 * 60 * 60) / 10 
        
        for row in top_artists:
            artist = row['artist_name']
            total_count = row['play_count']
            cursor.execute("SELECT timestamp FROM listening_history WHERE artist_name = ? AND timestamp >= ? AND skipped = 0", (artist, cutoff))
            timestamps = [r['timestamp'] for r in cursor.fetchall()]
            
            buckets = [0] * 10
            for ts in timestamps:
                delta = ts - cutoff
                bucket_idx = int(delta / bucket_size_seconds)
                if bucket_idx >= 10: bucket_idx = 9 
                if bucket_idx >= 0: buckets[bucket_idx] += 1
                    
            results.append({"name": artist, "count": total_count, "trend": buckets})
            
        conn.close()
        return {"artists": results}
    except Exception as e:
        print(f"[API Error] Top Artists: {e}")
        return {"artists": []}

@app.get("/api/stats/activedeck")
def get_active_deck():
    try:
        with open("/dev/shm/void_now_playing.json", "r") as f:
            return json.load(f)
    except Exception:
        return {"is_playing": False, "title": "No Deck Active", "progress_pct": 0}

@app.get("/api/stats/cover")
def get_cover_art():
    cover_path = "/dev/shm/void_cover.png"
    if os.path.exists(cover_path):
        return FileResponse(cover_path)
    return JSONResponse(status_code=404, content={"error": "No cover art"})

@app.get("/api/stats/weekly")
def get_weekly_stats():
    if not os.path.exists(DB_PATH):
        return {"data": [0, 0, 0, 0, 0, 0, 0]}
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT strftime('%w', datetime(timestamp, 'unixepoch', 'localtime')) as day_of_week, 
                   COUNT(*) as play_count 
            FROM listening_history 
            WHERE timestamp >= ? AND skipped = 0
            GROUP BY day_of_week
        """, ((datetime.now() - timedelta(days=7)).timestamp(),))
        results = cursor.fetchall()
        conn.close()
        
        week_data = [0, 0, 0, 0, 0, 0, 0]
        for row in results:
            day_idx = int(row['day_of_week'])
            chart_idx = 6 if day_idx == 0 else day_idx - 1
            week_data[chart_idx] = row['play_count']
        return {"data": week_data}
    except Exception:
        return {"data": [0, 0, 0, 0, 0, 0, 0]}

@app.get("/api/stats/habits")
def get_listening_habits():
    if not os.path.exists(DB_PATH):
        return {"data": [0, 0, 0, 0, 0], "peak_label": "Start Listening!", "peak_time": "", "peak_index": 4}
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT strftime('%H', datetime(CAST(timestamp AS INTEGER), 'unixepoch', 'localtime')) as hour, 
                   COUNT(*) as play_count 
            FROM listening_history 
            WHERE skipped = 0
            GROUP BY hour
        """)
        results = cursor.fetchall()
        conn.close()
        
        buckets = [0, 0, 0, 0, 0]
        for row in results:
            if row['hour'] is None: continue 
            h = int(row['hour'])
            if 6 <= h < 10: buckets[0] += row['play_count']   
            elif 10 <= h < 14: buckets[1] += row['play_count'] 
            elif 14 <= h < 18: buckets[2] += row['play_count'] 
            elif 18 <= h < 22: buckets[3] += row['play_count'] 
            else: buckets[4] += row['play_count']              
            
        labels = ["Morning", "Midday", "Afternoon", "Evening", "Night"]
        times = ["6AM — 10AM", "10AM — 2PM", "2PM — 6PM", "6PM — 10PM", "10PM — 6AM"]
        peak_idx = buckets.index(max(buckets)) if max(buckets) > 0 else 4
            
        return {"data": buckets, "peak_label": labels[peak_idx], "peak_time": times[peak_idx], "peak_index": peak_idx}
    except Exception as e:
        print(f"[API Error] Habits: {e}")
        return {"data": [0, 0, 0, 0, 0], "peak_label": "Error", "peak_time": "", "peak_index": 4}

@app.get("/api/sys/health")
def get_sys_health():
    try:
        with open("/sys/class/thermal/thermal_zone0/temp", "r") as f:
            temp_c = round(int(f.read()) / 1000, 1)
    except:
        temp_c = 0.0
        
    try:
        with open("/proc/meminfo", "r") as f:
            lines = f.readlines()
            total = int(lines[0].split()[1])
            free = int(lines[1].split()[1])
            buffers = int(lines[3].split()[1])
            cached = int(lines[4].split()[1])
            ram_pct = round(100 - ((free + buffers + cached) / total * 100))
    except:
        ram_pct = 0
        
    try:
        total_b, used_b, free_b = shutil.disk_usage("/")
        disk_pct = round((used_b / total_b) * 100)
    except:
        disk_pct = 0
        
    return {"cpu_temp": temp_c, "ram_pct": ram_pct, "disk_pct": disk_pct}

@app.get("/api/stats/genres")
def get_genre_profile():
    if not os.path.exists(DB_PATH):
        return {"labels": ["No Data"], "values": [100]}
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT genre, COUNT(*) as play_count 
            FROM listening_history 
            WHERE skipped = 0 AND genre != 'Unknown'
            GROUP BY genre 
            ORDER BY play_count DESC LIMIT 4
        """)
        results = cursor.fetchall()
        conn.close()
        
        if not results:
             return {"labels": ["Unknown"], "values": [100]}
             
        labels = [r['genre'] for r in results]
        values = [r['play_count'] for r in results]
        return {"labels": labels, "values": values}
    except Exception as e:
        print(f"[API Error] Genres: {e}")
        return {"labels": ["Error"], "values": [100]}
    
# ==========================================
# 4. ADMIN / SETTINGS API ROUTES
# ==========================================

@app.post("/api/admin/reboot")
def reboot_system():
    """Safely reboots the Raspberry Pi OS."""
    try:
        # Note: This requires the user running the server to have sudo privileges without a password prompt.
        # Alternatively, relying on standard shutdown commands if allowed.
        subprocess.Popen(["sudo", "reboot"])
        return {"message": "System is rebooting..."}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": f"Failed to reboot: {e}"})

@app.post("/api/admin/restart")
def restart_server():
    """Exits the Uvicorn process so systemd can automatically restart it."""
    # This assumes you are running the script via a systemd service that is set to 'Restart=always'
    import sys
    sys.exit(0)
    return {"message": "Restarting server..."} # Note: This line may not execute before exit

@app.post("/api/admin/wipe")
def wipe_telemetry_database():
    """Drops the listening_history table and recreates it."""
    if not os.path.exists(DB_PATH):
        return JSONResponse(status_code=404, content={"error": "Database not found."})
        
    try:
        # Connect in read-write mode for this operation
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Danger: We are wiping the table!
        cursor.execute("DROP TABLE IF EXISTS listening_history")
        
        # Recreate the table schema exactly as defined in your db.py
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS listening_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp REAL,
                track_name TEXT,
                artist_name TEXT,
                album_name TEXT,
                genre TEXT,
                duration_listened REAL,
                track_length REAL,
                skipped INTEGER
            )
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_timestamp ON listening_history(timestamp);")
        
        conn.commit()
        conn.close()
        return {"message": "Telemetry database wiped successfully."}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": f"Failed to wipe database: {e}"})
    
# --- Settings Configuration API ---

class SettingsModel(BaseModel):
    auto_play: bool
    boot_volume: int
    sleep_timer: int
    scroll_speed: int

def load_settings_file():
    """Reads settings.json or creates it with defaults."""
    defaults = {
        "auto_play": True, 
        "boot_volume": 40, 
        "sleep_timer": 300, 
        "scroll_speed": 3
    }
    if not os.path.exists(SETTINGS_PATH):
        with open(SETTINGS_PATH, "w") as f:
            json.dump(defaults, f)
        return defaults
    try:
        with open(SETTINGS_PATH, "r") as f:
            return json.load(f)
    except:
        return defaults

@app.get("/api/settings")
def get_settings():
    """Sends current settings to the dashboard."""
    return load_settings_file()

@app.post("/api/settings")
def update_settings(settings: SettingsModel):
    """Saves updated settings from the dashboard."""
    with open(SETTINGS_PATH, "w") as f:
        json.dump(settings.dict(), f)
    return {"message": "Settings saved successfully."}
    
if __name__ == "__main__":
    print(f"Starting Void Player UI on http://0.0.0.0:8000")
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="warning")