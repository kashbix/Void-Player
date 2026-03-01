from contextlib import contextmanager
import time
#local import
import display
import player
import file_share
import buttons
import playlist
import settings.settings as setin
from buttons import btn_mgr

menu_options = [
    "Play Music",
    "Playlists",
    "File Sharing",
    "Settings",
]

@contextmanager
def menu_mode():
    """Context manager to ensure menu bindings are cleaned up on exit."""
    try:
        yield
    finally:
        btn_mgr.unbind()


def menu(event_queue=None):
    """Interactive menu system with automatic callback restoration and internal routing"""
    
    # NEW: An outer loop so when an app exits, we automatically return to the menu
    while True:
        menu_index = 0
        in_menu = True
        selected_app = None

        with menu_mode():
            def menu_up():
                nonlocal menu_index
                menu_index = (menu_index - 1) % len(menu_options)
                display.main_menu(menu_options, menu_index)

            def menu_down():
                nonlocal menu_index
                menu_index = (menu_index + 1) % len(menu_options)
                display.main_menu(menu_options, menu_index)

            def menu_select():
                nonlocal in_menu, selected_app
                # 1. Record what the user chose
                selected_app = menu_options[menu_index]
                # 2. Kill the inner loop instantly to release the hardware thread lock!
                in_menu = False

            # Set menu button callbacks
            btn_mgr.bind({
                buttons.buttons["center"]: menu_select,
                buttons.buttons["next"]: menu_down,
                buttons.buttons["prev"]: menu_up,
            })

            try:
                display.main_menu(menu_options, menu_index)
                
                # The main thread safely waits here while the menu is active
                while in_menu:
                    time.sleep(0.1)
            finally:
                # Buttons are automatically unbound here by the context manager
                pass

        # --- WE ARE NOW OUTSIDE THE LOCK ---
        # The hardware thread is fully released. We are safely back on the main thread.
        # Now we can launch the heavy modules without freezing the system!

        if selected_app == "Play Music":
            player.start_playback(event_queue)
            
        elif selected_app == "Playlists":
            # 1. Capture what the playlist returns!
            playlist_decision = playlist.playlist_menu()
            
            # 2. If a song was clicked, launch the player instantly!
            if playlist_decision == "PLAYER":
                player.start_playback(event_queue)
                
        elif selected_app == "File Sharing":
            file_share.file_share()
            
        elif selected_app == "Settings":
            setin.setting()
            
        # When the launched app finishes (e.g., you press the menu button to exit the player),
        # the code hits the bottom of this 'while True' loop and restarts the menu automatically.
            
