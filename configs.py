from PIL import ImageFont #type:ignore

try:
    font_head = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 25)
    font_menu = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 11)
    font_below = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 11)
    
except Exception as e:
    # NOW WE WILL SEE THE ACTUAL ERROR!
    print(f"\n[WARNING] Failed to load custom font: {e}")
    print("[WARNING] Falling back to default ugly font...\n")
    
    font_head = ImageFont.load_default()
    font_menu = ImageFont.load_default()
    font_below = ImageFont.load_default()

#music folders
MUSIC_DIR = '/home/kash/Music'
SUPPORTED_FORMATS = ('.flac', '.wav', '.mp3')