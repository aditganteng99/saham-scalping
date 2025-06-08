import os
import streamlit as st
import yfinance as yf
import pandas as pd
import matplotlib.pyplot as plt
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from fpdf import FPDF
import tempfile
from io import BytesIO

# Konfigurasi email
EMAIL_PENGIRIM = "m.aldek.saputra08@gmail.com"
EMAIL_PASSWORD = os.environ.get("EMAIL_PASSWORD")
st.set_page_config(page_title="Saham IDX Real-Time", layout="wide")
st.title("📊 Analisis Saham IDX - Real-Time + Grafik + Sinyal Scalping")

modal = st.number_input("💰 Modal Trading (Rp)", min_value=1000000, value=10000000, step=1000000)
email_user = st.text_input("📧 Masukkan Email Anda:", value="m.aldek.saputra08@gmail.com")

daftar_saham = ["ANTM.JK", "BBCA.JK", "TLKM.JK", "ADRO.JK", "MDKA.JK"]

# Kirim Email
def kirim_email(path_pdf, tujuan):
    msg = MIMEMultipart()
    msg['From'] = EMAIL_PENGIRIM
    msg['To'] = tujuan
    msg['Subject'] = "📈 Hasil Analisis Saham Harian Anda"
    body = "Berikut lampiran hasil analisis saham harian Anda."
    msg.attach(MIMEText(body, 'plain'))

    with open(path_pdf, "rb") as f:
        part = MIMEBase('application', 'octet-stream')
        part.set_payload(f.read())
        encoders.encode_base64(part)
        part.add_header('Content-Disposition', 'attachment; filename="analisis_saham.pdf"')
        msg.attach(part)

    try:
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(EMAIL_PENGIRIM, EMAIL_PASSWORD)
        server.send_message(msg)
        server.quit()
        return True
    except Exception as e:
        st.error(f"Gagal kirim email: {e}")
        return False

# PDF Export
class PDF(FPDF):
    def header(self):
        self.set_font('Arial', 'B', 12)
        self.cell(0, 10, 'Laporan Analisis Saham Harian', ln=True, align='C')
        self.ln(10)

    def chapter_body(self, df):
        self.set_font('Arial', '', 10)
        for _, row in df.iterrows():
            line = f"{row['Kode']} | Harga: {row['Harga Terbaru']} | Lot: {row['Est. Lot']} | TP: {row['TP']} | SL: {row['SL']} | Est. Profit: {row['Est. Profit']} | Est. Loss: {row['Est. Loss']} | Sinyal: {row['Sinyal']}"
            self.multi_cell(0, 10, line)

    def print_chapter(self, df):
        self.add_page()
        self.chapter_body(df)

# Analisis saham
if st.button("🔍 Ambil Data & Analisis"):
    hasil = []
    st.markdown("## 📊 Hasil Analisis")

    for kode in daftar_saham:
        try:
            data = yf.Ticker(kode).history(period="1d", interval="1m")
            if data.empty:
                continue
            harga = data["Close"].iloc[-1]
            ma5 = data["Close"].rolling(5).mean().iloc[-1]
            lot = max(int(modal // (harga * 100)), 1)
            tp = harga * 1.03
            sl = harga * 0.98
            est_profit = (tp - harga) * lot * 100
            est_loss = (harga - sl) * lot * 100
            sinyal = "📈 PASTI NAIK" if harga > ma5 else "-"

            hasil.append({
                "Kode": kode,
                "Harga Terbaru": round(harga, 2),
                "Est. Lot": lot,
                "TP": round(tp, 2),
                "SL": round(sl, 2),
                "Est. Profit": int(est_profit),
                "Est. Loss": int(est_loss),
                "Sinyal": sinyal
            })

            # Grafik harga & MA5
            st.markdown(f"### 📈 Grafik {kode}")
            fig, ax = plt.subplots()
            data["Close"].plot(ax=ax, label="Harga", color='blue')
            data["Close"].rolling(5).mean().plot(ax=ax, label="MA5", color='orange')
            ax.set_title(kode)
            ax.legend()
            st.pyplot(fig)

        except Exception as e:
            st.error(f"Gagal memproses {kode}: {e}")

    df = pd.DataFrame(hasil)
    st.dataframe(df)

    # Export
    st.markdown("## 📤 Export dan Kirim Email")
    col1, col2 = st.columns(2)

    excel_buffer = BytesIO()
    df.to_excel(excel_buffer, index=False)
    excel_buffer.seek(0)
    with col1:
        st.download_button("⬇️ Download Excel", data=excel_buffer, file_name="analisis_saham.xlsx")

    pdf = PDF()
    pdf.print_chapter(df)
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
    pdf.output(tmp.name)
    with open(tmp.name, "rb") as f:
        st.download_button("⬇️ Download PDF", data=f.read(), file_name="analisis_saham.pdf")

    with col2:
        if st.button("📧 Kirim ke Email Saya"):
            if kirim_email(tmp.name, email_user):
                st.success(f"📬 Berhasil dikirim ke {email_user}")


# --- FITUR BARU: Screening IDX Otomatis Seluruh Saham ---

@st.cache_data
def get_all_idx_tickers():
    import requests
    import re
    try:
        url = "https://raw.githubusercontent.com/dudung/daftar-saham-IDX/main/data/saham-idx.txt"
        response = requests.get(url)
        tickers = re.findall(r'\b[A-Z]{4,5}\b', response.text)
        return [ticker + ".JK" for ticker in tickers]
    except:
        return ["BBCA.JK", "ANTM.JK", "TLKM.JK", "ADRO.JK", "MDKA.JK"]  # fallback

def screening_idx():
    from datetime import datetime

    st.markdown("## 🔍 Screening IDX Otomatis (Top 5 Sinyal Pasti Naik)")
    saham_list = get_all_idx_tickers()
    hasil = []

    progress = st.progress(0)
    total = len(saham_list)

    for i, kode in enumerate(saham_list):
        try:
            df = yf.Ticker(kode).history(period="7d", interval="1d")
            df_intraday = yf.Ticker(kode).history(period="1d", interval="5m")
            if df.empty or df_intraday.empty: continue

            harga = df_intraday["Close"].iloc[-1]
            open_now = df_intraday["Open"].iloc[-1]
            close = df["Close"]
            volume = df["Volume"]
            ma5 = close.rolling(5).mean().iloc[-1]
            ma20 = close.rolling(20).mean().iloc[-1]
            avg_vol = volume.rolling(5).mean().iloc[-1]

            delta = close.diff()
            gain = delta.where(delta > 0, 0)
            loss = -delta.where(delta < 0, 0)
            avg_gain = gain.rolling(14).mean().iloc[-1]
            avg_loss = loss.rolling(14).mean().iloc[-1]
            rs = avg_gain / avg_loss if avg_loss != 0 else 0
            rsi = 100 - (100 / (1 + rs)) if rs != 0 else 100

            if harga > open_now and ma5 > ma20 and rsi < 60 and volume.iloc[-1] > avg_vol:
                lot = max(int(modal // (harga * 100)), 1)
                tp = harga * 1.03
                sl = harga * 0.98
                est_profit = int((tp - harga) * lot * 100)
                est_loss = int((harga - sl) * lot * 100)

                hasil.append({
                    "Kode": kode,
                    "Harga Terbaru": round(harga, 2),
                    "Est. Lot": lot,
                    "TP": round(tp, 2),
                    "SL": round(sl, 2),
                    "RSI": int(rsi),
                    "Est. Profit": est_profit,
                    "Est. Loss": est_loss,
                    "Sinyal": "📈 PASTI NAIK"
                })
        except:
            continue
        progress.progress((i + 1) / total)

    if not hasil:
        st.info("Tidak ada saham yang memenuhi kriteria hari ini.")
        return

    # Ambil Top 5 berdasarkan Est. Profit
    df_hasil = pd.DataFrame(hasil)
    df_hasil = df_hasil.sort_values(by="Est. Profit", ascending=False).head(5)
    st.dataframe(df_hasil)

    # Export
    st.markdown("## 📤 Export dan Kirim Email")
    col1, col2 = st.columns(2)

    excel_buf = BytesIO()
    df_hasil.to_excel(excel_buf, index=False)
    excel_buf.seek(0)

    with col1:
        st.download_button("⬇️ Download Excel IDX", data=excel_buf, file_name="hasil_screening_top5.xlsx")

    pdf = PDF()
    pdf.print_chapter(df_hasil)
    tmp2 = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
    pdf.output(tmp2.name)
    with open(tmp2.name, "rb") as f:
        st.download_button("⬇️ Download PDF IDX", data=f.read(), file_name="hasil_screening_top5.pdf")

    with col2:
        if st.button("📧 Kirim Hasil IDX ke Email"):
            if kirim_email(tmp2.name, email_user):
                st.success(f"📬 Hasil screening IDX dikirim ke {email_user}")

# Tombol pemicu
if st.button("🔍 Screening IDX Otomatis"):
    screening_idx()
