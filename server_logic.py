# server_logic.py

import logging
from datetime import datetime

from desi_brain import desi_brain
from hybrid_intent import resolve_intent
from llm_engine import call_llm_api, save_chat
#from util import hinglish_to_hindi_global

try:
    from rag_query_ollama import query_rag
except Exception:
    query_rag = None

logger = logging.getLogger(__name__)

# -----------------------------
# Movement Safety (HARD RULE)
# -----------------------------

MOVEMENT_KEYWORDS = {
    "aage", "peeche", "baaye", "daaye",
    "forward", "backward", "left", "right", "move", "chal"
}

# -----------------------------
# MAIN BRAIN
# -----------------------------

async def handle_text(text: str, lang: str = "hinglish") -> dict:
    text = (text or "").strip()
    t = text.lower()

    print("🔥 handle_text:", text)

    # 0️⃣ Movement safety (NO LLM)
    if any(w in t for w in MOVEMENT_KEYWORDS):
        return {
            "reply": 
                "Please provide complete movement command. Example: aage jao."
            ,
            "intent": {"name": "MOVEMENT", "state": "CLARIFY"}
        }

    # 1️⃣ Desi Brain (small talk)
    try:
        desi_reply = desi_brain(text)
        if desi_reply:
            return {
                "reply": desi_reply,
                "intent": {"name": "SMALL_TALK", "state": "OK"}
            }
    except Exception:
        logger.exception("desi_brain failed")

    # 2️⃣ HYBRID INTENT RESOLUTION
    intent, slots, source = resolve_intent(text)
    print(f"🧠 Intent={intent} via {source}")

    # 3️⃣ TIME
    if intent == "TIME":
        now = datetime.now().strftime("%I:%M %p")
        return {
            "reply": f"Current time {now} hai",
            "intent": {"name": "TIME", "state": "OK"}
        }

    # 4️⃣ COLLEGE INTENTS → RAG ONLY
    if intent in {
        "DEPARTMENT_HOD",
        "PLACEMENTS",
        "COURSES",
        "CAMPUS",
        "COLLEGE_DIRECTOR",
        "COLLEGE_CHAIRMAN"
    }:
        if not query_rag:
            reply = "College information system is not available."
        else:
            try:
                reply = query_rag(text) or "Information not available in the college document."
            except Exception:
                logger.exception("RAG failed")
                reply = "Information not available in the college document."

        reply = reply
        save_chat(text, reply, lang)

        return {
            "reply": reply,
            "intent": {
                "name": intent,
                "state": "OK",
                "source": source,
                "slots": slots
            }
        }

    # 5️⃣ GENERAL → LLM
    try:
        reply = call_llm_api(text, lang)
    except Exception:
        logger.exception("LLM failed")
        reply = "Technical issue aa gaya hai. Please try again."

    reply = reply
    save_chat(text, reply, lang)

    return {
        "reply": reply,
        "intent": {
            "name": "GENERAL",
            "state": "OK",
            "source": source
        }
    }
