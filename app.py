import streamlit as st
import qrcode
import uuid
import json
import os

st.set_page_config(page_title="Karta Lojalnościowa", layout="centered")

st.title("💄 Karta lojalnościowa")

# baza klientów
DB_FILE = "clients.json"

def load_clients():
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "r") as f:
            return json.load(f)
    return {}

def save_clients(data):
    with open(DB_FILE, "w") as f:
        json.dump(data, f)

clients = load_clients()

name = st.text_input("Imię i nazwisko")

if st.button("Generuj kartę"):
    if name:
        user_id = str(uuid.uuid4())

        clients[user_id] = {
            "name": name,
            "stamps": 0
        }

        save_clients(clients)

        # QR
        qr = qrcode.make(user_id)
        qr.save("qr.png")

        st.success("Karta wygenerowana!")

        st.image("qr.png", caption="Twój kod QR")

        st.write(f"Twoje ID: {user_id}")
