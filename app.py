"""
Mitra Mobile Repair Assistant - main GUI (CustomTkinter)

Safe by design:
  * Scan se pehle owner ki permission (dialog) - har command explain hoti hai
  * Sirf read-only ADB commands (adb_helper.py ki allow-list)
  * Koi lock bypass / FRP bypass / data extraction nahi
"""

import queue
import threading
import webbrowser
from tkinter import filedialog, messagebox

import customtkinter as ctk

import adb_helper as adb
import diagnostics as diag
import recovery_data as rec
import report as rpt

APP_NAME = "Mitra Mobile Repair Assistant"
VERSION = "1.0.0"

BLUE = "#1f6feb"
BLUE_HOVER = "#388bfd"
BG = "#0d1117"
PANEL = "#161b22"
CARD = "#1c2330"
TEXT_MUTED = "#8b949e"
STATUS_COLORS = {"ok": "#3fb950", "warn": "#d29922", "fail": "#f85149", "info": "#58a6ff"}
STATUS_ICONS = {"ok": "✔", "warn": "⚠", "fail": "✖", "info": "ℹ"}

CONSENT_TEXT = (
    "Diagnostics shuru karne se pehle PHONE KE OWNER ki permission zaroori hai.\n\n"
    "Ye tool sirf ye READ-ONLY commands chalayega (phone me kuch change/install/delete nahi hoga):\n\n"
    "  1. adb version            - ADB ka version dekhna\n"
    "  2. adb devices -l         - connected phones ki list\n"
    "  3. getprop (model, Android version, security patch) - phone ki basic info\n"
    "  4. dumpsys battery        - battery level/health\n"
    "  5. wm size, df /data      - screen size aur storage ki jaankari\n"
    "  6. Windows driver check   - USB driver errors (sirf padhta hai)\n\n"
    "Ye tool KABHI PIN, password, Google account, photos, contacts ya messages collect nahi karta, "
    "aur lock-screen/FRP bypass nahi karta.\n\n"
    "Kya phone ke owner ne is scan ki permission di hai?"
)


class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        self.title(f"{APP_NAME}  v{VERSION}")
        self.geometry("1150x720")
        self.minsize(960, 620)
        self.configure(fg_color=BG)

        self.adb_path = adb.find_adb()
        self.devices = []
        self.last_result = None
        self.busy = False
        self.ui_queue: "queue.Queue" = queue.Queue()

        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self._build_sidebar()
        self.pages = {
            "dashboard": self._build_dashboard(),
            "recovery": self._build_recovery(),
            "report": self._build_report_page(),
            "help": self._build_help(),
        }
        self.show_page("dashboard")

        self.after(100, self._poll_queue)
        self.after(300, self.refresh_devices)

    # ------------------------------------------------------------ thread-safe UI
    def _poll_queue(self):
        try:
            while True:
                fn = self.ui_queue.get_nowait()
                fn()
        except queue.Empty:
            pass
        self.after(100, self._poll_queue)

    def _ui(self, fn):
        self.ui_queue.put(fn)

    # ------------------------------------------------------------ layout
    def _build_sidebar(self):
        sb = ctk.CTkFrame(self, width=230, corner_radius=0, fg_color=PANEL)
        sb.grid(row=0, column=0, sticky="nsew")
        sb.grid_propagate(False)

        ctk.CTkLabel(sb, text="🔧 MITRA", font=ctk.CTkFont(size=26, weight="bold"),
                     text_color=BLUE_HOVER).pack(pady=(28, 0), padx=20, anchor="w")
        ctk.CTkLabel(sb, text="Mobile Repair Assistant", font=ctk.CTkFont(size=13),
                     text_color=TEXT_MUTED).pack(padx=20, anchor="w", pady=(0, 24))

        self.nav_buttons = {}
        for key, label in (("dashboard", "📊  Dashboard"),
                           ("recovery", "🔐  Screen-Lock Recovery"),
                           ("report", "📄  Repair Report"),
                           ("help", "❓  Help / Troubleshoot")):
            b = ctk.CTkButton(sb, text=label, anchor="w", height=40, corner_radius=8,
                              fg_color="transparent", hover_color="#21262d",
                              command=lambda k=key: self.show_page(k))
            b.pack(fill="x", padx=14, pady=3)
            self.nav_buttons[key] = b

        ctk.CTkLabel(
            sb, text="Sirf official & read-only\ntools. Koi bypass nahi.",
            font=ctk.CTkFont(size=11), text_color=TEXT_MUTED, justify="left",
        ).pack(side="bottom", padx=20, pady=20, anchor="w")

        self.content = ctk.CTkFrame(self, fg_color=BG, corner_radius=0)
        self.content.grid(row=0, column=1, sticky="nsew")
        self.content.grid_columnconfigure(0, weight=1)
        self.content.grid_rowconfigure(0, weight=1)

    def show_page(self, key):
        for k, p in self.pages.items():
            p.grid_forget()
        self.pages[key].grid(row=0, column=0, sticky="nsew", padx=22, pady=18)
        for k, b in self.nav_buttons.items():
            b.configure(fg_color=BLUE if k == key else "transparent")
        if key == "report":
            self._refresh_report_preview()

    def _card(self, parent, title):
        f = ctk.CTkFrame(parent, fg_color=CARD, corner_radius=12)
        ctk.CTkLabel(f, text=title, font=ctk.CTkFont(size=12), text_color=TEXT_MUTED
                     ).pack(anchor="w", padx=16, pady=(12, 0))
        value = ctk.CTkLabel(f, text="-", font=ctk.CTkFont(size=17, weight="bold"),
                             wraplength=230, justify="left")
        value.pack(anchor="w", padx=16, pady=(2, 4))
        sub = ctk.CTkLabel(f, text="", font=ctk.CTkFont(size=11), text_color=TEXT_MUTED,
                           wraplength=230, justify="left")
        sub.pack(anchor="w", padx=16, pady=(0, 12))
        return f, value, sub

    # ------------------------------------------------------------ Dashboard
    def _build_dashboard(self):
        page = ctk.CTkFrame(self.content, fg_color="transparent")
        page.grid_columnconfigure((0, 1, 2, 3), weight=1, uniform="cards")
        page.grid_rowconfigure(6, weight=1)

        ctk.CTkLabel(page, text=APP_NAME, font=ctk.CTkFont(size=26, weight="bold")
                     ).grid(row=0, column=0, columnspan=4, sticky="w")
        ctk.CTkLabel(page, text="USB se Android phone connect karein aur safe, read-only diagnostics chalayein.",
                     text_color=TEXT_MUTED).grid(row=1, column=0, columnspan=4, sticky="w", pady=(0, 12))

        c1, self.v_usb, self.s_usb = self._card(page, "USB / ADB STATUS")
        c2, self.v_count, self.s_count = self._card(page, "CONNECTED DEVICES")
        c3, self.v_model, self.s_model = self._card(page, "PHONE MODEL")
        c4, self.v_scan, self.s_scan = self._card(page, "LAST SCAN")
        for i, c in enumerate((c1, c2, c3, c4)):
            c.grid(row=2, column=i, sticky="nsew", padx=5, pady=5)

        # buttons
        bar = ctk.CTkFrame(page, fg_color="transparent")
        bar.grid(row=3, column=0, columnspan=4, sticky="ew", pady=(10, 6))
        self.btn_scan = ctk.CTkButton(bar, text="▶  Start Scan", width=150, height=38,
                                      fg_color=BLUE, hover_color=BLUE_HOVER, command=self.start_scan)
        self.btn_scan.pack(side="left", padx=(5, 8))
        self.btn_refresh = ctk.CTkButton(bar, text="⟳  Refresh Devices", width=160, height=38,
                                         fg_color="#30363d", hover_color="#484f58",
                                         command=self.refresh_devices)
        self.btn_refresh.pack(side="left", padx=8)
        self.btn_report = ctk.CTkButton(bar, text="📄  Generate Report", width=170, height=38,
                                        fg_color="#30363d", hover_color="#484f58",
                                        command=self.generate_report)
        self.btn_report.pack(side="left", padx=8)
        self.btn_adbpath = ctk.CTkButton(bar, text="ADB Path Choose Karein", width=190, height=38,
                                         fg_color="transparent", border_width=1, border_color="#30363d",
                                         hover_color="#21262d", command=self.choose_adb)
        self.btn_adbpath.pack(side="right", padx=5)

        # device selector + progress
        sel = ctk.CTkFrame(page, fg_color="transparent")
        sel.grid(row=4, column=0, columnspan=4, sticky="ew", pady=(6, 0))
        ctk.CTkLabel(sel, text="Selected device:", text_color=TEXT_MUTED).pack(side="left", padx=(5, 8))
        self.device_menu = ctk.CTkOptionMenu(sel, values=["(koi device nahi)"], width=380,
                                             fg_color=CARD, button_color=BLUE,
                                             button_hover_color=BLUE_HOVER)
        self.device_menu.pack(side="left")
        self.device_menu_map = {}

        prog = ctk.CTkFrame(page, fg_color="transparent")
        prog.grid(row=5, column=0, columnspan=4, sticky="ew", pady=(10, 0))
        self.progress = ctk.CTkProgressBar(prog, progress_color=BLUE)
        self.progress.set(0)
        self.progress.pack(fill="x", padx=5)
        self.progress_label = ctk.CTkLabel(prog, text="Ready.", text_color=TEXT_MUTED, anchor="w")
        self.progress_label.pack(fill="x", padx=5, pady=(4, 0))

        # diagnostics list
        box = ctk.CTkFrame(page, fg_color=PANEL, corner_radius=12)
        box.grid(row=6, column=0, columnspan=4, sticky="nsew", pady=(10, 0))
        box.grid_columnconfigure(0, weight=1)
        box.grid_rowconfigure(1, weight=1)
        ctk.CTkLabel(box, text="Diagnostic Status", font=ctk.CTkFont(size=15, weight="bold")
                     ).grid(row=0, column=0, sticky="w", padx=16, pady=(12, 4))
        self.diag_list = ctk.CTkScrollableFrame(box, fg_color="transparent")
        self.diag_list.grid(row=1, column=0, sticky="nsew", padx=8, pady=(0, 8))
        self.diag_list.grid_columnconfigure(0, weight=1)
        self._show_diag_placeholder("Abhi koi scan nahi hua. 'Start Scan' dabayein (owner ki permission ke baad).")
        return page

    def _show_diag_placeholder(self, msg):
        for w in self.diag_list.winfo_children():
            w.destroy()
        ctk.CTkLabel(self.diag_list, text=msg, text_color=TEXT_MUTED, wraplength=700,
                     justify="left").grid(row=0, column=0, sticky="w", padx=10, pady=10)

    def _render_checks(self, checks):
        for w in self.diag_list.winfo_children():
            w.destroy()
        for i, c in enumerate(checks):
            row = ctk.CTkFrame(self.diag_list, fg_color=CARD, corner_radius=8)
            row.grid(row=i, column=0, sticky="ew", padx=4, pady=3)
            row.grid_columnconfigure(1, weight=1)
            ctk.CTkLabel(row, text=STATUS_ICONS[c.status], width=34,
                         text_color=STATUS_COLORS[c.status], font=ctk.CTkFont(size=18, weight="bold")
                         ).grid(row=0, column=0, rowspan=2, padx=(8, 2), pady=6)
            ctk.CTkLabel(row, text=c.name, font=ctk.CTkFont(weight="bold"), anchor="w"
                         ).grid(row=0, column=1, sticky="w", pady=(6, 0))
            ctk.CTkLabel(row, text=c.detail, text_color=TEXT_MUTED, anchor="w", justify="left",
                         wraplength=680).grid(row=1, column=1, sticky="w", pady=(0, 2))
            if c.hint and c.status in ("warn", "fail"):
                ctk.CTkLabel(row, text="➜ " + c.hint, text_color=STATUS_COLORS[c.status], anchor="w",
                             justify="left", wraplength=680).grid(row=2, column=1, sticky="w", pady=(0, 6))

    # ------------------------------------------------------------ actions
    def _set_busy(self, busy: bool):
        self.busy = busy
        state = "disabled" if busy else "normal"
        for b in (self.btn_scan, self.btn_refresh, self.btn_report):
            b.configure(state=state)

    def _set_progress(self, frac, msg):
        self.progress.set(max(0.0, min(1.0, frac)))
        self.progress_label.configure(text=msg)

    def choose_adb(self):
        path = filedialog.askopenfilename(
            title="adb.exe select karein",
            filetypes=[("ADB", "adb.exe adb"), ("All files", "*.*")])
        if not path:
            return
        res = adb.run_host(path, "version")
        if not res.ok:
            messagebox.showerror(APP_NAME, "Ye file valid ADB nahi lag rahi.\n\n" + (res.stderr or ""))
            return
        adb.save_adb_path(path)
        self.adb_path = path
        messagebox.showinfo(APP_NAME, "ADB set ho gayi:\n" + res.stdout.splitlines()[0])
        self.refresh_devices()

    def refresh_devices(self):
        if self.busy:
            return
        if not self.adb_path:
            self._update_status_no_adb()
            return
        self._set_busy(True)
        self._set_progress(0.3, "Devices dhoondh rahe hain (adb devices -l)...")

        def work():
            devices, res = diag.list_devices(self.adb_path)
            self._ui(lambda: self._after_refresh(devices, res))

        threading.Thread(target=work, daemon=True).start()

    def _update_status_no_adb(self):
        self.v_usb.configure(text="ADB nahi mili", text_color=STATUS_COLORS["fail"])
        self.s_usb.configure(text="Platform-Tools install karein, phir 'ADB Path Choose Karein' dabayein.")
        self.v_count.configure(text="0")
        self._show_diag_placeholder(
            "ADB (Android Platform-Tools) is laptop par nahi mili.\n\n"
            "Step: Platform-Tools download karke extract karein -> 'ADB Path Choose Karein' button se "
            "adb.exe select karein. Detail README me / Help page me hai.")

    def _after_refresh(self, devices, res):
        self._set_busy(False)
        self._set_progress(0, "Ready.")
        self.devices = devices
        if not res.ok:
            self.v_usb.configure(text="ADB error", text_color=STATUS_COLORS["fail"])
            self.s_usb.configure(text=(res.stderr or res.stdout or "Unknown error")[:120])
            self.v_count.configure(text="0")
            return

        self.v_count.configure(text=str(len(devices)))
        self.device_menu_map = {d.label: d for d in devices}
        if devices:
            self.device_menu.configure(values=list(self.device_menu_map))
            self.device_menu.set(devices[0].label)
            d = devices[0]
            level, msg = adb.STATE_HELP.get(d.state, ("warn", f"State: {d.state}"))
            self.v_usb.configure(text="Connected" if d.state == "device" else d.state.capitalize(),
                                 text_color=STATUS_COLORS[level])
            self.s_usb.configure(text=msg[:110])
            self.v_model.configure(text=d.details.get("model", "Unknown").replace("_", " "))
            self.s_model.configure(
                text="Android version dekhne ke liye scan chalayein" if d.state == "device"
                else "Authorize hone ke baad model/version dikhega")
            self.s_count.configure(text=f"{len(devices)} device(s) detected")
        else:
            self.device_menu.configure(values=["(koi device nahi)"])
            self.device_menu.set("(koi device nahi)")
            self.v_usb.configure(text="Phone nahi mila", text_color=STATUS_COLORS["warn"])
            self.s_usb.configure(text="Cable, USB mode, USB debugging aur driver check karein.")
            self.v_model.configure(text="-")
            self.s_model.configure(text="")
            self.s_count.configure(text="")

    def _selected_serial(self):
        d = self.device_menu_map.get(self.device_menu.get())
        return d.serial if d else None

    def start_scan(self):
        if self.busy:
            return
        if not self.adb_path:
            self._update_status_no_adb()
            messagebox.showwarning(APP_NAME, "Pehle ADB set karein (ADB Path Choose Karein).")
            return
        if not messagebox.askyesno("Owner ki permission", CONSENT_TEXT, icon="question"):
            self._set_progress(0, "Scan cancel kiya gaya (permission nahi mili).")
            return

        serial = self._selected_serial()
        self._set_busy(True)
        self._show_diag_placeholder("Scan chal raha hai...")

        def progress(frac, msg):
            self._ui(lambda: self._set_progress(frac, msg))

        def work():
            try:
                result = diag.run_scan(self.adb_path, serial, progress)
            except Exception as exc:  # koi bhi unexpected error clear message ke saath dikhao
                self._ui(lambda: self._scan_failed(exc))
                return
            self._ui(lambda: self._scan_done(result))

        threading.Thread(target=work, daemon=True).start()

    def _scan_failed(self, exc):
        self._set_busy(False)
        self._set_progress(0, "Scan fail hua.")
        self._show_diag_placeholder(f"Scan me unexpected error aaya: {exc}")
        messagebox.showerror(APP_NAME, f"Scan fail hua:\n{exc}")

    def _scan_done(self, r):
        self._set_busy(False)
        self.last_result = r
        self._render_checks(r.checks)
        self.s_scan.configure(text="")
        self.v_scan.configure(text=r.timestamp.strftime("%d %b, %H:%M"))
        issues = len(r.issues)
        self.s_scan.configure(text=f"{issues} issue(s) mile" if issues else "Koi issue nahi mila")
        self.v_count.configure(text=str(r.device_count))
        if r.model:
            self.v_model.configure(text=f"{r.manufacturer} {r.model}".strip())
            self.s_model.configure(text=f"Android {r.android_version}")
        if r.connection_state == "device":
            self.v_usb.configure(text="Connected", text_color=STATUS_COLORS["ok"])
        self._refresh_report_preview()

    def generate_report(self):
        if self.last_result is None:
            messagebox.showinfo(APP_NAME, "Report ke liye pehle 'Start Scan' chalayein. "
                                          "Bina scan ke report nahi banegi (koi fake data nahi).")
            return
        self.show_page("report")

    # ------------------------------------------------------------ Recovery
    def _build_recovery(self):
        page = ctk.CTkFrame(self.content, fg_color="transparent")
        page.grid_columnconfigure(0, weight=1)
        page.grid_rowconfigure(3, weight=1)

        ctk.CTkLabel(page, text="Official Screen-Lock Recovery Guide",
                     font=ctk.CTkFont(size=24, weight="bold")).grid(row=0, column=0, sticky="w")
        warn = ctk.CTkFrame(page, fg_color="#3a1f1f", corner_radius=10)
        warn.grid(row=1, column=0, sticky="ew", pady=10)
        ctk.CTkLabel(warn, text="⚠  " + "\n⚠  ".join(rec.GENERAL_WARNINGS), justify="left",
                     wraplength=820, text_color="#ffa198").pack(anchor="w", padx=14, pady=10)

        top = ctk.CTkFrame(page, fg_color="transparent")
        top.grid(row=2, column=0, sticky="ew")
        ctk.CTkLabel(top, text="Phone brand chunein:").pack(side="left", padx=(0, 8))
        self.brand_menu = ctk.CTkOptionMenu(top, values=["-- select --"] + rec.BRAND_NAMES, width=220,
                                            fg_color=CARD, button_color=BLUE, button_hover_color=BLUE_HOVER,
                                            command=self._on_brand)
        self.brand_menu.pack(side="left")

        self.brand_box = ctk.CTkScrollableFrame(page, fg_color=PANEL, corner_radius=12)
        self.brand_box.grid(row=3, column=0, sticky="nsew", pady=(10, 0))
        self._render_brand(None)
        return page

    def _on_brand(self, name):
        self._render_brand(name if name in rec.BRANDS else None)

    def _render_brand(self, name):
        for w in self.brand_box.winfo_children():
            w.destroy()
        if not name:
            ctk.CTkLabel(self.brand_box, text="Upar se apne phone ka brand chunein.",
                         text_color=TEXT_MUTED).pack(anchor="w", padx=14, pady=14)
            return
        data = rec.BRANDS[name]
        ctk.CTkLabel(self.brand_box, text=f"{name} - {data['account']}",
                     font=ctk.CTkFont(size=17, weight="bold"), text_color=BLUE_HOVER
                     ).pack(anchor="w", padx=14, pady=(12, 6))

        ctk.CTkLabel(self.brand_box, text="Sabse pehle (sab brands ke liye):",
                     font=ctk.CTkFont(weight="bold")).pack(anchor="w", padx=14)
        for i, s in enumerate(rec.COMMON_STEPS, 1):
            ctk.CTkLabel(self.brand_box, text=f"{i}. {s}", wraplength=760, justify="left"
                         ).pack(anchor="w", padx=24, pady=2)

        ctk.CTkLabel(self.brand_box, text=f"{name} ke official tareeke:",
                     font=ctk.CTkFont(weight="bold")).pack(anchor="w", padx=14, pady=(12, 0))
        for i, s in enumerate(data["steps"], 1):
            ctk.CTkLabel(self.brand_box, text=f"{i}. {s}", wraplength=760, justify="left"
                         ).pack(anchor="w", padx=24, pady=2)

        ctk.CTkLabel(self.brand_box, text="Official links (browser me khulenge):",
                     font=ctk.CTkFont(weight="bold")).pack(anchor="w", padx=14, pady=(12, 4))
        for label, url in data["links"]:
            ctk.CTkButton(self.brand_box, text=f"🌐  {label}", anchor="w", width=360, height=34,
                          fg_color=CARD, hover_color="#30363d",
                          command=lambda l=label, u=url: self._open_link(l, u)
                          ).pack(anchor="w", padx=24, pady=3)

        ctk.CTkLabel(
            self.brand_box,
            text="Note: Features/links model aur region ke hisaab se alag ho sakte hain. "
                 "Apne model ke liye company ke official page par confirm karein.",
            text_color=TEXT_MUTED, wraplength=760, justify="left",
        ).pack(anchor="w", padx=14, pady=(12, 14))

    def _open_link(self, label, url):
        if rec.link_may_erase(label):
            if not messagebox.askyesno(
                "Data erase warning",
                f"'{label}' wale page par aise options ho sakte hain jo phone ka DATA ERASE kar dete hain.\n\n"
                "Ye app kuch bhi erase nahi karta - sirf official website kholta hai. "
                "Website par koi bhi erase option dabane se pehle apna data/backup aur "
                "Google account details check kar lein.\n\nWebsite kholein?",
                icon="warning"):
                return
        webbrowser.open(url)

    # ------------------------------------------------------------ Report page
    def _build_report_page(self):
        page = ctk.CTkFrame(self.content, fg_color="transparent")
        page.grid_columnconfigure(0, weight=1)
        page.grid_rowconfigure(2, weight=1)
        ctk.CTkLabel(page, text="Repair Report", font=ctk.CTkFont(size=24, weight="bold")
                     ).grid(row=0, column=0, sticky="w")

        bar = ctk.CTkFrame(page, fg_color="transparent")
        bar.grid(row=1, column=0, sticky="ew", pady=10)
        ctk.CTkButton(bar, text="💾  Save as TXT", fg_color=BLUE, hover_color=BLUE_HOVER,
                      command=lambda: self._save("txt")).pack(side="left", padx=(0, 8))
        ctk.CTkButton(bar, text="💾  Save as CSV", fg_color="#30363d", hover_color="#484f58",
                      command=lambda: self._save("csv")).pack(side="left", padx=8)
        self.serial_var = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(bar, text="Masked serial (last 4 chars) report me shamil karein",
                        variable=self.serial_var, command=self._refresh_report_preview
                        ).pack(side="left", padx=16)

        self.report_box = ctk.CTkTextbox(page, fg_color=PANEL, font=ctk.CTkFont(family="Consolas", size=13),
                                         wrap="none")
        self.report_box.grid(row=2, column=0, sticky="nsew")
        self._refresh_report_preview()
        return page

    def _refresh_report_preview(self):
        if not hasattr(self, "report_box"):
            return
        self.report_box.configure(state="normal")
        self.report_box.delete("1.0", "end")
        if self.last_result is None:
            self.report_box.insert("1.0", "Abhi koi scan result nahi hai.\n\n"
                                          "Dashboard par 'Start Scan' chalayein - uske baad yahan report dikhegi.")
        else:
            self.report_box.insert("1.0", rpt.build_text(self.last_result, self.serial_var.get()))
        self.report_box.configure(state="disabled")

    def _save(self, kind):
        if self.last_result is None:
            messagebox.showinfo(APP_NAME, "Pehle scan chalayein - bina scan ke report save nahi hoti.")
            return
        stamp = self.last_result.timestamp.strftime("%Y%m%d_%H%M%S")
        path = filedialog.asksaveasfilename(
            defaultextension=f".{kind}", initialfile=f"repair_report_{stamp}.{kind}",
            filetypes=[(kind.upper(), f"*.{kind}")])
        if not path:
            return
        try:
            if kind == "txt":
                rpt.save_txt(self.last_result, path, self.serial_var.get())
            else:
                rpt.save_csv(self.last_result, path, self.serial_var.get())
            messagebox.showinfo(APP_NAME, f"Report save ho gayi:\n{path}")
        except OSError as exc:
            messagebox.showerror(APP_NAME, f"Report save nahi ho payi:\n{exc}")

    # ------------------------------------------------------------ Help
    def _build_help(self):
        page = ctk.CTkFrame(self.content, fg_color="transparent")
        page.grid_columnconfigure(0, weight=1)
        page.grid_rowconfigure(1, weight=1)
        ctk.CTkLabel(page, text="USB Connection Help", font=ctk.CTkFont(size=24, weight="bold")
                     ).grid(row=0, column=0, sticky="w", pady=(0, 8))
        box = ctk.CTkTextbox(page, fg_color=PANEL, wrap="word", font=ctk.CTkFont(size=13))
        box.grid(row=1, column=0, sticky="nsew")
        box.insert("1.0", HELP_TEXT)
        box.configure(state="disabled")
        return page


HELP_TEXT = """\
PHONE DETECT NAHI HO RAHA? ye steps follow karein:

1. Original USB DATA cable use karein (kuch sasti cables sirf charging ke liye hoti hain).
2. Laptop ka doosra USB port try karein (direct port, USB hub nahi).
3. Phone par USB notification se mode 'File Transfer / MTP' chunein.
4. Developer options ON karein:
   Settings -> About phone -> 'Build number' par 7 baar tap karein.
5. Settings -> Developer options -> 'USB debugging' ON karein.
6. Phone par 'Allow USB debugging?' popup aaye to (sirf agar ye aapka apna phone hai)
   'Allow' dabayein. 'Always allow from this computer' optional hai.
7. Is app me 'Refresh Devices' dabayein.

STATUS KA MATLAB:
  * device        -> sab theek, phone authorized hai.
  * unauthorized  -> phone ne permission nahi di. Popup check karein.
  * offline       -> cable nikaal ke dobara lagayein / USB debugging off-on karein.
  * Phone nahi    -> driver ya cable ki problem. Neeche driver section dekhein.

USB DRIVER (Windows):
  * Pehle Windows Update chalayein - zyada tar phones ke driver apne aap aa jaate hain.
  * Samsung: Samsung USB Driver (Samsung ki official site se).
  * Doosre brands: apni company ki official site se USB driver, ya 'Google USB Driver'
    (Android Studio SDK Manager ke through).
  * Device Manager (Win + X -> Device Manager) me yellow warning wala device dhoondhein ->
    right-click -> Update driver.

ADB INSTALL:
  * 'Android SDK Platform-Tools for Windows' official developer.android.com se download karein,
    zip extract karein (jaise C:\\platform-tools), phir Dashboard par 'ADB Path Choose Karein'
    dabake adb.exe select karein.

IMPORTANT:
  * Ye tool screen lock, PIN, pattern, password ya FRP bypass NAHI karta.
  * Screen lock bhool gaye hon to 'Screen-Lock Recovery' page par official tareeke dekhein.
"""


def main():
    app = App()
    app.mainloop()


if __name__ == "__main__":
    main()
