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

st.set_page_config(page_title="B-Roll Finder", page_icon="🎬", layout="wide")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;900&display=swap');

html, body, [class*="css"] {
    font-family: 'Inter', sans-serif;
    background-color: #121212;
    color: #FFFFFF;
}
.block-container {
    max-width: 920px;
    margin: auto;
    padding-top: 2.5rem;
    padding-bottom: 4rem;
}
h1 {
    font-size: 2.6rem !important;
    font-weight: 900 !important;
    color: #1DB954 !important;
    letter-spacing: -1.5px;
    margin-bottom: 0 !important;
}
.subtitle { color: #6a6a6a; font-size: 0.95rem; margin-top: 6px; margin-bottom: 32px; }
.label { font-size: 0.7rem; font-weight: 700; letter-spacing: 2.5px; text-transform: uppercase; color: #535353; margin-bottom: 8px; }

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

/* All buttons base */
.stButton > button {
    background: #1DB954 !important;
    color: #000 !important;
    font-size: 0.88rem !important;
    font-weight: 700 !important;
    height: 44px !important;
    border-radius: 22px !important;
    border: none !important;
    width: 100% !important;
    letter-spacing: 0.8px;
    text-transform: uppercase;
}
.stButton > button:hover { background: #1ED760 !important; }

/* Danger button (remove) */
button[kind="secondary"] {
    background: #2a1a1a !important;
    color: #e05555 !important;
    border: 1px solid #533 !important;
}
button[kind="secondary"]:hover {
    background: #E91429 !important;
    color: #fff !important;
}

.stExpander {
    background-color: #181818 !important;
    border: 1px solid #282828 !important;
    border-radius: 12px !important;
    margin-bottom: 8px !important;
}
.stExpander summary {
    font-size: 0.85rem !important;
    font-weight: 700 !important;
    color: #e0e0e0 !important;
    letter-spacing: 0.5px;
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
.pro-table { width: 100%; border-collapse: collapse; margin: 12px auto 24px; }
.pro-table th { background: #1a1a1a; color: #1DB954; font-size: 0.75rem; letter-spacing: 1px; text-transform: uppercase; padding: 10px 14px; text-align: left; }
.pro-table td { padding: 10px 14px; font-size: 0.85rem; border-top: 1px solid #282828; color: #b3b3b3; }
.pro-table .check { color: #1DB954; font-weight: 700; }
.pro-table .cross { color: #535353; }

.stat { background: #181818; border: 1px solid #282828; border-radius: 12px; padding: 22px 16px; text-align: center; }
.stat-n { font-size: 2.2rem; font-weight: 900; color: #1DB954; line-height: 1; }
.stat-l { font-size: 0.72rem; color: #535353; margin-top: 6px; text-transform: uppercase; letter-spacing: 1px; }

/* Image card - click handled by button overlay */
.img-outer {
    position: relative;
    border-radius: 10px;
    overflow: hidden;
    margin-bottom: 2px;
}
.img-card-sel {
    border: 2.5px solid #1DB954;
    border-radius: 10px;
    overflow: hidden;
    cursor: pointer;
}
.img-card-desel {
    border: 2.5px solid #444;
    border-radius: 10px;
    overflow: hidden;
    opacity: 0.4;
    cursor: pointer;
}
.img-card-sel img, .img-card-desel img {
    width: 100%;
    height: 155px;
    object-fit: cover;
    display: block;
}
.img-badge-sel {
    position: absolute;
    top: 8px; right: 8px;
    background: #1DB954;
    color: #000;
    border-radius: 50%;
    width: 26px; height: 26px;
    display: flex; align-items: center; justify-content: center;
    font-size: 14px; font-weight: 900;
    pointer-events: none;
}
.img-badge-desel {
    position: absolute;
    top: 8px; right: 8px;
    background: #333;
    color: #777;
    border-radius: 50%;
    width: 26px; height: 26px;
    display: flex; align-items: center; justify-content: center;
    font-size: 14px; font-weight: 900;
    pointer-events: none;
}
.img-lbl { font-size: 0.68rem; color: #666; padding: 5px 8px; background: #181818; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }

/* Invisible click button over image */
.stButton.img-btn > button {
    position: absolute !important;
    top: 0 !important; left: 0 !important;
    width: 100% !important;
    height: 155px !important;
    opacity: 0 !important;
    z-index: 10 !important;
    border-radius: 0 !important;
    margin: 0 !important;
    padding: 0 !important;
    min-height: unset !important;
}

.kw-row-item {
    background: #1a1a1a;
    border: 1px solid #282828;
    border-radius: 8px;
    padding: 11px 16px;
    font-size: 0.9rem;
    color: #e0e0e0;
    display: flex;
    align-items: center;
}

.history-item {
    background: #181818;
    border: 1px solid #282828;
    border-radius: 8px;
    padding: 10px 14px;
    margin: 4px 0;
    font-size: 0.85rem;
    color: #b3b3b3;
}

.footer { text-align: center; color: #333; font-size: 0.75rem; margin-top: 20px; }
.made-by { text-align: center; color: #333; font-size: 0.78rem; margin-top: 8px; }
.made-by a { color: #1DB954; text-decoration: none; }
.prog-text { color: #535353; font-size: 0.85rem; margin: 6px 0; }
</style>
""", unsafe_allow_html=True)

# --- FIREBASE + STATE ---
db = init_firebase()

defaults = {
    "usage_count": 0,
    "visit_logged": False,
    "stage": "input",
    "pending_keywords": [],
    "confirmed_keywords": [],
    "removed_keywords": set(),
    "downloaded_files": [],
    "selected_files": {},
    "groups": {},           # group_name -> [fpath, ...]
    "removed_groups": set(),
    "search_history": [],
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

def clean_kw(kw):
    return re.sub(r"[^\w\s\-]", "", kw).strip()

def get_keywords_ai(topic, api_key, count):
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
- NO abstract concepts, emotions, or metaphors
- Output ONLY a comma-separated list. Nothing else."""
        resp = model.generate_content(prompt)
        kws = [clean_kw(k) for k in resp.text.strip().split(',')]
        return [k for k in kws if k and len(k) > 1][:count]
    except Exception as e:
        st.error(f"AI error: {e}")
        return []

def keywords_from_topic(topic, count):
    words = re.sub(r"[^\w\s]", "", topic).split()
    return [w for w in words if len(w) > 3][:count]

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

def fetch_kw(kw, pexels_key, pixabay_key, photos_per_kw):
    tmp = tempfile.mkdtemp()
    folder = os.path.join(tmp, clean_filename(kw))
    os.makedirs(folder, exist_ok=True)
    files = pexels_download(kw, folder, pexels_key, photos_per_kw)
    files += pixabay_download(kw, folder, pixabay_key, photos_per_kw)
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

def img_to_b64(fpath):
    try:
        with open(fpath, 'rb') as f:
            return base64.b64encode(f.read()).decode()
    except:
        return None

def render_group(group_name, group_files):
    """Render images for a keyword group inside an expander."""
    visible_files = [f for f in group_files if f not in st.session_state.get("hidden_files", set())]
    sel_count = sum(1 for f in visible_files if st.session_state.selected_files.get(f, True))
    total = len(visible_files)

    label = f"{'🟢' if sel_count > 0 else '⚪'} {group_name.replace('_', ' ').upper()}  ·  {sel_count}/{total} selected"

    with st.expander(label, expanded=True):
        # Remove all / Select all row
        ca, cb = st.columns([1, 1])
        all_sel = sel_count == total
        with ca:
            if st.button("✓ Select all", key=f"selall_{group_name}"):
                for f in visible_files:
                    st.session_state.selected_files[f] = True
                st.rerun()
        with cb:
            if st.button("✕ Remove all", key=f"rmall_{group_name}"):
                for f in visible_files:
                    st.session_state.selected_files[f] = False
                st.rerun()

        # Image grid — 4 columns
        cols = st.columns(4)
        for idx, fpath in enumerate(visible_files):
            with cols[idx % 4]:
                is_sel = st.session_state.selected_files.get(fpath, True)
                b64 = img_to_b64(fpath)
                card_cls = "img-card-sel" if is_sel else "img-card-desel"
                badge_cls = "img-badge-sel" if is_sel else "img-badge-desel"
                icon = "✓" if is_sel else "✗"

                # Render image HTML
                if b64:
                    st.markdown(f"""
                    <div class="img-outer">
                        <div class="{card_cls}">
                            <img src="data:image/jpeg;base64,{b64}" />
                            <div class="{badge_cls}">{icon}</div>
                            <div class="img-lbl">{os.path.basename(fpath)}</div>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)

                    # Invisible button same size as image — overlays on top
                    st.markdown('<style>.img-btn-wrap { position: relative; margin-top: -178px; height: 155px; }</style>', unsafe_allow_html=True)
                    st.markdown('<div class="img-btn-wrap">', unsafe_allow_html=True)
                    clicked = st.button(" ", key=f"img_{fpath}", help="Click to toggle")
                    st.markdown('</div>', unsafe_allow_html=True)

                    if clicked:
                        st.session_state.selected_files[fpath] = not is_sel
                        st.rerun()

# ============================================================
# HEADER
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
        <table class="pro-table" style="max-width:440px;">
            <tr><th>Feature</th><th>Free</th><th>Full Version</th></tr>
            <tr><td>Uses per session</td><td class="cross">3</td><td class="check">Unlimited</td></tr>
            <tr><td>Images per keyword</td><td class="cross">Up to 5</td><td class="check">Up to 10</td></tr>
            <tr><td>Image preview &amp; select</td><td class="check">✓</td><td class="check">✓</td></tr>
            <tr><td>Add keywords on the fly</td><td class="check">✓</td><td class="check">✓</td></tr>
            <tr><td>Collapsible groups</td><td class="check">✓</td><td class="check">✓</td></tr>
            <tr><td>Source code</td><td class="cross">✗</td><td class="check">✓</td></tr>
        </table>
        <br>
        <a href="https://gumroad.com" target="_blank"
           style="background:#1DB954;color:#000;padding:13px 32px;border-radius:24px;
                  text-decoration:none;font-weight:700;font-size:0.9rem;">
            GET IT ON GUMROAD — $12
        </a>
    </div>
    """, unsafe_allow_html=True)
    st.stop()

# --- API KEYS ---
with st.expander("⚙️  API Keys  —  all free", expanded=False):
    st.markdown("""<div style="color:#6a6a6a;font-size:0.83rem;margin-bottom:14px;line-height:1.8;">
    <a href="https://www.pexels.com/api/" target="_blank" style="color:#1DB954;">Pexels</a> &nbsp;·&nbsp;
    <a href="https://pixabay.com/api/" target="_blank" style="color:#1DB954;">Pixabay</a> &nbsp;·&nbsp;
    <a href="https://aistudio.google.com/" target="_blank" style="color:#1DB954;">Gemini</a>
    </div>""", unsafe_allow_html=True)
    c1, c2, c3 = st.columns(3)
    with c1:
        pexels_key = st.text_input("Pexels API Key", type="password", placeholder="px-...", key="pk")
    with c2:
        pixabay_key = st.text_input("Pixabay API Key", type="password", placeholder="53371816-...", key="pbk")
    with c3:
        gemini_key = st.text_input("Gemini API Key", type="password", placeholder="AIzaSy...", key="gk")

st.markdown('<div class="hr"></div>', unsafe_allow_html=True)

# ============================================================
# STAGE 1 — INPUT
# ============================================================
if st.session_state.stage == "input":

    if st.session_state.search_history:
        with st.expander("🕓  Recent searches", expanded=False):
            for item in st.session_state.search_history[-5:][::-1]:
                if st.button(f"↩  {item}", key=f"hist_{item}"):
                    st.session_state["_prefill"] = item
                    st.rerun()

    prefill = st.session_state.pop("_prefill", "")
    st.markdown('<div class="label">Video Topic</div>', unsafe_allow_html=True)
    topic = st.text_area("topic", value=prefill,
        placeholder="e.g. The dark psychology of true crime podcasts...",
        height=90, label_visibility="collapsed")

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
            with st.spinner("Generating keywords..."):
                kws = get_keywords_ai(topic, gemini_key, keyword_count) if gemini_key else keywords_from_topic(topic, keyword_count)
            if not kws:
                st.error("Could not generate keywords.")
            else:
                st.session_state.pending_keywords = kws
                st.session_state.pending_topic = topic
                st.session_state.pending_pexels = pexels_key
                st.session_state.pending_pixabay = pixabay_key
                st.session_state.pending_photos_per_kw = photos_per_kw
                st.session_state.removed_keywords = set()
                st.session_state.stage = "confirm_keywords"
                st.rerun()

# ============================================================
# STAGE 2 — CONFIRM KEYWORDS
# ============================================================
elif st.session_state.stage == "confirm_keywords":
    st.markdown(f'<p style="color:#535353;font-size:0.85rem;margin-bottom:16px;">Topic: <span style="color:#b3b3b3;">{st.session_state.pending_topic}</span></p>', unsafe_allow_html=True)
    st.markdown('<div class="label">Review Keywords — remove what you don\'t need</div>', unsafe_allow_html=True)

    active_kws = [k for k in st.session_state.pending_keywords if k not in st.session_state.removed_keywords]

    for kw in active_kws:
        col_kw, col_x = st.columns([9, 1])
        with col_kw:
            st.markdown(f'<div class="kw-row-item">{kw}</div>', unsafe_allow_html=True)
        with col_x:
            if st.button("✕", key=f"rm_{kw}", help="Remove"):
                st.session_state.removed_keywords.add(kw)
                st.rerun()

    # Add keyword with form (Enter submits)
    st.markdown('<div class="hr"></div>', unsafe_allow_html=True)
    st.markdown('<div class="label">Add a keyword</div>', unsafe_allow_html=True)
    with st.form("add_kw_form", clear_on_submit=True):
        col_in, col_btn = st.columns([5, 1])
        with col_in:
            new_kw = st.text_input("new_kw_input", placeholder="e.g. crime scene tape", label_visibility="collapsed")
        with col_btn:
            submitted = st.form_submit_button("＋ ADD")
        if submitted:
            cleaned = clean_kw(new_kw)
            if cleaned and cleaned not in st.session_state.pending_keywords:
                st.session_state.pending_keywords.append(cleaned)
                st.rerun()

    st.markdown('<div class="hr"></div>', unsafe_allow_html=True)

    col_back, col_dl = st.columns([1, 3])
    with col_back:
        if st.button("← Back"):
            st.session_state.stage = "input"
            st.rerun()
    with col_dl:
        final_kws = [k for k in st.session_state.pending_keywords if k not in st.session_state.removed_keywords]
        if st.button(f"⬇  DOWNLOAD FOOTAGE  ({len(final_kws)} keywords)"):
            if not final_kws:
                st.error("No keywords left.")
            else:
                st.session_state.confirmed_keywords = final_kws
                st.session_state.usage_count += 1
                st.session_state.downloaded_files = []
                st.session_state.selected_files = {}
                st.session_state.groups = {}
                log_event(db, "search")

                topic = st.session_state.pending_topic
                if topic not in st.session_state.search_history:
                    st.session_state.search_history.append(topic)

                tmp = tempfile.mkdtemp()
                folder = os.path.join(tmp, clean_filename(topic)[:30])
                os.makedirs(folder, exist_ok=True)

                all_files = []
                bar = st.progress(0)
                status = st.empty()

                for i, kw in enumerate(final_kws):
                    status.markdown(f'<p class="prog-text">↓ &nbsp;{kw} &nbsp;({i+1}/{len(final_kws)})</p>', unsafe_allow_html=True)
                    kw_folder = os.path.join(folder, clean_filename(kw))
                    os.makedirs(kw_folder, exist_ok=True)
                    files = pexels_download(kw, kw_folder, st.session_state.pending_pexels, st.session_state.pending_photos_per_kw)
                    files += pixabay_download(kw, kw_folder, st.session_state.pending_pixabay, st.session_state.pending_photos_per_kw)
                    all_files.extend(files)
                    gname = clean_filename(kw)
                    st.session_state.groups[gname] = files
                    bar.progress((i + 1) / len(final_kws))
                    time.sleep(0.2)

                status.empty()
                bar.empty()

                st.session_state.downloaded_files = all_files
                st.session_state.selected_files = {f: True for f in all_files}
                st.session_state.stage = "preview"
                st.rerun()

# ============================================================
# STAGE 3 — PREVIEW
# ============================================================
elif st.session_state.stage == "preview":

    if "hidden_files" not in st.session_state:
        st.session_state.hidden_files = set()

    all_files = st.session_state.downloaded_files
    selected_count = sum(1 for v in st.session_state.selected_files.values() if v)

    s1, s2, s3 = st.columns(3)
    with s1:
        st.markdown(f'<div class="stat"><div class="stat-n">{len(st.session_state.confirmed_keywords)}</div><div class="stat-l">Keywords</div></div>', unsafe_allow_html=True)
    with s2:
        st.markdown(f'<div class="stat"><div class="stat-n">{len(all_files)}</div><div class="stat-l">Images Found</div></div>', unsafe_allow_html=True)
    with s3:
        st.markdown(f'<div class="stat"><div class="stat-n">{selected_count}</div><div class="stat-l">Selected</div></div>', unsafe_allow_html=True)

    st.markdown('<div class="hr"></div>', unsafe_allow_html=True)

    # Render each keyword group as collapsible expander
    for group_name, group_files in st.session_state.groups.items():
        if not group_files:
            continue
        render_group(group_name, group_files)

    # Add keyword on the fly — does NOT reset existing state
    st.markdown('<div class="hr"></div>', unsafe_allow_html=True)
    st.markdown('<div class="label">Search another keyword</div>', unsafe_allow_html=True)
    with st.form("extra_kw_form", clear_on_submit=True):
        col_in, col_btn = st.columns([5, 1])
        with col_in:
            extra_kw = st.text_input("extra_kw_input", placeholder="e.g. forensic lab", label_visibility="collapsed")
        with col_btn:
            extra_submitted = st.form_submit_button("🔍 SEARCH")
        if extra_submitted:
            ekw = clean_kw(extra_kw)
            if ekw:
                with st.spinner(f"Searching: {ekw}..."):
                    new_files = fetch_kw(ekw, st.session_state.pending_pexels, st.session_state.pending_pixabay, st.session_state.pending_photos_per_kw)
                if new_files:
                    gname = clean_filename(ekw)
                    # Only add, never reset existing groups
                    if gname not in st.session_state.groups:
                        st.session_state.groups[gname] = []
                    st.session_state.groups[gname].extend(new_files)
                    st.session_state.downloaded_files.extend(new_files)
                    for f in new_files:
                        st.session_state.selected_files[f] = True
                    if ekw not in st.session_state.confirmed_keywords:
                        st.session_state.confirmed_keywords.append(ekw)
                    st.rerun()
                else:
                    st.warning(f"No images found for '{ekw}'")

    st.markdown('<div class="hr"></div>', unsafe_allow_html=True)

    col_back, col_dl = st.columns([1, 3])
    with col_back:
        if st.button("← New Search"):
            for key in ["downloaded_files", "selected_files", "confirmed_keywords", "groups", "hidden_files"]:
                st.session_state[key] = [] if isinstance(st.session_state[key], list) else ({} if isinstance(st.session_state[key], dict) else set())
            st.session_state.stage = "input"
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
