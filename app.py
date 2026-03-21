import streamlit as st
import uuid
import urllib.parse
import json
import os
import re
from datetime import datetime

st.set_page_config(
    page_title="WB Make-up & SFX",
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


def normalize_name(first_name: str, last_name: str) -> str:
    return f"{normalize_text(first_name)} {normalize_text(last_name)}".strip().lower()


def full_name(first_name: str, last_name: str) -> str:
    return f"{normalize_text(first_name)} {normalize_text(last_name)}".strip()


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

    return True, clean


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
admin_mode = query.get("admin")

if scanned_code and not st.session_state.get("scan_loaded"):
    st.session_state["scan_code"] = scanned_code
    st.session_state["scan_loaded"] = True
    scanned_client_id, scanned_client = find_client_by_code(clients, scanned_code)
    if scanned_client_id:
        st.session_state["selected_client_id"] = scanned_client_id

st.markdown("""
<style>
html, body, [class*="css"] {
    font-family: Inter, Arial, sans-serif;
}

.stApp {
    background: linear-gradient(180deg, #050505 0%, #090909 100%);
    color: #f5f5f5;
}

.block-container {
    max-width: 860px;
    padding-top: 2.2rem;
    padding-bottom: 3rem;
}

h1, h2, h3 {
    letter-spacing: -0.4px;
}

.main-title {
    font-size: 44px;
    font-weight: 800;
    margin-bottom: 6px;
    color: #ffffff;
}

.sub-text {
    color: #a3a3a3;
    margin-bottom: 26px;
    font-size: 16px;
}

.stTabs [data-baseweb="tab-list"] {
    gap: 10px;
    background: transparent;
}

.stTabs [data-baseweb="tab"] {
    background: #101010;
    border: 1px solid #1f1f1f;
    border-radius: 14px 14px 0 0;
    color: #d4d4d4;
    padding-left: 18px;
    padding-right: 18px;
}

.stTabs [aria-selected="true"] {
    background: #171717 !important;
    color: #ffffff !important;
    border-color: #2a2a2a !important;
}

.card-box {
    background: linear-gradient(180deg, #0a0a0a 0%, #111111 100%);
    border: 1px solid #202020;
    border-radius: 24px;
    padding: 28px;
    margin-top: 18px;
    box-shadow: 0 12px 40px rgba(0,0,0,0.35);
}

.code-box {
    background: #151515;
    border: 1px solid #242424;
    border-radius: 16px;
    padding: 16px;
    text-align: center;
    font-size: 24px;
    font-weight: 800;
    letter-spacing: 2px;
    margin-top: 8px;
    margin-bottom: 18px;
    color: #ffffff;
}

.muted {
    color: #8f8f8f;
    font-size: 14px;
}

.stamp-big {
    font-size: 30px;
    letter-spacing: 6px;
    margin-top: 8px;
    color: #f5f5f5;
}

.small-space {
    height: 14px;
}

.search-box {
    background: #0d0d0d;
    border: 1px solid #1e1e1e;
    border-radius: 20px;
    padding: 20px;
    margin-top: 16px;
}

.section-title {
    font-size: 20px;
    font-weight: 700;
    margin-bottom: 6px;
    color: #ffffff;
}

.pro-note {
    background: #111111;
    border: 1px solid #2a2a2a;
    border-radius: 16px;
    padding: 14px 16px;
    margin-top: 10px;
    color: #d4d4d4;
}

.stTextInput input {
    background: #111111 !important;
    color: #ffffff !important;
    border: 1px solid #2a2a2a !important;
    border-radius: 14px !important;
}

.stTextInput input::placeholder {
    color: #6f6f6f !important;
}

.stSelectbox div[data-baseweb="select"] > div {
    background: #111111 !important;
    border: 1px solid #2a2a2a !important;
    border-radius: 14px !important;
    color: #ffffff !important;
}

.stButton > button,
.stDownloadButton > button,
.stLinkButton > a {
    background: #111111 !important;
    color: #ffffff !important;
    border: 1px solid #2b2b2b !important;
    border-radius: 14px !important;
    min-height: 48px;
    font-weight: 700 !important;
}

.stButton > button:hover,
.stDownloadButton > button:hover,
.stLinkButton > a:hover {
    border-color: #4a4a4a !important;
    background: #181818 !important;
}

div[data-testid="stAlert"] {
    border-radius: 16px !important;
    border: 1px solid #2a2a2a !important;
}

.stSuccess {
    background: rgba(34,197,94,0.12) !important;
}

.stWarning {
    background: rgba(245,158,11,0.12) !important;
}

.stError {
    background: rgba(239,68,68,0.12) !important;
}

.stInfo {
    background: rgba(255,255,255,0.04) !important;
}

hr {
    border: none;
    border-top: 1px solid #202020;
    margin: 24px 0;
}
</style>
""", unsafe_allow_html=True)

tab1, tab2 = st.tabs(["🖤 Karta klientki", "🔒 Panel salonu "])

with tab1:
    st.markdown('<div class="main-title">WB Make-up & SFX</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="sub-text">Karta lojalnościowa klientki.</div>',
        unsafe_allow_html=True
    )

    with st.form("create_card_form"):
        col1, col2 = st.columns(2)
        with col1:
            first_name = st.text_input("Imię")
        with col2:
            last_name = st.text_input("Nazwisko")

        submitted = st.form_submit_button("Wygeneruj kartę", use_container_width=True)

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
        client_name = full_name(
            client.get("first_name", ""),
            client.get("last_name", "")
        )
        qr_data = f"WB-LOYALTY:{client['code']}"
        qr_url = "https://api.qrserver.com/v1/create-qr-code/?size=320x320&data=" + urllib.parse.quote(qr_data)

        st.markdown('<div class="card-box">', unsafe_allow_html=True)
        st.markdown('<div class="muted">Klientka</div>', unsafe_allow_html=True)
        st.subheader(client_name)

        st.markdown('<div class="small-space"></div>', unsafe_allow_html=True)
        st.markdown('<div class="muted">Kod karty</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="code-box">{client["code"]}</div>', unsafe_allow_html=True)

        st.markdown('<div class="muted">Status lojalnościowy</div>', unsafe_allow_html=True)
        st.markdown(
            f'<div class="stamp-big">{stamp_visual(client["stamps"])}</div>',
            unsafe_allow_html=True
        )
        st.caption(f'{client["stamps"]} / {MAX_STAMPS} pieczątek')

        if client["reward_ready"]:
            st.success("Nagroda gotowa do odebrania.")

        st.markdown('</div>', unsafe_allow_html=True)

        left, center, right = st.columns([1, 2, 1])
        with center:
            st.image(qr_url, caption="Kod QR klientki", use_container_width=True)

        st.info("Zapisz ten kod QR lub pokaż go przy kolejnej wizycie.")

with tab2:
    st.markdown('<div class="main-title" style="font-size:34px;">Panel salonu</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="sub-text">Obsługa kart klientek, skanowanie i pieczątki.</div>',
        unsafe_allow_html=True
    )

    pin = st.text_input("PIN salonu", type="password")

    if pin == ADMIN_PIN:
        st.success("Zalogowano do panelu salonu.")

        if scanned_code:
            st.success(f"Zeskanowano kod: {scanned_code}")

        st.markdown(
            '<div class="pro-note"><strong>Skaner telefonu:</strong> otwórz aparat i zeskanuj kartę klientki.</div>',
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
            placeholder="Np. Jan Kowalski",
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
            final_name = full_name(
                final_client.get("first_name", ""),
                final_client.get("last_name", "")
            )

            st.markdown('<div class="card-box">', unsafe_allow_html=True)
            st.markdown('<div class="muted">Klientka</div>', unsafe_allow_html=True)
            st.subheader(final_name)

            st.markdown('<div class="small-space"></div>', unsafe_allow_html=True)
            st.markdown('<div class="muted">Kod</div>', unsafe_allow_html=True)
            st.markdown(f'<div class="code-box">{final_client["code"]}</div>', unsafe_allow_html=True)

            st.markdown('<div class="muted">Pieczątki</div>', unsafe_allow_html=True)
            st.markdown(
                f'<div class="stamp-big">{stamp_visual(final_client["stamps"])}</div>',
                unsafe_allow_html=True
            )
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
                confirm_delete = st.checkbox(
                    "Potwierdź usunięcie",
                    key=f"confirm_delete_{final_client_id}"
                )
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
