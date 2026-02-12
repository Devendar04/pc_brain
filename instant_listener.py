
"""
VOSK instant listener wrapper.
Provides: listen_instant(timeout=8) -> str
Uses sounddevice raw stream and vosk.KaldiRecognizer.
"""

import os
import queue
import json
import time
import logging

import sounddevice as sd
from vosk import Model, KaldiRecognizer

logger = logging.getLogger(__name__)

# configuration via environment or defaults
MODEL_PATH = os.environ.get("VOSK_MODEL_PATH", os.path.join(os.path.dirname(__file__), "vosk-model"))
SAMPLE_RATE = 16000
_BLOCKSIZE = 2000

_audio_queue = queue.Queue(maxsize=15)
_model = None
_recognizer = None

def _ensure_model():
    global _model, _recognizer
    if _model is None:
        if not os.path.exists(MODEL_PATH):
            raise FileNotFoundError(f"VOSK model not found at {MODEL_PATH}")
        _model = Model(MODEL_PATH)
        _recognizer = KaldiRecognizer(_model, SAMPLE_RATE)
    return _recognizer

def _callback(indata, frames, time_info, status):
    try:
        # put raw bytes; if queue full, drop oldest to avoid blocking
        if _audio_queue.full():
            try:
                _audio_queue.get_nowait()
            except queue.Empty:
                pass
        _audio_queue.put(bytes(indata))
    except Exception as e:
        logger.debug("audio callback error: %s", e)

def listen_instant(timeout: float = 8.0) -> str:
    """
    Listen short bursts and return the first recognized text (lowercased).
    Returns "" if nothing recognized within timeout.
    """
    try:
        recognizer = _ensure_model()
    except Exception as e:
        logger.exception("VOSK model load failed")
        return ""

    recognizer.Reset()
    start = time.time()

    try:
        with sd.RawInputStream(samplerate=SAMPLE_RATE, blocksize=_BLOCKSIZE,
                               dtype="int16", channels=1, callback=_callback):
            while time.time() - start < timeout:
                try:
                    data = _audio_queue.get(timeout=0.4)
                except queue.Empty:
                    continue

                if recognizer.AcceptWaveform(data):
                    res = json.loads(recognizer.Result())
                    text = res.get("text", "").strip().lower()
                    if text:
                        return text
                else:
                    # partial result is available but often noisy; ignore for wake to avoid false triggers
                    pass
    except Exception as e:
        logger.exception("listen_instant stream error: %s", e)
        return ""

    return ""