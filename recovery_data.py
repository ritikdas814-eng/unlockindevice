"""
recovery_data.py - Official screen-lock recovery guide (sirf official tareeke).

Is app me koi lock bypass / FRP bypass / PIN-pattern cracking nahi hai.
Links har company ke official support pages ke hain. Company links/features
model aur region ke hisaab se badal sakte hain - isliye guide me hamesha
'apne model ke official support page par confirm karein' likha hai.
"""

GENERAL_WARNINGS = [
    "FACTORY RESET se phone ka local data (photos, apps, files) ERASE ho sakta hai.",
    "Reset ke baad phone me PEHLE WALA Google account (aur brand account) dobara login karna pad sakta hai "
    "(Factory Reset Protection). Account ka email/password yaad hona zaroori hai.",
    "Ye tool ADB se screen lock hata NAHI sakta, aur aisa koi claim nahi karta. "
    "Sirf phone ke asli owner ko official tareeke se recover karna chahiye.",
    "Phone ki ownership ka proof (purchase bill, box, IMEI) service center par saath rakhein.",
]

COMMON_STEPS = [
    "Pehle apna lock yaad karne ki koshish karein (purane PIN/pattern/password, family ke log jo set karte the).",
    "Google account recovery try karein: apne Google account ka password recover kar sakte hain "
    "(ye phone ka lock nahi hataata, par account access wapas deta hai).",
    "Brand ka official account / 'Find my phone' service check karein (neeche brand section me).",
    "Agar upar ke tareeke na chalein to company ke AUTHORIZED service center jayein, "
    "bill + ID proof ke saath.",
]

BRANDS = {
    "Samsung": {
        "account": "Samsung account / Find My Mobile",
        "steps": [
            "Agar phone me pehle se Samsung account logged-in tha aur 'Remote controls' ON tha, "
            "to Find My Mobile website par login karke official 'Unlock' option check karein.",
            "Samsung account ka password bhool gaye hon to Samsung account recovery page use karein.",
            "Option na mile ya model support na kare to Samsung authorized service center se sampark karein.",
            "Reset ki zaroorat pade to pehle apna backup (agar available ho) aur Google/Samsung account "
            "credentials ready rakhein.",
        ],
        "links": [
            ("Samsung Find My Mobile", "https://findmymobile.samsung.com"),
            ("Samsung India Support", "https://www.samsung.com/in/support/"),
            ("Samsung Account", "https://account.samsung.com"),
        ],
    },
    "Xiaomi": {
        "account": "Mi Account / Xiaomi Cloud / Find Device",
        "steps": [
            "Mi Account login ho to Xiaomi Cloud ke official 'Find Device' options check karein.",
            "Mi Account ka password bhool gaye hon to account.xiaomi.com par official recovery use karein.",
            "Reset ke baad Mi Account aur Google account verification maanga ja sakta hai.",
            "Nazdiki Mi Service Center par bill aur ID proof ke saath jayein.",
        ],
        "links": [
            ("Xiaomi Account", "https://account.xiaomi.com"),
            ("Xiaomi India Support", "https://www.mi.com/in/support/"),
        ],
    },
    "Redmi": {
        "account": "Mi Account / Xiaomi Cloud / Find Device",
        "steps": [
            "Redmi phones Xiaomi ke hi hain - Mi Account aur Xiaomi Cloud ke official options check karein.",
            "Mi Account ka password bhool gaye hon to account.xiaomi.com par official recovery use karein.",
            "Reset ke baad Mi Account aur Google account verification maanga ja sakta hai.",
            "Nazdiki Mi/Redmi Service Center par bill aur ID proof ke saath jayein.",
        ],
        "links": [
            ("Xiaomi Account", "https://account.xiaomi.com"),
            ("Xiaomi India Support", "https://www.mi.com/in/support/"),
        ],
    },
    "Vivo": {
        "account": "vivo account / Google account",
        "steps": [
            "vivo official support page par apne model ke liye 'forgot screen lock' guidance dekhein.",
            "Google account recovery se account access wapas lein (agar phone me Google account tha).",
            "Zyada tar cases me vivo authorized service center par ownership proof dikhana padta hai.",
            "Reset ke baad original Google account ki zaroorat pad sakti hai.",
        ],
        "links": [
            ("vivo India Support", "https://www.vivo.com/in/support"),
        ],
    },
    "Oppo": {
        "account": "OPPO / HeyTap account (model par depend)",
        "steps": [
            "OPPO support page par apne model ke liye official screen-lock guidance dekhein.",
            "Agar aapke model par official 'Find my phone' / cloud service enabled thi, to usse account "
            "se recovery options check karein (sab models par available nahi hota).",
            "Nahi chale to OPPO authorized service center jayein (bill + ID proof ke saath).",
            "Reset ke baad original Google account ki zaroorat pad sakti hai.",
        ],
        "links": [
            ("OPPO India Support", "https://support.oppo.com/in/"),
        ],
    },
    "Realme": {
        "account": "realme account / Google account",
        "steps": [
            "realme support page par apne model ke liye official guidance dekhein.",
            "Google account recovery se account access wapas lein.",
            "realme authorized service center par bill + ID proof ke saath jayein.",
            "Reset ke baad original Google account ki zaroorat pad sakti hai.",
        ],
        "links": [
            ("realme India Support", "https://www.realme.com/in/support"),
        ],
    },
    "Motorola": {
        "account": "Motorola support / Google account",
        "steps": [
            "Motorola support page par apne model ke liye official software-repair/unlock guidance dekhein "
            "(Motorola ka official 'Rescue and Smart Assistant' tool software repair ke liye hai - "
            "isse DATA ERASE ho sakta hai).",
            "Google account recovery se account access wapas lein.",
            "Motorola authorized service center par bill + ID proof ke saath jayein.",
            "Reset ke baad original Google account ki zaroorat pad sakti hai.",
        ],
        "links": [
            ("Motorola India Support", "https://www.motorola.in/support"),
        ],
    },
    "Google Pixel": {
        "account": "Google account / Google Find Hub (Find My Device)",
        "steps": [
            "Google Find Hub (pehle Find My Device) me apne Google account se login karke official "
            "options dekhein. Dhyan rahe: 'Erase device' option phone ka data ERASE kar deta hai.",
            "Google account ka password bhool gaye hon to Google account recovery use karein.",
            "Reset ke baad wahi Google account se phone setup karna padega.",
            "Pixel Help / authorized repair center se sampark karein.",
        ],
        "links": [
            ("Google Find Hub (Find My Device)", "https://www.google.com/android/find"),
            ("Google Account Recovery", "https://accounts.google.com/signin/recovery"),
            ("Pixel Phone Help", "https://support.google.com/pixelphone"),
        ],
    },
}

BRAND_NAMES = list(BRANDS.keys())

# Ye links 'data erase' wale process se related ho sakte hain -> confirmation dialog ke saath khulte hain.
ERASE_RELATED_LINK_KEYWORDS = ("find", "rescue", "erase")


def link_may_erase(label: str) -> bool:
    return any(k in label.lower() for k in ERASE_RELATED_LINK_KEYWORDS)
