from flask import Flask, request
import openai
import requests
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from pydub import AudioSegment
import os
import base64
import json
import time
from datetime import datetime
from dotenv import load_dotenv
from twilio.rest import Client as TwilioClient

load_dotenv()

# --- API KEYLER ---
openai.api_key = os.getenv("OPENAI_API_KEY")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_PHONE = os.getenv("TWILIO_PHONE")
KULLANICI_PHONE = os.getenv("KULLANICI_PHONE")

# --- GOOGLE SHEET ---
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds_json = base64.b64decode(os.getenv("GOOGLE_CREDENTIALS_B64")).decode("utf-8")
creds_dict = json.loads(creds_json)
creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
client = gspread.authorize(creds)
sheet = client.open("Gunluk_takip").sheet1

# --- TWILIO ---
twilio_client = TwilioClient(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)

# --- APP ---
app = Flask(__name__)

def transcribe_audio(audio_url):
    for _ in range(3):
        r = requests.get(audio_url)
        if r.ok and len(r.content) > 1000:
            break
        time.sleep(2)
    with open("temp.wav", "wb") as f:
        f.write(r.content)

    sound = AudioSegment.from_file("temp.wav")
    sound.export("temp.mp3", format="mp3")

    with open("temp.mp3", "rb") as audio_file:
        transcript = openai.Audio.transcribe("whisper-1", audio_file)
    return transcript["text"]

@app.route("/twilio-webhook", methods=["POST"])
def webhook():
    audio_url = request.form["RecordingUrl"] + ".wav"
    yazi = transcribe_audio(audio_url)
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    sheet.append_row([now, yazi])
    return "OK", 200

@app.route("/trigger-call", methods=["GET"])
def trigger_call():
    twilio_client.calls.create(
        to=KULLANICI_PHONE,
        from_=TWILIO_PHONE,
        url="https://daily-logger-ym66.onrender.com/twiml"
    )
    return "Arama başlatıldı", 200

@app.route("/twiml", methods=["POST", "GET"])
def twiml():
    return """
    <Response>
        <Say voice="alice" language="tr-TR">Günlük notlarınızı konuşabilirsiniz. Kayıt başladı.</Say>
        <Record timeout="5" maxLength="60" action="/twilio-webhook" method="POST" />
        <Say>Kayıt sona erdi. Güle güle.</Say>
    </Response>
    """, 200, {"Content-Type": "application/xml"}

@app.route("/", methods=["GET"])
def home():
    return "Daily Logger aktif", 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)