import streamlit as st
import uuid

st.set_page_config(page_title="Karta Lojalnościowa", layout="centered")

if "clients" not in st.session_state:
    st.session_state.clients = {}

st.title("💄 Karta lojalnościowa")
st.subheader("Wygeneruj swoją kartę")

name = st.text_input("Imię i nazwisko")

if st.button("Generuj kartę"):
    if name.strip():
        user_id = str(uuid.uuid4())[:8].upper()
        st.session_state.clients[user_id] = {
            "name": name,
            "stamps": 0
        }

        st.success("Karta została wygenerowana")
        st.write(f"**Klientka:** {name}")
        st.write(f"**Kod karty:** {user_id}")
        st.code(user_id)
    else:
        st.error("Wpisz imię i nazwisko")

st.divider()
st.subheader("Lista klientek")

if st.session_state.clients:
    for cid, data in st.session_state.clients.items():
        st.write(f"**{data['name']}** — kod: `{cid}` — pieczątki: {data['stamps']}")
else:
    st.info("Brak klientek")
