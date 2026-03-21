import streamlit as st
import uuid
import json
import os
import re
import base64
import unicodedata
import io
import csv
from datetime import datetime, timedelta
from urllib.parse import quote

st.set_page_config(
    page_title="WB Make-up & SFX",
    page_icon="🖤",
    layout="centered"
)

DB_FILE = "clients.json"
MAX_STAMPS = 5
MAX_CARDS_PER_SESSION = 3
SCANNER_LINK = "https://adampruchniak-a11y.github.io/WB-MAKEUP-SFX/"
ADMIN_LOGIN = "wiktoria"
ADMIN_PASSWORD = "WB2024!"

# Celowo bez Q, V, X oraz bez Ą, Ę, Ś itd. na początku
ALLOWED_START_LETTERS = set("ABCDEFGHIJKLMNOPRSTUWYZ")

BANNED_ROOTS = {
    "kurw", "chuj", "huj", "pizd", "jeb", "pierdol", "spierdal", "wypierdal",
    "skurw", "kutas", "fiut", "cipa", "szmat", "debil", "idiot",
    "fuck", "bitch", "asshole", "cunt", "nigg"
}

BANNED_EXACT = {
    "test", "spam", "admin", "administrator", "root", "xxx",
    "qwerty", "asdf", "abc", "aaaa", "bbbb", "cccc", "dupa"
}


# =========================
# Helpers
# =========================

def now_iso():
    return datetime.utcnow().replace(microsecond=0).isoformat()


def parse_iso(value):
    try:
        return datetime.fromisoformat(value)
    except Exception:
        return None


def normalize_spaces(value):
    return " ".join(str(value or "").strip().split())


def strip_accents(value):
    value = str(value or "")
    normalized = unicodedata.normalize("NFKD", value)
    return "".join(ch for ch in normalized if not unicodedata.combining(ch))


def format_name_case(value):
    clean = normalize_spaces(value).lower()
    if not clean:
        return ""

    parts = clean.split(" ")
    out = []

    for part in parts:
        subparts = part.split("-")
        formatted = [p[:1].upper() + p[1:] for p in subparts if p]
        out.append("-".join(formatted))

    return " ".join(out)


def full_name(first_name, last_name):
    return f"{format_name_case(first_name)} {format_name_case(last_name)}".strip()


def normalize_name_key(first_name, last_name):
    return full_name(first_name, last_name).lower()


def normalize_phone(phone):
    return re.sub(r"\D", "", str(phone or ""))


def normalize_for_filter(value):
    value = str(value or "")
    value = value.lower()
    value = strip_accents(value)

    replacements = str.maketrans({
        "0": "o",
        "1": "i",
        "3": "e",
        "4": "a",
        "5": "s",
        "7": "t",
        "@": "a",
        "$": "s",
        "!": "i"
    })

    value = value.translate(replacements)
    value = re.sub(r"[^a-z]", "", value)
    value = re.sub(r"(.)\1{1,}", r"\1", value)
    return value


def contains_banned_content(value):
    value = str(value or "")
    raw = normalize_spaces(value).lower()
    raw_ascii = strip_accents(raw)

    tokens = [t for t in re.split(r"[\s\-_\.]+", raw_ascii) if t]

    for token in tokens:
        if token in BANNED_EXACT:
            return True

    compact = normalize_for_filter(value)

    if compact in BANNED_EXACT:
        return True

    for root in BANNED_ROOTS:
        if root in compact:
            return True

    return False


def starts_with_allowed_letter(value):
    clean = normalize_spaces(value)
    if not clean:
        return False
    return clean[0].upper() in ALLOWED_START_LETTERS


def validate_personal_name(value, field_name):
    clean = normalize_spaces(value)

    if len(clean) < 2:
        return False, f"{field_name} musi mieć co najmniej 2 znaki."

    if len(clean) > 40:
        return False, f"{field_name} jest za długie."

    if re.search(r"\d", clean):
        return False, f"{field_name} nie może zawierać cyfr."

    if not re.fullmatch(r"[A-Za-zÀ-ÖØ-öø-ÿĄąĆćĘęŁłŃńÓóŚśŹźŻż \-]+", clean):
        return False, f"{field_name} może zawierać tylko litery, spacje i myślnik."

    if "--" in clean:
        return False, f"{field_name} ma nieprawidłowy format."

    if not starts_with_allowed_letter(clean):
        return False, f"{field_name} musi zaczynać się od zwykłej litery, np. A, B, C, D."

    if contains_banned_content(clean):
        return False, f"{field_name} zawiera niedozwolone słowo."

    return True, format_name_case(clean)


def validate_phone(phone):
    clean = normalize_spaces(phone)
    if not clean:
        return True, ""
    digits = normalize_phone(clean)
    if len(digits) < 9 or len(digits) > 15:
        return False, "Telefon ma nieprawidłowy format."
    return True, clean


def validate_email(email):
    clean = normalize_spaces(email).lower()
    if not clean:
        return True, ""
    if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", clean):
        return False, "E-mail ma nieprawidłowy format."
    return True, clean


def make_code():
    return str(uuid.uuid4())[:8].upper()


def logo_data_uri(path):
    if not os.path.exists(path):
        return ""
    with open(path, "rb") as f:
        encoded = base64.b64encode(f.read()).decode("utf-8")
    return f"data:image/png;base64,{encoded}"


def stamp_visual(stamps, max_stamps=MAX_STAMPS):
    stamps = max(0, min(max_stamps, int(stamps)))
    return ("●" * stamps) + ("○" * (max_stamps - stamps))


def add_history_event(client, event_type, by_user, note=""):
    client.setdefault("history", [])
    client["history"].insert(0, {
        "timestamp": now_iso(),
        "type": event_type,
        "by": by_user,
        "note": note
    })


# =========================
# Database
# =========================

def load_clients():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list):
                    return data
                return []
        except Exception:
            return []
    return []


def save_clients(data):
    try:
        with open(DB_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception:
        st.error("Błąd zapisu bazy klientek.")


def migrate_clients(clients):
    changed = False
    for c in clients:
        if "id" not in c:
            c["id"] = str(uuid.uuid4())
            changed = True
        if "first_name" not in c:
            c["first_name"] = ""
            changed = True
        if "last_name" not in c:
            c["last_name"] = ""
            changed = True
        if "name" not in c:
            c["name"] = full_name(c.get("first_name", ""), c.get("last_name", ""))
            changed = True
        if "phone" not in c:
            c["phone"] = ""
            changed = True
        if "email" not in c:
            c["email"] = ""
            changed = True
        if "code" not in c:
            c["code"] = make_code()
            changed = True
        if "stamps" not in c:
            c["stamps"] = 0
            changed = True
        if "reward_ready" not in c:
            c["reward_ready"] = c.get("stamps", 0) >= MAX_STAMPS
            changed = True
        if "active" not in c:
            c["active"] = True
            changed = True
        if "created_at" not in c:
            c["created_at"] = now_iso()
            changed = True
        if "history" not in c or not isinstance(c["history"], list):
            c["history"] = []
            changed = True

    if changed:
        save_clients(clients)
    return clients


clients = migrate_clients(load_clients())
if not isinstance(clients, list):
    clients = []


# =========================
# Find / search
# =========================

def find_existing_client(first_name, last_name, phone, email):
    name_key = normalize_name_key(first_name, last_name)
    phone_key = normalize_phone(phone)
    email_key = normalize_spaces(email).lower()

    for c in clients:
        if not c.get("active", True):
            continue

        c_name_key = normalize_name_key(c.get("first_name", ""), c.get("last_name", ""))
        c_phone_key = normalize_phone(c.get("phone", ""))
        c_email_key = normalize_spaces(c.get("email", "")).lower()

        if c_name_key == name_key:
            return c
        if phone_key and c_phone_key and phone_key == c_phone_key:
            return c
        if email_key and c_email_key and email_key == c_email_key:
            return c

    return None


def find_client_by_code(code):
    code = str(code or "").strip().upper()
    if code.startswith("WB-LOYALTY:"):
        code = code.replace("WB-LOYALTY:", "").strip().upper()

    for c in clients:
        if not c.get("active", True):
            continue
        if c.get("code", "").upper() == code:
            return c
    return None


def search_clients(phrase):
    phrase = normalize_spaces(phrase).lower()
    results = []

    for c in clients:
        if not c.get("active", True):
            continue

        name = full_name(c.get("first_name", ""), c.get("last_name", "")).lower()
        phone = normalize_spaces(c.get("phone", "")).lower()
        email = normalize_spaces(c.get("email", "")).lower()
        code = c.get("code", "").lower()

        haystack = " | ".join([name, phone, email, code])
        if phrase in haystack:
            results.append(c)

    return results


def get_stats():
    active_clients = [c for c in clients if c.get("active", True)]
    total = len(active_clients)

    by_stamps = {i: 0 for i in range(MAX_STAMPS + 1)}
    for c in active_clients:
        s = max(0, min(MAX_STAMPS, int(c.get("stamps", 0))))
        by_stamps[s] += 1

    month_start = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    week_ago = datetime.utcnow() - timedelta(days=7)

    new_this_month = 0
    stamps_last_7_days = 0

    for c in active_clients:
        created_at = parse_iso(c.get("created_at", ""))
        if created_at and created_at >= month_start:
            new_this_month += 1

        for h in c.get("history", []):
            ts = parse_iso(h.get("timestamp", ""))
            if ts and ts >= week_ago and h.get("type") == "stamp_added":
                stamps_last_7_days += 1

    return total, by_stamps, new_this_month, stamps_last_7_days


def make_csv():
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "id", "first_name", "last_name", "name", "phone", "email",
        "code", "stamps", "reward_ready", "active", "created_at"
    ])

    for c in clients:
        writer.writerow([
            c.get("id", ""),
            c.get("first_name", ""),
            c.get("last_name", ""),
            c.get("name", ""),
            c.get("phone", ""),
            c.get("email", ""),
            c.get("code", ""),
            c.get("stamps", 0),
            c.get("reward_ready", False),
            c.get("active", True),
            c.get("created_at", "")
        ])

    return output.getvalue()


# =========================
# Session / params
# =========================

if "last_client_id" not in st.session_state:
    st.session_state["last_client_id"] = None

if "selected_client_id" not in st.session_state:
    st.session_state["selected_client_id"] = None

if "created_cards_counter" not in st.session_state:
    st.session_state["created_cards_counter"] = 0

if "admin_logged_in" not in st.session_state:
    st.session_state["admin_logged_in"] = False

if "admin_user" not in st.session_state:
    st.session_state["admin_user"] = ""

if "scan_code" not in st.session_state:
    st.session_state["scan_code"] = ""

query = st.query_params
scanned_code = query.get("scan")
if scanned_code:
    st.session_state["scan_code"] = scanned_code
    scanned_client = find_client_by_code(scanned_code)
    if scanned_client:
        st.session_state["selected_client_id"] = scanned_client["id"]


# =========================
# UI styles
# =========================

logo_uri = logo_data_uri("logo.png")

st.markdown("""
<style>
html, body, [class*="css"] {
    font-family: Inter, Arial, sans-serif;
}
.stApp {
    background:
        radial-gradient(circle at top, rgba(194,156,76,0.10) 0%, rgba(0,0,0,0) 24%),
        linear-gradient(180deg, #020202 0%, #060606 50%, #0a0a0a 100%);
    color: #f4f4f4;
}
.block-container {
    max-width: 900px;
    padding-top: 0.8rem;
    padding-bottom: 2.8rem;
}
.stTabs [data-baseweb="tab-list"] {
    gap: 10px;
    margin-bottom: 14px;
    background: transparent;
}
.stTabs [data-baseweb="tab"] {
    background: #101010;
    border: 1px solid #1f1f1f;
    border-radius: 14px 14px 0 0;
    color: #d7d7d7;
    padding-left: 18px;
    padding-right: 18px;
    font-weight: 600;
}
.stTabs [aria-selected="true"] {
    background: #151515 !important;
    color: #f1d88e !important;
    border-color: #564118 !important;
}
.hero {
    margin: 0 0 10px 0;
    min-height: 100px;
    display: flex;
    align-items: center;
    justify-content: center;
}
.hero img {
    width: 220px;
    max-width: 74%;
    display: block;
    filter: drop-shadow(0 4px 14px rgba(194,156,76,0.14));
}
.panel-logo img {
    width: 170px;
    max-width: 64%;
}
.form-box {
    background: linear-gradient(180deg, rgba(10,10,10,0.98) 0%, rgba(6,6,6,0.98) 100%);
    border: 1px solid #232323;
    border-radius: 24px;
    padding: 18px;
    margin-top: 0;
    box-shadow:
        0 14px 34px rgba(0,0,0,0.32),
        inset 0 1px 0 rgba(255,255,255,0.02);
}
.card-box {
    background: linear-gradient(180deg, rgba(15,15,15,0.98) 0%, rgba(8,8,8,0.98) 100%);
    border: 1px solid #232323;
    border-radius: 24px;
    padding: 22px;
    margin-top: 18px;
    box-shadow:
        0 16px 40px rgba(0,0,0,0.36),
        inset 0 1px 0 rgba(255,255,255,0.02);
}
.client-name {
    font-size: 28px;
    font-weight: 800;
    margin-top: 6px;
    color: #ffffff;
}
.code-box {
    background: #121212;
    border: 1px solid #2d2d2d;
    border-radius: 16px;
    padding: 16px;
    text-align: center;
    font-size: 24px;
    font-weight: 800;
    letter-spacing: 2px;
    margin-top: 8px;
    margin-bottom: 18px;
    color: #f1d88e;
}
.muted {
    color: #9b9b9b;
    font-size: 14px;
}
.stamp-big {
    font-size: 28px;
    letter-spacing: 6px;
    margin-top: 8px;
    color: #f1d88e;
}
.search-box {
    background: #0b0b0b;
    border: 1px solid #1f1f1f;
    border-radius: 20px;
    padding: 18px;
    margin-top: 16px;
}
.section-title {
    font-size: 19px;
    font-weight: 700;
    margin-bottom: 6px;
    color: #f6f6f6;
}
.pro-note {
    background: linear-gradient(180deg, #111111 0%, #0d0d0d 100%);
    border: 1px solid #3b2f17;
    border-radius: 16px;
    padding: 14px 16px;
    margin-top: 10px;
    color: #ddd1a5;
}
.stTextInput label, .stSelectbox label {
    color: #dbdbdb !important;
    font-weight: 600 !important;
}
.stTextInput input {
    background: #0f0f0f !important;
    color: #ffffff !important;
    border: 1px solid #2a2a2a !important;
    border-radius: 16px !important;
    min-height: 52px !important;
}
.stTextInput input::placeholder {
    color: #666 !important;
}
.stSelectbox div[data-baseweb="select"] > div {
    background: #0f0f0f !important;
    border: 1px solid #2a2a2a !important;
    border-radius: 16px !important;
    color: #ffffff !important;
}
.stButton > button,
.stLinkButton > a,
.stDownloadButton > button {
    background: linear-gradient(180deg, #1a1a1a 0%, #111111 100%) !important;
    color: #f1d88e !important;
    border: 1px solid #58431a !important;
    border-radius: 16px !important;
    min-height: 50px;
    font-weight: 700 !important;
    box-shadow: 0 8px 20px rgba(0,0,0,0.22);
}
.stButton > button:hover,
.stLinkButton > a:hover,
.stDownloadButton > button:hover {
    background: linear-gradient(180deg, #232323 0%, #171717 100%) !important;
    border-color: #9a7626 !important;
    color: #ffe7a0 !important;
}
div[data-testid="stAlert"] {
    border-radius: 16px !important;
    border: 1px solid #2a2a2a !important;
}
.qr-wrap {
    display: flex;
    justify-content: center;
    margin-top: 14px;
}
.qr-wrap img {
    width: 180px;
    border-radius: 26px;
    display: block;
    box-shadow: 0 14px 34px rgba(0,0,0,0.40);
    border: 1px solid #2e2e2e;
    background: #ffffff;
    padding: 8px;
}
.qr-caption {
    text-align: center;
    color: #979797;
    margin-top: 10px;
    font-size: 14px;
}
.counter-text {
    margin-top: 10px;
    color: #9b9b9b;
    font-size: 14px;
}
.reward-banner {
    background: linear-gradient(180deg, rgba(194,156,76,0.18) 0%, rgba(117,89,25,0.16) 100%);
    border: 1px solid #7a5c1c;
    border-radius: 18px;
    padding: 14px 16px;
    margin-top: 16px;
    color: #ffe5a3;
    font-weight: 700;
    text-align: center;
}
.stat-box {
    background: #0c0c0c;
    border: 1px solid #1f1f1f;
    border-radius: 18px;
    padding: 18px;
    text-align: center;
}
.stat-big {
    font-size: 30px;
    font-weight: 800;
    color: #f1d88e;
}
.history-item {
    background: #0f0f0f;
    border: 1px solid #232323;
    border-radius: 16px;
    padding: 12px 14px;
    margin-bottom: 10px;
}
.small-label {
    color: #8f8f8f;
    font-size: 13px;
}
</style>
""", unsafe_allow_html=True)


# =========================
# Tabs
# =========================

tab1, tab2 = st.tabs(["🖤 Karta klientki", "🔒 Panel salonu"])

with tab1:
    if logo_uri:
        st.markdown(
            f'<div class="hero"><img src="{logo_uri}" alt="Logo"></div>',
            unsafe_allow_html=True
        )

    st.markdown('<div class="form-box">', unsafe_allow_html=True)
    with st.form("create_card_form"):
        col1, col2 = st.columns(2)
        with col1:
            first_name = st.text_input("Imię")
        with col2:
            last_name = st.text_input("Nazwisko")

        col3, col4 = st.columns(2)
        with col3:
            phone = st.text_input("Telefon (opcjonalnie)")
        with col4:
            email = st.text_input("E-mail (opcjonalnie)")

        submitted = st.form_submit_button("Wygeneruj kartę", use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)

    if submitted:
        if st.session_state["created_cards_counter"] >= MAX_CARDS_PER_SESSION:
            st.warning("Osiągnięto limit tworzenia kart w tej sesji.")
        else:
            ok_first, first_result = validate_personal_name(first_name, "Imię")
            ok_last, last_result = validate_personal_name(last_name, "Nazwisko")
            ok_phone, phone_result = validate_phone(phone)
            ok_email, email_result = validate_email(email)

            if not ok_first:
                st.error(first_result)
            elif not ok_last:
                st.error(last_result)
            elif not ok_phone:
                st.error(phone_result)
            elif not ok_email:
                st.error(email_result)
            else:
                full_candidate = f"{first_result} {last_result}"
                if contains_banned_content(full_candidate):
                    st.error("Imię i nazwisko zawiera niedozwolone słowo.")
                else:
                    existing = find_existing_client(first_result, last_result, phone_result, email_result)

                    if existing:
                        st.session_state["last_client_id"] = existing["id"]
                        st.warning("Ta klientka już istnieje w bazie. Pokazuję istniejącą kartę.")
                    else:
                        client = {
                            "id": str(uuid.uuid4()),
                            "first_name": first_result,
                            "last_name": last_result,
                            "name": full_name(first_result, last_result),
                            "phone": phone_result,
                            "email": email_result,
                            "code": make_code(),
                            "stamps": 0,
                            "reward_ready": False,
                            "active": True,
                            "created_at": now_iso(),
                            "history": []
                        }

                        while any(c.get("code") == client["code"] for c in clients):
                            client["code"] = make_code()

                        add_history_event(client, "created", "self-service", "Utworzono kartę klientki")
                        clients.append(client)
                        save_clients(clients)
                        st.session_state["last_client_id"] = client["id"]
                        st.session_state["created_cards_counter"] += 1
                        st.success("Karta została wygenerowana.")

    current = None
    if st.session_state["last_client_id"]:
        current = next((c for c in clients if c.get("id") == st.session_state["last_client_id"]), None)

    if current:
        client_name = full_name(current.get("first_name", ""), current.get("last_name", ""))
        qr_data = f"WB-LOYALTY:{current['code']}"
        qr_url = "https://api.qrserver.com/v1/create-qr-code/?size=320x320&data=" + quote(qr_data)

        st.markdown('<div class="card-box">', unsafe_allow_html=True)
        st.markdown('<div class="muted">Klientka</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="client-name">{client_name}</div>', unsafe_allow_html=True)

        if current.get("phone"):
            st.markdown(f'<div class="small-label" style="margin-top:8px;">Telefon: {current["phone"]}</div>', unsafe_allow_html=True)
        if current.get("email"):
            st.markdown(f'<div class="small-label">E-mail: {current["email"]}</div>', unsafe_allow_html=True)

        st.markdown('<div class="muted" style="margin-top: 18px;">Kod karty</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="code-box">{current["code"]}</div>', unsafe_allow_html=True)

        st.markdown('<div class="muted">Postęp</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="stamp-big">{stamp_visual(current["stamps"])}</div>', unsafe_allow_html=True)
        st.markdown(
            f'<div class="counter-text">{current["stamps"]} / {MAX_STAMPS} pieczątek</div>',
            unsafe_allow_html=True
        )

        if current.get("reward_ready"):
            st.markdown('<div class="reward-banner">🎁 Nagroda gotowa do odebrania</div>', unsafe_allow_html=True)

        st.markdown('</div>', unsafe_allow_html=True)

        st.markdown(
            f"""
            <div class="qr-wrap">
                <img src="{qr_url}" alt="QR">
            </div>
            <div class="qr-caption">Kod QR klientki</div>
            """,
            unsafe_allow_html=True
        )

with tab2:
    if logo_uri:
        st.markdown(
            f'<div class="hero panel-logo" style="min-height: 90px; margin-bottom: 10px;"><img src="{logo_uri}" alt="Logo"></div>',
            unsafe_allow_html=True
        )

    if not st.session_state["admin_logged_in"]:
        st.markdown('<div class="form-box">', unsafe_allow_html=True)
        login_input = st.text_input("Login", key="admin_login_input")
        password_input = st.text_input("Hasło", type="password", key="admin_password_input")

        if st.button("Zaloguj się", use_container_width=True):
            if login_input == ADMIN_LOGIN and password_input == ADMIN_PASSWORD:
                st.session_state["admin_logged_in"] = True
                st.session_state["admin_user"] = login_input
                st.success("Zalogowano do panelu salonu.")
                st.rerun()
            else:
                st.error("Nieprawidłowy login lub hasło.")
        st.markdown('</div>', unsafe_allow_html=True)

    if st.session_state["admin_logged_in"]:
        st.success(f"Zalogowano jako: {st.session_state['admin_user']}")

        col_a, col_b = st.columns([3, 1])
        with col_b:
            if st.button("🚪 Wyloguj", use_container_width=True):
                st.session_state["admin_logged_in"] = False
                st.session_state["admin_user"] = ""
                st.rerun()

        st.markdown(
            '<div class="pro-note"><strong>Skaner telefonu:</strong> otwórz skaner i zeskanuj kartę klientki.</div>',
            unsafe_allow_html=True
        )
        st.link_button("📷 Otwórz skaner", SCANNER_LINK, use_container_width=True)

        if st.session_state["scan_code"]:
            st.success(f"Zeskanowano kod: {st.session_state['scan_code']}")

        if st.button("✖ Wyczyść zeskanowany kod", use_container_width=True):
            st.session_state["scan_code"] = ""
            st.session_state["selected_client_id"] = None
            st.query_params.clear()
            st.rerun()

        st.markdown('<div class="search-box">', unsafe_allow_html=True)
        st.markdown('<div class="section-title">Szukaj klientki</div>', unsafe_allow_html=True)

        search_phrase = st.text_input(
            "Imię, nazwisko, telefon, e-mail lub kod",
            placeholder="Np. Julia / 501... / mail / kod",
            key="search_phrase"
        )

        if search_phrase.strip():
            results = search_clients(search_phrase)
            if results:
                options = {
                    f"{full_name(c.get('first_name', ''), c.get('last_name', ''))} — {c.get('phone', '') or c.get('code', '')}": c["id"]
                    for c in results
                }
                chosen_label = st.selectbox("Wybierz klientkę z listy", list(options.keys()), key="search_select")
                st.session_state["selected_client_id"] = options[chosen_label]
            else:
                st.warning("Brak klientek pasujących do wyszukiwania.")
        st.markdown('</div>', unsafe_allow_html=True)

        final_client = next((c for c in clients if c["id"] == st.session_state["selected_client_id"]), None) if st.session_state["selected_client_id"] else None

        if final_client:
            final_name = full_name(final_client.get("first_name", ""), final_client.get("last_name", ""))

            st.markdown('<div class="card-box">', unsafe_allow_html=True)
            st.markdown('<div class="muted">Klientka</div>', unsafe_allow_html=True)
            st.markdown(f'<div class="client-name">{final_name}</div>', unsafe_allow_html=True)

            if final_client.get("phone"):
                st.markdown(f'<div class="small-label" style="margin-top:8px;">Telefon: {final_client["phone"]}</div>', unsafe_allow_html=True)
            if final_client.get("email"):
                st.markdown(f'<div class="small-label">E-mail: {final_client["email"]}</div>', unsafe_allow_html=True)

            st.markdown('<div class="muted" style="margin-top: 18px;">Kod</div>', unsafe_allow_html=True)
            st.markdown(f'<div class="code-box">{final_client["code"]}</div>', unsafe_allow_html=True)

            st.markdown('<div class="muted">Pieczątki</div>', unsafe_allow_html=True)
            st.markdown(f'<div class="stamp-big">{stamp_visual(final_client["stamps"])}</div>', unsafe_allow_html=True)
            st.markdown(
                f'<div class="counter-text">{final_client["stamps"]} / {MAX_STAMPS}</div>',
                unsafe_allow_html=True
            )

            if final_client["reward_ready"]:
                st.markdown('<div class="reward-banner">🎁 Ta klientka ma gotową nagrodę</div>', unsafe_allow_html=True)

            st.markdown('</div>', unsafe_allow_html=True)

            confirm_stamp = st.checkbox("Potwierdzam dodanie pieczątki", key=f"confirm_stamp_{final_client['id']}")

            col1, col2, col3 = st.columns(3)

            with col1:
                if st.button("➕ Dodaj pieczątkę", use_container_width=True):
                    if not confirm_stamp:
                        st.warning("Zaznacz najpierw potwierdzenie dodania pieczątki.")
                    elif final_client["stamps"] < MAX_STAMPS:
                        final_client["stamps"] += 1
                        if final_client["stamps"] >= MAX_STAMPS:
                            final_client["reward_ready"] = True
                        add_history_event(
                            final_client,
                            "stamp_added",
                            st.session_state["admin_user"],
                            f"Dodano pieczątkę. Stan: {final_client['stamps']}/{MAX_STAMPS}"
                        )
                        save_clients(clients)
                        st.success("Dodano pieczątkę.")
                        st.rerun()
                    else:
                        st.warning("Klientka ma już komplet pieczątek.")

            with col2:
                if st.button("🎁 Reset nagrody", use_container_width=True):
                    final_client["stamps"] = 0
                    final_client["reward_ready"] = False
                    add_history_event(
                        final_client,
                        "reward_reset",
                        st.session_state["admin_user"],
                        "Rozliczono nagrodę i wyzerowano licznik"
                    )
                    save_clients(clients)
                    st.success("Nagroda rozliczona, licznik wyzerowany.")
                    st.rerun()

            with col3:
                if st.button("⏸ Dezaktywuj kartę", use_container_width=True):
                    final_client["active"] = False
                    add_history_event(
                        final_client,
                        "deactivated",
                        st.session_state["admin_user"],
                        "Dezaktywowano kartę"
                    )
                    save_clients(clients)
                    st.session_state["selected_client_id"] = None
                    st.success("Karta została dezaktywowana.")
                    st.rerun()

            with st.expander("✏️ Edytuj dane klientki"):
                edit_first = st.text_input("Imię", value=final_client.get("first_name", ""), key=f"edit_first_{final_client['id']}")
                edit_last = st.text_input("Nazwisko", value=final_client.get("last_name", ""), key=f"edit_last_{final_client['id']}")
                edit_phone = st.text_input("Telefon", value=final_client.get("phone", ""), key=f"edit_phone_{final_client['id']}")
                edit_email = st.text_input("E-mail", value=final_client.get("email", ""), key=f"edit_email_{final_client['id']}")

                if st.button("💾 Zapisz zmiany", key=f"save_edit_{final_client['id']}", use_container_width=True):
                    ok_first, first_result = validate_personal_name(edit_first, "Imię")
                    ok_last, last_result = validate_personal_name(edit_last, "Nazwisko")
                    ok_phone, phone_result = validate_phone(edit_phone)
                    ok_email, email_result = validate_email(edit_email)

                    if not ok_first:
                        st.error(first_result)
                    elif not ok_last:
                        st.error(last_result)
                    elif not ok_phone:
                        st.error(phone_result)
                    elif not ok_email:
                        st.error(email_result)
                    else:
                        final_client["first_name"] = first_result
                        final_client["last_name"] = last_result
                        final_client["name"] = full_name(first_result, last_result)
                        final_client["phone"] = phone_result
                        final_client["email"] = email_result
                        add_history_event(
                            final_client,
                            "edited",
                            st.session_state["admin_user"],
                            "Zmieniono dane klientki"
                        )
                        save_clients(clients)
                        st.success("Zapisano zmiany.")
                        st.rerun()

            with st.expander("🗑 Trwale usuń kartę"):
                confirm_delete = st.checkbox("Potwierdzam trwałe usunięcie", key=f"confirm_delete_{final_client['id']}")
                if st.button("Usuń trwale", key=f"hard_delete_{final_client['id']}", use_container_width=True):
                    if confirm_delete:
                        clients[:] = [c for c in clients if c["id"] != final_client["id"]]
                        save_clients(clients)
                        st.session_state["selected_client_id"] = None
                        if st.session_state.get("last_client_id") == final_client["id"]:
                            st.session_state["last_client_id"] = None
                        st.success("Karta została usunięta trwale.")
                        st.rerun()
                    else:
                        st.warning("Zaznacz najpierw potwierdzenie usunięcia.")

            with st.expander("🕘 Historia wizyt i zmian"):
                history = final_client.get("history", [])
                if history:
                    for event in history[:20]:
                        st.markdown(
                            f"""
                            <div class="history-item">
                                <div><strong>{event.get("type", "")}</strong></div>
                                <div class="small-label">Kiedy: {event.get("timestamp", "")}</div>
                                <div class="small-label">Kto: {event.get("by", "")}</div>
                                <div class="small-label">Opis: {event.get("note", "")}</div>
                            </div>
                            """,
                            unsafe_allow_html=True
                        )
                else:
                    st.info("Brak historii dla tej klientki.")

        total_clients, by_stamps, new_this_month, stamps_last_7_days = get_stats()

        st.markdown('<div class="card-box">', unsafe_allow_html=True)
        st.markdown('<div class="section-title">Statystyki salonu</div>', unsafe_allow_html=True)

        s1, s2, s3, s4 = st.columns(4)
        with s1:
            st.markdown(f'<div class="stat-box"><div class="small-label">Aktywne klientki</div><div class="stat-big">{total_clients}</div></div>', unsafe_allow_html=True)
        with s2:
            st.markdown(f'<div class="stat-box"><div class="small-label">Nowe w miesiącu</div><div class="stat-big">{new_this_month}</div></div>', unsafe_allow_html=True)
        with s3:
            st.markdown(f'<div class="stat-box"><div class="small-label">Pieczątki 7 dni</div><div class="stat-big">{stamps_last_7_days}</div></div>', unsafe_allow_html=True)
        with s4:
            st.markdown(f'<div class="stat-box"><div class="small-label">Nagrody gotowe</div><div class="stat-big">{by_stamps[MAX_STAMPS]}</div></div>', unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)

        cols = st.columns(MAX_STAMPS + 1)
        for i in range(MAX_STAMPS + 1):
            with cols[i]:
                st.markdown(
                    f'<div class="stat-box"><div class="small-label">{i} pieczątek</div><div class="stat-big">{by_stamps[i]}</div></div>',
                    unsafe_allow_html=True
                )

        st.markdown('</div>', unsafe_allow_html=True)

        csv_data = make_csv()
        st.download_button(
            "⬇️ Pobierz bazę klientek CSV",
            data=csv_data,
            file_name="klientki_wiktoria_betler.csv",
            mime="text/csv",
            use_container_width=True
        )