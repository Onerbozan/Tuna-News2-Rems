import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

# --- SAYFA AYARLARI ---
st.set_page_config(page_title="NEWS2 & REMS Çalışması", layout="wide")

# --- GİRİŞ KONTROLÜ VE OTURUM ---
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.username = ""

if not st.session_state.logged_in:
    st.title("🔒 NEWS2 & REMS Veri Girişi")
    with st.form("login"):
        u = st.text_input("Kullanıcı Adı")
        p = st.text_input("Şifre", type="password")
        if st.form_submit_button("Giriş"):
            if "passwords" in st.secrets and u in st.secrets["passwords"] and st.secrets["passwords"][u] == p:
                st.session_state.logged_in = True
                st.session_state.username = u
                st.rerun()
            else: 
                st.error("Hatalı giriş! Şifreyi veya kullanıcı adını kontrol edin.")
    st.stop()

# --- ANA EKRAN KARŞILAMA ---
st.markdown(f"### 👤 Hoş geldin, **{st.session_state.username.capitalize()}**")
st.markdown("---")

# --- VERİ BAĞLANTISI VE OTOMATİK SÜTUN OLUŞTURMA ---
conn = st.connection("gsheets", type=GSheetsConnection)

def load_data():
    try:
        df = conn.read(ttl=0) 
        # TABLO BOŞSA VEYA SÜTUN YOKSA OTOMATİK OLUŞTUR
        if df.empty or len(df.columns) == 0:
            df_bos = pd.DataFrame(columns=[
                "Kayit_Tarihi", "Kaydeden", "Protokol_No", "Yas", "Cinsiyet", 
                "Sikayet", "Komorbiditeler", "KOAH_Oykusu", "SBP", "Nabiz", 
                "Solunum_Sayisi", "Ates", "SpO2", "GCS", "O2_Destegi", 
                "NEWS2_Skoru", "REMS_Skoru", "Nihai_Karar", "Yatis_Gunu", 
                "YB_Ihtiyaci", "Mortalite"
            ])
            # Sütunları Google Sheets'e yazdırıyoruz
            conn.update(data=df_bos)
            return df_bos
            
        # Protokol No'yu güvenli formata çevir (Mükerrer kontrolü için)
        if 'Protokol_No' in df.columns:
            df['Protokol_No'] = df['Protokol_No'].astype(str).str.replace(r'\.0$', '', regex=True).str.strip()
        return df
    except Exception as e:
        st.error(f"⚠️ Bağlantı hatası: {e}")
        st.stop()
        return pd.DataFrame()

df = load_data()

# --- SEKMELER ---
tab1, tab2, tab3, tab4 = st.tabs([
    "➕ 1. Yeni Kayıt (Vitaller)", 
    "🏥 2. Klinik Takip", 
    "📋 3. İzlem Paneli", 
    "📈 4. Raporlar & Yedek"
])

with tab1:
    st.info("Burası Yeni Hasta Kayıt alanı olacak. NEWS2 ve REMS skorları burada otomatik hesaplanacak.")
with tab2:
    st.info("Burası Taburculuk ve Mortalite takip alanı olacak.")
with tab3:
    st.info("Burası tıpkı önceki projedeki gibi düzenlenebilir Excel tablosu olacak.")
with tab4:
    st.info("Burası istatistikler ve bilgisayara indirme alanı olacak.")

# --- ÇIKIŞ ---
st.markdown("---")
if st.button("🚪 Güvenli Çıkış Yap"):
    st.session_state.logged_in = False
    st.session_state.username = ""
    st.rerun()
