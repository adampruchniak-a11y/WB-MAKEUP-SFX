import streamlit as st
import uuid
import urllib.parse
import json
import os
import re
from datetime import datetime
import numpy as np
from PIL import Image
import cv2

st.set_page_config(
    page_title="WB Loyalty",
    page_icon="💄",
    layout="centered"
)

DB_FILE = "clients.json"
ADMIN_PIN = "1234"
MAX_STAMPS = 5
MAX_CARDS_PER_SESSION = 3


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


def parse_scanned_qr(raw_value: str):
    if not raw_value:
        return None
    raw_value = raw_value.strip()
    if raw_value.startswith("WB-LOYALTY:"):
        return raw_value.replace("WB-LOYALTY:", "").strip().upper()
    return raw_value.upper()


def decode_qr_from_uploaded_image(uploaded_file):
    if uploaded_file is None:
        return None

    try:
        image = Image.open(uploaded_file).convert("RGB")
        image_np = np.array(image)
        image_bgr = cv2.cvtColor(image_np, cv2.COLOR_RGB2BGR)

        detector = cv2.QRCodeDetector()
        value, points, _ = detector.detectAndDecode(image_bgr)

        if value:
            return parse_scanned_qr(value)
        return None
    except Exception:
        return None


clients = load_clients()

if "last_client_id" not in st.session_state:
    st.session_state["last_client_id"] = None

if "selected_client_id" not in st.session_state:
    st.session_state["selected_client_id"] = None

if "created_cards_counter" not in st.session_state:
    st.session_state["created_cards_counter"] = 0

st.markdown("""
<style>
.block-container {
    max-width: 820px;
    padding-top: 2rem;
    padding-bottom: 3rem;
}
.main-title {
    font-size: 42px;
    font-weight: 800;
    margin-bottom: 6px;
}
.sub-text {
    opacity: 0.82;
    margin-bottom: 24px;
}
.card-box {
    background: linear-gradient(180deg, #0f172a 0%, #111827 100%);
    border: 1px solid rgba(255,255,255,0.08);
    border-radius: 22px;
    padding: 26px;
    margin-top: 18px;
    box-shadow: 0 10px 30px rgba(0,0,0,0.25);
}
.code-box {
    background: rgba(255,255,255,0.06);
    border-radius: 14px;
    padding: 14px 16px;
    text-align: center;
    font-size: 24px;
    font-weight: 800;
    letter-spacing: 1.5px;
    margin-top: 8px;
    margin-bottom: 18px;
}
.muted {
    opacity: 0.72;
    font-size: 14px;
}
.stamp-big {
    font-size: 28px;
    letter-spacing: 4px;
    margin-top: 6px;
}
.small-space {
    height: 14px;
}
.search-box {
    background: rgba(255,255,255,0.03);
    border: 1px solid rgba(255,255,255,0.06);
    border-radius: 18px;
    padding: 18px;
    margin-top: 16px;
}
.section-title {
    font-size: 20px;
    font-weight: 700;
    margin-bottom: 6px;
}
</style>
""", unsafe_allow_html=True)

tab1, tab2 = st.tabs(["💄 Karta klientki", "🔒 Panel salonu"])

with tab1:
    st.markdown('<div class="main-title">Karta lojalnościowa</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="sub-text">Wpisz imię i nazwisko, aby wygenerować kartę klientki.</div>',
        unsafe_allow_html=True
    )

    with st.form("create_card_form"):
        col1, col2 = st.columns(2)
        with col1:
            first_name = st.text_input("Imię")
        with col2:
            last_name = st.text_input("Nazwisko")

        submitted = st.form_submit_button("Generuj kartę", use_container_width=True)

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
                    st.warning("Ta klientka już istnieje w bazie. Pokazuję istniejącą kartę zamiast tworzyć nową.")
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

        st.markdown('<div class="muted">Postęp</div>', unsafe_allow_html=True)
        st.markdown(
            f'<div class="stamp-big">{stamp_visual(client["stamps"])}</div>',
            unsafe_allow_html=True
        )
        st.caption(f'{client["stamps"]} / {MAX_STAMPS} pieczątek')

        if client["reward_ready"]:
            st.success("Gotowe 🎉 Klientka ma już nagrodę do odebrania.")

        st.markdown('</div>', unsafe_allow_html=True)

        left, center, right = st.columns([1, 2, 1])
        with center:
            st.image(qr_url, caption="Twój kod QR", use_container_width=True)

        st.info("Zapisz ten kod QR lub pokaż go przy kolejnej wizycie.")

with tab2:
    st.markdown('<div class="main-title" style="font-size:34px;">Panel salonu</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="sub-text">Tutaj Wiktoria może wyszukać klientkę po nazwisku, wpisać kod ręcznie albo zeskanować go aparatem.</div>',
        unsafe_allow_html=True
    )

    pin = st.text_input("PIN salonu", type="password")

    if pin == ADMIN_PIN:
        st.success("Zalogowano do panelu salonu.")

        st.markdown('<div class="search-box">', unsafe_allow_html=True)
        st.markdown('<div class="section-title">Szukaj po imieniu i nazwisku</div>', unsafe_allow_html=True)
        search_name = st.text_input(
            "Wpisz imię lub nazwisko",
            placeholder="Np. Wiktoria Betler",
            key="search_name"
        )

        selected_client_id = None

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
                selected_client_id = options[chosen_label]
            else:
                st.warning("Brak klientek pasujących do wyszukiwania.")
        st.markdown('</div>', unsafe_allow_html=True)

        st.markdown('<div class="search-box">', unsafe_allow_html=True)
        st.markdown('<div class="section-title">Skanuj / wpisz kod karty</div>', unsafe_allow_html=True)

        scan_code = st.text_input(
            "Kod zeskanowany ze skanera lub wpisany ręcznie",
            placeholder="Np. 9B5E7076",
            key="scan_code"
        )

        if st.button("Znajdź po kodzie", use_container_width=True):
            code_client_id, code_client = find_client_by_code(clients, scan_code)
            if code_client:
                st.session_state["selected_client_id"] = code_client_id
            else:
                st.warning("Nie znaleziono klientki o takim kodzie.")

        st.markdown("---")
        st.markdown("**📷 Zeskanuj aparatem**")
        photo = st.camera_input("Zrób zdjęcie kodu QR klientki")

        if photo is not None:
            scanned_code = decode_qr_from_uploaded_image(photo)
            if scanned_code:
                code_client_id, code_client = find_client_by_code(clients, scanned_code)
                if code_client:
                    st.session_state["selected_client_id"] = code_client_id
                    st.success(f"Zeskanowano kartę: {code_client['name']}")
                else:
                    st.warning(f"Odczytano kod QR, ale nie znaleziono klientki: {scanned_code}")
            else:
                st.warning("Nie udało się odczytać kodu QR z tego zdjęcia.")

        st.markdown('</div>', unsafe_allow_html=True)

        if selected_client_id:
            st.session_state["selected_client_id"] = selected_client_id

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

            st.markdown('</div>', unsafe_allow_html=True)

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
    elif pin:
        st.error("Nieprawidłowy PIN.")
