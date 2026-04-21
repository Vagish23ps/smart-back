# SmartBack 🔙

> **Context-aware ESC key remapper for Windows.**  
> Press ESC — and it *knows* what you actually want.

---

## What Is SmartBack?

SmartBack is a lightweight background utility that upgrades your ESC key with contextual intelligence:

| Active Window         | ESC Does…                       |
|-----------------------|----------------------------------|
| Chrome, Edge, Firefox, Brave, Opera, Vivaldi… | **Navigate back** in browser history (Alt+Left) |
| File Explorer         | **Go to parent folder** (Alt+Up) |
| Everything else       | **Normal ESC** — completely transparent |

No configuration files, no system tray icon needed, no bloat.  
It runs silently in the background as a single `.exe`.

---
## Why SmartBack?

Windows lacks a universal "Back" behavior like mobile OS.
SmartBack brings intuitive navigation by making ESC context-aware.

---

## Features

- 🌐 **Browser back** — Works with Chrome, Edge, Firefox, Brave, Opera, Vivaldi, Waterfox, LibreWolf, Arc
- 📁 **Explorer navigation** — Jump to parent folder with ESC
- 🔄 **Toggle on/off** — Press `F9` to enable or disable SmartBack at any time
- 🔒 **Shift+ESC** — Always sends a real ESC, in any context, regardless of toggle state
- 🛡️ **Crash-safe** — Gracefully handles process detection failures; falls back to normal ESC
- 🚀 **Silent background operation** — No window, no tray icon, minimal CPU usage
- 🔑 **Admin-aware** — Warns if not running with elevated privileges

---

## Download

[![Download SmartBack](https://img.shields.io/badge/Download-EXE-blue?style=for-the-badge)](https://github.com/Vagish23ps/smart-back/releases)

### Quick Start
- Download the `.exe` from Releases
- Run as Administrator
- Press ESC and enjoy smart navigation

---

## Supported Browsers

| Browser | Process |
|---------|---------|
| Google Chrome | `chrome.exe` |
| Microsoft Edge | `msedge.exe` |
| Mozilla Firefox | `firefox.exe` |
| Brave | `brave.exe` |
| Opera / Opera GX | `opera.exe` / `operagx.exe` |
| Vivaldi | `vivaldi.exe` |
| Waterfox | `waterfox.exe` |
| LibreWolf | `librewolf.exe` |
| Arc | `arc.exe` |

> To add a custom browser, see [Configuration](#configuration).

---

## Requirements

- Windows 10 / 11
- Python 3.8 or higher
- **Administrator privileges** (required for global keyboard hooks)
- Libraries: `keyboard`, `pywin32`, `psutil`

---

## Quick Start (Python)

```bash
# 1. Clone the repo
git clone https://github.com/your-username/smart-back.git
cd smart-back

# 2. Install dependencies
pip install -r requirements.txt

# 3. Run as Administrator
#    Right-click your terminal → "Run as administrator", then:
python smart_back.py
```

Console output you'll see:

```
[10:42:01] INFO     ────────────────────────────────────────────────
[10:42:01] INFO       SmartBack v1.0  ·  Context-Aware ESC Remapper
[10:42:01] INFO     ────────────────────────────────────────────────
[10:42:01] INFO       Browser       ESC  →  Alt+Left  (back)
[10:42:01] INFO       File Explorer ESC  →  Alt+Up    (parent folder)
[10:42:01] INFO       Other apps    ESC  →  Normal ESC
[10:42:01] INFO       Toggle         F9  (enable / disable)
[10:42:01] INFO       Override       Shift+ESC  (real ESC, always)
[10:42:01] INFO     ────────────────────────────────────────────────
[10:42:01] INFO     Running …  F9 = toggle  |  Ctrl+C = quit
```

---

## Build a Standalone EXE

### Method 1 — One Click

```bash
build.bat
```

### Method 2 — Manual PyInstaller

```bash
pip install pyinstaller

pyinstaller --onefile --noconsole --name SmartBack \
    --hidden-import=win32api \
    --hidden-import=win32con \
    --hidden-import=win32gui \
    --hidden-import=win32process \
    --hidden-import=pywintypes \
    smart_back.py
```

Output: `dist\SmartBack.exe`

> **`--noconsole`** means no terminal window appears when the exe runs.  
> **`--onefile`** bundles everything into a single portable executable.

---

## Startup Setup (Run at Login)

The recommended method is **Task Scheduler** — it launches SmartBack with Administrator privileges at login, with **no UAC popup**.

### Automated (Recommended)

```powershell
# Open PowerShell as Administrator, then:
.\setup_startup.ps1
```

This registers a scheduled task named `SmartBack` that:
- Triggers at every user logon
- Runs with Highest (Administrator) privileges
- Never shows a UAC prompt

### Manual — Task Scheduler

1. Press `Win + R` → type `taskschd.msc` → Enter
2. Click **Create Task** (not "Create Basic Task")
3. **General tab:**
   - Name: `SmartBack`
   - ✅ Check **"Run with highest privileges"**
4. **Triggers tab:** → New → **At log on** → OK
5. **Actions tab:** → New → Browse to `dist\SmartBack.exe` → OK
6. **Conditions tab:**
   - ❌ Uncheck "Start the task only if the computer is on AC power"
7. **Settings tab:**
   - Select "Do not start a new instance" for "If the task is already running"
8. Click **OK**, enter your password if prompted.

### Alternative — Registry Startup (No admin)

> ⚠ This method runs WITHOUT admin rights. Keyboard hooks may fail for UAC-elevated windows.

Open Registry Editor (`regedit`) and add a string value at:
```
HKEY_CURRENT_USER\Software\Microsoft\Windows\CurrentVersion\Run
```

| Name | Value |
|------|-------|
| `SmartBack` | `C:\full\path\to\dist\SmartBack.exe` |

---

## Configuration

To customize SmartBack, edit `smart_back.py`:

### Add a Browser

```python
BROWSER_PROCESSES: frozenset[str] = frozenset({
    # ... existing entries ...
    "yournewbrowser.exe",   # ← add here (lowercase!)
})
```

### Change Toggle Key

```python
TOGGLE_KEY = "f8"   # Change F9 to any key
```

### Adjust Log Cooldown

```python
LOG_COOLDOWN = 0.40  # Min seconds between repeated log lines
```

---

## How It Works

```
User presses ESC
       │
       ▼
Is Shift held? ─── Yes ──→ Send real ESC (passthrough)
       │
       No
       │
       ▼
SmartBack enabled? ─── No ──→ Send real ESC (passthrough)
       │
       Yes
       │
       ▼
Detect foreground window process name
       │
   ┌───┴───────────────────┐
   ▼                       ▼
Browser?              File Explorer?
   │                       │
Alt+Left             Alt+Up (parent)
(browser back)             │
                     All other apps
                           │
                    Real ESC passthrough
```

### Passthrough Mechanism

When a "real ESC" passthrough is needed:
1. Our suppressing hook is **temporarily unregistered**
2. `keyboard.send('esc')` is called — this ESC now reaches the active app
3. A 50ms pause ensures the OS delivers the event
4. The hook is **re-registered**

This prevents recursive hook triggering (synthetic keystrokes going through our own hook again).

---

## Project Structure

```
smart-back/
├── smart_back.py          # Main application script
├── requirements.txt       # Runtime dependencies
├── requirements-dev.txt   # Build dependencies (PyInstaller)
├── build.bat              # One-click EXE build script (Windows)
├── setup_startup.ps1      # Task Scheduler registration script
├── README.md              # This file
├── .gitignore
└── LICENSE
```

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| ESC does nothing | Make sure you're running as Administrator |
| Browser back not working | Check if your browser `.exe` name is in `BROWSER_PROCESSES` |
| Hook fails after Windows update | Rebuild the exe and re-run `setup_startup.ps1` |
| F9 toggle not working | Some games capture F9 globally; try changing `TOGGLE_KEY` |
| Explorer not detected | Right-click the Explorer window title and check `_active_title()` output |

---

## Uninstall

```powershell
# Remove from Task Scheduler
Unregister-ScheduledTask -TaskName "SmartBack" -Confirm:$false

# Or from Registry (if added manually)
# Delete the SmartBack entry from:
# HKCU\Software\Microsoft\Windows\CurrentVersion\Run
```

---

## License

MIT License — see [LICENSE](LICENSE)

---

## Contributing

1. Fork the repo
2. Create your branch: `git checkout -b feature/your-feature`
3. Commit: `git commit -m "Add your feature"`
4. Push: `git push origin feature/your-feature`
5. Open a Pull Request

---

*Built with Python · keyboard · pywin32 · psutil*
