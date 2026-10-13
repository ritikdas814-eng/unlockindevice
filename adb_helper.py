"""
adb_helper.py - ADB ke saath safe communication.

SECURITY DESIGN:
  * Sirf READ-ONLY commands ki allow-list hai. Koi bhi aur command
    (install, uninstall, push, pull, reboot, wipe, input, settings put ...)
    yahan se chal hi nahi sakti - ValueError aayega.
  * Koi lock-screen bypass / FRP bypass / data extraction code nahi hai.
"""

import json
import os
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

CREATE_NO_WINDOW = 0x08000000 if os.name == "nt" else 0
ADB_EXE = "adb.exe" if os.name == "nt" else "adb"

# ---------------------------------------------------------------- allow-lists
# Host-side commands (PC par chalti hain, phone ko change nahi karti)
_ALLOWED_HOST = {
    ("version",),
    ("start-server",),
    ("devices", "-l"),
}

# Phone par chalne wale sirf read-only getprop keys
_ALLOWED_PROPS = {
    "ro.product.manufacturer",
    "ro.product.brand",
    "ro.product.model",
    "ro.product.name",
    "ro.build.version.release",
    "ro.build.version.sdk",
    "ro.build.version.security_patch",
    "ro.build.display.id",
}

# Phone par chalne wale read-only shell commands (exact match)
_ALLOWED_SHELL = {
    "dumpsys battery",
    "wm size",
    "df /data",
}

_SERIAL_RE = re.compile(r"^[A-Za-z0-9._:\-]{1,64}$")


# ---------------------------------------------------------------- data types
@dataclass
class Device:
    serial: str
    state: str                      # device / unauthorized / offline / ...
    details: dict = field(default_factory=dict)  # model:, product:, ...

    @property
    def label(self) -> str:
        model = self.details.get("model", "Unknown").replace("_", " ")
        return f"{model}  [{mask_serial(self.serial)}]  - {self.state}"


@dataclass
class AdbResult:
    ok: bool
    stdout: str = ""
    stderr: str = ""
    returncode: int = -1


# ---------------------------------------------------------------- config
def config_dir() -> str:
    base = os.environ.get("APPDATA") or os.path.expanduser("~")
    path = os.path.join(base, "MitraRepairAssistant")
    os.makedirs(path, exist_ok=True)
    return path


def _config_file() -> str:
    return os.path.join(config_dir(), "config.json")


def load_saved_adb_path() -> Optional[str]:
    try:
        with open(_config_file(), "r", encoding="utf-8") as f:
            return json.load(f).get("adb_path")
    except (OSError, ValueError):
        return None


def save_adb_path(path: str) -> None:
    """Sirf ADB ka path save hota hai - aur kuch nahi."""
    try:
        with open(_config_file(), "w", encoding="utf-8") as f:
            json.dump({"adb_path": path}, f)
    except OSError:
        pass


def app_base_dir() -> str:
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


# ---------------------------------------------------------------- find adb
def find_adb() -> Optional[str]:
    """ADB dhoondhta hai: saved path -> app folder -> PATH -> SDK folders."""
    candidates: List[str] = []

    saved = load_saved_adb_path()
    if saved:
        candidates.append(saved)

    base = app_base_dir()
    candidates.append(os.path.join(base, "platform-tools", ADB_EXE))
    candidates.append(os.path.join(base, ADB_EXE))

    on_path = shutil.which("adb")
    if on_path:
        candidates.append(on_path)

    for env in ("ANDROID_HOME", "ANDROID_SDK_ROOT"):
        root = os.environ.get(env)
        if root:
            candidates.append(os.path.join(root, "platform-tools", ADB_EXE))

    if os.name == "nt":
        candidates.append(r"C:\platform-tools\adb.exe")
        local = os.environ.get("LOCALAPPDATA")
        if local:
            candidates.append(os.path.join(local, "Android", "Sdk", "platform-tools", "adb.exe"))

    for c in candidates:
        if c and os.path.isfile(c):
            return c
    return None


# ---------------------------------------------------------------- run
def _run(cmd: List[str], timeout: int) -> AdbResult:
    try:
        p = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            creationflags=CREATE_NO_WINDOW,
            encoding="utf-8",
            errors="replace",
        )
        return AdbResult(p.returncode == 0, p.stdout.strip(), p.stderr.strip(), p.returncode)
    except FileNotFoundError:
        return AdbResult(False, "", "ADB file nahi mili (adb not found).", -1)
    except subprocess.TimeoutExpired:
        return AdbResult(False, "", f"Timeout: command {timeout}s me complete nahi hui.", -2)
    except OSError as exc:
        return AdbResult(False, "", f"OS error: {exc}", -3)


def run_host(adb: str, *args: str, timeout: int = 20) -> AdbResult:
    """PC-side read-only ADB command (allow-list ke andar)."""
    if tuple(args) not in _ALLOWED_HOST:
        raise ValueError(f"Blocked: '{' '.join(args)}' allow-list me nahi hai.")
    return _run([adb, *args], timeout)


def run_getprop(adb: str, serial: str, prop: str, timeout: int = 10) -> AdbResult:
    if prop not in _ALLOWED_PROPS:
        raise ValueError(f"Blocked: getprop '{prop}' allow-list me nahi hai.")
    if not _SERIAL_RE.match(serial):
        raise ValueError("Invalid device serial.")
    return _run([adb, "-s", serial, "shell", "getprop", prop], timeout)


def run_shell_readonly(adb: str, serial: str, command: str, timeout: int = 15) -> AdbResult:
    if command not in _ALLOWED_SHELL:
        raise ValueError(f"Blocked: shell '{command}' allow-list me nahi hai.")
    if not _SERIAL_RE.match(serial):
        raise ValueError("Invalid device serial.")
    return _run([adb, "-s", serial, "shell", *command.split()], timeout)


# ---------------------------------------------------------------- parse
_DEVICE_LINE = re.compile(
    r"^(?P<serial>\S+)\s+"
    r"(?P<state>device|offline|unauthorized|recovery|sideload|bootloader|rescue|authorizing|no permissions)"
    r"(?P<rest>.*)$"
)


def parse_devices(output: str) -> List[Device]:
    """'adb devices -l' ka output parse karta hai."""
    devices: List[Device] = []
    for raw in output.splitlines():
        line = raw.strip()
        if not line or line.startswith("List of devices") or line.startswith("*"):
            continue
        m = _DEVICE_LINE.match(line)
        if not m:
            continue
        details = {}
        for token in m.group("rest").split():
            if ":" in token:
                k, v = token.split(":", 1)
                details[k] = v
        devices.append(Device(m.group("serial"), m.group("state"), details))
    return devices


def mask_serial(serial: str) -> str:
    """Privacy: serial ke sirf last 4 characters dikhao."""
    if len(serial) <= 4:
        return "****"
    return "*" * (len(serial) - 4) + serial[-4:]


# state -> (level, Hinglish message)   level: ok / warn / fail
STATE_HELP = {
    "device": ("ok", "Phone connected hai aur USB debugging authorized hai."),
    "unauthorized": (
        "warn",
        "Phone ne is laptop ko authorize nahi kiya. Phone ki screen unlock karke "
        "'Allow USB debugging?' wale popup me 'Allow' dabayein "
        "(owner ki permission zaroori hai). Agar popup na aaye to USB cable nikaal "
        "kar dobara lagayein.",
    ),
    "offline": (
        "warn",
        "Device 'offline' dikh raha hai. Cable nikaal ke dobara lagayein, USB debugging "
        "off/on karein, ya phone restart karein.",
    ),
    "no permissions": (
        "fail",
        "Is computer ko device ka access nahi mila. Windows par USB driver install karein "
        "(README ka driver section dekhein).",
    ),
    "authorizing": ("warn", "Authorization chal rahi hai - phone ki screen par popup check karein."),
    "recovery": ("warn", "Phone Recovery mode me hai. Normal diagnostics ke liye phone ko normal boot karein."),
    "sideload": ("warn", "Phone Sideload mode me hai. Normal diagnostics ke liye normal boot karein."),
    "bootloader": ("warn", "Phone Bootloader mode me hai. Normal diagnostics ke liye normal boot karein."),
    "rescue": ("warn", "Phone Rescue mode me hai."),
}


def parse_battery(text: str) -> dict:
    """'dumpsys battery' ka output -> dict."""
    info = {}
    for line in text.splitlines():
        if ":" in line:
            k, v = line.split(":", 1)
            info[k.strip().lower()] = v.strip()
    return info


def parse_df(text: str) -> Optional[Tuple[str, str, str, str]]:
    """'df /data' -> (total, used, available, use%) as human text, ya None."""
    lines = [l for l in text.splitlines() if l.strip()]
    if len(lines) < 2:
        return None
    parts = lines[-1].split()
    if len(parts) < 5:
        return None
    try:
        total, used, avail = (int(parts[1]), int(parts[2]), int(parts[3]))
    except ValueError:
        return None

    def gb(kb: int) -> str:
        return f"{kb / (1024 * 1024):.1f} GB"

    return gb(total), gb(used), gb(avail), parts[4]
