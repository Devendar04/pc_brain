# hybrid_intent.py

import re
from nlu_engine import nlu_pipeline
from llm_engine import call_llm_api

# -----------------------------
# Confidence Heuristics
# -----------------------------
# intent_registry.py

ALLOWED_INTENTS = {
    # college
    "DEPARTMENT_HOD",
    "PLACEMENTS",
    "COURSES",
    "CAMPUS",
    "COLLEGE_DIRECTOR",
    "COLLEGE_CHAIRMAN",

    # utility
    "TIME",

    # control
    "MOVEMENT",
    "SMALL_TALK",

    # fallback
    "GENERAL"
}

def _low_confidence(intent: str, state: str, text: str) -> bool:
    """
    When should we consult LLM?
    """
    if state == "CLARIFY":
        return True

    # long GENERAL queries are often misclassified
    if intent == "GENERAL" and len(text.split()) > 4:
        return True

    return False


# -----------------------------
# LLM Intent Picker (SAFE)
# -----------------------------

def _llm_pick_intent(text: str) -> str:
    """
    LLM is forced to choose ONE intent from whitelist.
    """
    prompt = (
        "You are an intent classifier.\n\n"
        f"Allowed intents:\n{', '.join(sorted(ALLOWED_INTENTS))}\n\n"
        "Rules:\n"
        "- Respond with ONLY ONE intent name\n"
        "- Do NOT explain\n"
        "- Do NOT invent new intents\n\n"
        f"User text: {text}\n\n"
        "Intent:"
    )

    try:
        raw = call_llm_api(prompt, lang="en")
        cleaned = re.sub(r"[^A-Z_]", "", raw.upper())
        if cleaned in ALLOWED_INTENTS:
            return cleaned
    except Exception:
        pass

    return "GENERAL"


# -----------------------------
# Public Resolver
# -----------------------------

def resolve_intent(text: str):
    """
    Returns:
      intent (str)
      slots (dict)
      source ("rule" | "llm")
    """

    # 1️⃣ Rule-based NLU
    intent, slots, state = nlu_pipeline(text)

    # 2️⃣ If confident → trust rules
    if not _low_confidence(intent, state, text):
        return intent, slots, "rule"

    # 3️⃣ LLM fallback (restricted)
    llm_intent = _llm_pick_intent(text)

    return llm_intent, slots, "llm"
