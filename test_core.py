import os, sys, tempfile, unittest, csv
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import adb_helper as adb
import diagnostics as diag
import report as rpt
import recovery_data as rec

FAKE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fake_adb.py")
FAKE_BIN = None

def setUpModule():
    global FAKE_BIN
    d = tempfile.mkdtemp()
    FAKE_BIN = os.path.join(d, "adb")
    with open(FAKE_BIN, "w") as f:
        f.write(f"#!/bin/sh\nexec {sys.executable} {FAKE} \"$@\"\n")
    os.chmod(FAKE_BIN, 0o755)

class TestAllowList(unittest.TestCase):
    def test_blocked_host(self):
        for bad in (("reboot",), ("shell", "rm", "-rf", "/"), ("install", "a.apk"), ("pull", "/sdcard")):
            with self.assertRaises(ValueError):
                adb.run_host("adb", *bad)
    def test_blocked_shell(self):
        for bad in ("input text 1234", "settings put global x 1", "wipe data", "dumpsys battery; reboot", "pm uninstall x"):
            with self.assertRaises(ValueError):
                adb.run_shell_readonly("adb", "ABC123", bad)
    def test_blocked_prop_and_serial(self):
        with self.assertRaises(ValueError):
            adb.run_getprop("adb", "ABC123", "persist.sys.anything")
        with self.assertRaises(ValueError):
            adb.run_getprop("adb", "x; reboot", "ro.product.model")

class TestParse(unittest.TestCase):
    def test_parse(self):
        out = ("* daemon started successfully\nList of devices attached\n"
               "R58M123  device usb:1-1 product:x model:SM_A145F device:a14 transport_id:1\n"
               "EMU1 unauthorized usb:1-2 transport_id:2\n"
               "EMU2 offline\nEMU3 no permissions (user in plugdev group)\n")
        d = adb.parse_devices(out)
        self.assertEqual([x.state for x in d], ["device", "unauthorized", "offline", "no permissions"])
        self.assertEqual(d[0].details["model"], "SM_A145F")
    def test_empty(self):
        self.assertEqual(adb.parse_devices("List of devices attached\n\n"), [])
    def test_mask(self):
        self.assertEqual(adb.mask_serial("ABCD1234EF"), "******34EF")
    def test_df(self):
        self.assertEqual(adb.parse_df("Filesystem 1K-blocks Used Available Use% Mounted on\n/d 104857600 52428800 52428800 50% /data")[3], "50%")

class TestScan(unittest.TestCase):
    def run_mode(self, mode):
        os.environ["FAKE_ADB_MODE"] = mode
        prog = []
        r = diag.run_scan(FAKE_BIN, None, lambda f, m: prog.append((f, m)))
        return r, prog
    def test_ok(self):
        r, prog = self.run_mode("device")
        self.assertEqual(r.model, "SM-A145F"); self.assertEqual(r.android_version, "14")
        self.assertEqual(r.device_count, 1); self.assertEqual(prog[-1][0], 1.0)
        self.assertFalse(r.issues)
    def test_unauthorized(self):
        r, _ = self.run_mode("unauthorized")
        self.assertEqual(r.connection_state, "unauthorized"); self.assertTrue(r.issues)
        self.assertEqual(r.model, "")
    def test_none(self):
        r, _ = self.run_mode("none")
        self.assertEqual(r.device_count, 0); self.assertTrue(r.issues)
    def test_no_adb(self):
        r = diag.run_scan(None, None)
        self.assertEqual(r.checks[0].status, "fail")

class TestReport(unittest.TestCase):
    def test_files(self):
        os.environ["FAKE_ADB_MODE"] = "device"
        r = diag.run_scan(FAKE_BIN, None)
        txt = rpt.build_text(r)
        self.assertIn("SM-A145F", txt); self.assertNotIn("ABCD1234EF", txt); self.assertNotIn("34EF", txt)
        self.assertIn("34EF", rpt.build_text(r, True)); self.assertNotIn("ABCD1234EF", rpt.build_text(r, True))
        d = tempfile.mkdtemp()
        rpt.save_txt(r, os.path.join(d, "a.txt")); rpt.save_csv(r, os.path.join(d, "a.csv"))
        rows = list(csv.reader(open(os.path.join(d, "a.csv"), encoding="utf-8-sig")))
        self.assertEqual(rows[0], ["Section", "Field", "Value"]); self.assertGreater(len(rows), 8)

class TestRecovery(unittest.TestCase):
    def test_brands(self):
        self.assertEqual(rec.BRAND_NAMES, ["Samsung","Xiaomi","Redmi","Vivo","Oppo","Realme","Motorola","Google Pixel"])
        for b in rec.BRANDS.values():
            self.assertTrue(b["links"]); self.assertTrue(all(u.startswith("https://") for _, u in b["links"]))

if __name__ == "__main__":
    unittest.main(verbosity=1)
