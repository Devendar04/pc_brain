# desi_brain.py (v2.1 – Respect Enforced)

import re
import random
import datetime
from collections import defaultdict

# ---------------------------
# HARD RESPECT FILTER
# ---------------------------

FORBIDDEN_WORDS = {
    "beta", "bhai", "bro", "yaar", "dost",
    "dear", "boss", "buddy", "mate"
}

def enforce_respect(text: str) -> str:
    words = text.split()
    clean = [w for w in words if w.lower() not in FORBIDDEN_WORDS]
    return " ".join(clean)


# ---------------------------
# NORMALIZATION
# ---------------------------

HINGLISH_MAP = {
    "kya": "what",
    "kaun": "who",
    "kaise": "how",
    "kyu": "why",
    "kab": "when",
    "haan": "yes",
    "nahi": "no",
    "namaste": "hello",
    "shukriya": "thanks"
}

def normalize(text: str) -> str:
    t = text.lower().strip()
    for k, v in HINGLISH_MAP.items():
        t = re.sub(rf"\b{k}\b", v, t)
    t = re.sub(r"[^\w\s]", " ", t)
    t = re.sub(r"\s+", " ", t)
    return t


# ---------------------------
# CONTEXT (SHORT MEMORY)
# ---------------------------

_CONTEXT = defaultdict(str)

def set_ctx(key, value):
    _CONTEXT[key] = value

def get_ctx(key):
    return _CONTEXT.get(key)


# ---------------------------
# INTENTS (RESPECTFUL ONLY)
# ---------------------------

INTENTS = [
    {
        "name": "greeting",
        "patterns": ["hello", "hi", "hey", "namaste"],
        "replies": [
            "नमस्कार। कृपया बताइए, मैं आपकी किस प्रकार सहायता कर सकती हूँ?",
            "नमस्ते। मैं आपकी सहायता के लिए उपलब्ध हूँ।",
            "नमस्कार। आप क्या जानना चाहते हैं?"
        ]
    },
    {
        "name": "how_are_you",
        "patterns": ["how are you", "kya haal", "kya scene"],
        "replies": [
            "धन्यवाद। मैं ठीक हूँ। कृपया बताइए, मैं आपकी कैसे सहायता कर सकती हूँ?",
            "सब ठीक है। आप अपना प्रश्न बताइए।"
        ]
    },
    {
        "name": "who_are_you",
        "patterns": ["who are you", "tum kaun", "aap kaun"],
        "replies": [
            "मैं सारा हूँ, एक डिजिटल सहायक, जो आपकी सहायता के लिए बनाई गई है।",
            "मैं आपकी जानकारी और सहायता के लिए उपलब्ध एक एआई सहायक हूँ।"
        ]
    },
    {
        "name": "thanks",
        "patterns": ["thanks", "thank you", "shukriya"],
        "replies": [
            "आपका धन्यवाद। यदि कोई और प्रश्न हो, तो कृपया बताइए।",
            "धन्यवाद। आपकी सहायता करना मेरा उद्देश्य है।"
        ]
    },
    {
        "name": "time",
        "patterns": ["time", "samay", "kitna baje"],
        "dynamic": "time"
    },
    {
        "name": "date",
        "patterns": ["date", "aaj ka din"],
        "dynamic": "date"
    },
    {
        "name": "abuse",
        "patterns": ["stupid", "idiot", "chutiya", "bewakoof"],
        "replies": [
            "कृपया सम्मानजनक भाषा का प्रयोग करें।",
            "आइए शांति और सम्मान के साथ बातचीत करें।"
        ]
    },
    {
        "name": "joke",
        "patterns": ["joke", "mazaak", "hasao"],
        "replies": [
            "एक हल्का सा हास्य: शिक्षक पूछते हैं – देर से क्यों आए? उत्तर मिला – सर, समय प्रबंधन सीख रहा था।",
            "कभी-कभी मुस्कान भी ऊर्जा देती है।"
        ]
    },
    {
        "name": "motivation",
        "patterns": ["motivate", "himmat", "confidence"],
        "replies": [
            "आपमें क्षमता है। निरंतर प्रयास करते रहिए।",
            "धैर्य और अनुशासन सफलता की कुंजी हैं।"
        ]
    }
]

# ---------------------------
# SCORING
# ---------------------------

def score_intent(text: str, intent) -> int:
    score = 0
    for p in intent["patterns"]:
        if re.search(rf"\b{re.escape(p)}\b", text):
            score += 2
    return score


# ---------------------------
# DYNAMIC REPLIES
# ---------------------------

def dynamic_reply(kind: str) -> str:
    now = datetime.datetime.now()
    if kind == "time":
        return f"वर्तमान समय {now.strftime('%I:%M %p')} है।"
    if kind == "date":
        return f"आज की तिथि {now.strftime('%d %B %Y')} है।"
    return ""


# ---------------------------
# MAIN ENTRY
# ---------------------------

def desi_brain(text: str) -> str | None:
    if not text:
        return None

    t = normalize(text)

    best_intent = None
    best_score = 0

    for intent in INTENTS:
        s = score_intent(t, intent)
        if s > best_score:
            best_score = s
            best_intent = intent

    if not best_intent or best_score == 0:
        return None

    if "dynamic" in best_intent:
        return enforce_respect(dynamic_reply(best_intent["dynamic"]))

    reply = random.choice(best_intent["replies"])
    return enforce_respect(reply)
