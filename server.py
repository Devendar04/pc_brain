from datetime import datetime
import json
import os
import threading
import asyncio
from flask import Flask, send_from_directory, request, jsonify
from werkzeug.exceptions import BadRequest
from concurrent.futures import TimeoutError as FuturesTimeoutError
import numpy as np
import cv2
from flask_cors import CORS
from face_engine import recognize_faces
from pc_event_queue import push
from server_logic import handle_text
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
AUDIO_DIR = os.path.join(BASE_DIR, "audio_responses")
os.makedirs(AUDIO_DIR, exist_ok=True)

app = Flask(__name__)
CORS(app)
CHAT_FILE = "chat_history.jsonl"


_loop = asyncio.new_event_loop()

def _start_loop(loop):
    asyncio.set_event_loop(loop)
    loop.run_forever()

threading.Thread(
    target=_start_loop,
    args=(_loop,),
    daemon=True
).start()

def save_chat(user_text: str, reply_text: str, intent: str):
    record = {
        "time": datetime.now().isoformat(),
        "user": user_text,
        "assistant": reply_text,
        "intent": intent
    }

    with open(CHAT_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")

@app.route("/recognize", methods=["POST"])
def recognize():
    if "image" not in request.files:
        return jsonify({"faces": []})

    img_bytes = request.files["image"].read()
    npimg = np.frombuffer(img_bytes, np.uint8)
    frame = cv2.imdecode(npimg, cv2.IMREAD_COLOR)

    if frame is None:
        return jsonify({"faces": []})

    faces = recognize_faces(frame)
    for name in faces:
        if name != "Unknown":
            push({"type": "face", "name": name})
            break

    return jsonify({"faces": faces})
@app.route("/text", methods=["POST"])
def text_api():
    if not request.is_json:
        return jsonify({"error": "Content-Type must be application/json"}), 400

    try:
        data = request.get_json(force=False, silent=False)
    except BadRequest:
        return jsonify({"error": "Invalid JSON payload"}), 400

    if not isinstance(data, dict) or "text" not in data:
        return jsonify({"error": "Missing 'text' field"}), 400

    user_text = data["text"]
    if not isinstance(user_text, str) or not user_text.strip():
        return jsonify({"error": "'text' must be a non-empty string"}), 400

    future = asyncio.run_coroutine_threadsafe(
        handle_text(user_text),
        _loop
    )
    try:
        result = future.result(timeout=30)
    except FuturesTimeoutError:
        future.cancel()
        return jsonify({"error": "Request timed out"}), 504
    except Exception:
        return jsonify({"error": "Failed to process text request"}), 500
    
    return jsonify(result)

@app.route("/audio/<path:fname>")
def serve_audio(fname):
    return send_from_directory(AUDIO_DIR, fname)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
