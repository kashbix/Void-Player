#system/downloaded import
from luma.core.interface.serial import i2c #type:ignore
from luma.core.render import canvas #type:ignore
from luma.oled.device import ssd1306 #type:ignore
from PIL import Image, ImageSequence #type:ignore
import time
from time import sleep
#local import
import configs
import menu
import player
import file_share
import settings.system_info
import playlist
import settings.bluetooth as blue
import settings.settings as settings_module
import settings.Audio_devices as audio_devices_module

#setup of display
serial = i2c(port=1, address=0x3C)
device = ssd1306(serial)

def startup():
    gif = Image.open('/home/kash/testoled/animation.gif')
    for frame in ImageSequence.Iterator(gif):
        # Resize frame to display dimensions
        frame = frame.resize((128, 64))
        frame = frame.convert('1')  # Convert to monochrome

        # Display the frame
        device.display(frame)
        sleep(0.01)  # Control animation speed
    time.sleep(1.5) #time to pause
    with canvas(device) as draw:
        draw.text((2, 1), "VOID", font= configs.font_head, fill=255)
        draw.text((2, 27), "PLAYER", font= configs.font_head, fill=255)
    time.sleep(1)

def main_menu(options=None, index=0):
    """Display main menu with options and highlight selected index."""
    if options is None:
        options = menu.menu_options
    with canvas(device) as draw:
        draw.text((2, 5), "MAIN MENU", font=configs.font_menu, fill=255)
        for i, option in enumerate(options):
            y_pos = 20 + (i * 11)
            if i == index:
                draw.text((2, y_pos), f"> {option}", font=configs.font_menu, fill=255)
            else:
                draw.text((10, y_pos), option, font=configs.font_menu, fill=255)

def no_music_screen():
    """Show 'No Music / Found' when MUSIC_DIR is empty."""
    with canvas(device) as draw:
        draw.text((2, 5), "No Music", font=configs.font_head, fill=255)
        draw.text((2, 30), "Found", font=configs.font_below, fill=255)

def paused_screen():
    with canvas(device) as draw:
            # Handle long song titles with scrolling 
            if player.scrolling_title:
                display_song = player.scrolling_title.full_text
                if len(display_song) > 9:
                    display_song = display_song[:6] + "..."
            else:
                display_song = player.current_song
                if len(display_song) > 9:
                    display_song = display_song[:6] + "..."
            
            draw.text((2, 5), display_song, font=configs.font_head, fill=255)
            draw.text((2, 30), "PAUSED", font=configs.font_below, fill=255)

def volume_up_screen():
    with canvas(device) as draw:
        draw.text((2, 5), f"Volume: {player.new_vol}%", font=configs.font_below, fill=255)
        # Changed the triangle to a plus sign
        draw.text((2, 30), "+ UP", font=configs.font_below, fill=255)

def volume_down_screen():
    with canvas(device) as draw:
        draw.text((2, 5), f"Volume: {player.new_vol}%", font=configs.font_below, fill=255)
        # Changed the triangle to a minus sign
        draw.text((2, 30), "- DOWN", font=configs.font_below, fill=255)

def player_display():
     with canvas(device) as draw:
            draw.text((2, 5), player.display_song, font=configs.font_head, fill=255)
            draw.text((15, 35), f"{player.time_str}/{player.duration_str}", font=configs.font_below, fill=255)

def file_share_screen():
    with canvas(device) as draw:
        # Header at the top
        draw.text((2, 2), "SSH / SFTP", font=configs.font_menu, fill=255)
        
        # We split the user and IP onto two lines so it guarantees a perfect fit!
        draw.text((2, 25), f"User: {file_share.username}", font=configs.font_below, fill=255)
        draw.text((2, 35), f"IP:   {file_share.ip_address}", font=configs.font_below, fill=255)
        draw.text((2, 45), f"IP:   {file_share.ip_address}", font=configs.font_below, fill=255)

def system_info_display(info):
    with canvas(device) as draw:
        # We can now just read directly from the 'info' dictionary that was passed in!
        draw.text((0, 5), f"OS: {info['OS']}", font=configs.font_below, fill=255)
        draw.text((0, 15), f"Kernel: {info['Kernel']}", font=configs.font_below, fill=255)
        draw.text((0, 25), f"Arch: {info['Arch']}", font=configs.font_below, fill=255)
        draw.text((0, 35), f"RAM: {info['RAM']}", font=configs.font_below, fill=255)
        draw.text((0, 45), f"Uptime: {info['Uptime']}", font=configs.font_below, fill=255)

def playlist_menu(options=None, index=0):
    """Display playlist menu with options and highlight selected index."""
    if options is None:
        options = playlist.playlist_options
    with canvas(device) as draw:
        draw.text((2, 5), "Playlist", font=configs.font_menu, fill=255)
        for i, option in enumerate(options):
            y_pos = 20 + (i * 11)
            if i == index:
                draw.text((2, y_pos), f"> {option}", font=configs.font_menu, fill=255)
            else:
                draw.text((10, y_pos), option, font=configs.font_menu, fill=255)  

def settings_menu(options=None, index=0):
    """Display settings menu with options and highlight selected index."""
    if options is None:
        options = settings_module.setting_option
    with canvas(device) as draw:
        draw.text((2, 5), "SETTINGS", font=configs.font_menu, fill=255)
        for i, option in enumerate(options):
            y_pos = 20 + (i * 11)
            if i == index:
                draw.text((2, y_pos), f"> {option}", font=configs.font_menu, fill=255)
            else:
                draw.text((10, y_pos), option, font=configs.font_menu, fill=255)

def audiodevices(options=None, index=0):
    """Display audio devices menu with options and highlight selected index."""
    if options is None:
        options = audio_devices_module.audio_option
    with canvas(device) as draw:
        draw.text((2, 5), "AUDIO DEVICES", font=configs.font_menu, fill=255)
        for i, option in enumerate(options):
            y_pos = 20 + (i * 11)
            if i == index:
                draw.text((2, y_pos), f"> {option}", font=configs.font_menu, fill=255)
            else:
                draw.text((10, y_pos), option, font=configs.font_menu, fill=255)

def bluetooth_menu(device_list, select_index=0):
    """Display Bluetooth settings with toggle and devices."""
    with canvas(device) as draw:
        draw.text((2, 5), "BLUETOOTH", font=configs.font_menu, fill=255)
        
        for i, item in enumerate(device_list):
            y_pos = 20 + (i * 12)
            if i == select_index:
                draw.text((2, y_pos), f"> {item}", font=configs.font_menu, fill=255)
            else:
                draw.text((10, y_pos), item, font=configs.font_below, fill=255)

def power_menu_screen(selected_idx):
    """Draws the Power/Settings menu on the OLED."""
    options = ["Restart", "Power Off", "Back"]
    
    with canvas(device) as draw:
        # Match the header placement of the other menus
        draw.text((2, 5), "SYSTEM POWER", font=configs.font_menu, fill=255)
        
        # Match the arrow ">" highlight style
        for i, opt in enumerate(options):
            y_pos = 20 + (i * 12)
            if i == selected_idx:
                draw.text((2, y_pos), f"> {opt}", font=configs.font_menu, fill=255)
            else:
                draw.text((10, y_pos), opt, font=configs.font_below, fill=255) 

def generic_message_screen(text):
    """Draws a simple message before shutting down/restarting."""
    with canvas(device) as draw:
        # Actually use the 'text' variable passed into the function
        draw.text((10, 25), text, font=configs.font_menu, fill=255)

def blank_screen():
    """Draws an empty canvas to turn off OLED pixels and prevent burn-in."""
    with canvas(device) as draw:
        pass # Drawing nothing turns the pixels off