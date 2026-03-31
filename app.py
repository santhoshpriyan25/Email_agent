import streamlit as st
import os, time, base64, json
from email.mime.text import MIMEText
from dotenv import load_dotenv
from google import genai
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

# --- SETUP ---
load_dotenv()

# Securely fetch Gemini API Key
GEMINI_API_KEY = st.secrets.get("GEMINI_API_KEY") or os.getenv("GEMINI_API_KEY")

st.set_page_config(page_title="AI Command Center", page_icon="🛡️", layout="wide")

# --- PREMIUM UI CSS ---
st.markdown("""
    <style>
    .main { background: #0f172a; color: #f8fafc; }
    .stMetric { background: rgba(255,255,255,0.05); padding: 15px; border-radius: 12px; border: 1px solid #334155; }
    .email-card {
        background: rgba(255, 255, 255, 0.03);
        backdrop-filter: blur(10px);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 16px; padding: 25px; margin-bottom: 20px;
    }
    .priority-high { border-left: 5px solid #ef4444; }
    .priority-normal { border-left: 5px solid #3b82f6; }
    .action-chip { background: rgba(52, 211, 153, 0.1); color: #34d399; padding: 5px 12px; border-radius: 20px; font-size: 0.85rem; font-weight: 600; }
    .subject-header { font-weight: bold; font-size: 1.1rem; margin-bottom: 5px; }
    </style>
""", unsafe_allow_html=True)

# --- GMAIL & HELPER FUNCTIONS ---
def get_full_body(payload):
    body = ""
    if 'parts' in payload:
        for part in payload['parts']:
            if part['mimeType'] == 'text/plain':
                data = part['body'].get('data', '')
                if data: body += base64.urlsafe_b64decode(data).decode('utf-8')
            elif 'parts' in part: body += get_full_body(part)
    else:
        data = payload['body'].get('data', '')
        if data: body = base64.urlsafe_b64decode(data).decode('utf-8')
    return body

def send_reply(service, to_email, subject, body, thread_id, message_id):
    message = MIMEText(body)
    if not subject.lower().startswith("re:"):
        subject = f"Re: {subject}"
    message['to'] = to_email
    message['subject'] = subject
    message['In-Reply-To'] = message_id
    message['References'] = message_id
    raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
    try:
        service.users().messages().send(userId='me', body={'raw': raw, 'threadId': thread_id}).execute()
        return True
    except Exception:
        return False

def get_gmail_service():
    SCOPES = [
        'https://www.googleapis.com/auth/gmail.modify', 
        'https://www.googleapis.com/auth/gmail.send'
    ]
    creds = None
    
    if 'google_creds' in st.session_state:
        creds = st.session_state.google_creds

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            # --- OPTION 2: LOAD FROM STREAMLIT SECRETS ---
            try:
                # This reads the JSON dictionary you will paste into Streamlit Settings
                google_config = json.loads(st.secrets["GOOGLE_CREDENTIALS"])
                flow = InstalledAppFlow.from_client_config(google_config, SCOPES)
                creds = flow.run_local_server(port=0)
            except Exception as e:
                st.error("Credential Error: Please check your Streamlit Secrets.")
                return None
            
        st.session_state.google_creds = creds
            
    return build('gmail', 'v1', credentials=creds)

# --- APP INITIALIZATION ---
if 'email_data' not in st.session_state:
    st.session_state.email_data = []

with st.sidebar:
    st.title("🛡️ AI Controls")
    email_limit = st.slider("Messages to Analyze", 1, 15, 5)
    if st.button("🗑️ Reset Connection"):
        if 'google_creds' in st.session_state:
            del st.session_state.google_creds
        if os.path.exists('token.json'): 
            os.remove('token.json')
        st.rerun()

st.title("🧠 Intelligence Command Center")
tab1, tab2, tab3 = st.tabs(["📊 Analytics", "📬 Smart Digest", "🚀 Instant Reply"])

# --- MAIN SYNC LOGIC ---
if st.button("⚡ Run Full System Sync", use_container_width=True):
    if not GEMINI_API_KEY:
        st.error("Missing Gemini API Key. Please add it to your Secrets.")
    else:
        try:
            service = get_gmail_service()
            if service:
                client = genai.Client(api_key=GEMINI_API_KEY, http_options={'api_version': 'v1'})
                
                with st.status("Gathering Intelligence...", expanded=True) as status:
                    results = service.users().messages().list(userId='me', q='is:unread', maxResults=email_limit).execute()
                    messages = results.get('messages', [])
                    
                    if not messages:
                        st.success("Inbox is clear!")
                        st.session_state.email_data = []
                    else:
                        processed = []
                        context = ""
                        for m in messages:
                            msg = service.users().messages().get(userId='me', id=m['id']).execute()
                            body = get_full_body(msg['payload'])
                            headers = msg['payload']['headers']
                            subject = next((h['value'] for h in headers if h['name'] == 'Subject'), "No Subject")
                            sender = next((h['value'] for h in headers if h['name'] == 'From'), "Unknown")
                            msg_id = next((h['value'] for h in headers if h['name'] == 'Message-ID'), "")
                            
                            context += f"ID:{m['id']}\nFROM:{sender}\nSUBJ:{subject}\nBODY:{body[:800]}\n---\n"
                            processed.append({"id": m['id'], "threadId": m['threadId'], "messageId": msg_id, "sender": sender, "subject": subject})
                        
                        try:
                            ai_resp = client.models.generate_content(
                                model="gemini-2.0-flash", # Note: Changed to 2.0-flash as it's the current stable high-speed model
                                contents=f"Format each: PRIORITY: [High/Normal] | SUMMARY: [1 sentence] | ACTION: [1 step] | DRAFT: [2 sentence reply] | SPLIT\n\n{context}"
                            )
                            
                            entries = ai_resp.text.split("SPLIT")
                            for i, entry in enumerate(entries):
                                if i < len(processed) and "PRIORITY:" in entry:
                                    parts = entry.strip().split('|')
                                    processed[i].update({
                                        "prio": parts[0].replace("PRIORITY:","").strip(),
                                        "summary": parts[1].replace("SUMMARY:","").strip(),
                                        "action": parts[2].replace("ACTION:","").strip(),
                                        "draft": parts[3].replace("DRAFT:","").strip(),
                                    })
                            st.session_state.email_data = processed
                            status.update(label="Sync Complete!", state="complete")
                        
                        except Exception as ai_err:
                            if "429" in str(ai_err):
                                st.warning("⏱️ **AI Overload:** Free-tier limit reached. Wait 60s.")
                            else:
                                st.error(f"AI Error: {ai_err}")
                            status.update(label="Sync Paused", state="error")

        except Exception as e:
            st.error(f"System Connection Error: {e}")

# --- RENDER TABS ---
with tab1:
    if st.session_state.email_data:
        c1, c2 = st.columns(2)
        c1.metric("Unread Analyzed", len(st.session_state.email_data))
        c2.metric("Urgent Tasks", len([e for e in st.session_state.email_data if e.get('prio') == "High"]))
    else: st.info("Ready for sync.")

with tab2:
    for e in st.session_state.email_data:
        if 'prio' in e:
            p_class = "priority-high" if e['prio'] == "High" else "priority-normal"
            st.markdown(f'<div class="email-card {p_class}"><div style="color:#94a3b8;">{e["sender"]}</div><div class="subject-header">{e["subject"]}</div><div>{e["summary"]}</div><div class="action-chip">🎯 {e["action"]}</div></div>', unsafe_allow_html=True)

with tab3:
    for i, e in enumerate(st.session_state.email_data):
        if 'draft' in e:
            with st.expander(f"📩 Reply to: {e['subject']}"):
                reply_text = st.text_area("Edit AI Draft:", value=e['draft'], key=f"text_{i}", height=120)
                if st.button(f"🚀 Send Reply", key=f"btn_{i}"):
                    service = get_gmail_service()
                    if send_reply(service, e['sender'], e['subject'], reply_text, e['threadId'], e['messageId']):
                        st.success("Sent!")
                        service.users().messages().batchModify(userId='me', body={'ids': [e['id']], 'removeLabelIds': ['UNREAD']}).execute()
                    else:
                        st.error("Failed to send. Check permissions.")