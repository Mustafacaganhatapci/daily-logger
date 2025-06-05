
from flask import Flask, request
import openai
import requests
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import os
import base64
import json
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

# --- SESİ YAZIYA ÇEVİR ---
def transcribe_audio(audio_url):
    try:
        r = requests.get(audio_url)
        with open("temp.mp3", "wb") as f:
            f.write(r.content)
        with open("temp.mp3", "rb") as audio_file:
            transcript = openai.Audio.transcribe("whisper-1", audio_file)
        return transcript["text"]
    except Exception as e:
        print("Ses dönüştürme hatası:", e)
        raise

# --- TWILIO WEBHOOK ---
@app.route("/twilio-webhook", methods=["POST"])
def webhook():
    try:
        audio_url = request.form["RecordingUrl"] + ".mp3"
        yazi = transcribe_audio(audio_url)
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        sheet.append_row([now, yazi])
        return "OK", 200
    except Exception as e:
        print("Webhook hatası:", e)
        return "Hata", 500

# --- ARAMA TETİKLE ---
@app.route("/trigger-call", methods=["GET"])
def trigger_call():
    try:
        twilio_client.calls.create(
            to=KULLANICI_PHONE,
            from_=TWILIO_PHONE,
            url="https://daily-logger-ym66.onrender.com/twiml"
        )
        return "Arama başlatıldı", 200
    except Exception as e:
        print("Arama hatası:", e)
        return "Arama başlatılamadı", 500

# --- TWIML YANITI ---
@app.route("/twiml", methods=["POST", "GET"])
def twiml():
    return """
    <Response>
        <Say voice="max" language="tr-TR">Hi sir,How is your day going.</Say>
        <Record timeout="5" maxLength="60" finishOnKey="#" action="/twilio-webhook" method="POST" />
        <Say>End of the record bye.</Say>
    </Response>
    
    """, 200, {"Content-Type": "application/xml"}

# --- ANA SAYFA ---
@app.route("/", methods=["GET"])
def home():
    return "Daily Logger aktif", 200

# --- BAŞLAT ---
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)