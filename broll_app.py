import streamlit as st
import os
import requests
import urllib.parse
import re
import zipfile
import tempfile
import time
import base64
import google.generativeai as genai
import firebase_admin
from firebase_admin import credentials, firestore
from datetime import datetime
from collections import defaultdict

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
st.set_page_config(page_title="B-Roll Finder", page_icon="🎬", layout="wide")

# --- STYLES ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;900&display=swap');
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; background-color: #121212; color: #FFFFFF; }
    .block-container { max-width: 860px; margin: auto; padding-top: 2.5rem; padding-bottom: 3rem; }
    h1 { font-size: 2.6rem !important; font-weight: 900 !important; color: #1DB954 !important; letter-spacing: -1.5px; margin-bottom: 0 !important; }
    .subtitle { color: #6a6a6a; font-size: 0.95rem; margin-top: 6px; margin-bottom: 32px; }
    .label { font-size: 0.7rem; font-weight: 700; letter-spacing: 2.5px; text-transform: uppercase; color: #535353; margin-bottom: 8px; }
    .stTextInput > div > input, .stTextArea > div > textarea {
        background-color: #282828 !important; border: 1.5px solid #3a3a3a !important;
        border-radius: 8px !important; color: #FFFFFF !important; font-size: 0.95rem !important; padding: 12px 16px !important;
    }
    .stTextInput > div > input:focus, .stTextArea > div > textarea:focus {
        border-color: #1DB954 !important; box-shadow: 0 0 0 3px rgba(29,185,84,0.12) !important;
    }
    .stButton > button {
        background: #1DB954 !important; color: #000 !important; font-size: 0.9rem !important;
        font-weight: 700 !important; height: 48px !important; border-radius: 24px !important;
        border: none !important; width: 100% !important; letter-spacing: 1px; text-transform: uppercase;
    }
    .stButton > button:hover { background: #1ED760 !important; transform: scale(1.02); }
    .stExpander { background-color: #1a1a1a !important; border: 1px solid #282828 !important; border-radius: 12px !important; }
    .pill { display: inline-block; background: #282828; color: #1DB954; border-radius: 20px; padding: 5px 14px; margin: 3px 2px; font-size: 0.8rem; font-weight: 600; border: 1px solid #333; }
    .stat { background: #181818; border: 1px solid #282828; border-radius: 12px; padding: 22px 16px; text-align: center; }
    .stat-n { font-size: 2.2rem; font-weight: 900; color: #1DB954; line-height: 1; }
    .stat-l { font-size: 0.72rem; color: #535353; margin-top: 6px; text-transform: uppercase; letter-spacing: 1px; }
    .hr { border: none; border-top: 1px solid #282828; margin: 28px 0; }
    .limit-badge { background: #181818; border: 1px solid #282828; border-radius: 10px; padding: 12px 18px; margin-bottom: 28px; font-size: 0.88rem; color: #b3b3b3; }
    .paywall { background: #1a0a0a; border: 1px solid #533; border-radius: 14px; padding: 36px 28px; margin-bottom: 24px; text-align: center; }
    .pro-table { width: 100%; border-collapse: collapse; margin-top: 12px; }
    .pro-table th { background: #1a1a1a; color: #1DB954; font-size: 0.75rem; letter-spacing: 1px; text-transform: uppercase; padding: 10px 14px; text-align: left; }
    .pro-table td { padding: 10px 14px; font-size: 0.85rem; border-top: 1px solid #282828; color: #b3b3b3; }
    .pro-table .check { color: #1DB954; font-weight: 700; }
    .pro-table .cross { color: #535353; }

    /* Clickable image card */
    .img-card {
        position: relative;
        border-radius: 10px;
        overflow: hidden;
        cursor: pointer;
        border: 2px solid #282828;
        transition: border 0.15s;
        margin-bottom: 6px;
    }
    .img-card:hover { border-color: #1DB954; }
    .img-card.selected { border-color: #1DB954; }
    .img-card.deselected { border-color: #333; opacity: 0.45; }
    .img-card img { width: 100%; height: 110px; object-fit: cover; display: block; }
    .img-card .overlay {
        position: absolute; top: 6px; right: 6px;
        width: 22px; height: 22px; border-radius: 50%;
        background: #1DB954; display: flex; align-items: center; justify-content: center;
        font-size: 13px; font-weight: 700; color: #000;
    }
    .img-card.deselected .overlay { background: #333; color: #666; }
    .img-card .card-label { font-size: 0.7rem; color: #666; padding: 5px 8px; background: #181818; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }

    .section-header { font-size: 0.75rem; font-weight: 700; letter-spacing: 2px; text-transform: uppercase; color: #535353; margin: 20px 0 10px; }
    .history-item { background: #181818; border: 1px solid #282828; border-radius: 8px; padding: 10px 14px; margin: 4px 0; font-size: 0.85rem; color: #b3b3b3; }
    .footer { text-align: center; color: #333; font-size: 0.75rem; margin-top: 20px; }
    .made-by { text-align: center; color: #333; font-size: 0.78rem; margin-top: 8px; }
    .made-by a { color: #1DB954; text-decoration: none; }
    .made-by a:hover { color: #1ED760; }
    .prog-text { color: #535353; font-size: 0.85rem; margin: 6px 0; }

    /* Hide default checkbox labels for image toggle */
    .img-toggle { display: none; }
</style>
""", unsafe_allow_html=True)

# --- INIT STATE ---
db = init_firebase()

defaults = {
    "usage_count": 0,
    "visit_logged": False,
    "downloaded_files": [],
    "selected_files": {},
    "show_preview": False,
    "search_history": [],
    "stage": "input",        # "input" | "confirm_keywords" | "preview"
    "pending_keywords": [],  # keywords waiting for user confirmation
    "confirmed_keywords": [],
    "pending_topic": "",
    "pending_pexels": "",
    "pending_pixabay": "",
    "pending_photos_per_kw": 3,
}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

if not st.session_state.visit_logged:
    log_event(db, "visit")
    st.session_state.visit_logged = True

FREE_LIMIT = 3

# --- HELPERS ---
def clean_filename(text):
    text = str(text).replace(" ", "_").lower()
    tr_map = {'ı':'i','ğ':'g','ü':'u','ş':'s','ö':'o','ç':'c','İ':'I','Ğ':'G','Ü':'U','Ş':'S','Ö':'O','Ç':'C'}
    for tr, en in tr_map.items():
        text = text.replace(tr, en)
    return re.sub(r'[\\/*?:"<>|]', "", text)[:40]

def clean_keyword(kw):
    # Remove punctuation except hyphens and spaces
    kw = re.sub(r"[^\w\s\-]", "", kw)
    return kw.strip()

def get_keywords(topic, api_key, count):
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-2.0-flash')
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
        kws = [clean_keyword(k) for k in resp.text.strip().split(',')]
        return [k for k in kws if k and len(k) > 1][:count]
    except Exception as e:
        st.error(f"AI error: {e}")
        return []

def keywords_from_topic(topic, count):
    # Fallback: extract clean words from topic
    words = re.sub(r"[^\w\s]", "", topic).split()
    words = [w for w in words if len(w) > 3]
    return words[:count]

def pexels_download(query, folder, key, count):
    headers = {'Authorization': key}
    url = f"https://api.pexels.com/v1/search?query={urllib.parse.quote(query)}&per_page={count}&orientation=landscape&size=large"
    files = []
    try:
        data = requests.get(url, headers=headers, timeout=10).json()
        for i, p in enumerate(data.get('photos', [])):
            img_url = p['src'].get('large2x') or p['src']['large']
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

def make_zip(files):
    import io
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED) as zf:
        for fpath in files:
            if os.path.exists(fpath):
                parts = fpath.replace("\\", "/").split("/")
                arcname = "/".join(parts[-2:]) if len(parts) >= 2 else os.path.basename(fpath)
                zf.write(fpath, arcname)
    buf.seek(0)
    return buf.read()

def img_to_base64(fpath):
    try:
        with open(fpath, 'rb') as f:
            return base64.b64encode(f.read()).decode()
    except:
        return None

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
        <div style="color:#b3b3b3;margin-bottom:20px;font-size:0.9rem;max-width:400px;margin-left:auto;margin-right:auto;">
            Buy the source code once — run it on your own machine with no limits and no subscriptions.
        </div>
        <table class="pro-table" style="max-width:440px;margin:0 auto 24px;">
            <tr><th>Feature</th><th>Free</th><th>Full Version</th></tr>
            <tr><td>Uses per session</td><td class="cross">3</td><td class="check">Unlimited</td></tr>
            <tr><td>Images per keyword</td><td class="cross">Up to 5</td><td class="check">Up to 10</td></tr>
            <tr><td>Image preview &amp; select</td><td class="check">✓</td><td class="check">✓</td></tr>
            <tr><td>Keyword editor</td><td class="check">✓</td><td class="check">✓</td></tr>
            <tr><td>Search history</td><td class="check">✓</td><td class="check">✓</td></tr>
            <tr><td>Source code</td><td class="cross">✗</td><td class="check">✓</td></tr>
        </table>
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
        All APIs are completely free. Sign up, grab your key, paste below.<br>
        <a href="https://www.pexels.com/api/" target="_blank" style="color:#1DB954;">Pexels</a>
        &nbsp;·&nbsp;
        <a href="https://pixabay.com/api/" target="_blank" style="color:#1DB954;">Pixabay</a>
        &nbsp;·&nbsp;
        <a href="https://aistudio.google.com/" target="_blank" style="color:#1DB954;">Gemini (Google AI Studio)</a>
    </div>
    """, unsafe_allow_html=True)
    c1, c2, c3 = st.columns(3)
    with c1:
        pexels_key = st.text_input("Pexels API Key", type="password", placeholder="px-...", key="pexels_input")
    with c2:
        pixabay_key = st.text_input("Pixabay API Key", type="password", placeholder="53371816-...", key="pixabay_input")
    with c3:
        gemini_key = st.text_input("Gemini API Key", type="password", placeholder="AIzaSy...", key="gemini_input")

st.markdown('<div class="hr"></div>', unsafe_allow_html=True)

# --- SEARCH HISTORY ---
if st.session_state.search_history:
    with st.expander("🕓  Recent searches", expanded=False):
        for item in st.session_state.search_history[-5:][::-1]:
            st.markdown(f'<div class="history-item">🔍 &nbsp;{item}</div>', unsafe_allow_html=True)

# ============================================================
# STAGE 1: INPUT
# ============================================================
if st.session_state.stage == "input":
    st.markdown('<div class="label">Video Topic</div>', unsafe_allow_html=True)
    topic = st.text_area("topic", placeholder="e.g. The science of sleep, REM cycles, and why we dream...", height=90, label_visibility="collapsed")

    c1, c2 = st.columns(2)
    with c1:
        st.markdown('<div class="label">Keywords to generate</div>', unsafe_allow_html=True)
        keyword_count = st.slider("kw", 3, 20, 10, label_visibility="collapsed")
    with c2:
        st.markdown('<div class="label">Images per keyword</div>', unsafe_allow_html=True)
        photos_per_kw = st.slider("ph", 1, 5, 3, label_visibility="collapsed")

    st.markdown('<div class="hr"></div>', unsafe_allow_html=True)

    if st.button("🔍  GENERATE KEYWORDS"):
        if not topic.strip():
            st.warning("Please enter a video topic.")
        elif not pexels_key or not pixabay_key:
            st.warning("Please enter at least your Pexels and Pixabay API keys.")
        else:
            with st.spinner("Generating keywords with AI..."):
                if gemini_key:
                    keywords = get_keywords(topic, gemini_key, keyword_count)
                else:
                    keywords = keywords_from_topic(topic, keyword_count)
                    st.info("No Gemini key — extracted words from topic directly.")

            if not keywords:
                st.error("Could not generate keywords.")
            else:
                st.session_state.pending_keywords = keywords
                st.session_state.pending_topic = topic
                st.session_state.pending_pexels = pexels_key
                st.session_state.pending_pixabay = pixabay_key
                st.session_state.pending_photos_per_kw = photos_per_kw
                st.session_state.stage = "confirm_keywords"
                st.rerun()

# ============================================================
# STAGE 2: CONFIRM / EDIT KEYWORDS
# ============================================================
elif st.session_state.stage == "confirm_keywords":
    st.markdown('<div class="label">Review & Edit Keywords</div>', unsafe_allow_html=True)
    st.markdown('<div style="color:#6a6a6a;font-size:0.83rem;margin-bottom:12px;">One keyword per line. Edit, add or remove. Each line = one search.</div>', unsafe_allow_html=True)

    kw_text = st.text_area(
        "kw_editor",
        value="\n".join(st.session_state.pending_keywords),
        height=220,
        label_visibility="collapsed"
    )

    st.markdown('<div class="hr"></div>', unsafe_allow_html=True)

    c1, c2 = st.columns(2)
    with c1:
        if st.button("← Back", key="back_btn"):
            st.session_state.stage = "input"
            st.rerun()
    with c2:
        if st.button("⬇  DOWNLOAD FOOTAGE", key="download_btn"):
            # Parse edited keywords
            edited_kws = [clean_keyword(k) for k in kw_text.split("\n") if k.strip()]
            edited_kws = [k for k in edited_kws if k and len(k) > 1]

            if not edited_kws:
                st.error("No keywords found.")
            else:
                st.session_state.confirmed_keywords = edited_kws
                st.session_state.usage_count += 1
                st.session_state.downloaded_files = []
                st.session_state.selected_files = {}
                log_event(db, "search")

                # Save history
                topic = st.session_state.pending_topic
                if topic not in st.session_state.search_history:
                    st.session_state.search_history.append(topic)
                if len(st.session_state.search_history) > 10:
                    st.session_state.search_history = st.session_state.search_history[-10:]

                tmp = tempfile.mkdtemp()
                folder = os.path.join(tmp, clean_filename(topic)[:30])
                os.makedirs(folder, exist_ok=True)

                pills = "".join([f'<span class="pill">{k}</span>' for k in edited_kws])
                st.markdown(f'<div style="margin:10px 0 18px;">{pills}</div>', unsafe_allow_html=True)

                all_files = []
                bar = st.progress(0)
                status = st.empty()

                pexels_key_used = st.session_state.pending_pexels
                pixabay_key_used = st.session_state.pending_pixabay
                photos_per_kw = st.session_state.pending_photos_per_kw

                for i, kw in enumerate(edited_kws):
                    status.markdown(f'<p class="prog-text">↓ &nbsp;{kw} &nbsp;({i+1}/{len(edited_kws)})</p>', unsafe_allow_html=True)
                    kw_folder = os.path.join(folder, clean_filename(kw))
                    os.makedirs(kw_folder, exist_ok=True)
                    all_files += pexels_download(kw, kw_folder, pexels_key_used, photos_per_kw)
                    all_files += pixabay_download(kw, kw_folder, pixabay_key_used, photos_per_kw)
                    bar.progress((i + 1) / len(edited_kws))
                    time.sleep(0.25)

                status.empty()
                bar.empty()

                st.session_state.downloaded_files = all_files
                st.session_state.selected_files = {f: True for f in all_files}
                st.session_state.stage = "preview"
                st.rerun()

# ============================================================
# STAGE 3: PREVIEW & DOWNLOAD
# ============================================================
elif st.session_state.stage == "preview" and st.session_state.downloaded_files:
    files = st.session_state.downloaded_files

    selected_count = sum(1 for v in st.session_state.selected_files.values() if v)
    s1, s2, s3 = st.columns(3)
    with s1:
        st.markdown(f'<div class="stat"><div class="stat-n">{len(st.session_state.confirmed_keywords)}</div><div class="stat-l">Keywords</div></div>', unsafe_allow_html=True)
    with s2:
        st.markdown(f'<div class="stat"><div class="stat-n">{len(files)}</div><div class="stat-l">Images Found</div></div>', unsafe_allow_html=True)
    with s3:
        st.markdown(f'<div class="stat"><div class="stat-n">{selected_count}</div><div class="stat-l">Selected</div></div>', unsafe_allow_html=True)

    st.markdown('<div class="hr"></div>', unsafe_allow_html=True)
    st.markdown('<div class="label">Click image or checkbox to deselect</div>', unsafe_allow_html=True)

    groups = defaultdict(list)
    for fpath in files:
        folder_name = os.path.basename(os.path.dirname(fpath))
        groups[folder_name].append(fpath)

    for group_name, group_files in groups.items():
        st.markdown(f'<div class="section-header">{group_name.replace("_", " ")}</div>', unsafe_allow_html=True)
        cols = st.columns(min(len(group_files), 5))
        for idx, fpath in enumerate(group_files):
            with cols[idx % 5]:
                is_selected = st.session_state.selected_files.get(fpath, True)
                b64 = img_to_base64(fpath)
                card_class = "selected" if is_selected else "deselected"
                check_icon = "✓" if is_selected else "✗"

                if b64:
                    clicked = st.button(
                        " ",
                        key=f"imgbtn_{fpath}",
                        help=os.path.basename(fpath)
                    )
                    if clicked:
                        st.session_state.selected_files[fpath] = not is_selected
                        st.rerun()

                    st.markdown(f"""
                    <div class="img-card {card_class}" style="margin-top:-48px;pointer-events:none;">
                        <img src="data:image/jpeg;base64,{b64}" />
                        <div class="overlay">{check_icon}</div>
                        <div class="card-label">{os.path.basename(fpath)}</div>
                    </div>
                    """, unsafe_allow_html=True)

                cb = st.checkbox(
                    "Keep",
                    value=st.session_state.selected_files.get(fpath, True),
                    key=f"cb_{fpath}"
                )
                if cb != st.session_state.selected_files.get(fpath, True):
                    st.session_state.selected_files[fpath] = cb
                    st.rerun()

    st.markdown('<div class="hr"></div>', unsafe_allow_html=True)

    col_back, col_dl = st.columns([1, 3])
    with col_back:
        if st.button("← New Search", key="new_search"):
            st.session_state.stage = "input"
            st.session_state.downloaded_files = []
            st.session_state.selected_files = {}
            st.session_state.confirmed_keywords = []
            st.rerun()

    final_files = [f for f, v in st.session_state.selected_files.items() if v]

    with col_dl:
        if final_files:
            zip_data = make_zip(final_files)
            size_mb = round(len(zip_data) / 1024 / 1024, 1)
            st.markdown(f'<p style="color:#535353;font-size:0.85rem;margin-bottom:8px;">{len(final_files)} images · {size_mb} MB</p>', unsafe_allow_html=True)
            log_event(db, "download")
            st.download_button(
                label=f"⬇  DOWNLOAD ZIP  ({len(final_files)} images)",
                data=zip_data,
                file_name=f"broll_{int(time.time())}.zip",
                mime="application/zip",
                use_container_width=True
            )
        else:
            st.warning("No images selected.")

st.markdown('<div class="hr"></div>', unsafe_allow_html=True)
st.markdown('<p class="footer">B-Roll Finder &nbsp;·&nbsp; Pexels &amp; Pixabay &nbsp;·&nbsp; Gemini AI</p>', unsafe_allow_html=True)
st.markdown('<p class="made-by">Made by <a href="https://github.com/Wagandamundus" target="_blank">Wagandamundus</a></p>', unsafe_allow_html=True)
