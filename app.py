import streamlit as st
import uuid
import io
import base64
import segno

st.set_page_config(
    page_title="Karta Lojalnościowa",
    page_icon="💄",
    layout="centered"
)

# Styl
st.markdown("""
<style>
.block-container {
    max-width: 760px;
    padding-top: 3rem;
    padding-bottom: 3rem;
}
h1, h2, h3 {
    letter-spacing: -0.5px;
}
.qr-card {
    background: #111827;
    border: 1px solid rgba(255,255,255,0.08);
    border-radius: 18px;
    padding: 24px;
    margin-top: 20px;
}
.card-code {
    background: #1f2937;
    padding: 14px 16px;
    border-radius: 12px;
    font-weight: 700;
    letter-spacing: 1px;
    text-align: center;
    font-size: 20px;
}
.small-muted {
    opacity: 0.75;
    font-size: 14px;
}
</style>
""", unsafe_allow_html=True)

st.title("💄 Karta lojalnościowa")
st.subheader("Wygeneruj swoją kartę")

name = st.text_input("Imię i nazwisko")

if st.button("Generuj kartę", use_container_width=False):
    if name.strip():
        user_id = str(uuid.uuid4())[:8].upper()

        qr = segno.make(user_id)
        buffer = io.BytesIO()
        qr.save(buffer, kind="png", scale=8)
        qr_bytes = buffer.getvalue()

        st.success("Karta została wygenerowana")

        st.markdown(f"""
        <div class="qr-card">
            <div class="small-muted">Klientka</div>
            <h3 style="margin-top: 6px;">{name}</h3>
            <div class="small-muted" style="margin-top: 16px;">Kod karty</div>
            <div class="card-code">{user_id}</div>
        </div>
        """, unsafe_allow_html=True)

        st.image(qr_bytes, caption="Twój kod QR", width=260)

        st.info("Zapisz ten kod QR lub pokaż go przy kolejnej wizycie.")
    else:
        st.error("Wpisz imię i nazwisko")
