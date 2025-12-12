# grok_ai.py
import requests
import os
import json
import mimetypes
import re  # Added for robust JSON parsing
from datetime import datetime, timedelta

# --- Configuration ---
GROK_API_KEY = os.environ.get("GROK_API_KEY")
GROK_URL = "https://api.groq.com/openai/v1/chat/completions"
# Using the smart model for better reasoning on dates/times
GROK_MODEL_SMART = "llama-3.3-70b-versatile"
GROK_MODEL_FAST = "llama-3.1-8b-instant"

GROK_HEADERS = {
    "Authorization": f"Bearer {GROK_API_KEY}",
    "Content-Type": "application/json"
}

# --- 1. VOICE INTELLIGENCE (TRANSCRIPTION) ---
def transcribe_audio(audio_file_path):
    """
    Transcribes an audio file using Groq's Whisper model (via API).
    Includes strict filename handling to prevent 400 Errors.
    """
    if not GROK_API_KEY:
        print("❌ Groq API Key missing.")
        return None

    # Verify file exists and is not empty
    if not os.path.exists(audio_file_path) or os.path.getsize(audio_file_path) == 0:
        print("❌ Audio file is missing or empty.")
        return None

    url = "https://api.groq.com/openai/v1/audio/transcriptions"
    
    headers = {
        "Authorization": f"Bearer {GROK_API_KEY}"
    }
    
    try:
        # Open file in binary mode
        with open(audio_file_path, "rb") as file:
            # 1. Determine MIME type (WhatsApp uses audio/ogg usually)
            mime_type, _ = mimetypes.guess_type(audio_file_path)
            if not mime_type:
                mime_type = "audio/ogg" 

            # 2. CRITICAL FIX: Groq rejects files without specific extensions.
            # We force the filename in the request to be 'audio.ogg' to satisfy the validator.
            # This does not rename the actual file on disk, just the label in the upload.
            api_filename = "voice_note.ogg" 
            if mime_type == "audio/mpeg":
                api_filename = "voice_note.mp3"
            elif mime_type == "audio/wav":
                api_filename = "voice_note.wav"

            files = {
                "file": (api_filename, file, mime_type)
            }
            
            # 3. Payload
            data = {
                "model": "whisper-large-v3", # or "distil-whisper-large-v3-en"
                "response_format": "json"
            }
            
            # 4. Send Request
            response = requests.post(url, headers=headers, files=files, data=data, timeout=60)
            
            # Check for errors
            if response.status_code != 200:
                print(f"⚠️ Groq API Error: {response.text}")
                return None
            
            return response.json().get("text")
            
    except Exception as e:
        print(f"❌ Audio transcription error: {e}")
        return None

# --- 2. INTERACTIVE EMAIL DRAFTER (UPDATED) ---
def draft_email_interactive(conversation_history, user_name="User", recipients="Unknown"):
    """
    Manages the conversational email drafting loop with context awareness.
    Returns either a text response (question/draft) or a JSON object (final send command).
    """
    if not GROK_API_KEY:
        return "❌ Groq API Key is missing."

    current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    system_prompt = f"""
    You are an expert AI Email Assistant. Current Time: {current_time}.
    
    CONTEXT:
    - **Sender Name:** {user_name} (You MUST sign off the email with this name).
    - **Recipient(s):** {recipients}.
    
    YOUR GOAL: Draft a professional email based on the user's input.
    
    RULES:
    1. **Clarify First**: If the user's request is short or vague (e.g., "mail for leave", "write to boss"), DO NOT draft yet. 
       - Ask clarifying questions: "What is the specific reason?", "Any dates?".
    2. **Draft & Refine**: Once you have sufficient details, generate a clear Subject and Body. 
       - Ensure the Body ends with "Best regards, {user_name}".
       - Show the draft to the user.
       - Ask: "Shall I send this, or do you want to make changes?"
    3. **Handle Scheduling**: Listen for commands like "Send it tomorrow at 10am".
    4. **FINAL OUTPUT**: ONLY when the user explicitly confirms to SEND (e.g., "Yes", "Send", "Confirm"), output a JSON object in this format (no other text):
    
    {{
      "action": "SEND_EMAIL",
      "recipient_email": "{recipients}",
      "subject": "Final Subject Line",
      "body": "Final Email Body Text",
      "scheduled_time": "YYYY-MM-DD HH:MM:SS" (or "NOW" if immediate)
    }}
    """

    # Prepare messages: System prompt first, then the conversation history
    messages = [{"role": "system", "content": system_prompt}] + conversation_history

    payload = {
        "model": GROK_MODEL_SMART,
        "messages": messages,
        "temperature": 0.6,
        "max_tokens": 1024
    }

    try:
        response = requests.post(GROK_URL, headers=GROK_HEADERS, json=payload, timeout=45)
        response.raise_for_status()
        content = response.json()["choices"][0]["message"]["content"]
        
        # --- ROBUST REGEX PARSING (FIXES THE JSON LEAK) ---
        # Search for any JSON block containing the action key
        json_match = re.search(r'\{[\s\S]*"action":\s*"SEND_EMAIL"[\s\S]*\}', content)
        
        if json_match:
            try:
                json_str = json_match.group(0)
                # Remove any markdown formatting if present
                json_str = json_str.replace("```json", "").replace("```", "").strip()
                return json.loads(json_str)
            except Exception as e:
                print(f"JSON Parse Error: {e}")
                # If parsing fails, just return the text so user sees something
                return content
        
        return content

    except Exception as e:
        print(f"Grok Email Error: {e}")
        return "⚠️ I'm having trouble connecting to the AI right now. Please try again later."


# --- UNIFIED DAILY BRIEFING GENERATOR ---
def generate_full_daily_briefing(user_name, festival_name, quote, author, history_events, weather_data):
    """
    Uses a single, powerful AI call to generate all components of the daily briefing.
    """
    if not GROK_API_KEY:
        return {
            "greeting": f"☀️ Good Morning, {user_name}!",
            "quote_explanation": "Have a great day!",
            "detailed_history": "No historical fact found for today.",
            "detailed_weather": "Weather data is currently unavailable."
        }

    history_texts = [event.get("text", "") for event in history_events]
    
    prompt = f"""
    You are an expert AI assistant with a deep understanding of Indian culture. Your persona is that of a helpful Indian friend creating an engaging daily briefing.
    Today's date is {datetime.now().strftime('%A, %B %d, %Y')}. The user's name is {user_name}.

    You must generate four distinct pieces of content based on the data provided below and return them in a single JSON object with the keys: "greeting", "quote_explanation", "detailed_history", and "detailed_weather".

    1.  **Greeting Generation:**
        -   Today's known festival is: "{festival_name if festival_name else 'None'}".
        -   Task: Create a cheerful morning greeting.
        -   **Strict Rules:** If a festival_name is provided, generate a festive greeting. If "None", generate a standard "Good Morning" greeting.

    2.  **Quote Analysis:**
        -   Quote: "{quote}" by {author}
        -   Task: Explain the meaning of this quote in one insightful sentence.

    3.  **Historical Event:**
        -   Events: {json.dumps(history_texts)}
        -   Task: Pick the most interesting event from the list and write an engaging 2-3 sentence summary about it.

    4.  **Weather Forecast:**
        -   Weather Data: {json.dumps(weather_data)}
        -   Task: Write a friendly, detailed weather forecast for Vijayawada. Mention temperature, conditions, and a helpful suggestion.

    Return only the JSON object.
    """

    payload = {
        "model": GROK_MODEL_SMART,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.7,
        "response_format": {"type": "json_object"}
    }
    try:
        response = requests.post(GROK_URL, headers=GROK_HEADERS, json=payload, timeout=45)
        response.raise_for_status()
        result_text = response.json()["choices"][0]["message"]["content"]
        return json.loads(result_text)
    except Exception as e:
        print(f"Grok unified briefing error: {e}")
        return {
            "greeting": f"☀️ Good Morning, {user_name}!",
            "quote_explanation": "Could not generate explanation.",
            "detailed_history": "Could not generate historical fact.",
            "detailed_weather": "Could not generate weather forecast."
        }


# --- PRIMARY INTENT ROUTER ---
def route_user_intent(text):
    if not GROK_API_KEY:
        return {"intent": "general_query", "entities": {}}

    # We inject the current time so the AI can calculate "tomorrow", "next week", or "at 9pm"
    current_time_str = datetime.now().strftime('%Y-%m-%d %A, %H:%M:%S')

    prompt = f"""
    You are an advanced AI intent router. Analyze the user's text and extract structured data.
    
    **Current Date & Time:** {current_time_str}

    **Possible Intents:**

    1. "schedule_meeting":
       - Keywords: schedule, meeting, book call, find time.
       - "entities": {{"attendees": ["names"], "topic": "string", "duration_minutes": int}}

    2. "set_reminder":
       - Keywords: remind me, set alarm, alert me.
       - "entities": An ARRAY of objects: [{{"task": "string", "timestamp": "YYYY-MM-DD HH:MM:SS", "recurrence": "string or null"}}]
       - **CRITICAL RULE FOR REMINDERS:** - The "timestamp" field is MANDATORY. 
         - If the user says "Every day at 9pm" but gives no start date, assume they mean **starting Today**.
         - Calculate the specific "YYYY-MM-DD HH:MM:SS".

    3. "get_reminders":
       - Keywords: show reminders, check reminders, what are my reminders.
       - "entities": {{}}

    4. "log_expense":
       - Keywords: spent, paid, cost, bought.
       - "entities": ARRAY of [{{"cost": number, "item": "string", "place": "string", "timestamp": "YYYY-MM-DD HH:MM:SS"}}]

    5. "convert_currency":
       - Keywords: convert, usd to inr, how much is.
       - "entities": ARRAY of [{{"amount": number, "from_currency": "code", "to_currency": "code"}}]

    6. "get_weather":
       - Keywords: weather, temperature, forecast.
       - "entities": {{"location": "city_name"}}

    7. "drive_search_file":
       - Keywords: find file, search drive, look for document.
       - "entities": {{"query": "string"}}

    8. "drive_upload_file":
       - Keywords: upload this, save to drive.
       - "entities": {{}}
    
    9. "drive_analyze_file":
       - Keywords: analyze file, summarize document from drive.
       - "entities": {{"filename": "string"}}

    10. "youtube_search":
       - Keywords: search youtube, find video.
       - "entities": {{"query": "string"}}

    11. "email_assistant":
       - Keywords: write email, send mail, draft letter, email to.
       - "entities": {{}}

    12. "get_bot_identity":
       - Keywords: who made you, who created you, who are you, bot owner.
       - "entities": {{}}

    13. "get_features":
       - Keywords: what can you do, show features, help, capabilities.
       - "entities": {{}}

    14. "train_tracking":
       - Keywords: pnr, train status, track train, check status.
       - "entities": {{"pnr": "10_digit_number_string"}}

    15. "general_query":
       - Default for conversational questions or unknowns.
       - "entities": {{}}

    ---
    User Input: "{text}"
    ---
    
    Return ONLY the JSON object with "intent" and "entities".
    """
    
    payload = {
        "model": GROK_MODEL_SMART,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.1, 
        "response_format": {"type": "json_object"}
    }
    try:
        response = requests.post(GROK_URL, headers=GROK_HEADERS, json=payload, timeout=45)
        response.raise_for_status()
        return json.loads(response.json()["choices"][0]["message"]["content"])
    except Exception as e:
        print(f"Grok intent routing error: {e}")
        return {"intent": "general_query", "entities": {}}

# --- WEATHER SUMMARY FUNCTION ---
def generate_weather_summary(weather_data, location):
    """
    Uses AI to create a conversational weather summary from raw API data.
    """
    if not GROK_API_KEY:
        temp = weather_data.get('main', {}).get('temp', 'N/A')
        return f"🌤️ The weather in {location} is currently {temp}°C."

    prompt = f"""
    You are a friendly and helpful weather reporter. 
    Data: {json.dumps(weather_data)}. 
    Task: Write a 2-sentence summary for {location}.
    """

    payload = {
        "model": GROK_MODEL_FAST, 
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.7
    }
    try:
        response = requests.post(GROK_URL, headers=GROK_HEADERS, json=payload, timeout=20)
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"].strip()
    except Exception as e:
        print(f"Grok weather summary error: {e}")
        return "⚠️ Sorry, I couldn't generate a detailed weather summary right now."

# --- OTHER AI FUNCTIONS ---

def ai_reply(prompt):
    if not GROK_API_KEY: return "❌ AI service unavailable."
    payload = { "model": GROK_MODEL_SMART, "messages": [{"role": "user", "content": prompt}], "temperature": 0.7 }
    try:
        res = requests.post(GROK_URL, headers=GROK_HEADERS, json=payload, timeout=20)
        res.raise_for_status()
        return res.json()["choices"][0]["message"]["content"].strip()
    except Exception as e:
        print(f"Grok AI error: {e}")
        return "⚠️ I'm having trouble thinking right now."

def analyze_document_context(text):
    if not GROK_API_KEY or not text: return None
    prompt = f"""You are an expert document analysis AI. Analyze this text: {text[:4000]}. Return JSON with keys: "doc_type" and "data"."""
    payload = { "model": GROK_MODEL_SMART, "messages": [{"role": "user", "content": prompt}], "temperature": 0.1, "response_format": {"type": "json_object"} }
    try:
        response = requests.post(GROK_URL, headers=GROK_HEADERS, json=payload, timeout=30)
        response.raise_for_status()
        return json.loads(response.json()["choices"][0]["message"]["content"])
    except Exception as e:
        print(f"Grok document analysis error: {e}")
        return None

def get_contextual_ai_response(document_text, question):
    if not GROK_API_KEY: return "AI key missing."
    prompt = f"""AI assistant here. Document: {document_text[:6000]}. Question: {question}. Answer based on doc."""
    payload = { "model": GROK_MODEL_SMART, "messages": [{"role": "user", "content": prompt}], "temperature": 0.3 }
    try:
        response = requests.post(GROK_URL, headers=GROK_HEADERS, json=payload, timeout=45)
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"].strip()
    except Exception as e:
        print(f"Grok contextual response error: {e}")
        return "Could not answer based on file."

def is_document_followup_question(text):
    if text.lower() in ["menu", "start", "hi", "hello", "1", "2", "3", "4", "5", "6", "0"]:
        return False
    if not GROK_API_KEY: return True
    prompt = f"""Is "{text}" a follow-up question to a previous document? Reply 'yes' or 'no'."""
    payload = { "model": GROK_MODEL_FAST, "messages": [{"role": "user", "content": prompt}], "temperature": 0.0, "max_tokens": 5 }
    try:
        response = requests.post(GROK_URL, headers=GROK_HEADERS, json=payload, timeout=10)
        response.raise_for_status()
        return "yes" in response.json()["choices"][0]["message"]["content"].strip().lower()
    except:
        return True
