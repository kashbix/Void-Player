from gpiozero import Button  # type:ignore
import time
import threading
import logging

# Define GPIO pins for buttons
BTN_PINS = {
    "center": 18,
    "next": 22,
    "prev": 27,
    "vol_up": 17,
    "vol_down": 23,
    "menu": 24
}

# Create all buttons in a loop
buttons = {name: Button(pin, pull_up=True, bounce_time=0.05) for name, pin in BTN_PINS.items()}

# Optional convenience aliases for existing code that expects variables
center_btn = buttons["center"]
next_btn = buttons["next"]
prev_btn = buttons["prev"]
volume_up_btn = buttons["vol_up"]
volume_down_btn = buttons["vol_down"]
menu_btn = buttons["menu"]


class ButtonManager:
    """
    Manages exclusive button bindings across modes/screens.
    - bind(mapping): installs a new set of handlers, replacing any previous ones.
    - unbind(): removes the active set of handlers.
    Features:
    - Debounce to avoid double-fires.
    - Re-entrancy lock to prevent overlapping handler execution.
    - Centralized exception handling for button callbacks.
    """

    def __init__(self, debounce_ms=50, use_lock=True, on_error=None, logger=None):
        self.debounce_ms = debounce_ms
        self.use_lock = use_lock
        self.on_error = on_error  # optional: callable(exc, *, button_key=str) -> None
        self.logger = logger or logging.getLogger(__name__)
        self._last_ts = {}          # per-button timestamp for debounce
        self._lock = threading.Lock() if use_lock else None
        self._active_bindings = None  # list[(button_obj, attr_name, wrapped_fn)]

    def _now_ms(self):
        # monotonic avoids jumps if system clock changes
        return int(time.monotonic() * 1000)

    def _wrap(self, key_name, fn):
        """
        Returns a wrapped handler with debounce and optional mutual exclusion.
        key_name is a string identifier for the button/event used for debounce tracking.
        """
        def wrapped():
            now = self._now_ms()
            last = self._last_ts.get(key_name, 0)
            if self.debounce_ms and (now - last) < self.debounce_ms:
                return
            self._last_ts[key_name] = now

            if self._lock is None:
                try:
                    return fn()
                except Exception as exc:
                    self._handle_error(exc, key_name)
                    return

            # Mutual exclusion across all handlers if desired
            with self._lock:
                try:
                    return fn()
                except Exception as exc:
                    self._handle_error(exc, key_name)
                    return

        # Provide helpful introspection/debugging
        wrapped.__name__ = getattr(fn, "__name__", "wrapped_handler")
        wrapped.__doc__ = getattr(fn, "__doc__", "")
        return wrapped

    def _handle_error(self, exc, key_name):
        """
        Centralized exception handling for button callbacks so a single bad handler
        doesn't kill the event thread silently.
        """
        try:
            if callable(self.on_error):
                self.on_error(exc, button_key=key_name)
                return
        except Exception:
            # fall through to logging if the error handler itself fails
            pass

        try:
            self.logger.exception("Button handler error for %s", key_name, exc_info=exc)
        except Exception:
            # avoid any surprises if logging is misconfigured
            pass

    def bind(self, mapping, event_attr="when_pressed"):
        """
        mapping: dict of {button_obj: callable} to be attached on event_attr (default: 'when_pressed').
        Replaces any existing active bindings. Safe to call repeatedly when switching modes.
        event_attr: Which attribute on the button to set (e.g., 'when_pressed', 'when_released', 'when_held').
        """
        self.unbind()

        installed = []
        for btn, handler in mapping.items():
            # Build a stable key name for debounce tracking
            # Prefer a provided 'name' attr, else repr(btn) + event_attr
            base_name = getattr(btn, "name", None) or repr(btn)
            key_name = f"{base_name}:{event_attr}"

            wrapped = self._wrap(key_name, handler)

            # Attach to the requested event attribute
            if not hasattr(btn, event_attr):
                raise AttributeError(f"Button {btn} has no attribute '{event_attr}'")
            setattr(btn, event_attr, wrapped)

            installed.append((btn, event_attr, wrapped))

        # Remember what we installed so unbind can remove it
        self._active_bindings = installed

    def bind_multi(self, multi_mapping):
        """
        Advanced variant for multiple events per button.
        multi_mapping: dict of {button_obj: {event_attr: callable, ...}, ...}
        Example:
          button_mgr.bind_multi({
              buttons["next"]: {"when_pressed": on_next, "when_held": on_fast_forward},
              buttons["prev"]: {"when_pressed": on_prev}
          })
        """
        self.unbind()
        installed = []
        for btn, events in multi_mapping.items():
            for event, handler in events.items():
                base_name = getattr(btn, "name", None) or repr(btn)
                key_name = f"{base_name}:{event}"
                wrapped = self._wrap(key_name, handler)
                if not hasattr(btn, event):
                    raise AttributeError(f"Button {btn} has no attribute '{event}'")
                setattr(btn, event, wrapped)
                installed.append((btn, event, wrapped))
        self._active_bindings = installed

    def unbind(self):
        """
        Remove all active bindings installed by this manager.
        Safely clears event attributes back to None.
        """
        if not self._active_bindings:
            return

        for btn, event_attr, _wrapped in self._active_bindings:
            if hasattr(btn, event_attr):
                try:
                    setattr(btn, event_attr, None)
                except Exception:
                    # Some libraries may not allow setting None; handle gracefully
                    pass

        self._active_bindings = None
        # Reset debounce timing so the first press in a new mode isn't swallowed.
        self._last_ts.clear()

    def set_debounce(self, debounce_ms):
        """Adjust debounce window at runtime."""
        self.debounce_ms = debounce_ms

# Shared manager instance for all modules that want global button handling.
btn_mgr = ButtonManager()
