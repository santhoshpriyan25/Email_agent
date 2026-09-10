import os
import base64
import json
import time as _time
import streamlit as st
from email.mime.text import MIMEText
from dotenv import load_dotenv
from google import genai
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from requests_oauthlib import OAuth2Session

# ✅ Must be set before any OAuth work
os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"
os.environ["OAUTHLIB_RELAX_TOKEN_SCOPE"] = "1"

load_dotenv()

GEMINI_API_KEY = st.secrets.get("GEMINI_API_KEY") or os.getenv("GEMINI_API_KEY")

SCOPES = [
    'https://www.googleapis.com/auth/gmail.modify',
    'https://www.googleapis.com/auth/gmail.send'
]

GOOGLE_AUTH_URL  = "https://accounts.google.com/o/oauth2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"

st.set_page_config(page_title="MailMind AI", page_icon="🧠", layout="wide")

# ── Premium CSS ───────────────────────────────────────────────────────────────
st.markdown("""
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap" rel="stylesheet">
<style>
/* ── Global Reset ── */
* { font-family: 'Inter', sans-serif !important; box-sizing: border-box; }

html, body, [data-testid="stAppViewContainer"] {
    background: #050b18 !important;
    color: #e2e8f0 !important;
}

[data-testid="stAppViewContainer"] > .main {
    background: transparent !important;
}

/* ── Animated gradient background ── */
[data-testid="stAppViewContainer"]::before {
    content: '';
    position: fixed;
    top: 0; left: 0; right: 0; bottom: 0;
    background:
        radial-gradient(ellipse at 20% 20%, rgba(99,102,241,0.15) 0%, transparent 50%),
        radial-gradient(ellipse at 80% 80%, rgba(168,85,247,0.12) 0%, transparent 50%),
        radial-gradient(ellipse at 50% 50%, rgba(6,182,212,0.06) 0%, transparent 60%);
    pointer-events: none;
    z-index: 0;
}

/* ── Sidebar ── */
[data-testid="stSidebar"] {
    background: rgba(15, 23, 42, 0.95) !important;
    border-right: 1px solid rgba(99,102,241,0.2) !important;
    backdrop-filter: blur(20px);
}

[data-testid="stSidebar"] .stButton > button {
    background: linear-gradient(135deg, rgba(99,102,241,0.15), rgba(168,85,247,0.15)) !important;
    border: 1px solid rgba(99,102,241,0.3) !important;
    color: #a5b4fc !important;
    border-radius: 10px !important;
    font-weight: 500 !important;
    transition: all 0.3s ease !important;
    width: 100% !important;
}
[data-testid="stSidebar"] .stButton > button:hover {
    background: linear-gradient(135deg, rgba(99,102,241,0.3), rgba(168,85,247,0.3)) !important;
    border-color: rgba(168,85,247,0.5) !important;
    transform: translateY(-1px) !important;
    box-shadow: 0 4px 20px rgba(99,102,241,0.25) !important;
}

/* ── Main sync button ── */
.stButton > button[kind="secondary"],
.stButton > button {
    background: linear-gradient(135deg, #6366f1, #8b5cf6) !important;
    border: none !important;
    color: white !important;
    border-radius: 12px !important;
    font-weight: 600 !important;
    font-size: 1rem !important;
    padding: 0.6rem 1.5rem !important;
    transition: all 0.3s ease !important;
    box-shadow: 0 4px 24px rgba(99,102,241,0.35) !important;
}
.stButton > button:hover {
    background: linear-gradient(135deg, #4f46e5, #7c3aed) !important;
    transform: translateY(-2px) !important;
    box-shadow: 0 8px 32px rgba(99,102,241,0.5) !important;
}

/* ── Tabs ── */
[data-testid="stTabs"] [role="tablist"] {
    background: rgba(255,255,255,0.03) !important;
    border-radius: 14px !important;
    padding: 6px !important;
    border: 1px solid rgba(255,255,255,0.06) !important;
    gap: 4px !important;
}
[data-testid="stTabs"] [role="tab"] {
    border-radius: 10px !important;
    color: #94a3b8 !important;
    font-weight: 500 !important;
    padding: 8px 20px !important;
    transition: all 0.3s ease !important;
    border: none !important;
}
[data-testid="stTabs"] [role="tab"][aria-selected="true"] {
    background: linear-gradient(135deg, #6366f1, #8b5cf6) !important;
    color: white !important;
    box-shadow: 0 4px 16px rgba(99,102,241,0.4) !important;
}

/* ── Slider ── */
[data-testid="stSlider"] [data-baseweb="slider"] [role="slider"] {
    background: #6366f1 !important;
    border-color: #8b5cf6 !important;
    box-shadow: 0 0 12px rgba(99,102,241,0.6) !important;
}

/* ── Text area ── */
.stTextArea textarea {
    background: rgba(255,255,255,0.04) !important;
    border: 1px solid rgba(99,102,241,0.3) !important;
    border-radius: 12px !important;
    color: #e2e8f0 !important;
    font-size: 0.9rem !important;
}
.stTextArea textarea:focus {
    border-color: #6366f1 !important;
    box-shadow: 0 0 0 3px rgba(99,102,241,0.15) !important;
}

/* ── Expander ── */
[data-testid="stExpander"] {
    background: rgba(255,255,255,0.02) !important;
    border: 1px solid rgba(255,255,255,0.07) !important;
    border-radius: 14px !important;
    margin-bottom: 12px !important;
}
[data-testid="stExpander"]:hover {
    border-color: rgba(99,102,241,0.3) !important;
}

/* ── Custom components ── */

/* Hero header */
.hero-header {
    text-align: center;
    padding: 2rem 0 1.5rem 0;
}
.hero-title {
    font-size: 2.8rem;
    font-weight: 800;
    background: linear-gradient(135deg, #818cf8, #a78bfa, #38bdf8);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    line-height: 1.2;
    margin-bottom: 0.4rem;
    letter-spacing: -1px;
}
.hero-subtitle {
    font-size: 1rem;
    color: #64748b;
    font-weight: 400;
    letter-spacing: 0.3px;
}

/* Metric card */
.metric-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 16px; margin: 1.5rem 0; }
.metric-card {
    background: rgba(255,255,255,0.03);
    border: 1px solid rgba(255,255,255,0.07);
    border-radius: 18px;
    padding: 24px 20px;
    text-align: center;
    position: relative;
    overflow: hidden;
    transition: transform 0.3s ease, border-color 0.3s ease;
}
.metric-card::before {
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 3px;
}
.metric-card.total::before  { background: linear-gradient(90deg, #6366f1, #8b5cf6); }
.metric-card.urgent::before { background: linear-gradient(90deg, #ef4444, #f97316); }
.metric-card.normal::before { background: linear-gradient(90deg, #06b6d4, #3b82f6); }
.metric-card:hover { transform: translateY(-4px); border-color: rgba(99,102,241,0.3); }
.metric-icon { font-size: 2rem; margin-bottom: 8px; }
.metric-value { font-size: 2.4rem; font-weight: 800; color: #f1f5f9; line-height: 1; }
.metric-label { font-size: 0.8rem; color: #64748b; margin-top: 6px; font-weight: 500; text-transform: uppercase; letter-spacing: 1px; }

/* Email card */
.email-card {
    background: rgba(255,255,255,0.025);
    backdrop-filter: blur(20px);
    border: 1px solid rgba(255,255,255,0.07);
    border-radius: 20px;
    padding: 24px;
    margin-bottom: 16px;
    transition: all 0.3s ease;
    position: relative;
    overflow: hidden;
}
.email-card:hover {
    border-color: rgba(99,102,241,0.25);
    transform: translateY(-2px);
    box-shadow: 0 8px 40px rgba(0,0,0,0.3);
}
.email-card.high  { border-left: 4px solid #ef4444; }
.email-card.normal { border-left: 4px solid #6366f1; }

/* Sender avatar */
.email-header { display: flex; align-items: center; gap: 14px; margin-bottom: 14px; }
.avatar {
    width: 44px; height: 44px;
    border-radius: 50%;
    display: flex; align-items: center; justify-content: center;
    font-weight: 700; font-size: 1rem; color: white;
    flex-shrink: 0;
}
.avatar.high   { background: linear-gradient(135deg, #ef4444, #f97316); }
.avatar.normal { background: linear-gradient(135deg, #6366f1, #8b5cf6); }
.sender-info { flex: 1; min-width: 0; }
.sender-name { font-weight: 600; font-size: 0.9rem; color: #cbd5e1; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.email-time  { font-size: 0.75rem; color: #475569; margin-top: 2px; }

/* Priority badge */
.badge {
    display: inline-flex; align-items: center; gap: 5px;
    padding: 4px 12px; border-radius: 20px;
    font-size: 0.72rem; font-weight: 700; letter-spacing: 0.5px; text-transform: uppercase;
}
.badge.high   { background: rgba(239,68,68,0.15); color: #f87171; border: 1px solid rgba(239,68,68,0.25); }
.badge.normal { background: rgba(99,102,241,0.15); color: #a5b4fc; border: 1px solid rgba(99,102,241,0.25); }

.email-subject { font-size: 1.05rem; font-weight: 700; color: #f1f5f9; margin-bottom: 10px; line-height: 1.4; }
.email-summary { font-size: 0.9rem; color: #94a3b8; line-height: 1.6; margin-bottom: 16px; }

/* Action chip */
.action-chip {
    display: inline-flex; align-items: center; gap: 6px;
    background: rgba(52,211,153,0.08);
    border: 1px solid rgba(52,211,153,0.2);
    color: #34d399;
    padding: 6px 14px; border-radius: 20px;
    font-size: 0.82rem; font-weight: 600;
}

/* Empty state */
.empty-state {
    text-align: center; padding: 60px 20px;
    color: #334155;
}
.empty-state .icon { font-size: 4rem; margin-bottom: 16px; }
.empty-state .title { font-size: 1.2rem; font-weight: 600; color: #475569; margin-bottom: 8px; }
.empty-state .desc  { font-size: 0.9rem; color: #334155; }

/* Connected badge in sidebar */
.status-connected {
    display: flex; align-items: center; gap: 8px;
    background: rgba(52,211,153,0.1);
    border: 1px solid rgba(52,211,153,0.25);
    border-radius: 10px; padding: 10px 14px;
    color: #34d399; font-weight: 600; font-size: 0.9rem; margin-bottom: 16px;
}
.status-disconnected {
    display: flex; align-items: center; gap: 8px;
    background: rgba(251,191,36,0.1);
    border: 1px solid rgba(251,191,36,0.25);
    border-radius: 10px; padding: 10px 14px;
    color: #fbbf24; font-weight: 600; font-size: 0.9rem; margin-bottom: 16px;
}
.pulse {
    width: 8px; height: 8px; border-radius: 50%;
    background: #34d399;
    box-shadow: 0 0 0 0 rgba(52,211,153,0.4);
    animation: pulse-anim 2s infinite;
}
@keyframes pulse-anim {
    0%   { box-shadow: 0 0 0 0 rgba(52,211,153,0.4); }
    70%  { box-shadow: 0 0 0 8px rgba(52,211,153,0); }
    100% { box-shadow: 0 0 0 0 rgba(52,211,153,0); }
}

/* Divider */
.section-divider { border: none; border-top: 1px solid rgba(255,255,255,0.06); margin: 20px 0; }

/* Scrollbar */
::-webkit-scrollbar { width: 6px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: rgba(99,102,241,0.3); border-radius: 3px; }
::-webkit-scrollbar-thumb:hover { background: rgba(99,102,241,0.5); }
</style>
""", unsafe_allow_html=True)


# ── helpers ───────────────────────────────────────────────────────────────────

def get_initials(sender: str) -> str:
    """Extract initials from sender name/email."""
    name = sender.split("<")[0].strip().strip('"')
    parts = name.split()
    if len(parts) >= 2:
        return (parts[0][0] + parts[-1][0]).upper()
    return name[:2].upper() if name else "??"

def load_google_config():
    try:
        return json.loads(st.secrets["GOOGLE_CREDENTIALS"])
    except Exception as e:
        st.error(f"❌ Cannot load GOOGLE_CREDENTIALS: {e}")
        return None

def get_redirect_uri(cfg): return cfg["web"]["redirect_uris"][0]
def get_client_id(cfg):    return cfg["web"]["client_id"]
def get_client_secret(cfg): return cfg["web"]["client_secret"]


def get_full_body(payload):
    body = ""
    if 'parts' in payload:
        for part in payload['parts']:
            if part['mimeType'] == 'text/plain':
                data = part['body'].get('data', '')
                if data:
                    body += base64.urlsafe_b64decode(data).decode('utf-8')
            elif 'parts' in part:
                body += get_full_body(part)
    else:
        data = payload['body'].get('data', '')
        if data:
            body = base64.urlsafe_b64decode(data).decode('utf-8')
    return body


def send_reply(service, to_email, subject, body, thread_id, message_id):
    msg = MIMEText(body)
    if not subject.lower().startswith("re:"):
        subject = f"Re: {subject}"
    msg['to']           = to_email
    msg['subject']      = subject
    msg['In-Reply-To']  = message_id
    msg['References']   = message_id
    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
    try:
        service.users().messages().send(
            userId='me', body={'raw': raw, 'threadId': thread_id}
        ).execute()
        return True
    except Exception:
        return False


# ── OAuth ─────────────────────────────────────────────────────────────────────

def get_gmail_service():
    cfg = load_google_config()
    if not cfg:
        return None

    client_id     = get_client_id(cfg)
    client_secret = get_client_secret(cfg)
    redirect_uri  = get_redirect_uri(cfg)

    if 'token' in st.session_state:
        token = st.session_state.token
        try:
            creds = Credentials(
                token=token['access_token'],
                refresh_token=token.get('refresh_token'),
                token_uri=GOOGLE_TOKEN_URL,
                client_id=client_id,
                client_secret=client_secret,
                scopes=SCOPES
            )
            if creds.expired and creds.refresh_token:
                creds.refresh(Request())
                st.session_state.token['access_token'] = creds.token
            return build('gmail', 'v1', credentials=creds)
        except Exception:
            del st.session_state['token']

    query_params = st.query_params

    if "code" in query_params:
        try:
            saved_state = st.session_state.get('oauth_state')
            oauth = OAuth2Session(
                client_id=client_id,
                redirect_uri=redirect_uri,
                scope=SCOPES,
                state=saved_state
            )
            params   = dict(query_params)
            qs       = "&".join(f"{k}={v}" for k, v in params.items())
            full_url = f"{redirect_uri}?{qs}"
            token = oauth.fetch_token(
                token_url=GOOGLE_TOKEN_URL,
                authorization_response=full_url,
                client_secret=client_secret,
                include_client_id=True
            )
            st.session_state.token = token
            st.query_params.clear()
            st.rerun()
        except Exception as e:
            st.error(f"❌ OAuth callback failed: {e}")
            st.info("Please click **Reset Connection** in the sidebar and try again.")
            st.query_params.clear()
            return None

    oauth = OAuth2Session(client_id=client_id, redirect_uri=redirect_uri, scope=SCOPES)
    auth_url, state = oauth.authorization_url(
        GOOGLE_AUTH_URL, access_type="offline", prompt="consent"
    )
    st.session_state['oauth_state'] = state

    st.markdown("""
    <div style="text-align:center; padding: 60px 20px;">
        <div style="font-size:3rem; margin-bottom:16px;">🔐</div>
        <div style="font-size:1.3rem; font-weight:700; color:#f1f5f9; margin-bottom:8px;">Connect your Gmail</div>
        <div style="color:#64748b; margin-bottom:28px;">Authorize MailMind AI to read and manage your emails securely</div>
    </div>
    """, unsafe_allow_html=True)
    st.link_button("🔗 Connect Gmail Account", auth_url, use_container_width=True)
    st.stop()


# ── session init ──────────────────────────────────────────────────────────────

if 'email_data' not in st.session_state:
    st.session_state.email_data = []

# ── Sidebar ───────────────────────────────────────────────────────────────────

with st.sidebar:
    st.markdown("""
    <div style="text-align:center; padding: 20px 0 10px 0;">
        <div style="font-size:2.2rem;">🧠</div>
        <div style="font-size:1.1rem; font-weight:800; background:linear-gradient(135deg,#818cf8,#a78bfa);
             -webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text;">
             MailMind AI
        </div>
        <div style="font-size:0.72rem; color:#475569; margin-top:4px; text-transform:uppercase; letter-spacing:1px;">
            Intelligence Engine
        </div>
    </div>
    <hr style="border:none;border-top:1px solid rgba(255,255,255,0.06);margin:12px 0 16px 0;">
    """, unsafe_allow_html=True)

    if 'token' in st.session_state:
        st.markdown('<div class="status-connected"><div class="pulse"></div> Gmail Connected</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="status-disconnected">⚠️ Gmail Not Connected</div>', unsafe_allow_html=True)

    st.markdown('<div style="font-size:0.8rem;color:#64748b;font-weight:600;text-transform:uppercase;letter-spacing:1px;margin-bottom:8px;">Messages to Analyze</div>', unsafe_allow_html=True)
    email_limit = st.slider("", 1, 15, 5, label_visibility="collapsed")

    st.markdown('<hr class="section-divider">', unsafe_allow_html=True)

    if st.button("🗑️ Reset Connection"):
        for k in ['token', 'email_data', 'oauth_state']:
            st.session_state.pop(k, None)
        st.query_params.clear()
        st.rerun()

    st.markdown("""
    <div style="position:fixed;bottom:20px;left:0;right:0;text-align:center;padding:0 20px;">
        <div style="font-size:0.72rem;color:#1e293b;">Powered by Gemini AI · Gmail API</div>
    </div>
    """, unsafe_allow_html=True)

# ── Hero Header ───────────────────────────────────────────────────────────────

st.markdown("""
<div class="hero-header">
    <div class="hero-title">🧠 MailMind Intelligence</div>
    <div class="hero-subtitle">Your AI-powered email command center — summarize, prioritize & reply instantly</div>
</div>
""", unsafe_allow_html=True)

# ── Sync Button ───────────────────────────────────────────────────────────────

col_btn, col_right = st.columns([3, 1])
with col_btn:
    run_sync = st.button("⚡ Run Full System Sync", use_container_width=True)

if run_sync:
    if not GEMINI_API_KEY:
        st.error("❌ Missing Gemini API Key in Streamlit Secrets.")
    else:
        try:
            service = get_gmail_service()
            if service:
                client = genai.Client(api_key=GEMINI_API_KEY, http_options={'api_version': 'v1'})

                with st.status("🔍 Gathering Intelligence...", expanded=True) as status:
                    results  = service.users().messages().list(
                        userId='me', q='is:unread', maxResults=email_limit
                    ).execute()
                    messages = results.get('messages', [])

                    if not messages:
                        st.success("✅ Inbox is clear! No unread emails.")
                        st.session_state.email_data = []
                    else:
                        processed, context = [], ""
                        st.write(f"📬 Found **{len(messages)}** unread emails. Fetching content...")

                        for m in messages:
                            msg     = service.users().messages().get(userId='me', id=m['id']).execute()
                            body    = get_full_body(msg['payload'])
                            headers = msg['payload']['headers']
                            subject = next((h['value'] for h in headers if h['name'] == 'Subject'), "No Subject")
                            sender  = next((h['value'] for h in headers if h['name'] == 'From'), "Unknown")
                            msg_id  = next((h['value'] for h in headers if h['name'] == 'Message-ID'), "")

                            context += f"ID:{m['id']}\nFROM:{sender}\nSUBJ:{subject}\nBODY:{body[:800]}\n---\n"
                            processed.append({
                                "id": m['id'], "threadId": m['threadId'],
                                "messageId": msg_id, "sender": sender, "subject": subject
                            })

                        # --- AI with retry + fallback ---
                        MODELS = ["gemini-3.6-flash", "gemini-2.5-flash"]
                        prompt = (
                            "Format each email EXACTLY like this and separate with the word SPLIT:\n"
                            "PRIORITY: [High/Normal] | SUMMARY: [1 sentence] | ACTION: [1 step] | DRAFT: [2 sentence reply]\n\n"
                            f"Emails:\n{context}"
                        )
                        ai_resp = None
                        last_err = None
                        for model_name in MODELS:
                            for attempt in range(3):
                                try:
                                    st.write(f"🤖 Asking `{model_name}` to analyze... (attempt {attempt+1})")
                                    ai_resp = client.models.generate_content(
                                        model=model_name, contents=prompt
                                    )
                                    last_err = None
                                    break
                                except Exception as ai_err:
                                    last_err = ai_err
                                    err_str = str(ai_err)
                                    if "503" in err_str or "429" in err_str:
                                        wait = 15 * (attempt + 1)
                                        st.warning(f"⏱️ `{model_name}` busy. Retrying in {wait}s...")
                                        _time.sleep(wait)
                                    else:
                                        break
                            if ai_resp:
                                break

                        if ai_resp:
                            for i, entry in enumerate(ai_resp.text.split("SPLIT")):
                                if i < len(processed) and "PRIORITY:" in entry:
                                    parts = entry.strip().split('|')
                                    if len(parts) >= 4:
                                        processed[i].update({
                                            "prio":    parts[0].replace("PRIORITY:", "").strip(),
                                            "summary": parts[1].replace("SUMMARY:",  "").strip(),
                                            "action":  parts[2].replace("ACTION:",   "").strip(),
                                            "draft":   parts[3].replace("DRAFT:",    "").strip(),
                                        })
                            st.session_state.email_data = processed
                            status.update(label="✅ Intelligence Gathered!", state="complete")
                        else:
                            err_str = str(last_err)
                            if "503" in err_str:
                                st.warning("⏱️ All AI models overloaded. Wait 1–2 min and retry.")
                            elif "429" in err_str:
                                st.warning("⏱️ Rate limit hit. Wait 60s and retry.")
                            else:
                                st.error(f"AI Error: {last_err}")
                            status.update(label="Sync Paused", state="error")

        except Exception as e:
            st.error(f"System Connection Error: {e}")

st.markdown("<br>", unsafe_allow_html=True)

# ── Tabs ──────────────────────────────────────────────────────────────────────

tab1, tab2, tab3 = st.tabs(["📊  Analytics", "📬  Smart Digest", "🚀  Instant Reply"])

# ── Tab 1: Analytics ──────────────────────────────────────────────────────────
with tab1:
    if st.session_state.email_data:
        total  = len(st.session_state.email_data)
        urgent = len([e for e in st.session_state.email_data if e.get('prio') == "High"])
        normal = len([e for e in st.session_state.email_data if e.get('prio') == "Normal"])

        st.markdown(f"""
        <div class="metric-grid">
            <div class="metric-card total">
                <div class="metric-icon">📧</div>
                <div class="metric-value">{total}</div>
                <div class="metric-label">Emails Analyzed</div>
            </div>
            <div class="metric-card urgent">
                <div class="metric-icon">🔴</div>
                <div class="metric-value">{urgent}</div>
                <div class="metric-label">Urgent / High Priority</div>
            </div>
            <div class="metric-card normal">
                <div class="metric-icon">🔵</div>
                <div class="metric-value">{normal}</div>
                <div class="metric-label">Normal Priority</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        # Mini summary list
        st.markdown('<div style="margin-top:8px;font-size:0.8rem;color:#64748b;font-weight:600;text-transform:uppercase;letter-spacing:1px;margin-bottom:12px;">Quick Overview</div>', unsafe_allow_html=True)
        for e in st.session_state.email_data:
            prio = e.get('prio', 'Normal')
            color = "#f87171" if prio == "High" else "#a5b4fc"
            dot   = "🔴" if prio == "High" else "🔵"
            st.markdown(f"""
            <div style="display:flex;align-items:center;gap:10px;padding:10px 16px;
                 background:rgba(255,255,255,0.02);border-radius:10px;margin-bottom:6px;
                 border:1px solid rgba(255,255,255,0.05);">
                <span>{dot}</span>
                <span style="font-size:0.88rem;color:#94a3b8;flex:1;min-width:0;
                      white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">
                    {e.get('subject','—')}
                </span>
                <span style="font-size:0.75rem;color:{color};font-weight:600;">{prio}</span>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.markdown("""
        <div class="empty-state">
            <div class="icon">📊</div>
            <div class="title">No Data Yet</div>
            <div class="desc">Run a sync to see your email analytics here</div>
        </div>
        """, unsafe_allow_html=True)

# ── Tab 2: Smart Digest ───────────────────────────────────────────────────────
with tab2:
    if not st.session_state.email_data:
        st.markdown("""
        <div class="empty-state">
            <div class="icon">📬</div>
            <div class="title">Inbox Empty</div>
            <div class="desc">Click ⚡ Run Full System Sync above to analyze your emails</div>
        </div>
        """, unsafe_allow_html=True)
    else:
        high  = [e for e in st.session_state.email_data if e.get('prio') == 'High']
        other = [e for e in st.session_state.email_data if e.get('prio') != 'High']

        if high:
            st.markdown('<div style="font-size:0.8rem;color:#f87171;font-weight:700;text-transform:uppercase;letter-spacing:1px;margin-bottom:12px;">🔴 Urgent — Needs Attention</div>', unsafe_allow_html=True)
        for e in high:
            if 'prio' in e:
                initials = get_initials(e['sender'])
                sender_display = e['sender'].split('<')[0].strip().strip('"') or e['sender']
                st.markdown(f"""
                <div class="email-card high">
                    <div class="email-header">
                        <div class="avatar high">{initials}</div>
                        <div class="sender-info">
                            <div class="sender-name">{sender_display}</div>
                            <div class="email-time">Unread</div>
                        </div>
                        <span class="badge high">🔴 High Priority</span>
                    </div>
                    <div class="email-subject">{e['subject']}</div>
                    <div class="email-summary">{e.get('summary','')}</div>
                    <span class="action-chip">🎯 {e.get('action','')}</span>
                </div>
                """, unsafe_allow_html=True)

        if other:
            st.markdown('<div style="font-size:0.8rem;color:#a5b4fc;font-weight:700;text-transform:uppercase;letter-spacing:1px;margin:20px 0 12px 0;">🔵 Normal Priority</div>', unsafe_allow_html=True)
        for e in other:
            if 'prio' in e:
                initials = get_initials(e['sender'])
                sender_display = e['sender'].split('<')[0].strip().strip('"') or e['sender']
                st.markdown(f"""
                <div class="email-card normal">
                    <div class="email-header">
                        <div class="avatar normal">{initials}</div>
                        <div class="sender-info">
                            <div class="sender-name">{sender_display}</div>
                            <div class="email-time">Unread</div>
                        </div>
                        <span class="badge normal">🔵 Normal</span>
                    </div>
                    <div class="email-subject">{e['subject']}</div>
                    <div class="email-summary">{e.get('summary','')}</div>
                    <span class="action-chip">🎯 {e.get('action','')}</span>
                </div>
                """, unsafe_allow_html=True)

# ── Tab 3: Instant Reply ──────────────────────────────────────────────────────
with tab3:
    if not st.session_state.email_data:
        st.markdown("""
        <div class="empty-state">
            <div class="icon">🚀</div>
            <div class="title">No Drafts Ready</div>
            <div class="desc">Run a sync to generate AI reply drafts for your emails</div>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown('<div style="color:#64748b;font-size:0.88rem;margin-bottom:16px;">AI has drafted replies for each email. Edit and send with one click.</div>', unsafe_allow_html=True)
        for i, e in enumerate(st.session_state.email_data):
            if 'draft' in e:
                prio_icon = "🔴" if e.get('prio') == 'High' else "🔵"
                with st.expander(f"{prio_icon} {e['subject']}"):
                    sender_display = e['sender'].split('<')[0].strip().strip('"') or e['sender']
                    st.markdown(f'<div style="color:#64748b;font-size:0.82rem;margin-bottom:12px;">To: <span style="color:#94a3b8;">{sender_display}</span></div>', unsafe_allow_html=True)
                    reply_text = st.text_area("✏️ Edit AI Draft:", value=e['draft'], key=f"text_{i}", height=120)
                    col_send, col_info = st.columns([1, 2])
                    with col_send:
                        if st.button("🚀 Send Reply", key=f"btn_{i}"):
                            service = get_gmail_service()
                            if service and send_reply(service, e['sender'], e['subject'],
                                                      reply_text, e['threadId'], e['messageId']):
                                st.success("✅ Reply sent successfully!")
                                service.users().messages().batchModify(
                                    userId='me', body={'ids': [e['id']], 'removeLabelIds': ['UNREAD']}
                                ).execute()
                            else:
                                st.error("❌ Failed to send. Check Gmail permissions.")