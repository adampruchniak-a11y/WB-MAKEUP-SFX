import streamlit as st
import uuid
import json
import os
import re

# ===== CONFIG =====
st.set_page_config(page_title="WB Make-up & SFX", layout="centered")

DB_FILE = "clients.json"
MAX_STAMPS = 5

ADMIN_LOGIN = "admin"
ADMIN_PASSWORD = "haslo123"

# ===== UTILS =====

BAD_WORDS = [
    "kurwa", "dupa", "chuj", "pizda", "jebac", "fuck", "shit"
]

def contains_bad_word(text):
    text = text.lower()
    return any(word in text for word in BAD_WORDS)

def clean_name(name):
    name = name.strip().capitalize()
    return name

def valid_name(name):
    if len(name) < 2:
        return False

    if not re.match(r"^[A-Za-zŻŹĆĄŚĘŁÓŃżźćńółęąś][a-zżźćńółęąś]+$", name):
        return False

    if name[0] in "ĄĘŚĆŻŹŁÓŃ":
        return False

    if contains_bad_word(name):
        return False

    return True

def stamp_visual(stamps):
    return ("●" * stamps) + ("○" * (MAX_STAMPS - stamps))

def load_clients():
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "r") as f:
            return json.load(f)
    return []

def save_clients(data):
    with open(DB_FILE, "w") as f:
        json.dump(data, f, indent=2)

clients = load_clients()

# ===== STYLE =====
st.markdown("""
<style>
body { background-color: #000; }

.block-container {
    padding-top: 1rem;
}

.logo {
    text-align: center;
    margin-bottom: 10px;
}

.logo img {
    width: 70%;
    border-radius: 12px;
}

.input-box input {
    background: #111 !important;
    border-radius: 12px !important;
    color: white !important;
}

.stButton button {
    background: #222;
    color: white;
    border-radius: 12px;
}

.card {
    background: #111;
    padding: 20px;
    border-radius: 16px;
    margin-top: 20px;
}

.code {
    font-size: 28px;
    color: gold;
    text-align: center;
}

.stamps {
    font-size: 28px;
    text-align: center;
}

.muted {
    color: #aaa;
}
</style>
""", unsafe_allow_html=True)

# ===== LOGO =====
st.markdown("""
<div class="logo">
<img src="https://raw.githubusercontent.com/adampruchniak-a11y/WB-MAKEUP-SFX/main/logo.png">
</div>
""", unsafe_allow_html=True)

# ===== CREATE CLIENT =====
st.markdown("### Nowa klientka")

col1, col2 = st.columns(2)

with col1:
    imie = st.text_input("Imię")

with col2:
    nazwisko = st.text_input("Nazwisko")

if st.button("Wygeneruj kartę"):

    imie = clean_name(imie)
    nazwisko = clean_name(nazwisko)

    if not valid_name(imie) or not valid_name(nazwisko):
        st.error("Niepoprawne dane.")
    else:
        full = f"{imie} {nazwisko}"

        existing = next((c for c in clients if c["name"] == full), None)

        if existing:
            st.warning("Ta klientka już istnieje.")
            client = existing
        else:
            client = {
                "id": str(uuid.uuid4())[:8].upper(),
                "name": full,
                "stamps": 0
            }
            clients.append(client)
            save_clients(clients)
            st.success("Karta utworzona.")

        # ===== SHOW CARD =====
        st.markdown('<div class="card">', unsafe_allow_html=True)

        st.markdown(f"**Klientka**")
        st.markdown(f"# {client['name']}")

        st.markdown("**Kod**")
        st.markdown(f'<div class="code">{client["id"]}</div>', unsafe_allow_html=True)

        st.markdown("**Pieczątki**")
        st.markdown(f'<div class="stamps">{stamp_visual(client["stamps"])}</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="muted">{client["stamps"]} / {MAX_STAMPS}</div>', unsafe_allow_html=True)

        st.markdown('</div>', unsafe_allow_html=True)

# ===== SEARCH =====
st.markdown("---")
st.markdown("### Znajdź klientkę")

search = st.text_input("Szukaj")

if search:
    results = [c for c in clients if search.lower() in c["name"].lower()]

    for c in results:
        st.markdown(f"{c['name']} — {c['id']}")

# ===== ADMIN =====
st.markdown("---")
st.markdown("### Panel salonu")

login = st.text_input("Login")
password = st.text_input("Hasło", type="password")

if login == ADMIN_LOGIN and password == ADMIN_PASSWORD:

    code = st.text_input("Kod klientki")

    client = next((c for c in clients if c["id"] == code), None)

    if client:
        st.markdown(f"### {client['name']}")

        st.markdown(f'<div class="stamps">{stamp_visual(client["stamps"])}</div>', unsafe_allow_html=True)

        if st.button("Dodaj pieczątkę"):
            if client["stamps"] < MAX_STAMPS:
                client["stamps"] += 1
                save_clients(clients)
                st.rerun()

        if st.button("Reset"):
            client["stamps"] = 0
            save_clients(clients)
            st.rerun()