# Arctis Battery Tray

Systray battery indicator for the SteelSeries Arctis Nova 7. Shows the
battery percentage as two digits in the tray icon: green while charging,
red while discharging, gray (`--`) when the headset is offline.

## Requirements

- Python 3
- `hidapi`, `pystray`, `Pillow`

```
pip install hidapi pystray Pillow
```

## Run

```
python arctis_tray.py
```

Right-click the tray icon for "Refresh now" / "Quit".

## Autostart

The app is registered to launch silently on login via a per-user
registry key (no admin rights required):

```
Path:  HKCU\Software\Microsoft\Windows\CurrentVersion\Run
Name:  ArctisBatteryTray
Value: "C:\Users\brett\AppData\Local\Programs\Python\Python312\pythonw.exe" "C:\Users\brett\arctis\arctis_tray.py"
```

It runs via `pythonw.exe` so no console window appears.

**Do not move or rename this folder/file** — the registry value above
points at an absolute path. If you move `arctis_tray.py`, autostart
will silently fail on the next login until you update that registry
value to match the new location.

To remove autostart:

```powershell
Remove-ItemProperty -Path "HKCU:\Software\Microsoft\Windows\CurrentVersion\Run" -Name "ArctisBatteryTray"
```

## How it works

Talks directly to the headset dongle over USB HID (no SteelSeries GG
required), using the same protocol as the
[HeadsetControl](https://github.com/Sapd/HeadsetControl) project.
