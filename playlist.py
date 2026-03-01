import time
import os
import display
import buttons
import menu
from buttons import btn_mgr
import player 

def playlist_menu():
    """Interactive playlist selection menu"""
    
    full_paths = player.get_playlist()
    
    if full_paths:
        playlist_options = [os.path.basename(path) for path in full_paths]
    else:
        playlist_options = ["No Music Found"]

    with menu.menu_mode(): 
        playlist_index = 0
        in_plmenu = True
        next_action = None  # NEW: Keep track of where to go next

        def menu_up():
            nonlocal playlist_index
            playlist_index = (playlist_index - 1) % len(playlist_options)
            display.playlist_menu(playlist_options, playlist_index)

        def menu_down():
            nonlocal playlist_index
            playlist_index = (playlist_index + 1) % len(playlist_options)
            display.playlist_menu(playlist_options, playlist_index)

        def menu_select():
            nonlocal in_plmenu, next_action
            if playlist_options[0] != "No Music Found":
                # 1. Update the player's track
                player.current_track = playlist_index
                
                # 2. Tell main.py to launch the player!
                next_action = "PLAYER"
                
            in_plmenu = False # Kill the loop to release the hardware lock
        
        def exit_app():
            nonlocal in_plmenu
            in_plmenu = False

        btn_mgr.bind({
            buttons.buttons["center"]: menu_select,
            buttons.buttons["next"]: menu_down,
            buttons.buttons["prev"]: menu_up,
            buttons.buttons["menu"]: exit_app
        })
        
        try:
            display.playlist_menu(playlist_options, playlist_index)
            while in_plmenu:
                time.sleep(0.1)
        finally:
            pass

    # Return the decision back to main.py
    return next_action