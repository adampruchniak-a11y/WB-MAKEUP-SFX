import streamlit as st
import uuid
import urllib.parse
import json
import os
from datetime import datetime

st.set_page_config(
    page_title="WB Loyalty",
    page_icon="💄",
    layout="centered"
)

DB_FILE = "clients.json"
ADMIN_PIN = "1234"  # zmień później


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


def find_client_by_code(clients, code):
    for client_id, data in clients.items():
        if data.get("code") == code:
            return client_id, data
    return None, None


def search_clients_by_name(clients, phrase):
    phrase = phrase.strip().lower()
    results = []
    for client_id, data in clients.items():
        if phrase in data.get("name", "").lower():
            results.append((client_id, data))
    return results


def stamp_visual(stamps, max_stamps=5):
    filled = "●" * stamps
    empty = "○" * (max_stamps - stamps)
    return filled + empty


clients = load_clients()

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
.stTabs [data-baseweb="tab-list"] {
    gap: 8px;
}
.stTabs [data-baseweb="tab"] {
    border-radius: 12px 12px 0 0;
    padding-left: 18px;
    padding-right: 18px;
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
.qr-center {
    text-align: center;
    margin-top: 28px;
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
        submitted = st.form_submit_button("Generuj kartę", use_container_width=True)

    if submitted:
        if not name.strip():
            st.error("Wpisz imię i nazwisko.")
        else:
            client_id = str(uuid.uuid4())
            card_code = generate_card_code()

            while any(c.get("code") == card_code for c in clients.values()):
                card_code = generate_card_code()

            clients[client_id] = {
                "name": name.strip(),
                "code": card_code,
                "stamps": 0,
                "reward_ready": False,
                "created_at": datetime.utcnow().isoformat()
            }
            save_clients(clients)
            st.session_state["last_client_id"] = client_id
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
        st.caption(f'{client["stamps"]} / 5 pieczątek')

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
        '<div class="sub-text">Tutaj Wiktoria może wyszukać klientkę po imieniu i nazwisku albo kodzie karty.</div>',
        unsafe_allow_html=True
    )

    pin = st.text_input("PIN salonu", type="password")

    if pin == ADMIN_PIN:
        st.success("Zalogowano do panelu salonu.")

        mode = st.radio(
            "Sposób wyszukiwania",
            ["Imię i nazwisko", "Kod karty"],
            horizontal=True
        )

        selected_client_id = None
        selected_client = None

        if mode == "Imię i nazwisko":
            search_name = st.text_input("Wyszukaj klientkę", placeholder="Np. Wiktoria Betler")

            if search_name.strip():
                results = search_clients_by_name(clients, search_name)

                if results:
                    options = {
                        f"{data['name']} — {data['code']}": client_id
                        for client_id, data in results
                    }
                    chosen_label = st.selectbox("Wybierz klientkę", list(options.keys()))
                    selected_client_id = options[chosen_label]
                    selected_client = clients[selected_client_id]
                else:
                    st.warning("Brak klientek pasujących do wyszukiwania.")

        else:
            code_to_find = st.text_input("Kod klientki", placeholder="Np. 9B5E7076").strip().upper()
            if code_to_find:
                selected_client_id, selected_client = find_client_by_code(clients, code_to_find)
                if not selected_client:
                    st.warning("Nie znaleziono klientki o takim kodzie.")

        if selected_client:
            st.markdown('<div class="card-box">', unsafe_allow_html=True)
            st.markdown('<div class="muted">Klientka</div>', unsafe_allow_html=True)
            st.subheader(selected_client["name"])

            st.markdown('<div class="small-space"></div>', unsafe_allow_html=True)
            st.markdown('<div class="muted">Kod</div>', unsafe_allow_html=True)
            st.markdown(f'<div class="code-box">{selected_client["code"]}</div>', unsafe_allow_html=True)

            st.markdown('<div class="muted">Pieczątki</div>', unsafe_allow_html=True)
            st.markdown(
                f'<div class="stamp-big">{stamp_visual(selected_client["stamps"])}</div>',
                unsafe_allow_html=True
            )
            st.caption(f'{selected_client["stamps"]} / 5')

            if selected_client["reward_ready"]:
                st.success("Ta klientka ma gotową nagrodę.")

            st.markdown('</div>', unsafe_allow_html=True)

            col1, col2 = st.columns(2)

            with col1:
                if st.button("➕ Dodaj pieczątkę", use_container_width=True):
                    if selected_client["stamps"] < 5:
                        selected_client["stamps"] += 1
                        if selected_client["stamps"] >= 5:
                            selected_client["reward_ready"] = True
                        clients[selected_client_id] = selected_client
                        save_clients(clients)
                        st.success("Dodano pieczątkę.")
                        st.rerun()
                    else:
                        st.warning("Klientka ma już komplet pieczątek.")

            with col2:
                if st.button("🎁 Odbierz nagrodę / reset", use_container_width=True):
                    selected_client["stamps"] = 0
                    selected_client["reward_ready"] = False
                    clients[selected_client_id] = selected_client
                    save_clients(clients)
                    st.success("Nagroda rozliczona, licznik wyzerowany.")
                    st.rerun()

    elif pin:
        st.error("Nieprawidłowy PIN.")
