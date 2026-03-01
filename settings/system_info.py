import platform
import psutil #type:ignore
import time
import datetime

# Local imports
import display
import buttons
from buttons import btn_mgr
import menu

def format_uptime():
    boot_time = psutil.boot_time()
    uptime_seconds = time.time() - boot_time
    return str(datetime.timedelta(seconds=int(uptime_seconds)))

def format_ram():
    mem = psutil.virtual_memory()
    used_mb = round(mem.used / (1024 ** 2), 1)
    total_mb = round(mem.total / (1024 ** 2), 1)
    return f"{used_mb}MB/{total_mb}MB"

def get_system_info():
    return {
        "OS": platform.system(),
        "Kernel": platform.release(),
        "Arch": platform.machine(),
        "CPU": platform.processor() or "N/A",
        "RAM": format_ram(),
        "Uptime": format_uptime()
    }

def system_info():
    """Displays system stats and safely handles backing out to the menu."""
    with menu.menu_mode():
        in_sys_info = True

        def exit_app():
            nonlocal in_sys_info
            in_sys_info = False

        # Bind the Back/Menu button and the Center button to exit
        btn_mgr.bind({
            buttons.buttons["menu"]: exit_app,
            buttons.buttons["center"]: exit_app 
        })

        try:
            while in_sys_info:
                # 1. Grab the latest stats
                current_info = get_system_info()
                
                # 2. Pass them directly to the display function!
                display.system_info_display(current_info)
                
                # Update every 1 second instead of 5 so the exit button feels responsive
                time.sleep(1) 
        finally:
            pass