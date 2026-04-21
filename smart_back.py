#!/usr/bin/env python3
"""
SmartBack v1.0
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Context-Aware ESC Key Remapper for Windows

Behavior
  Browser (Chrome, Edge, Firefox, Brave, etc.)
      ESC  →  Alt+Left   (navigate back in history)

  File Explorer
      ESC  →  Alt+Up     (go to parent folder)

  All other applications
      ESC  →  Normal ESC (transparent passthrough)

Hotkeys
  F9         Toggle SmartBack on / off
  Shift+ESC  Always sends a real ESC (override)

Requirements
  Python 3.8+  |  Windows 10/11  |  Run as Administrator
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

import sys
import time
import ctypes
import logging
import threading

import keyboard
import psutil
import win32gui
import win32process

# ─────────────────────────────────────────────────────────────────────────────
# LOGGING
# ─────────────────────────────────────────────────────────────────────────────

def _setup_logging() -> logging.Logger:
    """
    Safe logging setup that handles --noconsole exe builds
    (where sys.stdout is None).
    """
    handlers: list[logging.Handler] = []

    if sys.stdout is not None:
        handlers.append(logging.StreamHandler(sys.stdout))

    # Fallback: silent NullHandler (for --noconsole builds)
    if not handlers:
        handlers.append(logging.NullHandler())

    logging.basicConfig(
        level=logging.INFO,
        format="[%(asctime)s] %(levelname)-7s  %(message)s",
        datefmt="%H:%M:%S",
        handlers=handlers,
        force=True,
    )
    return logging.getLogger("SmartBack")


log = _setup_logging()


# ─────────────────────────────────────────────────────────────────────────────
# CONFIGURATION
# ─────────────────────────────────────────────────────────────────────────────

# Add or remove browser process names here (all lowercase)
BROWSER_PROCESSES: frozenset[str] = frozenset({
    "chrome.exe",
    "msedge.exe",
    "firefox.exe",
    "brave.exe",
    "opera.exe",
    "operagx.exe",
    "vivaldi.exe",
    "waterfox.exe",
    "librewolf.exe",
    "arc.exe",
    "thorium.exe",
    "iridium.exe",
})

# Window titles that belong to the desktop shell (explorer.exe but NOT folder windows)
_EXPLORER_EXCLUDED_TITLES: frozenset[str] = frozenset({
    "",
    "program manager",
    "start",
    "desktop",
    "taskbar",
    "search",
})

TOGGLE_KEY   = "f9"    # Key to enable / disable SmartBack
REHOOK_DELAY = 0.05    # Seconds to pause before re-hooking after passthrough
LOG_COOLDOWN = 0.40    # Minimum seconds between repeated log lines


# ─────────────────────────────────────────────────────────────────────────────
# APPLICATION STATE
# ─────────────────────────────────────────────────────────────────────────────

class _AppState:
    enabled: bool         = True   # Is SmartBack active?
    hook_ref              = None   # keyboard library hook reference for ESC
    rehook_lock           = threading.Lock()
    _last_log_time: float = 0.0


_s = _AppState()


# ─────────────────────────────────────────────────────────────────────────────
# PRIVILEGE CHECK
# ─────────────────────────────────────────────────────────────────────────────

def _is_admin() -> bool:
    """Returns True if the current process has Administrator privileges."""
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False


# ─────────────────────────────────────────────────────────────────────────────
# WINDOW / PROCESS DETECTION
# ─────────────────────────────────────────────────────────────────────────────

def _active_process() -> str:
    """
    Returns the lowercase .exe name of the foreground window's process.
    Returns '' on any failure so callers can handle it gracefully.
    """
    try:
        hwnd = win32gui.GetForegroundWindow()
        if not hwnd:
            return ""
        _, pid = win32process.GetWindowThreadProcessId(hwnd)
        if pid <= 0:
            return ""
        return psutil.Process(pid).name().lower()
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        return ""
    except Exception as exc:
        log.debug(f"Process lookup failed: {exc}")
        return ""


def _active_title() -> str:
    """Returns the title of the foreground window, or '' on failure."""
    try:
        hwnd = win32gui.GetForegroundWindow()
        return (win32gui.GetWindowText(hwnd) or "") if hwnd else ""
    except Exception:
        return ""


def _is_browser() -> bool:
    """Returns True if a known browser is in the foreground."""
    return _active_process() in BROWSER_PROCESSES


def _is_file_explorer() -> bool:
    """
    Returns True only for real File Explorer folder windows.

    The desktop shell (Progman / WorkerW), taskbar, and Start menu
    also run under explorer.exe but should NOT trigger Alt+Up.
    They are filtered out by checking the window title.
    """
    if _active_process() != "explorer.exe":
        return False
    title = _active_title().strip().lower()
    return title not in _EXPLORER_EXCLUDED_TITLES


# ─────────────────────────────────────────────────────────────────────────────
# RATE-LIMITED LOGGER
# ─────────────────────────────────────────────────────────────────────────────

def _log(msg: str) -> None:
    """
    Logs at INFO level but respects LOG_COOLDOWN to avoid console spam
    when keys are held down or pressed rapidly.
    """
    now = time.monotonic()
    if now - _s._last_log_time >= LOG_COOLDOWN:
        log.info(msg)
        _s._last_log_time = now


# ─────────────────────────────────────────────────────────────────────────────
# KEY ACTIONS
# ─────────────────────────────────────────────────────────────────────────────

def _passthrough_esc() -> None:
    """
    Passes a real ESC keystroke to the active application.

    Strategy — unhook / send / rehook:
      1. Temporarily remove our suppressing ESC hook so the next ESC
         event reaches the active application normally.
      2. Send ESC via keyboard.send().
      3. Sleep briefly so the OS delivers the event.
      4. Re-register the suppressing hook.

    Uses rehook_lock so concurrent rapid ESC presses don't cause
    overlapping hook / unhook sequences.
    """
    with _s.rehook_lock:

        # ── Step 1: Remove our hook ───────────────────────────────────────
        if _s.hook_ref is not None:
            try:
                keyboard.unhook(_s.hook_ref)
                _s.hook_ref = None
            except Exception as exc:
                log.debug(f"Unhook error: {exc}")

        # ── Step 2: Send real ESC ─────────────────────────────────────────
        try:
            keyboard.send("esc")
        except Exception as exc:
            log.error(f"keyboard.send('esc') failed: {exc}")

        # ── Step 3: Let the OS deliver the keystroke ──────────────────────
        time.sleep(REHOOK_DELAY)

        # ── Step 4: Re-register suppressing hook ──────────────────────────
        try:
            _s.hook_ref = keyboard.on_press_key(
                "esc", _esc_handler, suppress=True
            )
        except Exception as exc:
            log.critical(
                f"ESC hook re-registration failed: {exc}  "
                f"—  SmartBack is now DEGRADED (ESC will pass through)."
            )


# ─────────────────────────────────────────────────────────────────────────────
# ESC HANDLER
# ─────────────────────────────────────────────────────────────────────────────

def _esc_handler(_event: keyboard.KeyboardEvent) -> None:
    """
    Invoked on every ESC key-down event.

    Because the hook was registered with suppress=True, the raw ESC
    has already been blocked from reaching other applications by the
    time this function runs.  We decide what to send instead.

    Passthrough actions run in a daemon thread to avoid blocking the
    Windows keyboard hook callback (sleeping inside a hook callback
    can delay the entire input queue on some systems).
    """

    # ── Priority 1: Shift+ESC always sends a real ESC ────────────────────
    if keyboard.is_pressed("shift"):
        _log("Shift+ESC → passthrough")
        threading.Thread(target=_passthrough_esc, daemon=True).start()
        return

    # ── Priority 2: SmartBack is disabled ────────────────────────────────
    if not _s.enabled:
        threading.Thread(target=_passthrough_esc, daemon=True).start()
        return

    # ── Priority 3: Context-aware routing ────────────────────────────────
    if _is_browser():
        _log("Browser  →  Alt+Left  (back)")
        keyboard.send("alt+left")

    elif _is_file_explorer():
        _log("Explorer  →  Alt+Up  (parent folder)")
        keyboard.send("alt+up")

    else:
        proc = _active_process() or "unknown"
        _log(f"[{proc}]  →  ESC passthrough")
        threading.Thread(target=_passthrough_esc, daemon=True).start()


# ─────────────────────────────────────────────────────────────────────────────
# TOGGLE HANDLER
# ─────────────────────────────────────────────────────────────────────────────

def _on_toggle() -> None:
    """Flip SmartBack enabled state and log the new status."""
    _s.enabled = not _s.enabled
    state_str = "✓ ENABLED" if _s.enabled else "✗ DISABLED"
    log.info(f"SmartBack  →  {state_str}")


# ─────────────────────────────────────────────────────────────────────────────
# STARTUP BANNER
# ─────────────────────────────────────────────────────────────────────────────

def _print_banner() -> None:
    sep = "─" * 48
    log.info(sep)
    log.info("  SmartBack v1.0  ·  Context-Aware ESC Remapper")
    log.info(sep)
    log.info("  Browser       ESC  →  Alt+Left  (back)")
    log.info("  File Explorer ESC  →  Alt+Up    (parent folder)")
    log.info("  Other apps    ESC  →  Normal ESC")
    log.info(f"  Toggle         {TOGGLE_KEY.upper()}  (enable / disable)")
    log.info("  Override       Shift+ESC  (real ESC, always)")
    log.info(sep)

    if not _is_admin():
        log.warning("  ⚠  Not running as Administrator!")
        log.warning("     Global keyboard hooks require admin privileges.")
        log.warning("     Re-run as admin or use Task Scheduler (see README).")
        log.info(sep)


# ─────────────────────────────────────────────────────────────────────────────
# ENTRY POINT
# ─────────────────────────────────────────────────────────────────────────────

def main() -> None:
    _print_banner()

    # Register the suppressing ESC hook
    _s.hook_ref = keyboard.on_press_key("esc", _esc_handler, suppress=True)

    # Register toggle hotkey (suppress=True so F9 doesn't bleed into other apps)
    keyboard.add_hotkey(TOGGLE_KEY, _on_toggle, suppress=True)

    log.info("Running …  F9 = toggle  |  Ctrl+C = quit\n")

    try:
        keyboard.wait()   # Blocks the main thread indefinitely
    except KeyboardInterrupt:
        pass
    except Exception as exc:
        log.critical(f"Unexpected error: {exc}")
    finally:
        keyboard.unhook_all()
        log.info("SmartBack stopped.")


if __name__ == "__main__":
    main()
