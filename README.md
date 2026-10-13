# 🔧 Mitra Mobile Repair Assistant

Windows 10/11 ke liye ek beginner-friendly **Android Mobile Repair Assistant**.
USB se phone connect karke **read-only diagnostics** chalata hai aur screen-lock bhool jane par
**sirf official recovery tareeke** batata hai.

> ⚠️ **Ye tool kya NAHI karta:** screen lock / PIN / pattern / password crack ya bypass, FRP bypass,
> data extraction, phone me app install, ya koi destructive command. ADB se screen lock hataane ka
> koi claim nahi hai.

---

## 📁 Project files

| File | Kaam |
|---|---|
| `app.py` | Main GUI (CustomTkinter, dark + blue theme) |
| `adb_helper.py` | ADB find/run + **read-only allow-list** (baaki commands block) |
| `diagnostics.py` | Asli diagnostic checks (koi fake result nahi) |
| `recovery_data.py` | Brand-wise official recovery guide + official links |
| `report.py` | TXT / CSV report |
| `requirements.txt` | Python libraries |
| `run_app.bat` | App chalane ke liye double-click |
| `build_exe.bat` | EXE banane ke liye |
| `tests/` | Unit tests + GUI smoke test (fake adb ke saath) |

---

## 1️⃣ Windows par Installation (Step by Step)

### Step 1: Python 3 install karein
1. https://www.python.org/downloads/windows/ se Python 3.10+ (64-bit) download karein.
2. Installer kholein aur **"Add python.exe to PATH"** ✅ tick karein, phir **Install Now**.
3. Check: `Win + R` → `cmd` → likhein: `python --version`

### Step 2: Project folder aur libraries
`MitraRepairAssistant` folder ko kahin extract karein (jaise `C:\MitraRepairAssistant`). Phir Command Prompt me:

```bat
cd C:\MitraRepairAssistant
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

### Step 3: Android Platform-Tools (ADB) install karein
1. Official page kholein: https://developer.android.com/tools/releases/platform-tools
2. **"Download SDK Platform-Tools for Windows"** par click karke zip download karein.
3. Zip ko extract karein, jaise `C:\platform-tools` (andar `adb.exe` hona chahiye).
4. Do tareeke (koi ek):
   * **Aasaan:** app kholein → Dashboard par **"ADB Path Choose Karein"** → `C:\platform-tools\adb.exe` select karein.
   * Ya `platform-tools` folder ko project folder ke andar rakh dein (`MitraRepairAssistant\platform-tools\adb.exe`) - app khud dhoondh legi.
5. Check (optional): `C:\platform-tools\adb.exe version`

> Agar ADB nahi mili, app crash nahi hoti - Dashboard par saaf message dikhata hai.

---

## 2️⃣ App chalana

```bat
cd C:\MitraRepairAssistant
venv\Scripts\activate
python app.py
```
Ya `run_app.bat` par double-click karein.

---

## 3️⃣ Phone ko USB se connect karna (sirf apna phone)

1. **Original data cable** lagayein (sirf-charging cable kaam nahi karegi).
2. Phone par USB mode: **File Transfer (MTP)**.
3. **Developer options ON:** Settings → About phone → *Build number* par 7 baar tap.
4. Settings → Developer options → **USB debugging ON**.
5. Phone par **"Allow USB debugging?"** popup aaye to (owner khud) **Allow** dabaye.
6. App me **Refresh Devices** dabayein.

### USB Troubleshooting
| Problem | Solution |
|---|---|
| "Phone nahi mila" | Doosri cable / doosra USB port (hub nahi), MTP mode, USB debugging ON, laptop restart |
| `unauthorized` | Phone unlock karke popup me Allow karein. Popup na aaye: Developer options → *Revoke USB debugging authorizations* → cable nikaal ke dobara lagayein |
| `offline` | Cable nikaal ke lagayein, USB debugging off/on, phone restart; `adb kill-server` phir `adb start-server` |
| Device Manager me yellow ⚠ | Right-click → Update driver. Samsung: official Samsung USB driver. Baaki: apni company ka USB driver ya Google USB Driver |
| Pehle chalta tha, ab nahi | Windows Update, driver reinstall, antivirus ne `adb.exe` block to nahi kiya |

---

## 4️⃣ App kaise use karein

* **Dashboard:** USB status, device count, model, last scan. **Start Scan** dabane par pehle **owner ki permission dialog** aata hai jisme har command explain hoti hai. Cancel karne par kuch nahi chalta.
* **Screen-Lock Recovery:** brand chunein (Samsung, Xiaomi, Redmi, Vivo, Oppo, Realme, Motorola, Google Pixel) → official steps + official links. Data-erase se judi pages kholne se pehle confirmation aata hai.
* **Repair Report:** scan ke baad hi report banti hai (bina scan ke nahi). TXT ya CSV me save karein. Serial number by default report me **nahi** hota; tick karne par sirf last 4 characters.

### Scan me kya check hota hai (sab read-only)
`adb version` · `adb devices -l` · `getprop` (model, Android version, security patch) ·
`dumpsys battery` · `wm size` · `df /data` · Windows USB driver errors (read-only).

---

## 5️⃣ Apna phone use karke verify kaise karein

1. Apne Android phone par USB debugging ON karke connect karein.
2. **Refresh Devices** → count `1` aur status `Connected` ya `Unauthorized` aana chahiye.
3. Phone par popup **Allow** karne se pehle: status `unauthorized` dikhna chahiye (ye sahi behaviour hai - tool bypass nahi karta).
4. Allow karne ke baad Start Scan → permission dialog → model aur Android version **wahi hone chahiye jo phone ke Settings → About phone me hain**.
5. Battery % ko phone ke battery % se milayein.
6. Cable nikaal ke scan karein → "Koi device detect nahi hua" aana chahiye (fake success nahi).
7. ADB path galat karke (ya platform-tools rename karke) app kholein → "ADB nahi mili" message aana chahiye, crash nahi.
8. Report TXT/CSV save karke kholein: PIN/password/Google account/contacts/photos kuch nahi hona chahiye.

**Developer tests (bina phone ke):**
```bat
python -m unittest discover -s tests -v
```

---

## 6️⃣ Windows EXE banana (PyInstaller)

Simple: `build_exe.bat` par double-click. Ya manually:

```bat
venv\Scripts\activate
pip install -r requirements.txt
for /f "delims=" %i in ('python -c "import customtkinter, os; print(os.path.dirname(customtkinter.__file__))"') do set CTK=%i
python -m PyInstaller --noconfirm --clean --onefile --windowed --name MitraMobileRepairAssistant --add-data "%CTK%;customtkinter" app.py
```

Output: `dist\MitraMobileRepairAssistant.exe`.
`platform-tools` folder ko EXE ke bagal me rakhein: `dist\platform-tools\adb.exe`
(ya app me **ADB Path Choose Karein** use karein).

---

## 🔒 Security & Privacy

* Owner ki permission ke bina scan shuru nahi hota.
* `adb_helper.py` me sirf allow-listed read-only commands; baaki (`install`, `pull`, `reboot`, `input`, `settings put`, `wipe` ...) `ValueError` se block (tests me verified).
* PIN, password, Google credentials, photos, contacts, messages - kuch collect nahi hota.
* Config me sirf ADB ka path save hota hai (`%APPDATA%\MitraRepairAssistant\config.json`).
* App phone me kuch install nahi karta aur kuch erase nahi karta.

## ⚠️ Zaroori baatein
* Recovery links company ke official sites ke hain, par **links/features model aur region ke hisaab se badalte rehte hain** - use karne se pehle confirm karein (khaaskar Motorola/OPPO/vivo links).
* Factory reset se data erase ho sakta hai aur reset ke baad original Google account ki zaroorat padti hai.
* Sirf apne ya authorized ownership wale phones par use karein.
