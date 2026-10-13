"""
diagnostics.py - Read-only phone diagnostics.

Har result asli command output par based hai. Agar kuch check nahi ho paya
to 'info/warn' me "check nahi ho paya" likha jata hai - kabhi fake success nahi.
"""

import datetime
import json
import os
import subprocess
from dataclasses import dataclass, field
from typing import Callable, List, Optional

import adb_helper as adb

OK, WARN, FAIL, INFO = "ok", "warn", "fail", "info"

ProgressCb = Callable[[float, str], None]


@dataclass
class CheckResult:
    name: str
    status: str            # ok / warn / fail / info
    detail: str
    hint: str = ""         # recommended repair / troubleshooting step (Hinglish)


@dataclass
class ScanResult:
    timestamp: datetime.datetime
    adb_path: Optional[str] = None
    adb_version: str = ""
    device_count: int = 0
    serial: str = ""                    # sirf memory me; report me masked jaata hai
    connection_state: str = "N/A"
    manufacturer: str = ""
    model: str = ""
    android_version: str = ""
    sdk_level: str = ""
    security_patch: str = ""
    checks: List[CheckResult] = field(default_factory=list)

    @property
    def issues(self) -> List[CheckResult]:
        return [c for c in self.checks if c.status in (WARN, FAIL)]

    def add(self, name, status, detail, hint=""):
        self.checks.append(CheckResult(name, status, detail, hint))


def list_devices(adb_path: str):
    """(devices, AdbResult) return karta hai."""
    adb.run_host(adb_path, "start-server", timeout=30)
    res = adb.run_host(adb_path, "devices", "-l")
    devices = adb.parse_devices(res.stdout) if res.ok else []
    return devices, res


# ------------------------------------------------------------ Windows driver check
_USB_KEYWORDS = (
    "android", "adb", "mtp", "usb", "composite", "phone", "mobile",
    "samsung", "xiaomi", "redmi", "oppo", "vivo", "realme", "motorola", "pixel", "google",
)


def windows_driver_problems() -> Optional[List[str]]:
    """
    Windows par aise USB devices ki list jinke driver me problem hai (read-only).
    Non-Windows par ya error par None return karta hai.
    """
    if os.name != "nt":
        return None
    ps = (
        "Get-CimInstance Win32_PnPEntity | Where-Object { $_.ConfigManagerErrorCode -ne 0 } "
        "| Select-Object Name,ConfigManagerErrorCode | ConvertTo-Json -Compress"
    )
    try:
        p = subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command", ps],
            capture_output=True, text=True, timeout=25,
            creationflags=adb.CREATE_NO_WINDOW, encoding="utf-8", errors="replace",
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    out = p.stdout.strip()
    if p.returncode != 0:
        return None
    if not out:
        return []
    try:
        data = json.loads(out)
    except ValueError:
        return None
    if isinstance(data, dict):
        data = [data]
    names = []
    for item in data:
        name = str(item.get("Name") or "")
        if any(k in name.lower() for k in _USB_KEYWORDS):
            names.append(f"{name} (error code {item.get('ConfigManagerErrorCode')})")
    return names


# ------------------------------------------------------------ main scan
def run_scan(adb_path: Optional[str], selected_serial: Optional[str],
             progress: Optional[ProgressCb] = None) -> ScanResult:
    def step(frac: float, msg: str):
        if progress:
            progress(frac, msg)

    result = ScanResult(timestamp=datetime.datetime.now(), adb_path=adb_path)

    # ---- 1. ADB availability
    step(0.05, "ADB check ho raha hai (adb version)...")
    if not adb_path:
        result.add(
            "ADB availability", FAIL,
            "ADB (Platform-Tools) is computer par nahi mili.",
            "Android Platform-Tools download karke extract karein aur 'ADB Path Choose Karein' "
            "button se adb.exe select karein (README Step 3).",
        )
        step(1.0, "Scan ruk gaya: ADB nahi mili.")
        return result

    ver = adb.run_host(adb_path, "version")
    if not ver.ok:
        result.add("ADB availability", FAIL,
                   f"ADB chal nahi paayi: {ver.stderr or 'unknown error'}",
                   "Platform-Tools dobara download karke extract karein. Antivirus ne adb.exe "
                   "block kiya ho to allow karein.")
        step(1.0, "Scan ruk gaya: ADB error.")
        return result
    result.adb_version = ver.stdout.splitlines()[0] if ver.stdout else "unknown"
    result.add("ADB availability", OK, f"ADB mil gayi: {result.adb_version}")

    # ---- 2. Device detection
    step(0.20, "Connected devices dhoondh rahe hain (adb devices -l)...")
    devices, res = list_devices(adb_path)
    if not res.ok:
        result.add("USB data connection", FAIL,
                   f"'adb devices' fail hua: {res.stderr or res.stdout}",
                   "Command Prompt me 'adb kill-server' phir 'adb start-server' chalayein, "
                   "ya laptop restart karein.")
        step(1.0, "Scan ruk gaya.")
        return result

    result.device_count = len(devices)
    if not devices:
        result.add(
            "USB data connection", FAIL,
            "Koi Android device detect nahi hua.",
            "1) Original data-cable use karein (sirf charging wali cable nahi). "
            "2) Phone par USB mode 'File Transfer (MTP)' chunein. "
            "3) Developer Options me 'USB debugging' ON karein. "
            "4) Doosra USB port try karein. 5) USB driver install karein.",
        )
        step(0.6, "Windows USB driver check ho raha hai (read-only)...")
        problems = windows_driver_problems()
        if problems is None:
            result.add("Windows USB driver", INFO,
                       "Driver check is system par nahi ho paya (Windows par hi chalta hai).")
        elif problems:
            result.add("Windows USB driver", WARN,
                       "Ye devices me driver problem mili: " + "; ".join(problems[:5]),
                       "Device Manager kholein, yellow warning wale device par right-click "
                       "-> Update driver. Phone company ka USB driver ya Google USB Driver install karein.")
        else:
            result.add("Windows USB driver", OK,
                       "Windows ne koi USB/phone driver error report nahi kiya.")
        step(1.0, "Scan complete.")
        return result

    result.add("USB data connection", OK, f"{len(devices)} device detect hua.")

    # ---- 3. Pick device
    dev = None
    if selected_serial:
        dev = next((d for d in devices if d.serial == selected_serial), None)
    dev = dev or devices[0]
    result.serial = dev.serial
    result.connection_state = dev.state
    if len(devices) > 1:
        result.add("Multiple devices", INFO,
                   f"{len(devices)} devices connected hain. Scan sirf selected device par hua.")

    level, msg = adb.STATE_HELP.get(dev.state, (WARN, f"Unknown state: {dev.state}"))
    if dev.state != "device":
        result.add("ADB authorization", level, f"State: {dev.state}. {msg}",
                   "" if level == OK else msg)
        step(0.7, "Windows USB driver check ho raha hai (read-only)...")
        problems = windows_driver_problems()
        if problems:
            result.add("Windows USB driver", WARN,
                       "Driver problem: " + "; ".join(problems[:5]),
                       "Device Manager me driver update karein.")
        step(1.0, "Scan complete (device authorized nahi hai, isliye detail diagnostics skip hui).")
        return result

    result.add("ADB authorization", OK, "Device authorized hai (state: device).")

    # ---- 4. Properties
    step(0.40, "Device model aur Android version padh rahe hain (getprop)...")

    def prop(key: str) -> str:
        r = adb.run_getprop(adb_path, dev.serial, key)
        return r.stdout.strip() if r.ok else ""

    result.manufacturer = prop("ro.product.manufacturer")
    result.model = prop("ro.product.model") or dev.details.get("model", "")
    result.android_version = prop("ro.build.version.release")
    result.sdk_level = prop("ro.build.version.sdk")
    result.security_patch = prop("ro.build.version.security_patch")

    if result.model and result.android_version:
        result.add("Device model & Android version", OK,
                   f"{result.manufacturer} {result.model} - Android {result.android_version} "
                   f"(API {result.sdk_level or '?'})")
    else:
        result.add("Device model & Android version", WARN,
                   "Model/Android version padh nahi paye.",
                   "Cable dobara lagayein aur scan repeat karein.")

    if result.security_patch:
        result.add("Security patch", INFO, f"Security patch level: {result.security_patch}")

    # ---- 5. Battery
    step(0.60, "Battery information padh rahe hain (dumpsys battery - read-only)...")
    bat = adb.run_shell_readonly(adb_path, dev.serial, "dumpsys battery")
    if bat.ok and bat.stdout:
        b = adb.parse_battery(bat.stdout)
        level_txt = b.get("level", "?")
        temp_raw = b.get("temperature", "")
        temp_txt = ""
        warn = False
        if temp_raw.isdigit():
            temp_c = int(temp_raw) / 10
            temp_txt = f", temperature {temp_c:.1f}°C"
            warn = temp_c >= 45
        usb_powered = b.get("usb powered", "?")
        health_map = {"1": "Unknown", "2": "Good", "3": "Overheat", "4": "Dead",
                      "5": "Over voltage", "6": "Failure", "7": "Cold"}
        health = health_map.get(b.get("health", ""), b.get("health", "?"))
        detail = f"Battery {level_txt}%, health: {health}{temp_txt}, USB powered: {usb_powered}"
        bad_health = health in ("Overheat", "Dead", "Over voltage", "Failure")
        if warn or bad_health:
            result.add("Battery", WARN, detail,
                       "Battery garam ya kharab dikh rahi hai. Phone ko thanda hone dein; "
                       "baar-baar problem ho to battery replace karwayein.")
        else:
            result.add("Battery", OK, detail)
        if usb_powered.lower() == "false" and b.get("ac powered", "").lower() == "false":
            result.add("USB charging", WARN,
                       "Phone USB se power nahi le raha (USB powered: false).",
                       "Cable ya USB port kharab ho sakta hai - doosri cable/port try karein.")
    else:
        result.add("Battery", INFO, "Battery info available nahi hui (check nahi ho paya).")

    # ---- 6. Screen & storage
    step(0.78, "Screen size aur storage padh rahe hain (wm size, df /data)...")
    wm = adb.run_shell_readonly(adb_path, dev.serial, "wm size")
    if wm.ok and wm.stdout:
        result.add("Screen resolution", INFO, wm.stdout.replace("\n", " | "))
    df = adb.run_shell_readonly(adb_path, dev.serial, "df /data")
    parsed = adb.parse_df(df.stdout) if df.ok else None
    if parsed:
        total, used, avail, pct = parsed
        pct_val = int(pct.strip("%")) if pct.strip("%").isdigit() else 0
        detail = f"Total {total}, used {used}, free {avail} ({pct} used)"
        if pct_val >= 95:
            result.add("Storage", WARN, detail,
                       "Storage lagbhag full hai. Phone slow/hang ho sakta hai - "
                       "owner se permission lekar fazool files/apps hatayein.")
        else:
            result.add("Storage", OK, detail)
    else:
        result.add("Storage", INFO, "Storage info check nahi ho paya.")

    step(1.0, "Scan complete.")
    return result


# ------------------------------------------------------------ recommendations
def recommended_steps(result: ScanResult) -> List[str]:
    steps: List[str] = []
    for c in result.checks:
        if c.status in (WARN, FAIL) and c.hint and c.hint not in steps:
            steps.append(c.hint)
    if not steps:
        if result.connection_state == "device":
            steps.append("Koi connection problem nahi mili. Agar phone me koi aur dikkat hai "
                         "to company ke authorized service center se sampark karein.")
        else:
            steps.append("Scan complete nahi hua - pehle device connect karke dobara scan chalayein.")
    return steps
