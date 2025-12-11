# grok_ai.py
import requests
import os
import json
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

# --- UNIFIED DAILY BRIEFING GENERATOR ---
def generate_full_daily_briefing(user_name, festival_name, quote, author, history_events, weather_data):
    """
    Uses a single, powerful AI call to generate all components of the daily briefing,
    including a culturally-aware greeting.
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
        -   **Strict Rules:** If a festival_name is provided (e.g., "Raksha Bandhan"), you MUST generate a festive greeting for it. If festival_name is "None", you MUST generate a standard "Good Morning" greeting.
        -   Example (if festival is "Raksha Bandhan"): "Happy Raksha Bandhan, {user_name}!"
        -   Example (if festival is "None"): "☀️ Good Morning, {user_name}!"

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

    # We inject the current time so the AI can calculate "tomorrow", "next week", or "at 9pm" (relative to today)
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
         - If the user says "Every day at 9pm" but gives no start date, assume they mean **starting Today** (or Tomorrow if 9pm has passed).
         - Calculate the specific "YYYY-MM-DD HH:MM:SS" for the *first occurrence* based on the Current Date provided above.
         - Do not return a null timestamp.

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

    11. "general_query":
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
        "temperature": 0.1, # Low temperature for precision
        "response_format": {"type": "json_object"}
    }
    try:
        response = requests.post(GROK_URL, headers=GROK_HEADERS, json=payload, timeout=45)
        response.raise_for_status()
        result_text = response.json()["choices"][0]["message"]["content"]
        return json.loads(result_text)
    except Exception as e:
        print(f"Grok intent routing error: {e}")
        return {"intent": "general_query", "entities": {}}

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
    prompt = f"""You are an expert document analysis AI. Read the following text and determine its type and extract key information. Your response MUST be a JSON object with two keys: "doc_type" and "data". Possible "doc_type" values are: "resume", "project_plan", "meeting_invite", "q_and_a", "generic_document". The "data" key should be an empty object `{{}}` unless it's a "meeting_invite", in which case it should be `{{"task": "description of event", "timestamp": "YYYY-MM-DD HH:MM:SS"}}`. The current date is {datetime.now().strftime('%Y-%m-%d %A')}. Here is the text to analyze: --- {text[:4000]} --- Return only the JSON object."""
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
    prompt = f"""You are an AI assistant with a document's content loaded into your memory. A user is now asking a question about this document. Your task is to answer their question based *only* on the information provided in the document text. Here is the full text of the document: --- DOCUMENT START --- {document_text[:6000]} --- DOCUMENT END --- Here is the user's question: "{question}". Provide a direct and helpful answer. If the answer cannot be found in the document, say "I couldn't find the answer to that in the document." """
    payload = { "model": GROK_MODEL_SMART, "messages": [{"role": "user", "content": prompt}], "temperature": 0.3 }
    try:
        response = requests.post(GROK_URL, headers=GROK_HEADERS, json=payload, timeout=45)
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"].strip()
    except Exception as e:
        print(f"Grok contextual response error: {e}")
        return "Could not answer based on file."

def is_document_followup_question(text):
    # Simple keyword check to avoid expensive API calls for navigation commands
    if text.lower() in ["menu", "start", "hi", "hello", "1", "2", "3", "4", "5", "6", "0"]:
        return False
    # If not a simple command, ask AI to classify
    if not GROK_API_KEY: return True
    prompt = f"""A user has previously uploaded a document and is in a follow-up conversation. Their new message is: "{text}". Is this message a question or command related to the document (e.g., "summarize it", "what are the key points?")? Or is it a completely new, unrelated command? Respond with only the word "yes" if it is a follow-up, or "no" if it is a new command."""
    payload = { "model": GROK_MODEL_FAST, "messages": [{"role": "user", "content": prompt}], "temperature": 0.0, "max_tokens": 5 }
    try:
        response = requests.post(GROK_URL, headers=GROK_HEADERS, json=payload, timeout=10)
        response.raise_for_status()
        return "yes" in response.json()["choices"][0]["message"]["content"].strip().lower()
    except:
        return True
