import streamlit as st
import os
import requests
import urllib.parse
import re
import zipfile
import tempfile
import time
import google.generativeai as genai
import firebase_admin
from firebase_admin import credentials, firestore
from datetime import datetime

# --- FIREBASE ---
@st.cache_resource
def init_firebase():
    if not firebase_admin._apps:
        key = dict(st.secrets["firebase"])
        cred = credentials.Certificate(key)
        firebase_admin.initialize_app(cred)
    return firestore.client()

def log_event(db, event_type):
    try:
        db.collection("analytics").add({
            "event": event_type,
            "timestamp": datetime.utcnow()
        })
    except:
        pass

# --- PAGE CONFIG ---
st.set_page_config(
    page_title="B-Roll Finder",
    page_icon="🎬",
    layout="wide"
)

# --- STYLES ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;900&display=swap');

    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
        background-color: #121212;
        color: #FFFFFF;
    }

    .block-container {
        max-width: 780px;
        margin: auto;
        padding-top: 2.5rem;
        padding-bottom: 3rem;
    }

    h1 {
        font-size: 2.6rem !important;
        font-weight: 900 !important;
        color: #1DB954 !important;
        letter-spacing: -1.5px;
        margin-bottom: 0 !important;
    }

    .subtitle {
        color: #6a6a6a;
        font-size: 0.95rem;
        margin-top: 6px;
        margin-bottom: 32px;
    }

    .label {
        font-size: 0.7rem;
        font-weight: 700;
        letter-spacing: 2.5px;
        text-transform: uppercase;
        color: #535353;
        margin-bottom: 8px;
    }

    .stTextInput > div > input,
    .stTextArea > div > textarea {
        background-color: #282828 !important;
        border: 1.5px solid #3a3a3a !important;
        border-radius: 8px !important;
        color: #FFFFFF !important;
        font-size: 0.95rem !important;
        padding: 12px 16px !important;
    }
    .stTextInput > div > input:focus,
    .stTextArea > div > textarea:focus {
        border-color: #1DB954 !important;
        box-shadow: 0 0 0 3px rgba(29,185,84,0.12) !important;
    }

    .stButton > button {
        background: #1DB954 !important;
        color: #000 !important;
        font-size: 0.9rem !important;
        font-weight: 700 !important;
        height: 48px !important;
        border-radius: 24px !important;
        border: none !important;
        width: 100% !important;
        letter-spacing: 1px;
        text-transform: uppercase;
    }
    .stButton > button:hover {
        background: #1ED760 !important;
        transform: scale(1.02);
    }

    .stExpander {
        background-color: #1a1a1a !important;
        border: 1px solid #282828 !important;
        border-radius: 12px !important;
    }

    .pill {
        display: inline-block;
        background: #282828;
        color: #1DB954;
        border-radius: 20px;
        padding: 5px 14px;
        margin: 3px 2px;
        font-size: 0.8rem;
        font-weight: 600;
        border: 1px solid #333;
    }

    .stat {
        background: #181818;
        border: 1px solid #282828;
        border-radius: 12px;
        padding: 22px 16px;
        text-align: center;
    }
    .stat-n {
        font-size: 2.2rem;
        font-weight: 900;
        color: #1DB954;
        line-height: 1;
    }
    .stat-l {
        font-size: 0.72rem;
        color: #535353;
        margin-top: 6px;
        text-transform: uppercase;
        letter-spacing: 1px;
    }

    .hr { border: none; border-top: 1px solid #282828; margin: 28px 0; }

    .limit-badge {
        background: #181818;
        border: 1px solid #282828;
        border-radius: 10px;
        padding: 12px 18px;
        margin-bottom: 28px;
        font-size: 0.88rem;
        color: #b3b3b3;
    }

    .paywall {
        background: #1a0a0a;
        border: 1px solid #533;
        border-radius: 14px;
        padding: 36px 28px;
        margin-bottom: 24px;
        text-align: center;
    }

    .footer {
        text-align: center;
        color: #333;
        font-size: 0.75rem;
        margin-top: 20px;
    }

    .prog-text {
        color: #535353;
        font-size: 0.85rem;
        margin: 6px 0;
    }
</style>
""", unsafe_allow_html=True)

# --- INIT ---
db = init_firebase()

if "usage_count" not in st.session_state:
    st.session_state.usage_count = 0
if "last_keywords" not in st.session_state:
    st.session_state.last_keywords = []
if "visit_logged" not in st.session_state:
    st.session_state.visit_logged = False

if not st.session_state.visit_logged:
    log_event(db, "visit")
    st.session_state.visit_logged = True

FREE_LIMIT = 3

# --- HELPERS ---
def clean_filename(text):
    text = str(text).replace(" ", "_").lower()
    tr_map = {'ı':'i','ğ':'g','ü':'u','ş':'s','ö':'o','ç':'c',
              'İ':'I','Ğ':'G','Ü':'U','Ş':'S','Ö':'O','Ç':'C'}
    for tr, en in tr_map.items():
        text = text.replace(tr, en)
    return re.sub(r'[\\/*?:"<>|]', "", text)[:40]

def get_keywords(topic, api_key, count):
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-2.5-flash')
        prompt = f"""You are a professional video editor and B-roll coordinator.

Video topic: "{topic}"

Generate exactly {count} stock footage search queries for Pexels and Pixabay.

RULES:
- English only
- Concrete, physically filmable objects or scenes ONLY
- 1-4 words each, highly specific
- Think like a camera operator: what can you actually film?
- NO abstract concepts, emotions, metaphors, or ideas
- Good examples: "slot machine lever", "lab rat cage", "neon casino sign", "person sleeping bed"
- Bad examples: "addiction", "anxiety", "psychological tension"

Output ONLY a comma-separated list. Nothing else."""

        resp = model.generate_content(prompt)
        kws = [k.strip().strip('"').strip("'") for k in resp.text.strip().split(',')]
        return [k for k in kws if k and len(k) > 1][:count]
    except Exception as e:
        st.error(f"AI error: {e}")
        return []

def pexels_download(query, folder, key, count):
    headers = {'Authorization': key}
    url = f"https://api.pexels.com/v1/search?query={urllib.parse.quote(query)}&per_page={count}&orientation=landscape&size=large"
    files = []
    try:
        data = requests.get(url, headers=headers, timeout=10).json()
        for i, p in enumerate(data.get('photos', [])):
            img_url = p['src'].get('original') or p['src'].get('large2x') or p['src']['large']
            fname = f"{clean_filename(query)}_pex_{i+1}.jpg"
            fpath = os.path.join(folder, fname)
            r = requests.get(img_url, timeout=20)
            if r.status_code == 200:
                with open(fpath, 'wb') as f:
                    f.write(r.content)
                files.append(fpath)
    except:
        pass
    return files

def pixabay_download(query, folder, key, count):
    url = f"https://pixabay.com/api/?key={key}&q={urllib.parse.quote(query)}&image_type=photo&orientation=horizontal&per_page={count}&safesearch=true&min_width=1920&order=popular"
    files = []
    try:
        data = requests.get(url, timeout=10).json()
        for i, h in enumerate(data.get('hits', [])):
            img_url = h.get('largeImageURL') or h.get('webformatURL')
            fname = f"{clean_filename(query)}_pix_{i+1}.jpg"
            fpath = os.path.join(folder, fname)
            r = requests.get(img_url, timeout=20)
            if r.status_code == 200:
                with open(fpath, 'wb') as f:
                    f.write(r.content)
                files.append(fpath)
    except:
        pass
    return files

def make_zip(folder):
    zpath = folder + ".zip"
    with zipfile.ZipFile(zpath, 'w', zipfile.ZIP_DEFLATED) as zf:
        for root, _, files in os.walk(folder):
            for file in files:
                fp = os.path.join(root, file)
                zf.write(fp, os.path.relpath(fp, folder))
    return zpath

# ============================================================
# UI
# ============================================================

st.markdown("# 🎬 B-Roll Finder")
st.markdown('<p class="subtitle">Describe your video — AI picks the keywords, footage downloads itself.</p>', unsafe_allow_html=True)

# --- LIMIT ---
remaining = FREE_LIMIT - st.session_state.usage_count
if remaining > 0:
    color = "#1DB954" if remaining > 1 else "#f59b00"
    st.markdown(f"""
    <div class="limit-badge">
        🆓 &nbsp; Free uses remaining: <strong style="color:{color};">{remaining} / {FREE_LIMIT}</strong>
        &nbsp;·&nbsp; <span style="color:#535353;">Buy once for unlimited use</span>
    </div>
    """, unsafe_allow_html=True)
else:
    st.markdown("""
    <div class="paywall">
        <div style="font-size:2rem;margin-bottom:12px;">🔒</div>
        <div style="font-size:1.2rem;font-weight:700;margin-bottom:10px;">Free limit reached</div>
        <div style="color:#b3b3b3;margin-bottom:24px;font-size:0.9rem;max-width:380px;margin-left:auto;margin-right:auto;">
            Buy the source code once — run it on your own machine with no limits and no subscriptions.
        </div>
        <a href="https://gumroad.com" target="_blank"
           style="background:#1DB954;color:#000;padding:13px 32px;border-radius:24px;
                  text-decoration:none;font-weight:700;font-size:0.9rem;letter-spacing:0.5px;">
            GET IT ON GUMROAD — $12
        </a>
    </div>
    """, unsafe_allow_html=True)
    st.stop()

# --- API KEYS ---
with st.expander("⚙️  API Keys  —  all free", expanded=False):
    st.markdown("""
    <div style="color:#6a6a6a;font-size:0.83rem;margin-bottom:14px;line-height:1.8;">
        All three APIs are completely free. Sign up, grab your key, paste below.<br>
        <a href="https://www.pexels.com/api/" target="_blank" style="color:#1DB954;">Pexels</a>
        &nbsp;·&nbsp;
        <a href="https://pixabay.com/api/" target="_blank" style="color:#1DB954;">Pixabay</a>
        &nbsp;·&nbsp;
        <a href="https://aistudio.google.com/" target="_blank" style="color:#1DB954;">Gemini (Google AI Studio)</a>
    </div>
    """, unsafe_allow_html=True)
    c1, c2, c3 = st.columns(3)
    with c1:
        pexels_key = st.text_input("Pexels API Key", type="password", placeholder="px-...")
    with c2:
        pixabay_key = st.text_input("Pixabay API Key", type="password", placeholder="53371816-...")
    with c3:
        gemini_key = st.text_input("Gemini API Key", type="password", placeholder="AIzaSy...")

st.markdown('<div class="hr"></div>', unsafe_allow_html=True)

# --- TOPIC ---
st.markdown('<div class="label">Video Topic</div>', unsafe_allow_html=True)
topic = st.text_area(
    "topic",
    placeholder="e.g. The science of sleep, REM cycles, and why we dream...",
    height=90,
    label_visibility="collapsed"
)

# --- SETTINGS ---
c1, c2 = st.columns(2)
with c1:
    st.markdown('<div class="label">Keywords to generate</div>', unsafe_allow_html=True)
    keyword_count = st.slider("kw", 3, 20, 10, label_visibility="collapsed")
with c2:
    st.markdown('<div class="label">Images per keyword</div>', unsafe_allow_html=True)
    photos_per_kw = st.slider("ph", 1, 5, 3, label_visibility="collapsed")

# --- LAST KEYWORDS ---
if st.session_state.last_keywords:
    st.markdown('<div class="hr"></div>', unsafe_allow_html=True)
    st.markdown('<div class="label">Last generated keywords</div>', unsafe_allow_html=True)
    pills = "".join([f'<span class="pill">{k}</span>' for k in st.session_state.last_keywords])
    st.markdown(pills, unsafe_allow_html=True)

st.markdown('<div class="hr"></div>', unsafe_allow_html=True)

# --- BUTTON ---
if st.button("⬇  FIND B-ROLL"):
    if not topic.strip():
        st.warning("Please enter a video topic.")
    elif not pexels_key or not pixabay_key:
        st.warning("Please enter at least your Pexels and Pixabay API keys.")
    else:
        st.session_state.usage_count += 1
        log_event(db, "search")

        with tempfile.TemporaryDirectory() as tmpdir:
            folder = os.path.join(tmpdir, clean_filename(topic)[:30])
            os.makedirs(folder)

            with st.spinner("Generating keywords with AI..."):
                if gemini_key:
                    keywords = get_keywords(topic, gemini_key, keyword_count)
                else:
                    keywords = [w for w in topic.split() if len(w) > 3][:keyword_count]
                    st.info("No Gemini key provided — searching topic words directly.")

            if not keywords:
                st.error("Could not generate keywords. Check your Gemini API key.")
                st.stop()

            st.session_state.last_keywords = keywords
            pills = "".join([f'<span class="pill">{k}</span>' for k in keywords])
            st.markdown(f'<div style="margin:10px 0 18px;">{pills}</div>', unsafe_allow_html=True)

            all_files = []
            bar = st.progress(0)
            status = st.empty()

            for i, kw in enumerate(keywords):
                status.markdown(f'<p class="prog-text">↓ &nbsp;{kw} &nbsp;({i+1}/{len(keywords)})</p>', unsafe_allow_html=True)
                kw_folder = os.path.join(folder, clean_filename(kw))
                os.makedirs(kw_folder, exist_ok=True)
                all_files += pexels_download(kw, kw_folder, pexels_key, photos_per_kw)
                all_files += pixabay_download(kw, kw_folder, pixabay_key, photos_per_kw)
                bar.progress((i + 1) / len(keywords))
                time.sleep(0.25)

            status.empty()

            zip_path = make_zip(folder)
            with open(zip_path, 'rb') as f:
                zip_data = f.read()

            st.markdown('<div class="hr"></div>', unsafe_allow_html=True)
            s1, s2, s3 = st.columns(3)
            size_mb = round(len(zip_data) / 1024 / 1024, 1)
            with s1:
                st.markdown(f'<div class="stat"><div class="stat-n">{len(keywords)}</div><div class="stat-l">Keywords</div></div>', unsafe_allow_html=True)
            with s2:
                st.markdown(f'<div class="stat"><div class="stat-n">{len(all_files)}</div><div class="stat-l">Images Found</div></div>', unsafe_allow_html=True)
            with s3:
                st.markdown(f'<div class="stat"><div class="stat-n">{size_mb}MB</div><div class="stat-l">Total Size</div></div>', unsafe_allow_html=True)

            st.markdown("<br>", unsafe_allow_html=True)
            log_event(db, "download")
            st.download_button(
                label="⬇  DOWNLOAD ZIP",
                data=zip_data,
                file_name=f"broll_{clean_filename(topic)[:20]}.zip",
                mime="application/zip",
                use_container_width=True
            )

st.markdown('<div class="hr"></div>', unsafe_allow_html=True)
st.markdown('<p class="footer">B-Roll Finder &nbsp;·&nbsp; Pexels &amp; Pixabay &nbsp;·&nbsp; Gemini AI</p>', unsafe_allow_html=True)
