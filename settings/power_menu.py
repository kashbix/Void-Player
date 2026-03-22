import time
import subprocess
import display
import buttons
from buttons import btn_mgr
import menu

options = ["Restart", "Power Off", "Back"]
current_selection = 0

def show_power_menu():
    """Displays the power menu and handles button navigation."""
    global current_selection
    current_selection = 0
    in_power_menu = True

    with menu.menu_mode():
        def player_display():
            display.power_menu_screen(current_selection)

        def next_opt():
            global current_selection
            current_selection = (current_selection + 1) % len(options)
            player_display()

        def prev_opt():
            global current_selection
            current_selection = (current_selection - 1) % len(options)
            player_display()

        def select_opt():
            nonlocal in_power_menu
            opt = options[current_selection]
            
            if opt == "Restart":
                display.generic_message_screen("Restarting...")
                subprocess.Popen(["sudo", "reboot"])
            elif opt == "Power Off":
                display.generic_message_screen("Shutting Down...")
                subprocess.Popen(["sudo", "shutdown", "-h", "now"])

        def exit_menu():
            nonlocal in_power_menu
            in_power_menu = False

        # Bind the hardware buttons
        btn_mgr.bind({
            buttons.buttons["next"]: next_opt,       # Scroll Down
            buttons.buttons["prev"]: prev_opt,       # Scroll Up
            buttons.buttons["center"]: select_opt,   # Enter
            buttons.buttons["menu"]: exit_menu       # Back
        })

        # Initial Draw
        player_display()
        
        # Keep the menu alive until exited
        while in_power_menu:
            time.sleep(0.1)