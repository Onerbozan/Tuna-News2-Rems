import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
import time

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

# --- VERİ BAĞLANTISI VE OTOMATİK SÜTUN SENKRONİZASYONU ---
conn = st.connection("gsheets", type=GSheetsConnection)

# Sistemde olması gereken tüm sütunların ana listesi
REQUIRED_COLUMNS = [
    "Kayit_Tarihi", "Kaydeden", "Protokol_No", "Ad_Soyad", "Yas", "Cinsiyet", 
    "Sikayet", "Komorbiditeler", "KOAH_Oykusu", "SBP", "Nabiz", 
    "Solunum_Sayisi", "Ates", "SpO2", "GCS", "O2_Destegi", 
    "NEWS2_Skoru", "REMS_Skoru", "Nihai_Karar", "Yatis_Gunu", 
    "YB_Ihtiyaci", "Mortalite"
]

def load_data():
    try:
        df = conn.read(ttl=0) 
        
        # 1. Senaryo: Tablo tamamen boşsa sıfırdan oluştur
        if df.empty or len(df.columns) == 0:
            df_bos = pd.DataFrame(columns=REQUIRED_COLUMNS)
            conn.update(data=df_bos)
            return df_bos
            
        # 2. Senaryo: Tablo dolu ama koda yeni sütunlar eklenmişse (Otomatik Yama)
        eksik_sutunlar = [col for col in REQUIRED_COLUMNS if col not in df.columns]
        if eksik_sutunlar:
            for col in eksik_sutunlar:
                df[col] = "" # Eksik sütunları boş olarak tabloya ekle
            
            # Sütunları doğru sıraya diz ve Google Sheet'i arka planda güncelle
            df = df[REQUIRED_COLUMNS + [c for c in df.columns if c not in REQUIRED_COLUMNS]]
            conn.update(data=df)
            
        # Protokol No'yu güvenli formata çevir (Mükerrer kontrolü için)
        if 'Protokol_No' in df.columns:
            df['Protokol_No'] = df['Protokol_No'].astype(str).str.replace(r'\.0$', '', regex=True).str.strip()
        
        return df
    except Exception as e:
        st.error(f"⚠️ Bağlantı hatası: {e}")
        st.stop()
        return pd.DataFrame(columns=REQUIRED_COLUMNS)

df = load_data()

# --- HESAPLAMA FONKSİYONLARI ---
def calc_news2(rr, spo2, is_coah, o2_support, sbp, hr, gcs, temp):
    score = 0
    if rr <= 8: score += 3
    elif 9 <= rr <= 11: score += 1
    elif 12 <= rr <= 20: score += 0
    elif 21 <= rr <= 24: score += 2
    elif rr >= 25: score += 3

    if is_coah == "Evet":
        if spo2 <= 83: score += 3
        elif 84 <= spo2 <= 85: score += 2
        elif 86 <= spo2 <= 87: score += 1
        elif 88 <= spo2 <= 92: score += 0
        elif spo2 >= 93 and o2_support == "Oda Havası": score += 0
        elif 93 <= spo2 <= 94 and o2_support != "Oda Havası": score += 1
        elif 95 <= spo2 <= 96 and o2_support != "Oda Havası": score += 2
        elif spo2 >= 97 and o2_support != "Oda Havası": score += 3
    else:
        if spo2 <= 91: score += 3
        elif 92 <= spo2 <= 93: score += 2
        elif 94 <= spo2 <= 95: score += 1
        elif spo2 >= 96: score += 0

    if o2_support != "Oda Havası": score += 2

    if sbp <= 90: score += 3
    elif 91 <= sbp <= 100: score += 2
    elif 101 <= sbp <= 110: score += 1
    elif 111 <= sbp <= 219: score += 0
    elif sbp >= 220: score += 3

    if hr <= 40: score += 3
    elif 41 <= hr <= 50: score += 1
    elif 51 <= hr <= 90: score += 0
    elif 91 <= hr <= 110: score += 1
    elif 111 <= hr <= 130: score += 2
    elif hr >= 131: score += 3

    if gcs == 15: score += 0
    else: score += 3

    if temp <= 35.0: score += 3
    elif 35.1 <= temp <= 36.0: score += 1
    elif 36.1 <= temp <= 38.0: score += 0
    elif 38.1 <= temp <= 39.0: score += 1
    elif temp >= 39.1: score += 2

    return score

def calc_rems(age, hr, rr, sbp, gcs, spo2):
    score = 0
    if age < 45: score += 0
    elif 45 <= age <= 54: score += 2
    elif 55 <= age <= 64: score += 3
    elif 65 <= age <= 74: score += 5
    elif age > 74: score += 6

    if hr > 179: score += 4
    elif 140 <= hr <= 179: score += 3
    elif 110 <= hr <= 139: score += 2
    elif 70 <= hr <= 109: score += 0
    elif 54 <= hr <= 69: score += 2
    elif 40 <= hr <= 53: score += 3
    elif hr < 40: score += 4

    if rr > 49: score += 4
    elif 35 <= rr <= 49: score += 3
    elif 25 <= rr <= 34: score += 1
    elif 12 <= rr <= 24: score += 0
    elif 10 <= rr <= 11: score += 1
    elif 6 <= rr <= 9: score += 2
    elif rr < 6: score += 4

    if sbp > 179: score += 4
    elif 130 <= sbp <= 179: score += 3
    elif 90 <= sbp <= 129: score += 0
    elif 70 <= sbp <= 89: score += 2
    elif sbp < 70: score += 4

    if gcs > 13: score += 0
    elif 11 <= gcs <= 13: score += 1
    elif 8 <= gcs <= 10: score += 2
    elif 5 <= gcs <= 7: score += 3
    elif gcs < 5: score += 4

    if spo2 > 89: score += 0
    elif 75 <= spo2 <= 89: score += 1
    elif spo2 < 75: score += 2

    return score

# --- SEKMELER ---
tab1, tab2, tab3, tab4 = st.tabs([
    "➕ 1. Yeni Kayıt (Vitaller)", 
    "🏥 2. Klinik Takip", 
    "📋 3. İzlem Paneli", 
    "📈 4. Raporlar & Yedek"
])

# ==========================================
# SEKME 1: YENİ HASTA KAYDI
# ==========================================
with tab1:
    st.subheader("BÖLÜM 2 & 3: Demografik Bilgiler ve T0 Vitalleri")
    
    uyari_alani = st.empty()
    
    with st.form("new_reg", clear_on_submit=True):
        st.markdown("**1. Temel Bilgiler**")
        
        c_tc, c_isim = st.columns(2)
        protokol = c_tc.text_input("Hasta TC Kimlik No*", max_chars=11)
        isim = c_isim.text_input("Hasta Adı Soyadı*")
        
        c1, c2 = st.columns(2)
        yas = c1.number_input("Yaş*", min_value=65, max_value=120, value=65)
        cinsiyet = c2.selectbox("Cinsiyet*", ["Erkek", "Kadın"])
        
        sikayet = st.text_input("Ambulans Şikayeti / Ön Tanı")
        
        komorbiditeler = st.multiselect(
            "Komorbiditeler (Birden fazla seçilebilir)", 
            ["HT", "DM", "KAH", "KKY", "SVO", "KBY", "Malignite", "Diğer"]
        )
        koah = st.selectbox("KOAH / Hiperkapnik Solunum Yetmezliği Öyküsü var mı? (NEWS2 için kritik)", ["Hayır", "Evet"])
        
        st.markdown("---")
        st.markdown("**2. T0 - Başvuru Anı Vital Bulguları**")
        v1, v2, v3, v4 = st.columns(4)
        sbp = v1.number_input("Sistolik Kan Basıncı (mmHg)", value=120)
        hr = v2.number_input("Nabız / KTA (vuru/dk)", value=80)
        rr = v3.number_input("Solunum Sayısı (nefes/dk)", value=16)
        ates = v4.number_input("Vücut Sıcaklığı (°C)", value=36.5, step=0.1, format="%.1f")
        
        v5, v6, v7 = st.columns(3)
        spo2 = v5.number_input("Oksijen Saturasyonu (SpO2 %)", value=95)
        gcs = v6.number_input("Bilinç Durumu (GCS)", min_value=3, max_value=15, value=15)
        o2_destegi = v7.selectbox("Oksijen Desteği Durumu", ["Oda Havası", "Oksijen Alıyor"])

        if st.form_submit_button("Hastayı Kaydet ve Skorları Hesapla"):
            temiz_protokol = str(protokol).strip()
            temiz_isim = str(isim).strip()
            sistemdeki_protokoller = [str(x).split('.')[0].strip() for x in df['Protokol_No'].tolist()]

            # 11 Hane ve Sadece Rakam Kontrolü
            if len(temiz_protokol) != 11 or not temiz_protokol.isdigit():
                uyari_alani.error("❌ Lütfen tam 11 haneli ve sadece rakamlardan oluşan bir TC Kimlik No giriniz.")
            elif not temiz_isim:
                uyari_alani.error("❌ Lütfen Hasta Adı Soyadı bilgisini giriniz.")
            elif temiz_protokol in sistemdeki_protokoller:
                uyari_alani.error(f"❌ HATA: '{temiz_protokol}' numaralı TC daha önce kaydedilmiş! Lütfen numarayı kontrol edin.")
                st.markdown("""
                    <style>
                    div[data-testid="stTextInput"] input[aria-label="Hasta TC Kimlik No*"] {
                        border: 2px solid red !important;
                        background-color: #fff0f0 !important;
                    }
                    </style>
                """, unsafe_allow_html=True)
            else:
                news2_val = calc_news2(rr, spo2, koah, o2_destegi, sbp, hr, gcs, ates)
                rems_val = calc_rems(yas, hr, rr, sbp, gcs, spo2)
                komorbid_str = ", ".join(komorbiditeler) if komorbiditeler else "Yok"

                new_row = pd.DataFrame([{
                    "Kayit_Tarihi": datetime.now().strftime("%d/%m/%Y %H:%M"),
                    "Kaydeden": st.session_state.username,
                    "Protokol_No": temiz_protokol,
                    "Ad_Soyad": temiz_isim.upper(), 
                    "Yas": yas, "Cinsiyet": cinsiyet, 
                    "Sikayet": sikayet, "Komorbiditeler": komorbid_str, "KOAH_Oykusu": koah, 
                    "SBP": sbp, "Nabiz": hr, "Solunum_Sayisi": rr, "Ates": ates, 
                    "SpO2": spo2, "GCS": gcs, "O2_Destegi": o2_destegi, 
                    "NEWS2_Skoru": news2_val, "REMS_Skoru": rems_val, 
                    "Nihai_Karar": "Bilinmiyor", "Yatis_Gunu": 0, 
                    "YB_Ihtiyaci": "Bilinmiyor", "Mortalite": "Bilinmiyor"
                }])
                
                updated = pd.concat([df, new_row], ignore_index=True)
                conn.update(data=updated)
                st.cache_data.clear()
                
                uyari_alani.success(f"✅ Kayıt Başarılı! Hesaplanan Skorlar 👉 NEWS2: **{news2_val}** | REMS: **{rems_val}**")
                time.sleep(2.5) 
                st.rerun()

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
