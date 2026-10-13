"""
report.py - Repair report banana aur TXT/CSV me save karna.

PRIVACY: Report me serial number sirf masked (last 4 characters) hota hai.
PIN/password/Google account/contacts/photos kuch bhi collect nahi hota.
"""

import csv
from typing import List

import adb_helper as adb
from diagnostics import ScanResult, recommended_steps

APP_NAME = "Mitra Mobile Repair Assistant"

_STATUS_LABEL = {"ok": "OK", "warn": "WARNING", "fail": "PROBLEM", "info": "INFO"}


def _basic_rows(r: ScanResult, include_masked_serial: bool) -> List[tuple]:
    device = " ".join(x for x in (r.manufacturer, r.model) if x) or "Not detected / not authorized"
    rows = [
        ("Date & Time", r.timestamp.strftime("%d-%m-%Y %H:%M:%S")),
        ("Connected device model", device),
        ("Android version", r.android_version or "N/A"),
        ("Connected devices", str(r.device_count)),
        ("USB/ADB connection status", _connection_text(r)),
        ("ADB version", r.adb_version or "ADB not found"),
    ]
    if include_masked_serial and r.serial:
        rows.append(("Device serial (masked)", adb.mask_serial(r.serial)))
    return rows


def _connection_text(r: ScanResult) -> str:
    if not r.adb_path:
        return "ADB not available"
    if r.device_count == 0:
        return "No device detected"
    mapping = {
        "device": "Connected & authorized",
        "unauthorized": "Connected but NOT authorized",
        "offline": "Offline",
    }
    return mapping.get(r.connection_state, f"Connected ({r.connection_state})")


def build_text(r: ScanResult, include_masked_serial: bool = False) -> str:
    lines = [
        "=" * 60,
        f"  {APP_NAME} - Repair Report",
        "=" * 60,
        "",
    ]
    for k, v in _basic_rows(r, include_masked_serial):
        lines.append(f"{k:<28}: {v}")

    lines += ["", "-" * 60, "DIAGNOSTIC CHECKS", "-" * 60]
    for c in r.checks:
        lines.append(f"[{_STATUS_LABEL.get(c.status, c.status)}] {c.name}: {c.detail}")

    lines += ["", "-" * 60, "DETECTED ISSUES", "-" * 60]
    if r.issues:
        for i, c in enumerate(r.issues, 1):
            lines.append(f"{i}. {c.name}: {c.detail}")
    else:
        lines.append("Koi issue detect nahi hua (scan me jo checks hue unke hisaab se).")

    lines += ["", "-" * 60, "RECOMMENDED REPAIR STEPS", "-" * 60]
    for i, s in enumerate(recommended_steps(r), 1):
        lines.append(f"{i}. {s}")

    lines += [
        "",
        "-" * 60,
        "Note: Ye report sirf read-only diagnostic information par based hai.",
        "Isme PIN, password, Google account ya personal data (photos/contacts/messages)",
        "collect ya save nahi kiya gaya.",
        "=" * 60,
    ]
    return "\n".join(lines)


def save_txt(r: ScanResult, path: str, include_masked_serial: bool = False) -> None:
    with open(path, "w", encoding="utf-8") as f:
        f.write(build_text(r, include_masked_serial))


def save_csv(r: ScanResult, path: str, include_masked_serial: bool = False) -> None:
    # utf-8-sig => Excel me sahi khulta hai
    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["Section", "Field", "Value"])
        for k, v in _basic_rows(r, include_masked_serial):
            w.writerow(["Summary", k, v])
        for c in r.checks:
            w.writerow(["Check", f"{c.name} [{_STATUS_LABEL.get(c.status, c.status)}]", c.detail])
        for i, c in enumerate(r.issues, 1):
            w.writerow(["Issue", f"Issue {i}", f"{c.name}: {c.detail}"])
        for i, s in enumerate(recommended_steps(r), 1):
            w.writerow(["Recommended step", f"Step {i}", s])
