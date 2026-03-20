import streamlit as st
import uuid
import urllib.parse
import json
import os
import re
from datetime import datetime

st.set_page_config(
    page_title="WB Loyalty",
    page_icon="💄",
    layout="centered"
)

DB_FILE = "clients.json"
ADMIN_PIN = "1234"  # zmień później
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


def normalize_name(name: str) -> str:
    return " ".join(name.strip().lower().split())


def find_existing_client_by_name(clients, name):
    normalized = normalize_name(name)
    for client_id, data in clients.items():
        if normalize_name(data.get("name", "")) == normalized:
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
        if phrase in data.get("name", "").lower():
            results.append((client_id, data))
    return results


def stamp_visual(stamps, max_stamps=MAX_STAMPS):
    filled = "●" * stamps
    empty = "○" * (max_stamps - stamps)
    return filled + empty


def validate_client_name(name: str):
    clean = " ".join(name.strip().split())

    if len(clean) < 5:
        return False, "Podaj pełne imię i nazwisko."

    parts = clean.split(" ")
    if len(parts) < 2:
        return False, "Wpisz imię i nazwisko, nie samo jedno słowo."

    if any(len(p) < 2 for p in parts):
        return False, "Imię i nazwisko muszą mieć co najmniej po 2 znaki."

    if re.search(r"\d", clean):
        return False, "Imię i nazwisko nie może zawierać cyfr."

    if not re.fullmatch(r"[A-Za-zÀ-ÖØ-öø-ÿĄąĆćĘęŁłŃńÓóŚśŹźŻż \-]+", clean):
        return False, "Dozwolone są tylko litery, spacje i myślnik."

    banned_words = {
        "dupa", "test", "spam", "admin", "xxx", "abc", "qwerty", "dupa1", "dupa2"
    }
    lowered = clean.lower()
    if lowered in banned_words:
        return False, "Podaj prawdziwe imię i nazwisko."

    return True, clean


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
        name = st.text_input("Imię i nazwisko")
        website = st.text_input("Website", value="", help="Pole techniczne", label_visibility="collapsed")
        submitted = st.form_submit_button("Generuj kartę", use_container_width=True)

    if submitted:
        if website.strip():
            st.error("Nie udało się utworzyć karty.")
        elif st.session_state["created_cards_counter"] >= MAX_CARDS_PER_SESSION:
            st.warning("Osiągnięto limit tworzenia kart w tej sesji. Odśwież stronę później lub skontaktuj się z salonem.")
        else:
            is_valid, result = validate_client_name(name)

            if not is_valid:
                st.error(result)
            else:
                clean_name = result
                existing_client_id, existing_client = find_existing_client_by_name(clients, clean_name)

                if existing_client:
                    st.session_state["last_client_id"] = existing_client_id
                    st.warning("Ta klientka już istnieje w bazie. Pokazuję istniejącą kartę zamiast tworzyć nową.")
                else:
                    client_id = str(uuid.uuid4())
                    card_code = generate_card_code()

                    while any(c.get("code") == card_code for c in clients.values()):
                        card_code = generate_card_code()

                    clients[client_id] = {
                        "name": clean_name,
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
        qr_data = f"WB-LOYALTY:{client['code']}"
        qr_url = "https://api.qrserver.com/v1/create-qr-code/?size=320x320&data=" + urllib.parse.quote(qr_data)

        st.markdown('<div class="card-box">', unsafe_allow_html=True)
        st.markdown('<div class="muted">Klientka</div>', unsafe_allow_html=True)
        st.subheader(client["name"])

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
        '<div class="sub-text">Opcje Salonu.</div>',
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
                    f"{data['name']} — {data['code']}": client_id
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
        st.caption("Tu możesz użyć skanera USB. Klikasz w pole i skanujesz kod z telefonu klientki.")

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

        st.markdown('</div>', unsafe_allow_html=True)

        if selected_client_id:
            st.session_state["selected_client_id"] = selected_client_id

        final_client_id = st.session_state.get("selected_client_id")
        final_client = clients.get(final_client_id) if final_client_id in clients else None

        if final_client:
            st.markdown('<div class="card-box">', unsafe_allow_html=True)
            st.markdown('<div class="muted">Klientka</div>', unsafe_allow_html=True)
            st.subheader(final_client["name"])

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
