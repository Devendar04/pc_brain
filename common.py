import uuid
import os
import asyncio
import edge_tts

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
AUDIO_DIR = os.path.join(BASE_DIR, "audio_responses")
os.makedirs(AUDIO_DIR, exist_ok=True)

VOICE = "hi-IN-SwaraNeural"

async def tts_to_file(text):
    fname = f"{uuid.uuid4().hex}.mp3"
    path = os.path.join(AUDIO_DIR, fname)

    communicate = edge_tts.Communicate(text, VOICE)
    await communicate.save(path)

    return fname
