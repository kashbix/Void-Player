import vlc #type:ignore
import os
import time
import threading
from tinytag import TinyTag #type:ignore
from time import sleep
import datetime #type:ignore
import queue
import json

#local import
import display
import configs
import menu
import buttons
from buttons import btn_mgr

# Background database logger
from data.db import log_track_event

# --- SETTINGS LOADER ---
SETTINGS_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "settings.json")

def load_settings():
    """Reads the user preferences from the web dashboard."""
    defaults = {"auto_play": True, "boot_volume": 40, "sleep_timer": 300, "scroll_speed": 3}
    try:
        with open(SETTINGS_PATH, "r") as f:
            return json.load(f)
    except Exception:
        return defaults

#global variables
scrolling_title = None
show_volume_display = False
volume_display_time = 0
volume_direction = "up"  
display_thread = None
stop_display = False
current_song = ""
current_duration = 0
current_menu = "main"
current_has_cover = False


# Telemetry Tracking Variables
current_file_path = None
track_start_time = 0
current_metadata = {}

# Set by display_updater for display.player_display()
display_song = ""
time_str = "0:00"
duration_str = "0:00"
new_vol = 0
pause_start_time = 0
screen_is_asleep = False

#scrolling function
class ScrollingText:
    def __init__(self, text, max_width=9):
        self.full_text = text
        self.max_width = max_width
        
        settings = load_settings()
        speed_level = settings.get("scroll_speed", 3)
        
        # Smoother delay calculation (ranges from ~0.4s down to 0.1s)
        self.scroll_speed = 0.45 - (speed_level * 0.07) 
        
        self.scroll_position = 0
        self.last_update = time.time()
        
        # Add a clear separator so the end of the song and the beginning don't blend together
        self.padded_text = self.full_text + " *** " 
        
        # Pause at the beginning for 1.5 seconds before scrolling starts
        self.is_paused = True
        self.pause_duration = 1.5
        
    def get_display_text(self):
        # If it fits on the screen, don't scroll at all
        if len(self.full_text) <= self.max_width:
            return self.full_text
            
        current_time = time.time()
        
        # Handle the pause at the very beginning of the track
        if self.is_paused:
            if current_time - self.last_update >= self.pause_duration:
                self.is_paused = False
                self.last_update = current_time
            return self.padded_text[0:self.max_width]
            
        # Handle the actual scrolling
        if current_time - self.last_update >= self.scroll_speed:
            self.last_update = current_time
            self.scroll_position += 1
            
            # If we've scrolled through the whole text + separator, reset
            if self.scroll_position >= len(self.padded_text):
                self.scroll_position = 0
                self.is_paused = True # Pause again before repeating
                
        # Seamlessly wrap the text back around if we reach the end of the string
        display_str = self.padded_text[self.scroll_position:self.scroll_position + self.max_width]
        if len(display_str) < self.max_width:
            display_str += self.padded_text[0:self.max_width - len(display_str)]
            
        return display_str

#player setup
def get_playlist():
    try:
        if not os.path.exists(configs.MUSIC_DIR):
            return []
        return [
            os.path.join(configs.MUSIC_DIR, f)
            for f in os.listdir(configs.MUSIC_DIR)
            if f.lower().endswith(configs.SUPPORTED_FORMATS)
        ]
    except OSError:
        return []

playlist = get_playlist()
instance = vlc.Instance()
player = instance.media_player_new()
current_track = 0

def get_current_time():
    """Get current playback time in seconds"""
    if player.is_playing():
        return player.get_time() // 1000
    return 0

def format_time(seconds):
    """Format seconds to MM:SS"""
    return f"{seconds//60:02d}:{seconds%60:02d}"

# The Telemetry Engine
def log_current_song():
    """Calculates duration listened and sends the data to the background DB queue."""
    global current_file_path, track_start_time, current_metadata
    
    if not current_file_path or not track_start_time:
        return
        
    duration_listened = time.time() - track_start_time
    track_length = current_metadata.get('length', 0)
    
    if duration_listened < 3:
        current_file_path = None
        return
        
    skipped = 1
    if track_length > 0 and (duration_listened / track_length) >= 0.5:
        skipped = 0
        
    event_data = {
        "timestamp": track_start_time,
        "track_name": current_metadata.get('title', 'Unknown Title'),
        "artist_name": current_metadata.get('artist', 'Unknown Artist'),
        "album_name": current_metadata.get('album', 'Unknown Album'),
        "genre": current_metadata.get('genre', 'Unknown'), # Extracted genre added here!
        "duration_listened": duration_listened,
        "track_length": track_length,
        "skipped": skipped
    }
    
    log_track_event(event_data)
    current_file_path = None

def play_track(index):
    global current_song, current_duration, scrolling_title
    global current_file_path, track_start_time, current_metadata, current_has_cover
    
    log_current_song()
    stop_display_thread()
    
    file_path = playlist[index]
    media = instance.media_new(file_path)
    player.set_media(media)
    player.play()
    
    tag = TinyTag.get(file_path, image=True) 
    current_song = tag.title or os.path.basename(file_path)
    current_duration = int(tag.duration) if tag.duration else 0
    
    image_data = tag.get_image()
    cover_path = "/dev/shm/void_cover.png"
    
    if image_data:
        with open(cover_path, 'wb') as f:
            f.write(image_data)
        current_has_cover = True
    else:
        if os.path.exists(cover_path):
            os.remove(cover_path)
        current_has_cover = False
    
    current_metadata = {
        'title': current_song,
        'artist': tag.artist or "Unknown Artist",
        'album': tag.album or "Unknown Album",
        'genre': tag.genre or "Unknown", # Extracted genre captured here!
        'length': current_duration
    }
    current_file_path = file_path
    track_start_time = time.time()
    
    if len(current_song) > 9:
        time.sleep(1)
        # REMOVED scroll_speed=0.3 since the class now handles it automatically!
        scrolling_title = ScrollingText(current_song, max_width=9)
    else:
        scrolling_title = None
    
    start_display_thread()

def next_track_event(): return "NEXT_TRACK"
def prev_track_event(): return "PREV_TRACK"
def pause_event(): return "TOGGLE_PAUSE"
def exit_player_event(): return "EXIT_PLAYER"
def volume_up_event(): return "VOL_UP"
def volume_down_event(): return "VOL_DOWN"

def handle_next_track():
    global current_track, playlist
    playlist = get_playlist()
    if playlist:
        current_track = (current_track + 1) % len(playlist)
        play_track(current_track)

def handle_prev_track():
    global current_track, playlist
    playlist = get_playlist()
    if playlist:
        current_track = (current_track - 1) % len(playlist)
        play_track(current_track)

def handle_pause():
    if player.is_playing():
        player.pause()
    else:
        player.play()

def handle_volume_up():
    global new_vol, show_volume_display, volume_display_time, volume_direction
    current_vol = player.audio_get_volume()
    new_vol = min(100, current_vol + 10)
    player.audio_set_volume(new_vol)
    volume_direction = "up"
    show_volume_display = True
    volume_display_time = time.time()

def handle_volume_down():
    global new_vol, show_volume_display, volume_display_time, volume_direction
    current_vol = player.audio_get_volume()
    new_vol = max(0, current_vol - 10)
    player.audio_set_volume(new_vol)
    volume_direction = "down"
    show_volume_display = True
    volume_display_time = time.time()

def start_display_thread():
    global display_thread, stop_display
    stop_display = False
    display_thread = threading.Thread(target=display_updater, daemon=True)
    display_thread.start()

def stop_display_thread():
    global stop_display, display_thread
    stop_display = True
    if display_thread and display_thread.is_alive():
        display_thread.join(timeout=1.0)

def display_updater():
    global stop_display, scrolling_title, show_volume_display, volume_display_time
    global display_song, time_str, duration_str, volume_direction, current_has_cover
    global pause_start_time, screen_is_asleep

    while not stop_display:
        try:
            current_time_stamp = time.time()

            if show_volume_display:
                if current_time_stamp - volume_display_time > 1.5:
                    show_volume_display = False
                else:
                    if volume_direction == "up":
                        display.volume_up_screen()
                    else:
                        display.volume_down_screen()
                    time.sleep(0.1)
                    continue 

            # Remember to add pause_start_time to the global statement at the top of display_updater!
            global pause_start_time 
            
            if player.is_playing():
                pause_start_time = 0 # Reset the idle timer because music is playing!
                
                current_time = get_current_time()
                time_str = format_time(current_time)
                duration_str = format_time(current_duration)
                if scrolling_title:
                    display_song = scrolling_title.get_display_text()
                else:
                    display_song = current_song[:9] if len(current_song) > 9 else current_song
                display.player_display()
                
                progress_pct = int((current_time / current_duration) * 100) if current_duration > 0 else 0
                deck_status = {
                    "is_playing": True,
                    "title": current_song,
                    "progress_pct": progress_pct,
                    "has_cover": current_has_cover
                }
                with open("/dev/shm/void_now_playing.json", "w") as f:
                    json.dump(deck_status, f)
                
            else:
                # --- SLEEP TIMER LOGIC ---
                if pause_start_time == 0:
                    pause_start_time = time.time()
                    
                settings = load_settings()
                sleep_timer = settings.get("sleep_timer", 300)
                
                if str(sleep_timer) != "never" and (time.time() - pause_start_time) > int(sleep_timer):
                    screen_is_asleep = True  # Tell the system we are asleep
                    display.blank_screen()
                else:
                    screen_is_asleep = False # Tell the system we are awake
                    display.paused_screen()
                
                # Always tell the web dashboard we are paused, even if screen is off
                with open("/dev/shm/void_now_playing.json", "w") as f:
                    json.dump({
                        "is_playing": False, 
                        "title": "Paused", 
                        "progress_pct": 0,
                        "has_cover": False
                    }, f)
        except Exception as e:
            print(f"Display Error: {e}")
            
        time.sleep(0.05) 
        
def start_playback(event_queue):
    with menu.menu_mode():
        in_player = True

        btn_mgr.bind({
            buttons.buttons["next"]: lambda: event_queue.put(next_track_event()),
            buttons.buttons["prev"]: lambda: event_queue.put(prev_track_event()),
            buttons.buttons["center"]: lambda: event_queue.put(pause_event()),
            buttons.buttons["vol_up"]: lambda: event_queue.put(volume_up_event()),
            buttons.buttons["vol_down"]: lambda: event_queue.put(volume_down_event()),
            buttons.buttons["menu"]: lambda: event_queue.put(exit_player_event()),
        })

        try:
            start_display_thread()
            
            # --- NEW: APPLY HARDWARE SETTINGS ON BOOT ---
            settings = load_settings()
            
            # 1. Set the Default Volume
            player.audio_set_volume(settings.get("boot_volume", 40))
            global new_vol 
            new_vol = settings.get("boot_volume", 40)
            
            # 2. Handle Auto-Play Logic
            if playlist:
                if settings.get("auto_play", True):
                    play_track(current_track)
                else:
                    # Setup silently but don't hit play
                    global current_song
                    current_song = os.path.basename(playlist[current_track])
                    display.paused_screen()
                    
                    # Tell the web dashboard we are paused
                    with open("/dev/shm/void_now_playing.json", "w") as f:
                        json.dump({
                            "is_playing": False, 
                            "title": "Paused", 
                            "progress_pct": 0, 
                            "has_cover": False
                        }, f)
            else:
                display.no_music_screen()
            while in_player:
                try:
                    event = event_queue.get(timeout=0.1) 
                    
                    # --- NEW: WAKE SCREEN INTERCEPT ---
                    global screen_is_asleep, pause_start_time
                    if screen_is_asleep:
                        pause_start_time = time.time() # Reset the idle timer!
                        screen_is_asleep = False       # Mark as awake
                        event_queue.task_done()
                        continue # Skip processing the button action this one time
                    
                    if event == "NEXT_TRACK": handle_next_track()
                    elif event == "PREV_TRACK": handle_prev_track()
                    elif event == "TOGGLE_PAUSE": handle_pause()
                    elif event == "VOL_UP": handle_volume_up()
                    elif event == "VOL_DOWN": handle_volume_down()
                    elif event == "EXIT_PLAYER":
                        in_player = False
                        log_current_song() 
                        player.stop()
                    
                    event_queue.task_done()

                except queue.Empty:
                    pass 
                
                if player.get_state() == vlc.State.Ended:
                    event_queue.put("NEXT_TRACK")

        finally:
            stop_display_thread()
            btn_mgr.unbind()