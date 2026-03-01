import time
import display
import buttons
from buttons import btn_mgr
import menu

# Import your sub-modules
import settings.system_info as sys_info
import settings.bluetooth as blue
import settings.Audio_devices as audio_devices_module

setting_option = [
    "System Info",
    "Bluetooth",
    "Audio Devices"
]

def setting():
    """Interactive settings menu with safe lock release and internal routing."""
    
    # Outer loop keeps you in Settings until you explicitly back out to Main Menu
    while True:
        with menu.menu_mode():
            setting_index = 0
            in_settings = True
            selected_action = None

            def menu_up():
                nonlocal setting_index
                setting_index = (setting_index - 1) % len(setting_option)
                display.settings_menu(setting_option, setting_index)

            def menu_down():
                nonlocal setting_index
                setting_index = (setting_index + 1) % len(setting_option)
                display.settings_menu(setting_option, setting_index)

            def menu_select():
                nonlocal in_settings, selected_action
                # 1. Record the choice
                selected_action = setting_option[setting_index]
                # 2. Instantly kill the loop to release the hardware lock!
                in_settings = False  

            def exit_app():
                nonlocal in_settings
                in_settings = False

            btn_mgr.bind({
                buttons.buttons["center"]: menu_select,
                buttons.buttons["next"]: menu_down,
                buttons.buttons["prev"]: menu_up,
                buttons.buttons["menu"]: exit_app
            })

            try:
                display.settings_menu(setting_option, setting_index)
                while in_settings:
                    time.sleep(0.1)
            finally:
                pass

        # --- WE ARE NOW OUTSIDE THE LOCK ---
        # The hardware thread is fully released. Safely boot up the sub-menus!
        
        if selected_action == "System Info":
            sys_info.system_info()
            
        elif selected_action == "Bluetooth":
            blue.bluetooth_menu()
            
            
        elif selected_action == "Audio Devices":
            audio_devices_module.audio_devices_menu()
            
        else:
            # If selected_action is still None, the user hit the Back button!
            # Break the outer loop to completely exit Settings and return to Main Menu.
            break