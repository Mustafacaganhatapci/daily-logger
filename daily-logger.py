# Sistem: GPT destekli sesli kontrol ve loglama sistemi (tek dosyada)
# Gerekli modüller: Flask, Twilio, openai, pydub, gspread, oauth2client

from flask import Flask, request
import openai
import requests
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from pydub import AudioSegment
import os
from datetime import datetime

# Uygulama başlat
app = Flask(__name__)

# --- AYARLAR ---
openai.api_key = "OPENAI_API_KEY"
TWILIO_AUTH_TOKEN = "TWILIO_AUTH_TOKEN"
TWILIO_ACCOUNT_SID = "TWILIO_ACCOUNT_SID"
TWILIO_PHONE = "+1234567890"
KULLANICI_PHONE = "+90xxxxxxxxxx"

# Google Sheets Yetkilendirme
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_name("google-credentials.json", scope)
client = gspread.authorize(creds)
sheet = client.open("Günlük Log").sheet1

# --- SESİ YAZIYA ÇEVİR ---
def transcribe_audio(audio_url):
    r = requests.get(audio_url)
    with open("temp.wav", "wb") as f:
        f.write(r.content)

    sound = AudioSegment.from_file("temp.wav")
    sound.export("temp.mp3", format="mp3")

    with open("temp.mp3", "rb") as audio_file:
        transcript = openai.Audio.transcribe("whisper-1", audio_file)

    os.remove("temp.wav")
    os.remove("temp.mp3")
    return transcript["text"]

# --- CEVABI ANALİZ ET ---
def analyze_response(text):
    prompt = f"Cevap: \"{text}\"\nBu cevap çok kısa, belirsiz veya boşsa 'Evet' yaz. Değilse 'Hayır' yaz."
    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[{"role": "user", "content": prompt}]
    )
    return response["choices"][0]["message"]["content"].strip()

# --- SHEET'E YAZ ---
def write_to_sheet(text):
    sheet.append_row([datetime.now().strftime("%Y-%m-%d %H:%M"), text])

# --- TWILIO MESAJ GÖNDER ---
def send_followup_sms():
    requests.post(
        f"https://api.twilio.com/2010-04-01/Accounts/{TWILIO_ACCOUNT_SID}/Messages.json",
        auth=(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN),
        data={
            "From": TWILIO_PHONE,
            "To": KULLANICI_PHONE,
            "Body": "Biraz daha detay verir misin? Hangi konuda ne kadar çalıştın?"
        }
    )

# --- WEBHOOK ENDPOINT ---
@app.route("/twilio-webhook", methods=["POST"])
def handle_call():
    recording_url = request.form.get("RecordingUrl")
    if not recording_url:
        return "No audio found", 400

    metin = transcribe_audio(recording_url)
    write_to_sheet(metin)

    if analyze_response(metin).lower() == "evet":
        send_followup_sms()

    return "OK", 200

# --- UYGULAMA ÇALIŞTIR ---
if __name__ == "__main__":
    app.run(debug=True)