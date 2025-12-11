# google_calendar_integration.py

import os
import json
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from datetime import timedelta

# --- CONFIGURATION ---
# SECURITY FIX: Load client secrets from environment variable instead of hardcoding
# You must set GOOGLE_CLIENT_SECRET_JSON in your .env file with the content of client_secret.json
CLIENT_SECRETS_JSON_STRING = os.environ.get("GOOGLE_CLIENT_SECRET_JSON")
REDIRECT_URI = os.environ.get("GOOGLE_REDIRECT_URI", "https://ai-buddy-bx6w.onrender.com/google-auth/callback")

SCOPES = [
    'https://www.googleapis.com/auth/calendar.events',
    'https://www.googleapis.com/auth/gmail.readonly',
    'https://www.googleapis.com/auth/gmail.send',
    'https://www.googleapis.com/auth/drive',
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/youtube.readonly',
    'https://www.googleapis.com/auth/userinfo.email'
]

def get_google_auth_flow():
    """Starts the Google OAuth 2.0 flow using secure credentials."""
    if not CLIENT_SECRETS_JSON_STRING:
        raise ValueError("❌ GOOGLE_CLIENT_SECRET_JSON environment variable is missing!")
    
    client_config = json.loads(CLIENT_SECRETS_JSON_STRING)
    
    flow = Flow.from_client_config(
        client_config,
        scopes=SCOPES,
        redirect_uri=REDIRECT_URI
    )
    return flow

def create_google_calendar_event(credentials, task, run_time, timezone='Asia/Kolkata'):
    """
    Creates an event on the user's primary Google Calendar and returns a link.
    """
    try:
        service = build('calendar', 'v3', credentials=credentials, cache_discovery=False)
        
        end_time = run_time + timedelta(minutes=30)

        event = {
            'summary': task,
            'description': f"Reminder set for {run_time.strftime('%I:%M %p')} via AI Buddy.",
            'start': {
                'dateTime': run_time.strftime('%Y-%m-%dT%H:%M:%S'),
                'timeZone': timezone,
            },
            'end': {
                'dateTime': end_time.strftime('%Y-%m-%dT%H:%M:%S'),
                'timeZone': timezone,
            },
            'reminders': {
                'useDefault': True,
            },
        }

        created_event = service.events().insert(calendarId='primary', body=event).execute()
        
        event_link = created_event.get('htmlLink')
        confirmation_message = f"🗓 Also added to your Google Calendar!"
        
        return confirmation_message, event_link

    except Exception as e:
        print(f"Google Calendar event creation error: {e}")
        return "❌ Failed to create Google Calendar event.", None
