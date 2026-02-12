import os, time, json, logging, requests
from dotenv import load_dotenv

logger = logging.getLogger(__name__)
CHAT_FILE = os.path.join(os.path.dirname(__file__), "chat_history.json")
def sanitize_reply(text):
    banned = ["bhai", "beta", "yaar", "dost", "bro", "dear"]
    for w in banned:
        text = text.replace(w, "")
    return text

def load_chat():
    try:
        if not os.path.exists(CHAT_FILE):
            return []

        with open(CHAT_FILE, "r", encoding="utf-8") as f:
            content = f.read().strip()
            if not content:
                return []
            data = json.loads(content)
            if isinstance(data, list):
                return data
            return []
    except Exception:
        logger.exception("load_chat failed")
        return []


def save_chat(user_text, bot_text, lang="hinglish"):
    try:
        history = load_chat()

        history.append({
            "time": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "language": lang,
            "user": user_text,
            "assistant": bot_text
        })

        # keep last N messages only
        history = history[-200:]

        with open(CHAT_FILE, "w", encoding="utf-8") as f:
            json.dump(history, f, ensure_ascii=False, indent=2)

    except Exception:
        logger.exception("save_chat failed")

def build_chat_context(user_text, lang, limit=6):
    messages = []

    try:
        history = load_chat()
        if not isinstance(history, list):
            history = []
    except Exception:
        history = []

    # keep only last N exchanges
    for h in history[-limit:]:
        if "user" in h:
            messages.append({
                "role": "user",
                "content": h.get("user", "")
            })
        if "assistant" in h:
            messages.append({
                "role": "assistant",
                "content": h.get("assistant", "")
            })

    # current user message
    messages.append({
        "role": "user",
        "content": user_text
    })

    return messages   # ✅ CRITICAL


def call_llm_api(user_text, lang="hinglish"):
    """
    Uses GROQ_API_KEY from env or .env and Groq chat endpoint.
    Mirrors your earlier call_llm_api implementation.
    """
    load_dotenv()
    API_KEY = os.getenv("GROQ_API_KEY")
    if not API_KEY:
        logger.warning("GROQ_API_KEY not set")
        return "Sorry yaar, server side thoda issue aa gaya hai 😕"

    if lang and lang.lower() in ["hi", "hindi"]:
        lang_prompt = ("Reply ONLY in simple, natural Hindi. Use easy everyday language. No complex Sanskrit words.")
    elif lang and lang.lower() in ["hinglish", "en-in"]:
        lang_prompt = ("Reply ONLY in natural Indian Hinglish (mix of simple Hindi + English). Keep it short & friendly.")
    else:
        lang_prompt = "Reply clearly, naturally and briefly in simple English."

    system_prompt = (
        "You are a friendly Indian voice assistant. Always talk like a real human. Short emotional friendly replies.\n"
        f"{lang_prompt}"
    )

    ctx = build_chat_context(user_text, lang)
    if not isinstance(ctx, list):
        ctx = [{"role": "user", "content": user_text}]

    payload = {
        "model": "llama-3.1-8b-instant",
        "temperature": 0.35,
        "max_tokens": 450,
        "messages": [
            {"role": "system", "content": system_prompt},
            *ctx
        ]
    }


    try:
        r = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {API_KEY}",
                "Content-Type": "application/json"
            },
            json=payload,
            timeout=30
        )
        r.raise_for_status()
        j = r.json()
        reply = sanitize_reply(
        j["choices"][0]["message"]["content"].strip()
    )

        
        return reply
    except Exception as e:
        logger.exception("LLM call failed")
        return "Sorry yaar, server side thoda issue aa gaya hai 😕"