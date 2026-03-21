import streamlit as st
import os
import requests
import urllib.parse
import re
import zipfile
import tempfile
import time
import google.generativeai as genai

# --- SAYFA AYARI ---
st.set_page_config(
    page_title="B-Roll Finder",
    page_icon="🎬",
    layout="wide"
)

# --- STİL ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;900&display=swap');

    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
        background-color: #0e0e0e;
        color: #f0f0f0;
    }

    .block-container {
        max-width: 820px;
        margin: auto;
        padding-top: 2rem;
    }

    h1 { 
        font-size: 2.8rem !important; 
        font-weight: 900 !important;
        color: #1DB954 !important;
        letter-spacing: -1px;
    }

    .subtitle {
        color: #888;
        font-size: 1.05rem;
        margin-top: -10px;
        margin-bottom: 30px;
    }

    .section-label {
        font-size: 0.75rem;
        font-weight: 700;
        letter-spacing: 2px;
        text-transform: uppercase;
        color: #555;
        margin-bottom: 6px;
    }

    .stTextInput > div > input, .stTextArea > div > textarea {
        background-color: #1a1a1a !important;
        border: 1.5px solid #2a2a2a !important;
        border-radius: 12px !important;
        color: #f0f0f0 !important;
        font-size: 1rem !important;
        padding: 14px !important;
    }
    .stTextInput > div > input:focus, .stTextArea > div > textarea:focus {
        border-color: #1DB954 !important;
        box-shadow: 0 0 0 2px rgba(29,185,84,0.15) !important;
    }

    .stButton > button {
        background: linear-gradient(135deg, #1DB954, #17a349) !important;
        color: white !important;
        font-size: 1.1rem !important;
        font-weight: 700 !important;
        height: 56px !important;
        border-radius: 28px !important;
        border: none !important;
        width: 100% !important;
        letter-spacing: 0.5px;
        transition: all 0.2s;
    }
    .stButton > button:hover {
        background: linear-gradient(135deg, #1ED760, #1DB954) !important;
        transform: translateY(-1px);
        box-shadow: 0 6px 20px rgba(29,185,84,0.3) !important;
    }

    .stExpander {
        background-color: #1a1a1a !important;
        border: 1px solid #2a2a2a !important;
        border-radius: 14px !important;
    }

    .stSlider > div > div > div {
        background-color: #1DB954 !important;
    }

    .stAlert {
        border-radius: 12px !important;
    }

    .keyword-tag {
        display: inline-block;
        background: #1a2e1a;
        color: #1DB954;
        border: 1px solid #1DB954;
        border-radius: 20px;
        padding: 4px 12px;
        margin: 3px;
        font-size: 0.85rem;
        font-weight: 600;
    }

    .stat-box {
        background: #1a1a1a;
        border: 1px solid #2a2a2a;
        border-radius: 14px;
        padding: 20px;
        text-align: center;
    }

    .stat-number {
        font-size: 2rem;
        font-weight: 900;
        color: #1DB954;
    }

    .stat-label {
        font-size: 0.8rem;
        color: #666;
        margin-top: 4px;
    }

    .divider {
        border: none;
        border-top: 1px solid #1e1e1e;
        margin: 28px 0;
    }

    .limit-bar {
        background: #1a1a1a;
        border: 1px solid #2a2a2a;
        border-radius: 12px;
        padding: 14px 20px;
        display: flex;
        align-items: center;
        gap: 10px;
        margin-bottom: 24px;
    }
</style>
""", unsafe_allow_html=True)

# --- KULLANIM SAYACI ---
if "usage_count" not in st.session_state:
    st.session_state.usage_count = 0
if "last_keywords" not in st.session_state:
    st.session_state.last_keywords = []

FREE_LIMIT = 3

# --- YARDIMCI FONKSİYONLAR ---
def clean_filename(text):
    text = str(text).replace(" ", "_").lower()
    tr_map = {'ı':'i','ğ':'g','ü':'u','ş':'s','ö':'o','ç':'c','İ':'I','Ğ':'G','Ü':'U','Ş':'S','Ö':'O','Ç':'C'}
    for tr, en in tr_map.items():
        text = text.replace(tr, en)
    return re.sub(r'[\\/*?:"<>|]', "", text)[:40]

def get_keywords_from_ai(topic, api_key, count=8):
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-2.5-flash')
        prompt = f"""You are a professional video editor and B-roll coordinator.

A content creator needs B-roll footage for this video topic:
"{topic}"

Generate exactly {count} search queries for stock footage sites like Pexels and Pixabay.

STRICT RULES:
1. English only
2. ONLY physically filmable, concrete objects or scenes — no abstract concepts
3. Each query must be 1-4 words max, highly specific
4. Think like a camera operator: what can you actually point a camera at?
5. Avoid: emotions, ideas, concepts, feelings, metaphors
6. Good examples: "slot machine lever", "laboratory pigeon", "casino neon sign", "dice rolling table", "human eye closeup"
7. Bad examples: "addiction", "curiosity", "psychological tension", "dopamine"

Output ONLY a comma-separated list. No numbering, no explanation, nothing else."""

        response = model.generate_content(prompt)
        raw = response.text.strip()
        keywords = [k.strip().strip('"').strip("'") for k in raw.split(',')]
        keywords = [k for k in keywords if k and len(k) > 1]
        return keywords[:count]
    except Exception as e:
        st.error(f"AI Hatası: {e}")
        return []

def download_from_pexels(query, folder, pexels_key, count=3):
    headers = {'Authorization': pexels_key}
    url = f"https://api.pexels.com/v1/search?query={urllib.parse.quote(query)}&per_page={count}&orientation=landscape&size=large"
    downloaded = []
    try:
        response = requests.get(url, headers=headers, timeout=10)
        data = response.json()
        if 'photos' in data:
            for i, photo in enumerate(data['photos']):
                # En yüksek kalite
                img_url = photo['src'].get('original', photo['src'].get('large2x', photo['src']['large']))
                filename = f"{clean_filename(query)}_pex_{i+1}.jpg"
                filepath = os.path.join(folder, filename)
                img_response = requests.get(img_url, timeout=20)
                if img_response.status_code == 200:
                    with open(filepath, 'wb') as f:
                        f.write(img_response.content)
                    downloaded.append(filepath)
    except Exception as e:
        pass
    return downloaded

def download_from_pixabay(query, folder, pixabay_key, count=3):
    url = f"https://pixabay.com/api/?key={pixabay_key}&q={urllib.parse.quote(query)}&image_type=photo&orientation=horizontal&per_page={count}&safesearch=true&min_width=1920&order=popular"
    downloaded = []
    try:
        response = requests.get(url, timeout=10)
        data = response.json()
        if 'hits' in data:
            for i, hit in enumerate(data['hits']):
                # En yüksek kalite URL
                img_url = hit.get('largeImageURL', hit.get('webformatURL'))
                filename = f"{clean_filename(query)}_pix_{i+1}.jpg"
                filepath = os.path.join(folder, filename)
                img_response = requests.get(img_url, timeout=20)
                if img_response.status_code == 200:
                    with open(filepath, 'wb') as f:
                        f.write(img_response.content)
                    downloaded.append(filepath)
    except Exception as e:
        pass
    return downloaded

def create_zip(base_folder):
    zip_path = base_folder + ".zip"
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(base_folder):
            for file in files:
                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path, base_folder)
                zipf.write(file_path, arcname)
    return zip_path

# ============================================================
# ARAYÜZ
# ============================================================

st.markdown("# 🎬 B-Roll Finder")
st.markdown('<p class="subtitle">Video konunu yaz — AI anahtar kelimeleri üretsin, görseller otomatik insin.</p>', unsafe_allow_html=True)

# Limit bar
remaining = FREE_LIMIT - st.session_state.usage_count
if remaining > 0:
    color = "#1DB954" if remaining > 1 else "#f0a500"
    st.markdown(f"""
    <div style="background:#1a1a1a;border:1px solid #2a2a2a;border-radius:12px;padding:12px 20px;margin-bottom:24px;display:flex;align-items:center;gap:12px;">
        <span style="font-size:1.3rem;">🆓</span>
        <span style="color:#aaa;font-size:0.95rem;">Ücretsiz kullanım: <strong style="color:{color};">{remaining}/{FREE_LIMIT}</strong> kaldı</span>
    </div>
    """, unsafe_allow_html=True)
else:
    st.markdown("""
    <div style="background:#2a1a1a;border:1px solid #E91429;border-radius:12px;padding:20px;margin-bottom:24px;">
        <div style="font-size:1.2rem;font-weight:700;color:#E91429;margin-bottom:8px;">🔒 Ücretsiz limit doldu</div>
        <div style="color:#aaa;margin-bottom:12px;">Sınırsız kullanım için kaynak kodu satın al — kendi bilgisayarında limitsiz çalıştır.</div>
        <a href="https://gumroad.com" target="_blank" style="background:#1DB954;color:white;padding:10px 24px;border-radius:20px;text-decoration:none;font-weight:700;">🛒 Gumroad'da Satın Al — $12</a>
    </div>
    """, unsafe_allow_html=True)
    st.stop()

# --- API AYARLARI ---
with st.expander("⚙️  API Key'lerini Gir", expanded=False):
    st.markdown("""
    <div style="color:#888;font-size:0.85rem;margin-bottom:14px;">
    Tüm API'lar ücretsiz. Kayıt ol, key al, yapıştır.<br>
    <a href="https://www.pexels.com/api/" target="_blank" style="color:#1DB954;">Pexels API</a> &nbsp;|&nbsp; 
    <a href="https://pixabay.com/api/" target="_blank" style="color:#1DB954;">Pixabay API</a> &nbsp;|&nbsp; 
    <a href="https://aistudio.google.com/" target="_blank" style="color:#1DB954;">Gemini API</a>
    </div>
    """, unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns(3)
    with col1:
        pexels_key = st.text_input("Pexels Key", type="password", placeholder="px-...")
    with col2:
        pixabay_key = st.text_input("Pixabay Key", type="password", placeholder="12345678-...")
    with col3:
        gemini_key = st.text_input("Gemini Key", type="password", placeholder="AIza...")

st.markdown('<div class="divider"></div>', unsafe_allow_html=True)

# --- KONU ---
st.markdown('<div class="section-label">Video Konusu</div>', unsafe_allow_html=True)
topic = st.text_area(
    "topic_input",
    placeholder="Örnek: İnternetin bağımlılık yapan mekanizmaları ve Skinner'ın güvercin deneyi...",
    height=100,
    label_visibility="collapsed"
)

# --- AYARLAR ---
col1, col2 = st.columns(2)
with col1:
    st.markdown('<div class="section-label">Kaç anahtar kelime?</div>', unsafe_allow_html=True)
    keyword_count = st.slider("kw", 3, 20, 10, label_visibility="collapsed")
with col2:
    st.markdown('<div class="section-label">Konu başına kaç görsel?</div>', unsafe_allow_html=True)
    photos_per_keyword = st.slider("ph", 1, 5, 3, label_visibility="collapsed")

st.markdown('<div class="divider"></div>', unsafe_allow_html=True)

# --- Son anahtar kelimeler göster ---
if st.session_state.last_keywords:
    st.markdown('<div class="section-label">Son üretilen anahtar kelimeler</div>', unsafe_allow_html=True)
    tags_html = "".join([f'<span class="keyword-tag">{k}</span>' for k in st.session_state.last_keywords])
    st.markdown(tags_html, unsafe_allow_html=True)
    st.markdown('<div class="divider"></div>', unsafe_allow_html=True)

# --- BUTON ---
if st.button("🚀  GÖRSELLERİ İNDİR"):
    if not topic.strip():
        st.warning("Lütfen bir video konusu yaz.")
    elif not pexels_key or not pixabay_key:
        st.warning("En az Pexels ve Pixabay key'lerini gir.")
    else:
        st.session_state.usage_count += 1

        with tempfile.TemporaryDirectory() as tmpdir:
            base_folder = os.path.join(tmpdir, clean_filename(topic)[:30])
            os.makedirs(base_folder)

            # Anahtar kelimeler
            with st.spinner("🧠  AI anahtar kelimeler üretiyor..."):
                if gemini_key:
                    keywords = get_keywords_from_ai(topic, gemini_key, keyword_count)
                else:
                    keywords = [w.strip() for w in topic.split() if len(w) > 3][:keyword_count]
                    st.info("Gemini key girilmedi — konudaki kelimeler direkt aranıyor.")

            if not keywords:
                st.error("Anahtar kelime üretilemedi.")
                st.stop()

            st.session_state.last_keywords = keywords

            # Tag göster
            tags_html = "".join([f'<span class="keyword-tag">{k}</span>' for k in keywords])
            st.markdown(f'<div style="margin-bottom:16px;">{tags_html}</div>', unsafe_allow_html=True)

            # İndirme
            total_downloaded = []
            progress_bar = st.progress(0)
            status_text = st.empty()

            for i, keyword in enumerate(keywords):
                status_text.markdown(f'<span style="color:#888;font-size:0.9rem;">⬇️ &nbsp;{keyword} &nbsp;<span style="color:#555;">({i+1}/{len(keywords)})</span></span>', unsafe_allow_html=True)

                kw_folder = os.path.join(base_folder, clean_filename(keyword))
                os.makedirs(kw_folder, exist_ok=True)

                pexels_files = download_from_pexels(keyword, kw_folder, pexels_key, photos_per_keyword)
                pixabay_files = download_from_pixabay(keyword, kw_folder, pixabay_key, photos_per_keyword)

                total_downloaded.extend(pexels_files + pixabay_files)
                progress_bar.progress((i + 1) / len(keywords))
                time.sleep(0.3)

            status_text.empty()

            # ZIP
            zip_path = create_zip(base_folder)
            with open(zip_path, 'rb') as f:
                zip_data = f.read()

            # Sonuç
            st.markdown('<div class="divider"></div>', unsafe_allow_html=True)
            
            c1, c2, c3 = st.columns(3)
            with c1:
                st.markdown(f'<div class="stat-box"><div class="stat-number">{len(keywords)}</div><div class="stat-label">Anahtar Kelime</div></div>', unsafe_allow_html=True)
            with c2:
                st.markdown(f'<div class="stat-box"><div class="stat-number">{len(total_downloaded)}</div><div class="stat-label">Görsel İndirildi</div></div>', unsafe_allow_html=True)
            with c3:
                size_mb = round(len(zip_data) / 1024 / 1024, 1)
                st.markdown(f'<div class="stat-box"><div class="stat-number">{size_mb}MB</div><div class="stat-label">Toplam Boyut</div></div>', unsafe_allow_html=True)

            st.markdown("<br>", unsafe_allow_html=True)
            st.download_button(
                label="⬇️  ZIP İNDİR",
                data=zip_data,
                file_name=f"broll_{clean_filename(topic)[:20]}.zip",
                mime="application/zip",
                use_container_width=True
            )

st.markdown('<div class="divider"></div>', unsafe_allow_html=True)
st.markdown('<p style="text-align:center;color:#333;font-size:0.8rem;">B-Roll Finder &nbsp;•&nbsp; Pexels &amp; Pixabay &nbsp;•&nbsp; Gemini AI</p>', unsafe_allow_html=True)
