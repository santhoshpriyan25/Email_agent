import os
import time
from dotenv import load_dotenv
from google import genai
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

# --- SECURITY SETUP ---
# This loads the variables from the .env file
load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# --- CONFIGURATION ---
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']

# Initialize the Client only if the key exists
if not GEMINI_API_KEY:
    print("❌ Error: GEMINI_API_KEY not found in .env file!")
    exit()

client = genai.Client(api_key=GEMINI_API_KEY, http_options={'api_version': 'v1'})

def get_gmail_service():
    """Handles Gmail OAuth2 authentication and token management."""
    creds = None
    # token.json stores the user's access and refresh tokens
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists('credentials.json'):
                print("❌ Error: credentials.json (from Google Cloud) is missing!")
                exit()
            flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        with open('token.json', 'w') as token:
            token.write(creds.to_json())
            
    return build('gmail', 'v1', credentials=creds)

def main():
    try:
        service = get_gmail_service()
        print("🔗 Connecting to Gmail...")
        
        # Fetch the 5 most recent unread emails
        results = service.users().messages().list(userId='me', q='is:unread', maxResults=5).execute()
        messages = results.get('messages', [])

        if not messages:
            print("✅ No unread emails found! Your inbox is clear.")
            return

        print(f"📧 Fetched {len(messages)} emails. Asking AI to summarize...")
        
        email_context = ""
        for message in messages:
            msg = service.users().messages().get(userId='me', id=message['id']).execute()
            headers = msg['payload'].get('headers', [])
            subject = next((h['value'] for h in headers if h['name'] == 'Subject'), "No Subject")
            sender = next((h['value'] for h in headers if h['name'] == 'From'), "Unknown Sender")
            snippet = msg.get('snippet', '')
            email_context += f"FROM: {sender}\nSUBJECT: {subject}\nCONTENT: {snippet}\n{'-'*30}\n"

        # --- AI GENERATION WITH RETRY LOGIC ---
        max_retries = 3
        for attempt in range(max_retries):
            try:
                # Using the stable gemini-2.5-flash model
                response = client.models.generate_content(
                    model="gemini-3.6-flash",
                    contents=(
                        f"You are a professional executive assistant. Summarize these unread emails "
                        f"into a clean daily digest. For each email, provide the sender, a 1-sentence "
                        f"summary, and a clear action item (if any).\n\nEmails:\n{email_context}"
                    )
                )
                
                print("\n" + "="*40)
                print("       ✨ YOUR AI EMAIL DIGEST ✨")
                print("="*40)
                print(response.text)
                print("="*40)
                break 

            except Exception as ai_err:
                if "429" in str(ai_err) and attempt < max_retries - 1:
                    print(f"🚦 AI is busy. Retrying in 15 seconds... (Attempt {attempt+1}/{max_retries})")
                    time.sleep(15)
                else:
                    raise ai_err

    except Exception as e:
        print(f"\n❌ Error: {e}")

if __name__ == "__main__":
    main()