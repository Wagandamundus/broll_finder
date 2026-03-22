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

@st.cache_resource
def init_firebase():
    if not firebase_admin._apps:
        key = dict(st.secrets["firebase"])
        cred = credentials.Certificate(key)
        firebase_admin.initialize_app(cred)
    return firestore.client()

def log_event(db, event_type):
    try:
        db.collection("analytics").add({"event": event_type, "timestamp": datetime.utcnow()})
    except:
        pass

st.set_page_config(page_title="B-Roll Finder", page_icon="🎬", layout="wide")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;900&display=swap');

*, *::before, *::after { box-sizing: border-box; }

html, body, [class*="css"] {
    font-family: 'Inter', sans-serif !important;
    background-color: #0a0a0a;
    color: #FFFFFF;
}
.stApp {
    background-color: #0a0a0a;
    background-image:
        linear-gradient(rgba(29,185,84,0.03) 1px, transparent 1px),
        linear-gradient(90deg, rgba(29,185,84,0.03) 1px, transparent 1px);
    background-size: 40px 40px;
}
.stApp::before {
    content: '';
    position: fixed;
    top: -200px;
    left: 50%;
    transform: translateX(-50%);
    width: 600px;
    height: 400px;
    background: radial-gradient(ellipse, rgba(29,185,84,0.08) 0%, transparent 70%);
    pointer-events: none;
    z-index: 0;
}
.block-container {
    max-width: 880px !important;
    margin: 0 auto !important;
    padding: 3rem 2rem 5rem !important;
    position: relative;
    z-index: 1;
}
h1 {
    font-size: 2.8rem !important;
    font-weight: 900 !important;
    color: #FFFFFF !important;
    letter-spacing: -2px !important;
    line-height: 1 !important;
    margin-bottom: 0 !important;
}
.subtitle { color: #4a4a4a; font-size: 0.95rem; margin-top: 8px; margin-bottom: 40px; }
.section-label { font-size: 0.65rem; font-weight: 700; letter-spacing: 3px; text-transform: uppercase; color: #3a3a3a; margin-bottom: 10px; }
.hr { border: none; border-top: 1px solid #1a1a1a; margin: 32px 0; }

.stTextInput > div > input,
.stTextArea > div > textarea {
    background-color: #111111 !important;
    border: 1px solid #222222 !important;
    border-radius: 10px !important;
    color: #FFFFFF !important;
    font-size: 0.93rem !important;
    padding: 13px 16px !important;
    font-family: 'Inter', sans-serif !important;
}
.stTextInput > div > input:focus,
.stTextArea > div > textarea:focus {
    border-color: #1DB954 !important;
    box-shadow: 0 0 0 3px rgba(29,185,84,0.1) !important;
.stTextArea > div > div {
    border-color: #1DB954 !important;
}
textarea:focus {
    outline: none !important;
    border-color: #1DB954 !important;
}
            
}
.stTextInput > div > input::placeholder,
.stTextArea > div > textarea::placeholder { color: #333 !important; }

.stButton > button {
    background: #1DB954 !important;
    color: #000000 !important;
    font-family: 'Inter', sans-serif !important;
    font-size: 0.82rem !important;
    font-weight: 700 !important;
    height: 42px !important;
    border-radius: 21px !important;
    border: none !important;
    width: 100% !important;
    letter-spacing: 1.2px !important;
    text-transform: uppercase !important;
    transition: all 0.15s ease !important;
}
.stButton > button:hover { background: #1ED760 !important; transform: scale(1.02) !important; }

.stSlider [data-baseweb="slider"] > div > div > div { background: #1DB954 !important; }

.stExpander {
    background: #0d0d0d !important;
    border: 1px solid #1a1a1a !important;
    border-radius: 12px !important;
    margin-bottom: 8px !important;
    overflow: hidden !important;
}

.stCheckbox > label { color: #555 !important; font-size: 0.8rem !important; }
.stCheckbox > label > span[data-baseweb="checkbox"] > div { border-color: #333 !important; background: transparent !important; border-radius: 4px !important; }
.stCheckbox > label > span[data-baseweb="checkbox"] > div[data-checked="true"] { background: #1DB954 !important; border-color: #1DB954 !important; }

.limit-badge {
    background: #0d0d0d;
    border: 1px solid #1a1a1a;
    border-radius: 10px;
    padding: 12px 20px;
    margin-bottom: 32px;
    font-size: 0.85rem;
    color: #555;
    display: flex;
    align-items: center;
    gap: 8px;
}
.paywall {
    background: #0d0d0d;
    border: 1px solid #1a1a1a;
    border-radius: 16px;
    padding: 48px 36px;
    text-align: center;
    margin-bottom: 24px;
}
.pro-table { width: 100%; border-collapse: collapse; margin: 16px auto 28px; max-width: 460px; }
.pro-table th { color: #1DB954; font-size: 0.7rem; letter-spacing: 2px; text-transform: uppercase; padding: 10px 16px; text-align: left; border-bottom: 1px solid #1a1a1a; }
.pro-table td { padding: 10px 16px; font-size: 0.85rem; border-bottom: 1px solid #111; color: #666; }
.pro-table .yes { color: #1DB954; font-weight: 700; }
.pro-table .no { color: #2a2a2a; }

.stat-card { background: #0d0d0d; border: 1px solid #1a1a1a; border-radius: 12px; padding: 24px 16px; text-align: center; }
.stat-num { font-size: 2.4rem; font-weight: 900; color: #1DB954; line-height: 1; }
.stat-lbl { font-size: 0.65rem; color: #333; margin-top: 8px; text-transform: uppercase; letter-spacing: 2px; }

.kw-row { display: flex; align-items: center; background: #0d0d0d; border: 1px solid #1a1a1a; border-radius: 8px; padding: 12px 16px; margin-bottom: 6px; font-size: 0.9rem; color: #ccc; }

.img-card { border-radius: 10px; overflow: hidden; border: 1.5px solid #1a1a1a; background: #0d0d0d; margin-bottom: 3px; }
.img-card img { width: 100%; height: 148px; object-fit: cover; display: block; }
.img-card.deselected img { opacity: 0.2; }
.img-card.deselected { border-color: #111; }
.img-card.selected { border-color: #1DB954; }
.img-lbl { font-size: 0.65rem; color: #333; padding: 5px 8px; background: #080808; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }

.hist-item { background: #0d0d0d; border: 1px solid #1a1a1a; border-radius: 8px; padding: 10px 14px; margin: 4px 0; font-size: 0.85rem; color: #555; }
.prog { color: #333; font-size: 0.85rem; margin: 4px 0; }
.footer { text-align: center; color: #222; font-size: 0.75rem; margin-top: 16px; }
.made-by { text-align: center; font-size: 0.75rem; margin-top: 6px; }
.made-by a { color: #1DB954; text-decoration: none; }

.stForm [data-testid="stFormSubmitButton"] > button {
    background: #1DB954 !important;
    color: #000 !important;
    font-weight: 700 !important;
    border-radius: 21px !important;
    height: 42px !important;
    font-size: 0.82rem !important;
    letter-spacing: 1.2px !important;
    text-transform: uppercase !important;
    width: 100% !important;
}
</style>
""", unsafe_allow_html=True)

# --- INIT ---
db = init_firebase()

# Built-in API keys from Streamlit secrets
PEXELS_KEY = st.secrets.get("PEXELS_KEY", "")
PIXABAY_KEY = st.secrets.get("PIXABAY_KEY", "")

defaults = {
    "usage_count": 0,
    "visit_logged": False,
    "stage": "input",
    "pending_keywords": [],
    "confirmed_keywords": [],
    "removed_keywords": set(),
    "downloaded_files": [],
    "selected_files": {},
    "groups": {},
    "search_history": [],
    "pending_topic": "",
    "pending_photos_per_kw": 3,
    "gemini_key": "",
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
RULES: English only. Concrete filmable objects/scenes only. 1-4 words. Highly specific.
NO abstract concepts, emotions, or metaphors.
Output ONLY a comma-separated list. Nothing else."""
        resp = model.generate_content(prompt)
        kws = [clean_kw(k) for k in resp.text.strip().split(',')]
        return [k for k in kws if k and len(k) > 1][:count]
    except Exception as e:
        st.error(f"AI error: {e}")
        return []

def keywords_from_topic(topic, count):
    words = re.sub(r"[^\w\s]", "", topic).split()
    return [w for w in words if len(w) > 2][:count]

def pexels_download(query, folder, count):
    headers = {'Authorization': PEXELS_KEY}
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
                with open(fpath, 'wb') as f: f.write(r.content)
                files.append(fpath)
    except: pass
    return files

def pixabay_download(query, folder, count):
    url = f"https://pixabay.com/api/?key={PIXABAY_KEY}&q={urllib.parse.quote(query)}&image_type=photo&orientation=horizontal&per_page={count}&safesearch=true&min_width=1920&order=popular"
    files = []
    try:
        data = requests.get(url, timeout=10).json()
        for i, h in enumerate(data.get('hits', [])):
            img_url = h.get('largeImageURL') or h.get('webformatURL')
            fname = f"{clean_filename(query)}_pix_{i+1}.jpg"
            fpath = os.path.join(folder, fname)
            r = requests.get(img_url, timeout=20)
            if r.status_code == 200:
                with open(fpath, 'wb') as f: f.write(r.content)
                files.append(fpath)
    except: pass
    return files

def fetch_kw(kw, n):
    tmp = tempfile.mkdtemp()
    folder = os.path.join(tmp, clean_filename(kw))
    os.makedirs(folder, exist_ok=True)
    files = pexels_download(kw, folder, n)
    files += pixabay_download(kw, folder, n)
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
        with open(fpath, 'rb') as f: return base64.b64encode(f.read()).decode()
    except: return None

# ============================================================
# HEADER
# ============================================================
st.markdown("# 🎬 B-Roll <span style='color:#1DB954'>Finder</span>", unsafe_allow_html=True)
st.markdown('<p class="subtitle">Describe your video — AI picks the keywords, footage downloads itself.</p>', unsafe_allow_html=True)

# LIMIT
remaining = FREE_LIMIT - st.session_state.usage_count
if remaining > 0:
    dot_color = "#1DB954" if remaining > 1 else "#f59b00"
    st.markdown(f"""
    <div class="limit-badge">
        <span style="width:8px;height:8px;border-radius:50%;background:{dot_color};display:inline-block;flex-shrink:0;"></span>
        Free uses remaining: <strong style="color:{dot_color};">{remaining} / {FREE_LIMIT}</strong>
        <span style="margin-left:auto;color:#2a2a2a;font-size:0.78rem;">Buy once · unlimited use</span>
    </div>
    """, unsafe_allow_html=True)
else:
    st.markdown("""
    <div class="paywall">
        <div style="font-size:1.8rem;margin-bottom:14px;">🔒</div>
        <div style="font-size:1.25rem;font-weight:800;margin-bottom:8px;">Free limit reached</div>
        <div style="color:#555;margin-bottom:28px;font-size:0.88rem;max-width:360px;margin-left:auto;margin-right:auto;line-height:1.6;">
            Buy the source code once and run it on your own machine — no limits, no subscriptions.
        </div>
        <table class="pro-table">
            <tr><th>Feature</th><th>Free</th><th>Full version</th></tr>
            <tr><td>Uses per session</td><td class="no">3</td><td class="yes">Unlimited</td></tr>
            <tr><td>Images per keyword</td><td class="no">Up to 5</td><td class="yes">Up to 10</td></tr>
            <tr><td>Image preview &amp; select</td><td class="yes">✓</td><td class="yes">✓</td></tr>
            <tr><td>Add keywords on the fly</td><td class="yes">✓</td><td class="yes">✓</td></tr>
            <tr><td>Source code included</td><td class="no">✗</td><td class="yes">✓</td></tr>
        </table>
        <br>
        <a href="https://gumroad.com" target="_blank"
           style="display:inline-block;background:#1DB954;color:#000;padding:14px 36px;
                  border-radius:24px;text-decoration:none;font-weight:800;font-size:0.88rem;
                  letter-spacing:1px;text-transform:uppercase;">
            Get it on Gumroad — $12
        </a>
    </div>
    """, unsafe_allow_html=True)
    st.stop()

# Optional Gemini key
with st.expander("✨  Add Gemini API Key for smarter keywords  (optional)", expanded=False):
    st.markdown("""<div style="color:#333;font-size:0.82rem;margin-bottom:12px;line-height:1.8;">
    Without a Gemini key the tool extracts words from your topic directly.<br>
    With it, AI generates specific, filmable search queries tailored to your video.<br>
    <a href="https://aistudio.google.com/" target="_blank" style="color:#1DB954;">Get free Gemini key →</a>
    </div>""", unsafe_allow_html=True)
    gemini_key_input = st.text_input("Gemini API Key", type="password", placeholder="AIzaSy...", key="gk",
                                      value=st.session_state.gemini_key)
    if gemini_key_input:
        st.session_state.gemini_key = gemini_key_input

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
    st.markdown('<div class="section-label">Video Topic</div>', unsafe_allow_html=True)
    topic = st.text_area("topic", value=prefill,
        placeholder="e.g. The dark psychology of true crime podcasts and why millions are obsessed...",
        height=100, label_visibility="collapsed")

    st.markdown("<br>", unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    with c1:
        st.markdown('<div class="section-label">Keywords to generate</div>', unsafe_allow_html=True)
        keyword_count = st.slider("kw", 3, 20, 10, label_visibility="collapsed")
    with c2:
        st.markdown('<div class="section-label">Images per keyword</div>', unsafe_allow_html=True)
        photos_per_kw = st.slider("ph", 1, 5, 3, label_visibility="collapsed")

    st.markdown('<div class="hr"></div>', unsafe_allow_html=True)

    if st.button("🔍  Generate Keywords"):
        if not topic.strip():
            st.warning("Please enter a video topic.")
        else:
            with st.spinner("Generating keywords..."):
                gk = st.session_state.gemini_key
                kws = get_keywords_ai(topic, gk, keyword_count) if gk else keywords_from_topic(topic, keyword_count)
            if not kws:
                st.error("Could not generate keywords.")
            else:
                st.session_state.pending_keywords = kws
                st.session_state.pending_topic = topic
                st.session_state.pending_photos_per_kw = photos_per_kw
                st.session_state.removed_keywords = set()
                st.session_state.stage = "confirm_keywords"
                st.rerun()

# ============================================================
# STAGE 2 — CONFIRM KEYWORDS
# ============================================================
elif st.session_state.stage == "confirm_keywords":
    st.markdown(f'<p style="color:#2a2a2a;font-size:0.82rem;margin-bottom:20px;">Topic: <span style="color:#555;">{st.session_state.pending_topic}</span></p>', unsafe_allow_html=True)
    st.markdown('<div class="section-label">Review keywords — remove what you don\'t need</div>', unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)

    active_kws = [k for k in st.session_state.pending_keywords if k not in st.session_state.removed_keywords]

    for kw in active_kws:
        col_kw, col_x = st.columns([10, 1])
        with col_kw:
            st.markdown(f'<div class="kw-row">{kw}</div>', unsafe_allow_html=True)
        with col_x:
            if st.button("✕", key=f"rm_{kw}"):
                st.session_state.removed_keywords.add(kw)
                st.rerun()

    st.markdown('<div class="hr"></div>', unsafe_allow_html=True)
    st.markdown('<div class="section-label">Add a keyword</div>', unsafe_allow_html=True)

    with st.form("add_kw_form", clear_on_submit=True):
        col_in, col_btn = st.columns([4, 1])
        with col_in:
            new_kw = st.text_input("nk", placeholder="e.g. crime scene tape", label_visibility="collapsed")
        with col_btn:
            submitted = st.form_submit_button("＋  Add")
        if submitted and new_kw.strip():
            cleaned = clean_kw(new_kw)
            if cleaned and cleaned not in st.session_state.pending_keywords:
                st.session_state.pending_keywords.append(cleaned)
                st.rerun()

    st.markdown('<div class="hr"></div>', unsafe_allow_html=True)

    final_kws = [k for k in st.session_state.pending_keywords if k not in st.session_state.removed_keywords]
    col_back, col_spacer, col_dl = st.columns([1, 0.2, 3])
    with col_back:
        if st.button("← Back"):
            st.session_state.stage = "input"
            st.rerun()
    with col_dl:
        if st.button(f"⬇  Download Footage  ({len(final_kws)} keywords)"):
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
                    status.markdown(f'<p class="prog">↓ &nbsp;{kw} &nbsp;<span style="color:#1a1a1a;">({i+1}/{len(final_kws)})</span></p>', unsafe_allow_html=True)
                    kw_folder = os.path.join(folder, clean_filename(kw))
                    os.makedirs(kw_folder, exist_ok=True)
                    files = pexels_download(kw, kw_folder, st.session_state.pending_photos_per_kw)
                    files += pixabay_download(kw, kw_folder, st.session_state.pending_photos_per_kw)
                    all_files.extend(files)
                    st.session_state.groups[clean_filename(kw)] = files
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
    all_files = st.session_state.downloaded_files
    sel_count = sum(1 for v in st.session_state.selected_files.values() if v)

    s1, s2, s3 = st.columns(3)
    with s1:
        st.markdown(f'<div class="stat-card"><div class="stat-num">{len(st.session_state.confirmed_keywords)}</div><div class="stat-lbl">Keywords</div></div>', unsafe_allow_html=True)
    with s2:
        st.markdown(f'<div class="stat-card"><div class="stat-num">{len(all_files)}</div><div class="stat-lbl">Images found</div></div>', unsafe_allow_html=True)
    with s3:
        st.markdown(f'<div class="stat-card"><div class="stat-num">{sel_count}</div><div class="stat-lbl">Selected</div></div>', unsafe_allow_html=True)

    st.markdown('<div class="hr"></div>', unsafe_allow_html=True)

    for group_name, group_files in st.session_state.groups.items():
        if not group_files:
            continue
        g_sel = sum(1 for f in group_files if st.session_state.selected_files.get(f, True))
        g_total = len(group_files)
        indicator = "🟢" if g_sel > 0 else "⚫"
        label = f"{indicator}  {group_name.replace('_', ' ').upper()}  ·  {g_sel} / {g_total}"

        with st.expander(label, expanded=True):
            ba, bb = st.columns(2)
            with ba:
                if st.button("✓  Select all", key=f"sa_{group_name}"):
                    for f in group_files:
                        st.session_state.selected_files[f] = True
                    st.rerun()
            with bb:
                if st.button("✕  Remove all", key=f"ra_{group_name}"):
                    for f in group_files:
                        st.session_state.selected_files[f] = False
                    st.rerun()

            st.markdown("<br>", unsafe_allow_html=True)
            cols = st.columns(4)
            for idx, fpath in enumerate(group_files):
                with cols[idx % 4]:
                    is_sel = st.session_state.selected_files.get(fpath, True)
                    b64 = img_to_b64(fpath)
                    card_cls = "selected" if is_sel else "deselected"
                    if b64:
                        st.markdown(f"""
                        <div class="img-card {card_cls}">
                            <img src="data:image/jpeg;base64,{b64}" />
                            <div class="img-lbl">{os.path.basename(fpath)}</div>
                        </div>
                        """, unsafe_allow_html=True)
                    new_val = st.checkbox(
                        "Keep" if is_sel else "Removed",
                        value=is_sel,
                        key=f"cb_{fpath}"
                    )
                    if new_val != is_sel:
                        st.session_state.selected_files[fpath] = new_val
                        st.rerun()

    st.markdown('<div class="hr"></div>', unsafe_allow_html=True)
    st.markdown('<div class="section-label">Search another keyword</div>', unsafe_allow_html=True)

    with st.form("extra_kw_form", clear_on_submit=True):
        col_in, col_btn = st.columns([4, 1])
        with col_in:
            extra_kw = st.text_input("ek", placeholder="e.g. forensic laboratory", label_visibility="collapsed")
        with col_btn:
            extra_sub = st.form_submit_button("🔍  Search")
        if extra_sub and extra_kw.strip():
            ekw = clean_kw(extra_kw)
            with st.spinner(f"Searching: {ekw}..."):
                new_files = fetch_kw(ekw, st.session_state.pending_photos_per_kw)
            if new_files:
                gname = clean_filename(ekw)
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

    final_files = [f for f, v in st.session_state.selected_files.items() if v]
    col_back, col_spacer, col_dl = st.columns([1, 0.2, 3])
    with col_back:
        if st.button("← New Search"):
            for k in ["downloaded_files", "selected_files", "confirmed_keywords", "groups"]:
                st.session_state[k] = [] if isinstance(st.session_state[k], list) else {}
            st.session_state.stage = "input"
            st.rerun()
    with col_dl:
        if final_files:
            zip_data = make_zip(final_files)
            size_mb = round(len(zip_data) / 1024 / 1024, 1)
            st.markdown(f'<p style="color:#2a2a2a;font-size:0.82rem;margin-bottom:8px;text-align:right;">{len(final_files)} images · {size_mb} MB</p>', unsafe_allow_html=True)
            log_event(db, "download")
            st.download_button(
                label=f"⬇  Download ZIP  ({len(final_files)} images)",
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
