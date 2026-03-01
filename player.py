import vlc #type:ignore
import os
import time
import threading
from tinytag import TinyTag #type:ignore
from time import sleep
import datetime #type:ignore
import queue

#local import
import display
import configs
import menu
import buttons
from buttons import btn_mgr

#global variables
scrolling_title = None
show_volume_display = False
volume_display_time = 0
volume_direction = "up"  # Added this global variable
display_thread = None
stop_display = False
current_song = ""
current_duration = 0
current_menu = "main"

# Set by display_updater for display.player_display()
display_song = ""
time_str = "0:00"
duration_str = "0:00"
new_vol = 0

#scrolling function
class ScrollingText:
    def __init__(self, text, max_width=9, scroll_speed=0.5):
        self.full_text = text
        self.max_width = max_width
        self.scroll_speed = scroll_speed
        self.scroll_position = 0
        self.last_update = time.time()
        self.pause_counter = 0
        self.pause_duration = 2
        self.padded_text = self.full_text + "   "  
        
    def get_display_text(self):
        if len(self.full_text) <= self.max_width:
            return self.full_text
            
        current_time = time.time()
        if current_time - self.last_update >= self.scroll_speed:
            self.last_update = current_time
            
            if self.pause_counter > 0:
                self.pause_counter -= 1
                return self.padded_text[self.scroll_position:self.scroll_position + self.max_width]
            
            self.scroll_position += 1
            
            if self.scroll_position >= len(self.padded_text):
                self.scroll_position = 0
                self.pause_counter = int(self.pause_duration / self.scroll_speed)
                
        return self.padded_text[self.scroll_position:self.scroll_position + self.max_width]


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

def play_track(index):
    global current_song, current_duration, scrolling_title
    stop_display_thread()
    
    file_path = playlist[index]
    media = instance.media_new(file_path)
    player.set_media(media)
    player.play()
    
    tag = TinyTag.get(file_path)
    current_song = tag.title or os.path.basename(file_path)
    current_duration = int(tag.duration) if tag.duration else 0
    
    # Initialize scrolling text for long titles
    if len(current_song) > 9:
        time.sleep(1)
        scrolling_title = ScrollingText(current_song, max_width=9, scroll_speed=0.3)
    else:
        scrolling_title = None
    
    start_display_thread()

def next_track_event():
    return "NEXT_TRACK"

def prev_track_event():
    return "PREV_TRACK"

def pause_event():
    return "TOGGLE_PAUSE"

def exit_player_event():
    return "EXIT_PLAYER"

def volume_up_event():
    return "VOL_UP"

def volume_down_event():
    return "VOL_DOWN"

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

# FIXED: Volume handlers now use the state flags to trigger the display
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
    """Start the display update thread"""
    global display_thread, stop_display
    stop_display = False
    display_thread = threading.Thread(target=display_updater, daemon=True)
    display_thread.start()

def stop_display_thread():
    """Stop the display update thread"""
    global stop_display, display_thread
    stop_display = True
    if display_thread and display_thread.is_alive():
        display_thread.join(timeout=1.0)

def display_updater():
    global stop_display, scrolling_title, show_volume_display, volume_display_time
    global display_song, time_str, duration_str, volume_direction
    
    while not stop_display:
        try:
            current_time_stamp = time.time()

            # 1. Check if we should show the Volume UI
            if show_volume_display:
                if current_time_stamp - volume_display_time > 1.5: # Show for 1.5s
                    show_volume_display = False
                else:
                    if volume_direction == "up":
                        display.volume_up_screen()
                    else:
                        display.volume_down_screen()
                    time.sleep(0.1)
                    continue # Skip the rest of the loop while showing volume

            # 2. Check if we should show the Playing UI
            if player.is_playing():
                current_time = get_current_time()
                time_str = format_time(current_time)
                duration_str = format_time(current_duration)
                if scrolling_title:
                    display_song = scrolling_title.get_display_text()
                else:
                    display_song = current_song[:9] if len(current_song) > 9 else current_song
                display.player_display()
                
            # 3. If neither Volume nor Playing is active, we are Paused
            else:
                display.paused_screen()

        except Exception as e:
            print(f"Display Error: {e}")
            
        time.sleep(0.2)  # Update every 200ms for smooth scrolling
        
def start_playback(event_queue):
    """Enter player mode: bind controls and process events."""
    with menu.menu_mode():
        in_player = True

        # 1. Bind buttons to push events to the queue
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
            if playlist:
                play_track(current_track)
            else:
                display.no_music_screen()

            # 2. The Non-Blocking Event Loop
            while in_player:
                try:
                    event = event_queue.get(timeout=0.1) 
                    
                    if event == "NEXT_TRACK":
                        handle_next_track()
                    elif event == "PREV_TRACK":
                        handle_prev_track()
                    elif event == "TOGGLE_PAUSE":
                        handle_pause()
                    elif event == "VOL_UP":
                        handle_volume_up()
                    elif event == "VOL_DOWN":
                        handle_volume_down()
                    elif event == "EXIT_PLAYER":
                        in_player = False
                        player.stop()
                    
                    event_queue.task_done()

                except queue.Empty:
                    pass 
                
                # FIXED: Auto-Advance to Next Track when a song finishes
                if player.get_state() == vlc.State.Ended:
                    event_queue.put("NEXT_TRACK")

        finally:
            stop_display_thread()
            btn_mgr.unbind()