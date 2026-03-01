import time
import subprocess
import display
import buttons
from buttons import btn_mgr
import menu

def get_bt_status():
    """Checks if Bluetooth is currently blocked or unblocked."""
    try:
        output = subprocess.check_output(['rfkill', 'list', 'bluetooth']).decode('utf-8')
        return "OFF" if "Soft blocked: yes" in output else "ON"
    except Exception:
        return "OFF"

def toggle_bt():
    """Toggles the Bluetooth power state."""
    current = get_bt_status()
    new_state = "block" if current == "ON" else "unblock"
    subprocess.run(['rfkill', new_state, 'bluetooth'])
    time.sleep(0.5)  # Brief pause to let the hardware radio catch up

def scan_devices():
    """Returns a list of tuples: (Device Name, MAC), filtering out unnamed devices."""
    if get_bt_status() == "OFF":
        return []
    try:
        # Run standard scan
        output = subprocess.check_output(['bluetoothctl', 'devices'], timeout=5).decode('utf-8')
        devices = []
        for line in output.split('\n'):
            if 'Device' in line:
                parts = line.split(' ', 2)
                if len(parts) >= 3:
                    mac = parts[1]
                    name = parts[2].strip()
                    
                    # THE FILTER: Ignore devices where the "name" is just the MAC address!
                    # (Un-named devices usually show up with dashes instead of colons)
                    if name == mac.replace(':', '-'):
                        continue 
                        
                    devices.append((name, mac))
        return devices
    except Exception:
        return []

def bluetooth_menu():
    """Main Bluetooth settings menu."""
    while True:
        selected_action = None
        
        with menu.menu_mode():
            bt_index = 0
            in_bt_menu = True

            def refresh_ui():
                status = get_bt_status()
                current_options = [f"Power: {status}", "Scan Devices"]
                display.bluetooth_menu(current_options, bt_index)

            def menu_up():
                nonlocal bt_index
                bt_index = (bt_index - 1) % 2
                refresh_ui()

            def menu_down():
                nonlocal bt_index
                bt_index = (bt_index + 1) % 2
                refresh_ui()

            def menu_select():
                nonlocal in_bt_menu, selected_action
                if bt_index == 0:
                    # Toggle Power and stay on this screen
                    toggle_bt()
                    refresh_ui()
                elif bt_index == 1:
                    # Exit this menu to launch the scanner
                    selected_action = "SCAN"
                    in_bt_menu = False

            def exit_app():
                nonlocal in_bt_menu, selected_action
                selected_action = "BACK"
                in_bt_menu = False

            btn_mgr.bind({
                buttons.buttons["center"]: menu_select,
                buttons.buttons["next"]: menu_down,
                buttons.buttons["prev"]: menu_up,
                buttons.buttons["menu"]: exit_app
            })
            
            refresh_ui()
            
            # The ultra-fast loop for snappy button response!
            while in_bt_menu:
                time.sleep(0.01) 
        
        # --- OUTSIDE THE LOCK ---
        if selected_action == "SCAN":
            device_selection_loop()
        elif selected_action == "BACK":
            break  # Break outer loop to return to Settings menu

def device_selection_loop():
    """Sub-menu for choosing and connecting to a specific device."""
    
    # 1. Give the user immediate visual feedback
    display.bluetooth_menu(["Scanning..."], 0)
    
    # 2. Force the Pi hardware to physically search for NEW devices for 5 seconds
    try:
        subprocess.run(['bluetoothctl', '--timeout', '5', 'scan', 'on'])
    except Exception:
        pass

    # 3. Now gather the list of everything it found
    raw_devices = scan_devices()
    
    # 4. If it's still empty, tell the user instead of silently failing!
    if not raw_devices or raw_devices == ["No Devices"] or raw_devices == ["Scan Error"]:
        display.bluetooth_menu(["No Devices Found"], 0)
        time.sleep(2)  # Pause for 2 seconds so the user can read it
        return  # Drop safely back to the main BT menu

    # Extract just the names for the OLED screen
    device_names = [d[0] for d in raw_devices]
    
    with menu.menu_mode():
        d_index = 0
        in_sel = True

        def refresh_sel():
            display.bluetooth_menu(device_names, d_index)

        def d_up():
            nonlocal d_index
            d_index = (d_index - 1) % len(device_names)
            refresh_sel()

        def d_down():
            nonlocal d_index
            d_index = (d_index + 1) % len(device_names)
            refresh_sel()

        def d_select():
            nonlocal in_sel
            mac = raw_devices[d_index][1]
            
            # Show connection feedback before freezing the thread!
            display.bluetooth_menu(["Pairing..."], 0)
            
            # Pair, trust, and connect
            subprocess.run(['bluetoothctl', 'pair', mac])
            subprocess.run(['bluetoothctl', 'trust', mac])
            subprocess.run(['bluetoothctl', 'connect', mac])
            
            in_sel = False  # Exit back to main BT menu

        def back_btn():
            nonlocal in_sel
            in_sel = False

        btn_mgr.bind({
            buttons.buttons["center"]: d_select,
            buttons.buttons["next"]: d_down,
            buttons.buttons["prev"]: d_up,
            buttons.buttons["menu"]: back_btn
        })
        
        refresh_sel()
        
        while in_sel:
            time.sleep(0.01)
    
    with menu.menu_mode():
        d_index = 0
        in_sel = True

        def refresh_sel():
            display.bluetooth_menu(device_names, d_index)

        def d_up():
            nonlocal d_index
            d_index = (d_index - 1) % len(device_names)
            refresh_sel()

        def d_down():
            nonlocal d_index
            d_index = (d_index + 1) % len(device_names)
            refresh_sel()

        def d_select():
            nonlocal in_sel
            mac = raw_devices[d_index][1]
            
            # Show connection feedback before freezing the thread!
            display.bluetooth_menu(["Pairing..."], 0)
            
            # 1. Turn on the auto-responder agent
            subprocess.run(['bluetoothctl', 'agent', 'NoInputNoOutput'])
            subprocess.run(['bluetoothctl', 'default-agent'])
            
            # 2. Pair, trust, and connect
            subprocess.run(['bluetoothctl', 'pair', mac])
            subprocess.run(['bluetoothctl', 'trust', mac])
            subprocess.run(['bluetoothctl', 'connect', mac])
            
            in_sel = False  # Exit back to main BT menu

        def back_btn():
            nonlocal in_sel
            in_sel = False

        btn_mgr.bind({
            buttons.buttons["center"]: d_select,
            buttons.buttons["next"]: d_down,
            buttons.buttons["prev"]: d_up,
            buttons.buttons["menu"]: back_btn
        })
        
        refresh_sel()
        
        while in_sel:
            time.sleep(0.01)