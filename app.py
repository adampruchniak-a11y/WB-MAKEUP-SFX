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
ADMIN_PIN = "1234"   # później zmień


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


clients = load_clients()

st.markdown("""
<style>
.block-container {
    max-width: 780px;
    padding-top: 2.2rem;
    padding-bottom: 3rem;
}
.main-title {
    font-size: 46px;
    font-weight: 800;
    line-height: 1.05;
    margin-bottom: 6px;
}
.sub-text {
    opacity: 0.82;
    margin-bottom: 28px;
}
.dark-card {
    background: linear-gradient(180deg, #0f172a 0%, #111827 100%);
    border: 1px solid rgba(255,255,255,0.08);
    border-radius: 22px;
    padding: 24px;
    margin-top: 18px;
    box-shadow: 0 10px 30px rgba(0,0,0,0.25);
}
.code-box {
    background: rgba(255,255,255,0.06);
    border-radius: 14px;
    padding: 16px;
    text-align: center;
    font-size: 24px;
    font-weight: 800;
    letter-spacing: 1.5px;
    margin-top: 8px;
}
.muted {
    opacity: 0.7;
    font-size: 14px;
}
.stamp-row {
    font-size: 28px;
    letter-spacing: 4px;
    margin-top: 8px;
}
.reward-box {
    background: rgba(34,197,94,0.14);
    border: 1px solid rgba(34,197,94,0.4);
    border-radius: 16px;
    padding: 14px 16px;
    margin-top: 14px;
}
.qr-wrap {
    text-align: center;
    margin-top: 34px;
}
.qr-wrap img {
    border-radius: 16px;
}
.qr-note {
    margin-top: 16px;
}
</style>
""", unsafe_allow_html=True)

tab1, tab2 = st.tabs(["💄 Karta klientki", "🔒 Panel salonu"])

with tab1:
    st.markdown('<div class="main-title">Karta lojalnościowa</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-text">Wpisz imię i nazwisko, aby wygenerować kartę klientki.</div>', unsafe_allow_html=True)

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

        filled = "●" * client["stamps"]
        empty = "○" * (5 - client["stamps"])
        stamp_visual = filled + empty

        reward_html = ""
        if client["reward_ready"]:
            reward_html = """
            <div class="reward-box">
                <strong>Gotowe 🎉</strong><br>
                Klientka ma już nagrodę do odebrania.
            </div>
            """

        card_html = f"""
        <div class="dark-card">
            <div class="muted">Klientka</div>
            <h2 style="margin-top: 6px; margin-bottom: 18px;">{client["name"]}</h2>

            <div class="muted">Kod karty</div>
            <div class="code-box">{client["code"]}</div>

            <div style="margin-top: 20px;" class="muted">Postęp</div>
            <div class="stamp-row">{stamp_visual}</div>
            <div class="muted">{client["stamps"]} / 5 pieczątek</div>

            {reward_html}
        </div>
        """
        st.markdown(card_html, unsafe_allow_html=True)

        st.markdown('<div class="qr-wrap">', unsafe_allow_html=True)
        st.image(qr_url, caption="Twój kod QR", width=240)
        st.markdown('</div>', unsafe_allow_html=True)

        st.markdown('<div class="qr-note">', unsafe_allow_html=True)
        st.info("Zapisz ten kod QR lub pokaż go przy kolejnej wizycie.")
        st.markdown('</div>', unsafe_allow_html=True)

with tab2:
    st.markdown('<div class="main-title" style="font-size:34px;">Panel salonu</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-text">Tutaj salon może wyszukać klientkę po kodzie i dodać pieczątkę.</div>', unsafe_allow_html=True)

    pin = st.text_input("PIN salonu", type="password")

    if pin == ADMIN_PIN:
        st.success("Zalogowano do panelu salonu.")

        code_to_find = st.text_input("Kod klientki", placeholder="Np. 9B5E7076").strip().upper()

        if st.button("Szukaj klientki", use_container_width=True):
            st.session_state["search_code"] = code_to_find

        search_code = st.session_state.get("search_code", "")
        if search_code:
            client_id, client = find_client_by_code(clients, search_code)

            if client:
                filled = "●" * client["stamps"]
                empty = "○" * (5 - client["stamps"])
                stamp_visual = filled + empty

                admin_html = f"""
                <div class="dark-card">
                    <div class="muted">Klientka</div>
                    <h3 style="margin-top: 6px;">{client["name"]}</h3>
                    <div class="muted" style="margin-top: 14px;">Kod</div>
                    <div class="code-box">{client["code"]}</div>
                    <div style="margin-top: 18px;" class="muted">Pieczątki</div>
                    <div class="stamp-row">{stamp_visual}</div>
                    <div class="muted">{client["stamps"]} / 5</div>
                </div>
                """
                st.markdown(admin_html, unsafe_allow_html=True)

                col1, col2 = st.columns(2)

                with col1:
                    if st.button("➕ Dodaj pieczątkę", use_container_width=True):
                        if client["stamps"] < 5:
                            client["stamps"] += 1
                            if client["stamps"] >= 5:
                                client["reward_ready"] = True
                            clients[client_id] = client
                            save_clients(clients)
                            st.success("Dodano pieczątkę.")
                            st.rerun()
                        else:
                            st.warning("Klientka ma już komplet pieczątek.")

                with col2:
                    if st.button("🎁 Odbierz nagrodę / reset", use_container_width=True):
                        client["stamps"] = 0
                        client["reward_ready"] = False
                        clients[client_id] = client
                        save_clients(clients)
                        st.success("Nagroda rozliczona, licznik wyzerowany.")
                        st.rerun()
            else:
                st.error("Nie znaleziono klientki o takim kodzie.")
    elif pin:
        st.error("Nieprawidłowy PIN.")
