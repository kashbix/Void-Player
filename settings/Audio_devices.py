import time
import subprocess
import display
import buttons
from buttons import btn_mgr
import menu

def get_audio_devices():
    """Asks the Pi for all available audio outputs and makes the names readable."""
    try:
        # Ask PulseAudio for a list of short sinks
        output = subprocess.check_output(['pactl', 'list', 'short', 'sinks']).decode('utf-8')
        devices = []
        
        for line in output.strip().split('\n'):
            if not line:
                continue
            parts = line.split('\t')
            if len(parts) >= 2:
                sink_name = parts[1]
                
                # Give them clean, friendly names for the OLED
                if 'bluez' in sink_name:
                    name = "Bluetooth"
                elif 'hdmi' in sink_name:
                    name = "HDMI TV"
                elif 'usb' in sink_name:
                    # Catch your USB DAC!
                    name = "USB DAC"
                elif 'bcm2835' in sink_name or 'platform' in sink_name:
                    # Keeping this just in case you use an older Pi or I2S DAC hat later
                    name = "Built-in Audio"
                else:
                    name = sink_name[:12]  # Fallback just in case
                    
                devices.append((name, sink_name))
                
        return devices if devices else [("Default", None)]
    except Exception as e:
        print(f"Audio Error: {e}")
        return [("Audio Error", None)]

def audio_devices_menu():
    """Interactive menu to select where the music plays."""
    raw_devices = get_audio_devices()
    
    # Extract just the friendly names for the screen
    device_names = [d[0] for d in raw_devices]

    with menu.menu_mode():
        a_index = 0
        in_audio_menu = True

        def refresh_ui():
            # We can totally reuse the bluetooth display UI here!
            display.bluetooth_menu(device_names, a_index)

        def menu_up():
            nonlocal a_index
            a_index = (a_index - 1) % len(device_names)
            refresh_ui()

        def menu_down():
            nonlocal a_index
            a_index = (a_index + 1) % len(device_names)
            refresh_ui()

        def menu_select():
            nonlocal in_audio_menu
            # Grab the actual Linux system name for the output
            sink = raw_devices[a_index][1]
            if sink:
                # Tell Linux to route all audio to this output immediately
                subprocess.run(['pactl', 'set-default-sink', sink])
                
            # Safely exit back to the Settings menu
            in_audio_menu = False 

        def exit_app():
            nonlocal in_audio_menu
            in_audio_menu = False

        btn_mgr.bind({
            buttons.buttons["center"]: menu_select,
            buttons.buttons["next"]: menu_down,
            buttons.buttons["prev"]: menu_up,
            buttons.buttons["menu"]: exit_app
        })

        try:
            refresh_ui()
            while in_audio_menu:
                time.sleep(0.01)  # Ultra-fast loop for snappy buttons
        finally:
            pass