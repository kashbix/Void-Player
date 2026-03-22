import display
import menu
import time
import sys
import queue
import threading
import uvicorn

# NEW: Import your data engine and web server
from data.db import init_db, start_worker
from web.server import app

# Create the central event queue
event_queue = queue.Queue()

def run_web_server():
    """Runs the FastAPI dashboard silently in the background."""
    # log_config=None stops uvicorn from spamming your terminal output, 
    # which keeps your console clean for audio/button debugging.
    uvicorn.run(app, host="0.0.0.0", port=8000, log_config=None)

def main():
    """Main entry point for Void Player."""
    try:
        # 1. Boot up the Telemetry Engine (Database & Worker)
        print("Initializing Database...")
        init_db()
        start_worker()

        # 2. Boot up the Web Dashboard
        print("Starting Web Dashboard on port 8000...")
        web_thread = threading.Thread(target=run_web_server, daemon=True)
        web_thread.start()

        # 3. Boot up the physical screen
        display.startup()
        
        # 4. Hand total control over to the menu router!
        # Because menu() has a 'while True' loop, this line will run forever.
        menu.menu(event_queue)
            
    except KeyboardInterrupt:
        print("\nShutting down Void Player...")
    except Exception as e:
        print(f"Fatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()