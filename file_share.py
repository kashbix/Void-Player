import socket
import time
import getpass  # NEW: Gets the current user

# Local imports
import display
import buttons
from buttons import btn_mgr
import menu

# Global variables so display.py can read them
username = "user"
ip_address = "127.0.0.1"
port = "8000"

def get_ip():
    """Tricks the Pi into revealing its actual local network IP address."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "No Network"

def file_share():
    """Displays SSH/SFTP connection info and safely handles exiting."""
    global username, ip_address, port
    
    # Grab the freshest User and IP
    username = getpass.getuser()  # Will grab 'kash'
    ip_address = get_ip()

    with menu.menu_mode():
        in_share_screen = True

        def exit_app():
            nonlocal in_share_screen
            in_share_screen = False

        # Bind BOTH the Center button and the Menu (Back) button to exit
        btn_mgr.bind({
            buttons.buttons["center"]: exit_app,
            buttons.buttons["menu"]: exit_app
        })

        try:
            display.file_share_screen()
            while in_share_screen:
                time.sleep(0.1)
        finally:
            pass