# Void Player

Void Player is a lightweight, headless audio player designed for the Raspberry Pi. Built entirely in Python, it bypasses the standard desktop environment to provide a pure, physical-button-driven music experience with a custom OLED UI.

The core of Void Player is built on a highly optimized, non-blocking state-machine architecture that handles hardware interrupts, dynamic audio routing, and headless Bluetooth device management without halting the main execution thread.

## Features

* **State-Machine Architecture:** Implements a multi-threaded, non-blocking UI and hardware button management system. Menu states and background processes run concurrently without thread starvation.
* **Headless Bluetooth Management:** Features a custom BlueZ integration via `bluetoothctl` subprocesses. Handles device scanning, filtering, pairing, trusting, and connecting entirely through the OLED interface without requiring a keyboard or desktop GUI.
* **Dynamic Audio Routing:** Seamlessly hot-swaps active audio output between Bluetooth sinks, the Pi's built-in audio jack, and external USB DACs. Built on PulseAudio/PipeWire and managed via `pactl`.
* **Hardware Interrupts:** Highly optimized GPIO button debouncing using `gpiozero`. Configured for instantaneous, snappy menu navigation to mimic the tactile feel of classic dedicated MP3 players.
* **OLED Display Interface:** Dynamic, multi-level menus and UI elements rendered via the Pillow (PIL) library over the I2C bus.

## Hardware Requirements

* **SBC:** Raspberry Pi (Zero 2 W, 3, or 4 recommended)
* **Display:** 128x64 I2C OLED Display (e.g., SSD1306)
* **Input:** 4x Tactile Push Buttons (Configured for Up, Down, Center/Select, Menu/Back)
* **Audio:** USB DAC (Optional, highly recommended for audiophile output) or Bluetooth Audio Device

## Software Dependencies

This project relies on standard Linux audio and Bluetooth stacks. Ensure the following are installed on your system:

* Python 3.x
* BlueZ (for Bluetooth stack)
* PulseAudio or PipeWire (with `pulseaudio-utils` and `pulseaudio-module-bluetooth`)

## Hardware Wiring & Pinout

Void Player utilizes the Raspberry Pi's internal pull-up resistors. Each tactile button should be wired directly between its designated GPIO pin and any available Ground (GND) pin on the Pi. No external resistors are required.

### Button Configuration (Default)
* **Up Button:** GPIO 17
* **Down Button:** GPIO 27
* **Center / Select:** GPIO 22
* **Menu / Back:** GPIO 24

### OLED Display (I2C Configuration)
The 128x64 display connects via the standard I2C pins.
* **VCC:** 3.3V (Pin 1)
* **GND:** Ground (Pin 6 or 9)
* **SDA:** GPIO 2 (Pin 3)
* **SCL:** GPIO 3 (Pin 5)

*(Note: Pin assignments can be easily modified in the `buttons.py` dictionary to fit your specific custom PCB or perfboard layout.)*

### Python Packages

* `gpiozero`
* `Pillow`
* `RPi.GPIO` or `lgpio`
* `luma.oled` (or equivalent display driver)

## Installation

**1. Clone the repository:**

```bash
git clone https://github.com/YOUR_USERNAME/void-player.git
cd void-player

```

**2. Configure the Linux Audio and Bluetooth Stack:**
Ensure the Pi is configured to run Bluetooth agents and PulseAudio/PipeWire sinks.

```bash
sudo apt-get update
sudo apt-get install pulseaudio-utils pulseaudio-module-bluetooth

```

**3. Run the application:**

```bash
python3 main.py

```

*(Note: It is recommended to run Void Player as a `systemd` service for automatic startup on boot.)*

## Architecture Overview

Void Player abandons simple `time.sleep()` UI loops in favor of a state-machine design. The button manager (`btn_mgr`) actively binds and unbinds callback functions depending on the active menu state. This allows the system to instantly break out of loops, release hardware locks, and safely launch sub-modules (like Bluetooth scanning or audio routing) without overlapping UI draws or ghost inputs.


## License

This project is licensed under the MIT License - see the LICENSE file for details.

---

Would you like me to draft up a standard `requirements.txt` file and an MIT `LICENSE` file for you so the repository is completely ready for the public?