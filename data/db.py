import sqlite3
import threading
import queue
import time
import os

# Safely resolve the path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "void_stats.db")

stats_queue = queue.Queue()

def init_db():
    """Bootstraps the SQLite database and optimizes it for the Pi Zero."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Enable Write-Ahead Logging for SD card efficiency
    cursor.execute("PRAGMA journal_mode=WAL;")
    
    # Create the master telemetry table
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
    
    # Migration: Add genre column if it doesn't exist yet
    try:
        cursor.execute("ALTER TABLE listening_history ADD COLUMN genre TEXT DEFAULT 'Unknown'")
    except sqlite3.OperationalError:
        pass

    cursor.execute("CREATE INDEX IF NOT EXISTS idx_timestamp ON listening_history(timestamp);")
    
    conn.commit()
    conn.close()
    print(f"[DB] Initialized database at {DB_PATH}")

def _database_worker():
    """The silent background daemon that writes logs without lagging the audio."""
    while True:
        track_data = stats_queue.get()
        
        # Buffer delay to prevent I/O spikes during track changes
        time.sleep(5)
        
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            
            # Match the 8 columns: timestamp, track, artist, album, genre, duration, length, skipped
            cursor.execute("""
                INSERT INTO listening_history 
                (timestamp, track_name, artist_name, album_name, genre, duration_listened, track_length, skipped)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                track_data.get('timestamp', 0),
                track_data.get('track_name', 'Unknown Track'),
                track_data.get('artist_name', 'Unknown Artist'),
                track_data.get('album_name', 'Unknown Album'),
                track_data.get('genre', 'Unknown'),
                track_data.get('duration_listened', 0),
                track_data.get('track_length', 0),
                track_data.get('skipped', 0)
            ))
            
            conn.commit()
            conn.close()
            print(f"[DB Worker] Logged: {track_data.get('track_name')} [{track_data.get('genre')}]")
            
        except sqlite3.Error as e:
            print(f"[DB ERROR] Failed to log track: {e}")
        finally:
            stats_queue.task_done()

def start_worker():
    worker = threading.Thread(target=_database_worker, daemon=True)
    worker.start()

def log_track_event(track_data: dict):
    stats_queue.put(track_data)