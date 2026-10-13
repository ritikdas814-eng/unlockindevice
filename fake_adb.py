#!/usr/bin/env python3
"""Fake adb jo test ke liye adb jaisa output deta hai (FAKE_ADB_MODE env se)."""
import os, sys
mode = os.environ.get("FAKE_ADB_MODE", "device")
a = sys.argv[1:]
if a[:1] == ["version"]:
    print("Android Debug Bridge version 1.0.41"); sys.exit(0)
if a[:1] == ["start-server"]:
    sys.exit(0)
if a[:2] == ["devices", "-l"]:
    print("List of devices attached")
    if mode == "device":
        print("ABCD1234EF           device usb:1-1 product:a14 model:SM_A145F device:a14 transport_id:1")
    elif mode == "unauthorized":
        print("ABCD1234EF           unauthorized usb:1-1 transport_id:2")
    sys.exit(0)
if a[:2] == ["-s", "ABCD1234EF"] and a[2] == "shell":
    cmd = " ".join(a[3:])
    out = {
        "getprop ro.product.manufacturer": "samsung",
        "getprop ro.product.model": "SM-A145F",
        "getprop ro.build.version.release": "14",
        "getprop ro.build.version.sdk": "34",
        "getprop ro.build.version.security_patch": "2024-05-01",
        "dumpsys battery": "Current Battery Service state:\n  AC powered: false\n  USB powered: true\n  status: 2\n  health: 2\n  level: 77\n  temperature: 312",
        "wm size": "Physical size: 1080x2408",
        "df /data": "Filesystem 1K-blocks Used Available Use% Mounted on\n/dev/block/dm-9 113000000 50000000 63000000 45% /data",
    }.get(cmd, "")
    print(out); sys.exit(0)
sys.exit(1)
