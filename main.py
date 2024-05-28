from fastapi import FastAPI, UploadFile, Request
from fastapi.responses import JSONResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles  # Import StaticFiles
import os
from dotenv import load_dotenv
from openai import OpenAI
import json
import requests
import io
import base64

load_dotenv()

elevenlabs_key = os.getenv("ELEVENLABS_KEY")


app = FastAPI()

client = OpenAI()

client.api_key = os.getenv('OPENAI_API_KEY')


# Mount the static files directory
app.mount("/static", StaticFiles(directory="static"), name="static")

# Initialize Jinja2Templates with the templates directory
templates = Jinja2Templates(directory="templates")

# Route to serve the index.html file
@app.get("/")
async def read_index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.post('/talk')
async def post_audio(file: UploadFile):
    try:
        user_message = await transcribe_audio(file)
        chat_response = get_chat_response(user_message)
        audio_output = text_to_speech(chat_response)

        response_data = {
            "user_message": user_message,
            "bot_message": chat_response,
            "audio": base64.b64encode(audio_output).decode('utf-8')
        }

        return JSONResponse(content=response_data)
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)

async def transcribe_audio(file: UploadFile):
    audio_content = await file.read()  # Read the file content
    audio_file = io.BytesIO(audio_content)
    audio_file.name = file.filename  # Ensure filename is set
    transcript = client.audio.transcriptions.create(
        model="whisper-1", 
        file=audio_file
    )
    print(transcript)
    return transcript.text  # Extracting the text correctly from the transcription

def get_chat_response(user_message):
    messages = load_messages()
    messages.append({"role": "user", "content": user_message})
    gpt_response = client.chat.completions.create(
        model="gpt-4o",
        messages=messages
    )
    parsed_gpt_response = gpt_response.choices[0].message.content
    save_messages(user_message, parsed_gpt_response)
    return parsed_gpt_response

def load_messages():
    messages = []
    file = 'database.json'
    empty = os.stat(file).st_size == 0
    if not empty:
        with open(file) as db_file:
            data = json.load(db_file)
            for item in data:
                messages.append(item)
    else:
        messages.append(
            {"role": "system", "content": "You are Dilbert, the corporate comic character. You speak in the first person. Everything you say is in the first person and from the mind of Dilbert. You are always in character. Keep responses under 30 words and be funny sometimes"}
        )
    return messages

def save_messages(user_message, gpt_response):
    file = 'database.json'
    messages = load_messages()
    messages.append({"role": "user", "content": user_message})
    messages.append({"role": "assistant", "content": gpt_response})
    with open(file, 'w') as f:
        json.dump(messages, f)

def text_to_speech(text):
    voice_id = 'wPWbJ75Oys1Co4lQJ0Cb'
    body = {
        "text": text,
        "model_id": "eleven_turbo_v2",
        "voice_settings": {
            "stability": 0.5,
            "similarity_boost": 0.3,
            "style": 0.4,
            "use_speaker_boost": True
        }
    }

    headers = {
        "Content-Type": "application/json",
        "accept": "audio/mpeg",
        "xi-api-key": elevenlabs_key
    }

    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"

    try:
        response = requests.post(url, json=body, headers=headers)
        if response.status_code == 200:
            return response.content
        else:
            print('something went wrong')
    except Exception as e:
        print(e)
