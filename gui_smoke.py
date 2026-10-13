import os, sys, tempfile, time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from tkinter import messagebox
messagebox.askyesno = lambda *a, **k: True
messagebox.showinfo = messagebox.showwarning = messagebox.showerror = lambda *a, **k: print("MSG:", a[1][:60].replace("\n"," "))
import adb_helper as adb
fake = sys.argv[1]
adb.find_adb = lambda: fake
import app as A
os.environ["FAKE_ADB_MODE"] = "device"
a = A.App()
def pump(sec):
    end = time.time() + sec
    while time.time() < end:
        a.update(); time.sleep(0.02)
pump(2.0)
print("devices:", a.v_count.cget("text"), "| usb:", a.v_usb.cget("text"))
a.generate_report(); pump(0.3)   # before scan -> info msg
a.start_scan(); pump(4.0)
print("model:", a.v_model.cget("text"), "|", a.s_model.cget("text"), "| issues:", a.s_scan.cget("text"))
assert a.last_result and a.last_result.model == "SM-A145F"
a.generate_report(); pump(0.3)
print("report preview has model:", "SM-A145F" in a.report_box.get("1.0", "end"))
for b in A.rec.BRAND_NAMES:
    a._on_brand(b); a.update()
print("brands rendered OK")
import report as rpt
d = tempfile.mkdtemp(); rpt.save_txt(a.last_result, d + "/r.txt"); rpt.save_csv(a.last_result, d + "/r.csv")
a.destroy(); print("GUI SMOKE OK")
