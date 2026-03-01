import display
import menu
import time
import sys
import queue

# Create the central event queue
event_queue = queue.Queue()

def main():
    """Main entry point for Void Player."""
    try:
        # 1. Boot up the screen
        display.startup()
        
        # 2. Hand total control over to the menu router!
        # Because menu() has a 'while True' loop, this line will run forever.
        menu.menu(event_queue)
            
    except KeyboardInterrupt:
        print("\nShutting down...")
    except Exception as e:
        print(f"Fatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()