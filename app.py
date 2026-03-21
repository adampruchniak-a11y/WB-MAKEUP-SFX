import streamlit as st
import uuid
import urllib.parse
import json
import os
import re
import base64
from datetime import datetime

st.set_page_config(
    page_title="Wiktoria Betler Makeup & SFX",
    page_icon="🖤",
    layout="centered"
)

DB_FILE = "clients.json"
ADMIN_PIN = "1234"
MAX_STAMPS = 5
MAX_CARDS_PER_SESSION = 3
SCANNER_LINK = "https://adampruchniak-a11y.github.io/WB-MAKEUP-SFX/"


def load_clients():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def save_clients(clients):
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(clients, f, ensure_ascii=False, indent=2)


def generate_card_code():
    return str(uuid.uuid4())[:8].upper()


def normalize_text(value: str) -> str:
    return " ".join(value.strip().split())


def format_name_case(value: str) -> str:
    clean = normalize_text(value).lower()
    if not clean:
        return ""
    parts = clean.split(" ")
    formatted_parts = []

    for part in parts:
        subparts = part.split("-")
        formatted_subparts = [p[:1].upper() + p[1:] for p in subparts if p]
        formatted_parts.append("-".join(formatted_subparts))

    return " ".join(formatted_parts)


def normalize_name(first_name: str, last_name: str) -> str:
    first = format_name_case(first_name)
    last = format_name_case(last_name)
    return f"{first} {last}".strip().lower()


def full_name(first_name: str, last_name: str) -> str:
    first = format_name_case(first_name)
    last = format_name_case(last_name)
    return f"{first} {last}".strip()


def find_existing_client(first_name, last_name, clients):
    target = normalize_name(first_name, last_name)
    for client_id, data in clients.items():
        existing = normalize_name(
            data.get("first_name", ""),
            data.get("last_name", "")
        )
        if existing == target:
            return client_id, data
    return None, None


def find_client_by_code(clients, code):
    code = code.strip().upper()
    if code.startswith("WB-LOYALTY:"):
        code = code.replace("WB-LOYALTY:", "").strip().upper()

    for client_id, data in clients.items():
        if data.get("code", "").upper() == code:
            return client_id, data
    return None, None


def search_clients_by_name(clients, phrase):
    phrase = phrase.strip().lower()
    results = []
    for client_id, data in clients.items():
        combined = full_name(
            data.get("first_name", ""),
            data.get("last_name", "")
        ).lower()
        if phrase in combined:
            results.append((client_id, data))
    return results


def stamp_visual(stamps, max_stamps=MAX_STAMPS):
    return ("●" * stamps) + ("○" * (max_stamps - stamps))


def validate_personal_name(value: str, field_name: str):
    clean = normalize_text(value)

    if len(clean) < 2:
        return False, f"{field_name} musi mieć co najmniej 2 znaki."

    if re.search(r"\d", clean):
        return False, f"{field_name} nie może zawierać cyfr."

    if not re.fullmatch(r"[A-Za-zÀ-ÖØ-öø-ÿĄąĆćĘęŁłŃńÓóŚśŹźŻż \-]+", clean):
        return False, f"{field_name} może zawierać tylko litery, spacje i myślnik."

    banned_words = {"dupa", "test", "spam", "admin", "xxx", "abc", "qwerty"}
    if clean.lower() in banned_words:
        return False, f"Podaj prawdziwe {field_name.lower()}."

    return True, format_name_case(clean)


def logo_data_uri(path: str) -> str:
    if not os.path.exists(path):
        return ""
    with open(path, "rb") as f:
        encoded = base64.b64encode(f.read()).decode("utf-8")
    return f"data:image/png;base64,{encoded}"


clients = load_clients()

if "last_client_id" not in st.session_state:
    st.session_state["last_client_id"] = None

if "selected_client_id" not in st.session_state:
    st.session_state["selected_client_id"] = None

if "created_cards_counter" not in st.session_state:
    st.session_state["created_cards_counter"] = 0

if "scan_loaded" not in st.session_state:
    st.session_state["scan_loaded"] = False

if "scan_code" not in st.session_state:
    st.session_state["scan_code"] = ""

query = st.query_params
scanned_code = query.get("scan")

if scanned_code and not st.session_state.get("scan_loaded"):
    st.session_state["scan_code"] = scanned_code
    st.session_state["scan_loaded"] = True
    scanned_client_id, scanned_client = find_client_by_code(clients, scanned_code)
    if scanned_client_id:
        st.session_state["selected_client_id"] = scanned_client_id

logo_uri = logo_data_uri("logo.png")

st.markdown("""
<style>
html, body, [class*="css"] {
    font-family: Inter, Arial, sans-serif;
}

.stApp {
    background:
        radial-gradient(circle at top, rgba(194,156,76,0.12) 0%, rgba(0,0,0,0) 28%),
        linear-gradient(180deg, #020202 0%, #060606 45%, #0a0a0a 100%);
    color: #f5f5f5;
}

.block-container {
    max-width: 820px;
    padding-top: 0.7rem;
    padding-bottom: 2.8rem;
}

.stTabs [data-baseweb="tab-list"] {
    gap: 10px;
    background: transparent;
    margin-bottom: 12px;
}

.stTabs [data-baseweb="tab"] {
    background: #0f0f0f;
    border: 1px solid #1f1f1f;
    border-radius: 14px 14px 0 0;
    color: #d8d8d8;
    padding-left: 18px;
    padding-right: 18px;
    font-weight: 600;
}

.stTabs [aria-selected="true"] {
    background: #151515 !important;
    color: #f5df9c !important;
    border-color: #4b3a15 !important;
}

.hero {
    margin: 6px 0 14px 0;
    border-radius: 28px;
    border: 1px solid #1b1b1b;
    background:
        radial-gradient(circle at center, rgba(185,145,63,0.10) 0%, rgba(0,0,0,0) 42%),
        linear-gradient(180deg, #080808 0%, #050505 100%);
    min-height: 170px;
    display: flex;
    align-items: center;
    justify-content: center;
    box-shadow:
        0 16px 40px rgba(0,0,0,0.38),
        inset 0 1px 0 rgba(255,255,255,0.02);
}

.hero img {
    width: 270px;
    max-width: 82%;
    display: block;
    filter: drop-shadow(0 3px 10px rgba(201, 166, 86, 0.10));
}

.form-box {
    background: linear-gradient(180deg, rgba(12,12,12,0.98) 0%, rgba(7,7,7,0.98) 100%);
    border: 1px solid #242424;
    border-radius: 24px;
    padding: 18px;
    margin-top: 4px;
    box-shadow:
        0 14px 34px rgba(0,0,0,0.34),
        inset 0 1px 0 rgba(255,255,255,0.02);
}

.card-box {
    background: linear-gradient(180deg, rgba(18,18,18,0.98) 0%, rgba(8,8,8,0.98) 100%);
    border: 1px solid #242424;
    border-radius: 24px;
    padding: 24px;
    margin-top: 18px;
    box-shadow:
        0 16px 40px rgba(0,0,0,0.40),
        inset 0 1px 0 rgba(255,255,255,0.02);
}

.code-box {
    background: #121212;
    border: 1px solid #2c2c2c;
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
    color: #979797;
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
    background: #0e0e0e !important;
    color: #ffffff !important;
    border: 1px solid #2a2a2a !important;
    border-radius: 16px !important;
    min-height: 52px !important;
}

.stTextInput input::placeholder {
    color: #666 !important;
}

.stSelectbox div[data-baseweb="select"] > div {
    background: #0e0e0e !important;
    border: 1px solid #2a2a2a !important;
    border-radius: 16px !important;
    color: #ffffff !important;
}

.stButton > button,
.stLinkButton > a {
    background: linear-gradient(180deg, #1a1a1a 0%, #111111 100%) !important;
    color: #f1d88e !important;
    border: 1px solid #58431a !important;
    border-radius: 16px !important;
    min-height: 50px;
    font-weight: 700 !important;
}

.stButton > button:hover,
.stLinkButton > a:hover {
    background: linear-gradient(180deg, #232323 0%, #171717 100%) !important;
    border-color: #9a7626 !important;
    color: #ffe7a0 !important;
}

div[data-testid="stAlert"] {
    border-radius: 16px !important;
    border: 1px solid #2a2a2a !important;
}

.qr-wrap {
    display:flex;
    justify-content:center;
    margin-top: 12px;
}

.qr-wrap img {
    width: 180px;
    border-radius: 26px;
    display:block;
    box-shadow: 0 14px 34px rgba(0,0,0,0.40);
    border: 1px solid #2f2f2f;
    background: #ffffff;
    padding: 8px;
}

.qr-caption {
    text-align:center;
    color:#989898;
    margin-top:10px;
    font-size:14px;
}
</style>
""", unsafe_allow_html=True)

tab1, tab2 = st.tabs(["🖤 Karta klientki", "🔒 Panel salonu"])

with tab1:
    if logo_uri:
        st.markdown(
            f"""
            <div class="hero">
                <img src="{logo_uri}" alt="Logo">
            </div>
            """,
            unsafe_allow_html=True
        )

    st.markdown('<div class="form-box">', unsafe_allow_html=True)

    with st.form("create_card_form"):
        col1, col2 = st.columns(2)
        with col1:
            first_name = st.text_input("Imię")
        with col2:
            last_name = st.text_input("Nazwisko")

        submitted = st.form_submit_button("Wygeneruj kartę", use_container_width=True)

    st.markdown('</div>', unsafe_allow_html=True)

    if submitted:
        if st.session_state["created_cards_counter"] >= MAX_CARDS_PER_SESSION:
            st.warning("Osiągnięto limit tworzenia kart w tej sesji.")
        else:
            ok_first, first_result = validate_personal_name(first_name, "Imię")
            ok_last, last_result = validate_personal_name(last_name, "Nazwisko")

            if not ok_first:
                st.error(first_result)
            elif not ok_last:
                st.error(last_result)
            else:
                existing_client_id, existing_client = find_existing_client(
                    first_result, last_result, clients
                )

                if existing_client:
                    st.session_state["last_client_id"] = existing_client_id
                    st.warning("Ta klientka już istnieje w bazie. Pokazuję istniejącą kartę.")
                else:
                    client_id = str(uuid.uuid4())
                    card_code = generate_card_code()

                    while any(c.get("code") == card_code for c in clients.values()):
                        card_code = generate_card_code()

                    clients[client_id] = {
                        "first_name": first_result,
                        "last_name": last_result,
                        "name": full_name(first_result, last_result),
                        "code": card_code,
                        "stamps": 0,
                        "reward_ready": False,
                        "created_at": datetime.utcnow().isoformat()
                    }
                    save_clients(clients)
                    st.session_state["last_client_id"] = client_id
                    st.session_state["created_cards_counter"] += 1
                    st.success("Karta została wygenerowana.")

    last_client_id = st.session_state.get("last_client_id")
    if last_client_id and last_client_id in clients:
        client = clients[last_client_id]
        client_name = full_name(client.get("first_name", ""), client.get("last_name", ""))
        qr_data = f"WB-LOYALTY:{client['code']}"
        qr_url = "https://api.qrserver.com/v1/create-qr-code/?size=320x320&data=" + urllib.parse.quote(qr_data)

        st.markdown('<div class="card-box">', unsafe_allow_html=True)
        st.markdown('<div class="muted">Klientka</div>', unsafe_allow_html=True)
        st.subheader(client_name)

        st.markdown('<div class="muted" style="margin-top: 12px;">Kod karty</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="code-box">{client["code"]}</div>', unsafe_allow_html=True)

        st.markdown('<div class="muted">Postęp</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="stamp-big">{stamp_visual(client["stamps"])}</div>', unsafe_allow_html=True)
        st.caption(f'{client["stamps"]} / {MAX_STAMPS} pieczątek')

        if client["reward_ready"]:
            st.success("Nagroda gotowa do odebrania.")

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
            f"""
            <div class="hero" style="min-height: 135px; margin-bottom: 14px;">
                <img src="{logo_uri}" alt="Logo" style="width: 220px; max-width: 74%;">
            </div>
            """,
            unsafe_allow_html=True
        )

    pin = st.text_input("PIN salonu", type="password")

    if pin == ADMIN_PIN:
        st.success("Zalogowano do panelu salonu.")

        if scanned_code:
            st.success(f"Zeskanowano kod: {scanned_code}")

        st.markdown(
            '<div class="pro-note"><strong>Skaner telefonu:</strong> otwórz skaner i zeskanuj kartę klientki.</div>',
            unsafe_allow_html=True
        )
        st.link_button("📷 Otwórz skaner", SCANNER_LINK, use_container_width=True)

        if st.button("✖ Wyczyść zeskanowany kod", use_container_width=True):
            st.session_state["scan_code"] = ""
            st.session_state["selected_client_id"] = None
            st.session_state["scan_loaded"] = False
            st.query_params.clear()
            st.rerun()

        st.markdown('<div class="search-box">', unsafe_allow_html=True)
        st.markdown('<div class="section-title">Szukaj po imieniu i nazwisku</div>', unsafe_allow_html=True)

        search_name = st.text_input(
            "Wpisz imię lub nazwisko",
            placeholder="Np. Julia Nowak",
            key="search_name"
        )

        if search_name.strip():
            results = search_clients_by_name(clients, search_name)
            if results:
                options = {
                    f"{full_name(data.get('first_name', ''), data.get('last_name', ''))} — {data['code']}": client_id
                    for client_id, data in results
                }
                chosen_label = st.selectbox(
                    "Wybierz klientkę z listy",
                    list(options.keys()),
                    key="name_select"
                )
                st.session_state["selected_client_id"] = options[chosen_label]
            else:
                st.warning("Brak klientek pasujących do wyszukiwania.")
        st.markdown('</div>', unsafe_allow_html=True)

        st.markdown('<div class="search-box">', unsafe_allow_html=True)
        st.markdown('<div class="section-title">Kod klientki</div>', unsafe_allow_html=True)

        scan_code = st.text_input(
            "Kod zeskanowany lub wpisany ręcznie",
            placeholder="Np. WB-LOYALTY:9B5E7076 albo samo 9B5E7076",
            key="scan_code"
        )

        if scan_code.strip():
            code_client_id, code_client = find_client_by_code(clients, scan_code)
            if code_client:
                st.session_state["selected_client_id"] = code_client_id
            elif len(scan_code.strip()) >= 8:
                st.warning("Nie znaleziono klientki o takim kodzie.")

        st.markdown('</div>', unsafe_allow_html=True)

        final_client_id = st.session_state.get("selected_client_id")
        final_client = clients.get(final_client_id) if final_client_id in clients else None

        if final_client:
            final_name = full_name(final_client.get("first_name", ""), final_client.get("last_name", ""))

            st.markdown('<div class="card-box">', unsafe_allow_html=True)
            st.markdown('<div class="muted">Klientka</div>', unsafe_allow_html=True)
            st.subheader(final_name)

            st.markdown('<div class="muted" style="margin-top: 12px;">Kod</div>', unsafe_allow_html=True)
            st.markdown(f'<div class="code-box">{final_client["code"]}</div>', unsafe_allow_html=True)

            st.markdown('<div class="muted">Pieczątki</div>', unsafe_allow_html=True)
            st.markdown(f'<div class="stamp-big">{stamp_visual(final_client["stamps"])}</div>', unsafe_allow_html=True)
            st.caption(f'{final_client["stamps"]} / {MAX_STAMPS}')

            if final_client["reward_ready"]:
                st.success("Ta klientka ma gotową nagrodę.")

            col1, col2, col3 = st.columns(3)

            with col1:
                if st.button("➕ Dodaj pieczątkę", use_container_width=True):
                    if final_client["stamps"] < MAX_STAMPS:
                        final_client["stamps"] += 1
                        if final_client["stamps"] >= MAX_STAMPS:
                            final_client["reward_ready"] = True
                        clients[final_client_id] = final_client
                        save_clients(clients)
                        st.success("Dodano pieczątkę.")
                        st.rerun()
                    else:
                        st.warning("Klientka ma już komplet pieczątek.")

            with col2:
                if st.button("🎁 Reset nagrody", use_container_width=True):
                    final_client["stamps"] = 0
                    final_client["reward_ready"] = False
                    clients[final_client_id] = final_client
                    save_clients(clients)
                    st.success("Nagroda rozliczona, licznik wyzerowany.")
                    st.rerun()

            with col3:
                confirm_delete = st.checkbox("Potwierdź usunięcie", key=f"confirm_delete_{final_client_id}")
                if st.button("🗑️ Usuń kartę", use_container_width=True):
                    if confirm_delete:
                        del clients[final_client_id]
                        save_clients(clients)
                        st.session_state["selected_client_id"] = None
                        if st.session_state.get("last_client_id") == final_client_id:
                            st.session_state["last_client_id"] = None
                        st.success("Karta została usunięta.")
                        st.rerun()
                    else:
                        st.warning("Zaznacz najpierw potwierdzenie usunięcia.")

            st.markdown('</div>', unsafe_allow_html=True)

    elif pin:
        st.error("Nieprawidłowy PIN.")
